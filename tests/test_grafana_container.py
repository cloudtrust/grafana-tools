#!/usr/bin/env python

"""Test of the grafana-service container.

"""

__author__ = 'Jean-Luc Beuchat'
__email__ = 'jean-luc.beuchat@elca.ch'
__copyright__ = 'Copyright 2018, ELCA'

import logging
import pytest
import sh
import time


@pytest.mark.usefixtures('container', 'container_name', 'container_started_at', 'monit_timeout', 'systemd_timeout')
class TestContainerGrafana:

    def get_active_state(self, container: sh.Command, service: str) -> str:
        busctl_command = 'get-property'
        busctl_service = 'org.freedesktop.systemd1'
        busctl_object = '/org/freedesktop/systemd1/unit/{}'.format(service)
        busctl_interface = 'org.freedesktop.systemd1.Unit'
        busctl_property = 'ActiveState'
        active_state: str = container.busctl(busctl_command, busctl_service, busctl_object, busctl_interface,
                                             busctl_property).stdout.decode('utf-8')
        return active_state

    def is_service_running(self, container: sh.Command, service: str) -> bool:
        current_state = self.get_active_state(container, service)
        expected_state = '"active"'
        return expected_state in current_state

    def is_service_stopped(self, container: sh.Command, service: str) -> bool:
        current_state = self.get_active_state(container, service)
        expected_state = '"inactive"'
        return expected_state in current_state

    def wait_until_service_is_restarted(self, container: sh.Command, busctl_service: str, timeout: int) -> None:
        counter = 0
        while True:
            time.sleep(1)
            if self.is_service_running(container, busctl_service):
                break
            counter = counter + 1
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
        container.systemctl(cmd, service)
        assert self.is_service_stopped(container, busctl_service) is True
        self.wait_until_service_is_restarted(container, busctl_service, monit_timeout)

    @pytest.mark.parametrize('service, busctl_service', [('monit', 'monit_2eservice')])
    def test_restart_service_with_systemd(self, service: str, busctl_service: str,
                                          container: sh.Command, systemd_timeout: int) -> None:
        container.systemctl('kill', service)
        self.wait_until_service_is_restarted(container, busctl_service, systemd_timeout)

    def test_monit_logs(self, container: sh.Command, container_started_at: str) -> None:
        monit_log = container.journalctl('-u', 'monit', '--since', container_started_at,
                                         '-p', 'err', '-b').stdout.decode('utf-8')
        expected_log = 'no entries'
        assert expected_log in monit_log.lower()
