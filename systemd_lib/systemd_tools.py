#!/usr/bin/env python

__author__ = 'Jean-Luc Beuchat'
__email__ = 'jean-luc.beuchat@elca.ch'
__copyright__ = 'Copyright 2018, ELCA'


import datetime
import sh
import time

from typing import Tuple


class Systemd:
    """
    Tools to check the status of services running inside a container
    """

    @staticmethod
    def _get_systemd_property(container_name: str, systemd_service: str, busctl_property: str) -> str:
        # Replace non-alphanumeric characters in systemd_service by their hexadecimal equivalents.
        # Example: 'grafana-server.service' becomes 'grafana_2dserver_2eservice'
        systemd_service_alnum = ''.join([char if char.isalnum() else
                                         '_{h}'.format(h=format(ord(char), 'x')) for char in systemd_service])

        busctl_command = 'get-property'
        busctl_service = 'org.freedesktop.systemd1'
        busctl_object = '/org/freedesktop/systemd1/unit/{service}'.format(service=systemd_service_alnum)
        busctl_interface = 'org.freedesktop.systemd1.Unit'
        docker_cmd = sh.docker.bake('exec', container_name, 'busctl', busctl_command, busctl_service, busctl_object,
                                    busctl_interface, busctl_property)
        return docker_cmd().stdout.decode('utf-8')

    @staticmethod
    def is_service_running(container_name: str, systemd_service: str) -> bool:
        """
        Checks if service *systemd_service" is running
        :param container_name:
        :param systemd_service:
        :return: True if *systemd_service* is running, False otherwise
        """
        busctl_property = 'ActiveState'
        current_state: str = Systemd._get_systemd_property(container_name, systemd_service, busctl_property)
        expected_state: str = '"active"'
        return expected_state in current_state

    @staticmethod
    def get_active_enter_timestamp(container_name: str, systemd_service: str) -> Tuple[str, float]:
        busctl_property: str = 'ActiveEnterTimestamp'
        active_enter_timestamp: str = Systemd._get_systemd_property(container_name, systemd_service, busctl_property)
        # active_enter_timestamp contains a string s.t. 't 1526305170850190'. Let's get the timestamp and convert it
        # to something compatible with datetime:
        try:
            timestamp: float = float(active_enter_timestamp.split()[1])/1000000.0
        except (IndexError, ValueError):
            raise
        else:
            return datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S'), \
                   timestamp

    @staticmethod
    def wait_until_service_is_restarted(container_name: str, systemd_service: str, timeout: int) -> None:
        counter = 0
        while True:
            time.sleep(1)
            counter = counter + 1
            if Systemd.is_service_running(container_name, systemd_service):
                return
            if counter > timeout:
                raise TimeoutError

    @staticmethod
    def systemctl(container_name: str, command: str, systemd_service: str) -> None:
        """
        Runs systemctl *command* *systemd_service*
        :param container_name:
        :param command:
        :param systemd_service:
        :return:
        """
        docker_cmd = sh.docker.bake('exec', container_name, 'systemctl', command, systemd_service)
        docker_cmd()

    @staticmethod
    def list_errors_not_older_than(container_name: str, systemd_service: str, date: str) -> str:
        container = sh.docker.bake('exec', container_name)
        errors = container.journalctl('-u', systemd_service, '--since', date, '-p', 'err', '-b').stdout.decode('utf-8')
        return errors
