#!/usr/bin/env python

import argparse
import logging
import requests
import sys
import urllib.parse

from http import HTTPStatus

VERSION = '1.0'

logging.basicConfig(
    format='%(asctime)s %'
           '(name)s %(levelname)s %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p'
)


def main():
    prog_name = sys.argv[0]
    usage = """{} [options]
    """.format(prog_name)
    parser = argparse.ArgumentParser(prog="{pn} {v}".format(pn=prog_name, v=VERSION), usage=usage)
    parser.add_argument('--debug', type=bool, default=False, dest='debug', help='Enable debug')
    parser.add_argument('--host', type=str, default='127.0.0.1', dest='host',
                        help='IP/hostname of the Grafana container, defaults to 127.0.0.1')
    parser.add_argument('--newpassword', type=str, dest='newpassword', required=True,
                        metavar='pwd', help='New password')
    parser.add_argument('--password', type=str, dest='password', required=True, metavar='pwd', help='Current password')
    parser.add_argument('--port', type=int, default=80, dest='port', help='Connection port, defaults to 80')
    args = parser.parse_args()

    debug = args.debug
    host = args.host
    newpassword = args.newpassword
    password = args.password
    port = args.port

    logger = logging.getLogger('grafana_tools.reset_admin_password')
    if debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('grafana_tools.reset_admin_password').setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
        logging.getLogger('grafana_tools.reset_admin_password').setLevel(logging.INFO)

    base = 'http://admin:{password}@{host}:{port}'.format(password=password, host=host, port=port)
    url = urllib.parse.urljoin(base, '/api/user/password')
    data = {'oldPassword': password,
            'newPassword': newpassword,
            'confirmNew': newpassword}
    try:
        response = requests.put(url, json=data)
    except requests.exceptions.ConnectionError as e:
        logger.error('Failed to establish a new connection ({host})'.format(host=base))
        logger.debug(e)
        sys.exit(1)

    if response.status_code == HTTPStatus.OK:
        logger.info('Grafana admin password has been updated')
        sys.exit(0)

    logger.error('Grafana admin password has not been updated')
    logger.info(response.text)
    sys.exit(1)


if __name__ == "__main__":
    if sys.version_info >= (3, 5):
        main()
    else:
        print('Requires Python >= 3.5')
        sys.exit(1)
