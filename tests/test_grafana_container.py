#!/usr/bin/env python

"""Test of the grafana-service container.

"""

__author__ = 'Jean-Luc Beuchat'
__email__ = 'jean-luc.beuchat@elca.ch'
__copyright__ = 'Copyright 2018, ELCA'

import logging
import pytest

from docker_lib.docker_tools import Container
from systemd_lib.systemd_tools import Systemd


logging.basicConfig(
    format='%(asctime)s %'
           '(name)s %(levelname)s %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@pytest.mark.usefixtures('container_name', 'monit_timeout', 'systemd_timeout', 'docker_timeout')
class TestContainerGrafana:

    def test_container(self, container_name: str) -> None:
        """
        Checks that our Grafana container is running
        :param container_name: from tests_config/dev.json
        :return:
        """
        current_status = Container.status(container_name)
        expected_status = 'running'
        assert expected_status in current_status

    @pytest.mark.parametrize('systemd_service', ['grafana-server.service', 'monit.service', 'nginx.service'])
    def test_services(self, container_name: str, systemd_service: str) -> None:
        """
        Checks that grafana-server, monit, and nginx are running when the container starts.
        :param container_name: from tests_config/dev.json
        :param systemd_service: service to check
        :return:
        """
        assert Systemd.is_service_running(container_name, systemd_service) is True

    @pytest.mark.parametrize('cmd', ['stop', 'kill'])
    @pytest.mark.parametrize('systemd_service', ['grafana-server.service', 'nginx.service'])
    def test_restart_service_with_monit(self, container_name: str, cmd: str, systemd_service: str,
                                        monit_timeout: int) -> None:
        timestamp, timestamp_before_restart_in_seconds = Systemd.get_active_enter_timestamp(container_name,
                                                                                            systemd_service)
        logger.info("Service {service} running since {timestamp} UTC. "
                    "Let's {cmd} it.".format(service=systemd_service, timestamp=timestamp, cmd=cmd))
        Systemd.systemctl(container_name, cmd, systemd_service)

        try:
            Systemd.wait_until_service_is_restarted(container_name, systemd_service, monit_timeout)
        except TimeoutError:
            pytest.fail('Service {service} did not restart after {delay} second(s)'.format(service=systemd_service,
                                                                                           delay=monit_timeout))

        timestamp, timestamp_after_restart_in_seconds = Systemd.get_active_enter_timestamp(container_name,
                                                                                           systemd_service)
        assert timestamp_before_restart_in_seconds < timestamp_after_restart_in_seconds
        logger.info('Service {service} restarted at {timestamp} UTC'.format(service=systemd_service, timestamp=timestamp))

    @pytest.mark.parametrize('systemd_service', ['monit.service'])
    def test_restart_service_with_systemd(self, container_name: str, systemd_service: str,
                                          systemd_timeout: int) -> None:
        timestamp, timestamp_before_restart_in_seconds = Systemd.get_active_enter_timestamp(container_name,
                                                                                            systemd_service)
        logger.info("Service {service} running since {timestamp} UTC. "
                    "Let's kill it.".format(service=systemd_service, timestamp=timestamp))
        Systemd.systemctl(container_name, 'kill', systemd_service)

        try:
            Systemd.wait_until_service_is_restarted(container_name, systemd_service, systemd_timeout)
        except TimeoutError:
            pytest.fail('Service {service} did not restart after {delay} second(s)'.format(service=systemd_service,
                                                                                           delay=systemd_timeout))

        timestamp, timestamp_after_restart_in_seconds = Systemd.get_active_enter_timestamp(container_name,
                                                                                           systemd_service)
        assert timestamp_before_restart_in_seconds < timestamp_after_restart_in_seconds
        logger.info('Service {service} restarted at {timestamp} UTC'.format(service=systemd_service, timestamp=timestamp))

    def test_monit_logs(self, container_name: str, monit_timeout: int, docker_timeout: int) -> None:
        """
        Checks that there is no error in the logs of monit.
        Note that an error message is written in the logs when you stop a service.
        Example:
        systemctl stop grafana-server
        journalctl -u monit -p "err"
        -- Logs begin at Tue 2018-05-15 12:09:54 UTC, end at Tue 2018-05-15 12:18:54 UTC. --
        May 15 12:18:54 b87ae82b67eb monit[21]: 'grafana-server' process is not running
        Thus, test_restart_service_with_monit will generate errors in the logs of monit. To avoid this issue we restart
        the container and check the logs newer than the restart date.

        :param container_name: name of the container under test
        :param monit_timeout: delay to restart service grafana-server
        :return:
        """
        timestamp, timestamp_before_stop_in_seconds = Container.started_at(container_name)
        logger.info("Container {container} running since {timestamp} UTC. "
                    "Let's restart it.".format(container=container_name, timestamp=timestamp))
        try:
            Container.restart(container_name, docker_timeout)
        except TimeoutError:
            pytest.fail('Container {container} did not restart after {delay} second(s)'.format(container=container_name,
                                                                                               delay=docker_timeout))

        try:
            Systemd.wait_until_service_is_restarted(container_name, 'grafana-server.service', monit_timeout)
        except TimeoutError:
            pytest.fail('Service grafana-server did not restart after {delay} second(s)'.format(delay=monit_timeout))

        timestamp, timestamp_after_restart_in_seconds = Container.started_at(container_name)
        logger.info('Container {container} restarted at {timestamp} UTC'.format(container=container_name,
                                                                                timestamp=timestamp))
        assert timestamp_before_stop_in_seconds < timestamp_after_restart_in_seconds

        monit_log = Systemd.list_errors_not_older_than(container_name, 'monit', timestamp)
        expected_substring = 'no entries'
        assert expected_substring in monit_log.lower()
