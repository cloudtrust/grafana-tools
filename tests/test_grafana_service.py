#!/usr/bin/env python

"""Test of the grafana-service container.

"""

__author__ = 'Jean-Luc Beuchat'
__email__ = 'jean-luc.beuchat@elca.ch'
__copyright__ = 'Copyright 2018, ELCA'

import logging
import pytest
import requests
import urllib.parse
import uuid

from http import HTTPStatus
from typing import Tuple

logging.basicConfig(
    format='%(asctime)s %'
           '(name)s %(levelname)s %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@pytest.mark.usefixtures('default_credentials', 'host', 'port')
class TestServiceGrafana:

    @pytest.mark.parametrize('get_method', ['/api/admin/settings', '/api/admin/stats'])
    def test_admin_api_wo_credentials(self, get_method, host: str, port: str) -> None:
        base = 'http://{host}:{port}'.format(host=host, port=port)
        url = urllib.parse.urljoin(base, get_method)
        response = requests.get(url)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    @pytest.mark.parametrize('get_method', ['/api/admin/settings', '/api/admin/stats'])
    def test_admin_api(self, get_method, default_credentials: Tuple[str, str], host: str, port: str) -> None:
        username, password = default_credentials
        base = 'http://{user}:{password}@{host}:{port}'.format(user=username, password=password, host=host, port=port)
        url = urllib.parse.urljoin(base, get_method)
        response = requests.get(url)
        assert response.status_code == HTTPStatus.OK

    def test_data_source_api(self, default_credentials: Tuple[str, str], host: str, port: str) -> None:
        """

        Test data from http://docs.grafana.org/http_api/data_source
        :param default_credentials:
        :param host:
        :param port:
        :return:
        """
        username, password = default_credentials
        base = 'http://{user}:{password}@{host}:{port}'.format(user=username, password=password, host=host, port=port)
        url = urllib.parse.urljoin(base, '/api/datasources')
        name = str(uuid.uuid4())
        data = {'name': name,
                'type': 'graphite',
                'url': 'http://mydatasource.com',
                'access': 'proxy',
                'basicAuth': False}
        response = requests.post(url, json=data)
        assert response.status_code == HTTPStatus.OK
        datasource_id = response.json().get('id')
        assert id, 'undefined id'
        logger.info('Data source created with id {id}'.format(id=datasource_id))
        logger.debug(response.text)

        data = {'id': datasource_id,
                'orgId': datasource_id,
                'name': name,
                'type': 'graphite',
                'access': 'proxy',
                'url': 'http://mydatasource.com',
                'password': '',
                'user': '',
                'database': '',
                'basicAuth': True,
                'basicAuthUser': 'basicuser',
                'basicAuthPassword': 'basicuser',
                'isDefault': False,
                'jsonData': None}
        url = urllib.parse.urljoin(base, '/api/datasources/{}'.format(datasource_id))
        response = requests.put(url, json=data)
        assert response.status_code == HTTPStatus.OK
        logger.info('Data source {id} updated'.format(id=datasource_id))
        logger.debug(response.text)

        response = requests.delete(url)
        assert response.status_code == HTTPStatus.OK
        logger.info('Data source {id} deleted'.format(id=datasource_id))
        logger.debug(response.text)

