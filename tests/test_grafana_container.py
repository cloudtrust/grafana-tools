#!/usr/bin/env python

"""Test of the grafana-service container.

"""

__author__ = 'Jean-Luc Beuchat'
__email__ = 'jean-luc.beuchat@elca.ch'
__copyright__ = 'Copyright 2018, ELCA'

import datetime
import dateutil.parser
import logging
import pytest
import sh
import time

from typing import Tuple

logging.basicConfig(
    format='%(asctime)s %'
           '(name)s %(levelname)s %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@pytest.mark.usefixtures('container', 'container_name', 'monit_timeout', 'systemd_timeout')
class TestContainerGrafana:

    @staticmethod
    def container_started_at(container_name: str) -> Tuple[str, float]:
        state_started_at: str = sh.docker('inspect', container_name,
                                          "--format='{{.State.StartedAt}}'").stdout.decode('utf-8').rstrip()
        started_at: datetime.datetime = dateutil.parser.parse(state_started_at)
        return started_at.strftime('%Y-%m-%d %H:%M:%S'), started_at.timestamp()

    @staticmethod
    def get_property(container: sh.Command, service: str, busctl_property: str) -> str:
        busctl_command = 'get-property'
        busctl_service = 'org.freedesktop.systemd1'
        busctl_object = '/org/freedesktop/systemd1/unit/{}'.format(service)
        busctl_interface = 'org.freedesktop.systemd1.Unit'
        return container.busctl(busctl_command, busctl_service, busctl_object, busctl_interface,
                                busctl_property).stdout.decode('utf-8')

    def get_active_enter_timestamp(self, container: sh.Command, service: str) -> Tuple[str, float]:
        busctl_property = 'ActiveEnterTimestamp'
        active_enter_timestamp: str = self.get_property(container, service, busctl_property)
        # active_enter_timestamp contains a string s.t. 't 1526305170850190'. Let's get the timestamp and convert it
        # to something compatible with datetime:
        try:
            timestamp: float = float(active_enter_timestamp.split()[1])/1000000.0
        except (IndexError, ValueError):
            pytest.fail('ActiveEnterTimestamp: unexpected format')
        else:
            return datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S'), \
                   timestamp

    def is_service_running(self, container: sh.Command, service: str) -> bool:
        busctl_property = 'ActiveState'
        current_state: str = self.get_property(container, service, busctl_property)
        expected_state = '"active"'
        return expected_state in current_state

    def wait_until_service_is_restarted(self, container: sh.Command, busctl_service: str, timeout: int) -> None:
        counter = 0
        while True:
            time.sleep(1)
            counter = counter + 1
            if self.is_service_running(container, busctl_service):
                break
            if counter > timeout:
                pytest.fail('Service did not restart after {} second(s)'.format(timeout))

    def test_container(self, container_name: str) -> None:
        current_status = sh.docker('inspect', container_name,
                                   "--format='{{.State.Status}}'").stdout.decode('utf-8')
        expected_status = 'running'
        assert expected_status in current_status

    @pytest.mark.parametrize('service', ['grafana_2dserver_2eservice', 'monit_2eservice', 'nginx_2eservice'])
    def test_services(self, service: str, container) -> None:
        assert self.is_service_running(container, service) is True

    @pytest.mark.parametrize('cmd', ['stop', 'kill'])
    @pytest.mark.parametrize('service, busctl_service', [('grafana-server', 'grafana_2dserver_2eservice'),
                                                         ('nginx', 'nginx_2eservice')])
    def test_restart_service_with_monit(self, cmd: str, service: str,
                                        busctl_service: str, container: sh.Command, monit_timeout: int) -> None:
        timestamp, timestamp_before_restart_in_seconds = self.get_active_enter_timestamp(container, busctl_service)
        logger.info("Service {} running since {} UTC. Let's {} it.".format(service, timestamp, cmd))
        container.systemctl(cmd, service)
        self.wait_until_service_is_restarted(container, busctl_service, monit_timeout)
        timestamp, timestamp_after_restart_in_seconds = self.get_active_enter_timestamp(container, busctl_service)
        assert timestamp_before_restart_in_seconds < timestamp_after_restart_in_seconds
        logger.info('Service {} restarted at {} UTC'.format(service, timestamp))

    @pytest.mark.parametrize('service, busctl_service', [('monit', 'monit_2eservice')])
    def test_restart_service_with_systemd(self, service: str, busctl_service: str,
                                          container: sh.Command, systemd_timeout: int) -> None:
        # systemd restarts services quicly. Checking if a service is stopped with systemctl does not work here.
        timestamp, timestamp_before_restart_in_seconds = self.get_active_enter_timestamp(container, busctl_service)
        logger.info("Service {} running since {} UTC. Let's kill it.".format(service, timestamp))
        container.systemctl('kill', service)
        self.wait_until_service_is_restarted(container, busctl_service, systemd_timeout)
        timestamp, timestamp_after_restart_in_seconds = self.get_active_enter_timestamp(container, busctl_service)
        assert timestamp_before_restart_in_seconds < timestamp_after_restart_in_seconds
        logger.info('Service {} restarted at {} UTC'.format(service, timestamp))

    def test_monit_logs(self, container_name: str, container: sh.Command, monit_timeout: int) -> None:
        """
        An error message is
        journalctl -u monit -p "err"
        -- Logs begin at Tue 2018-05-15 12:09:54 UTC, end at Tue 2018-05-15 12:18:54 UTC. --
        May 15 12:18:54 b87ae82b67eb monit[21]: 'grafana-server' process is not running


        :param container_name: name of the container under test (
        :param container:
        :param monit_timeout:
        :return:
        """
        timestamp_before_stop_s, timestamp_before_stop_f = self.container_started_at(container_name)
        logger.info("Container {} running since {} UTC. Let's stop it.".format(container_name, timestamp_before_stop_s))
        sh.docker('stop', container_name)
        sh.docker('restart', container_name)
        self.wait_until_service_is_restarted(container, 'grafana_2dserver_2eservice', monit_timeout)
        timestamp_s, timestamp_f = self.container_started_at(container_name)
        logger.info('Container {} restarted at {} UTC'.format(container_name, timestamp_s))
        assert timestamp_before_stop_f < timestamp_f
        monit_log = container.journalctl('-u', 'monit', '--since', timestamp_s,
                                         '-p', 'err', '-b').stdout.decode('utf-8')
        expected_substring = 'no entries'
        assert expected_substring in monit_log.lower()
