#!/usr/bin/env python

"""Test of the grafana-service container.

Fixtures.
"""

__author__ = 'Jean-Luc Beuchat'
__email__ = 'jean-luc.beuchat@elca.ch'
__copyright__ = 'Copyright 2018, ELCA'

import dateutil.parser
import json
import pytest
import sh

from typing import Optional


def pytest_addoption(parser):
    parser.addoption("--config-file", action="store", help="Json container configuration file ", dest="config_file")


@pytest.fixture(scope='class')
def settings(pytestconfig) -> dict:
    try:
        with open(pytestconfig.getoption('config_file')) as json_data:
            config = json.load(json_data)
    except (FileNotFoundError, IOError):
        pytest.fail('Config file {} not found'.format(pytestconfig.getoption('config_file')))
    else:
        return config


@pytest.fixture(scope='class')
def container_name(settings: dict) -> str:
    name: Optional[str] = settings.get('container_name')
    if not name:
        pytest.fail("property 'container_name' not found")
    return name


@pytest.fixture(scope='class')
def container(container_name: str) -> sh.Command:
    return sh.docker.bake('exec', container_name)


@pytest.fixture(scope='class')
def container_started_at(container_name: str):
    started_at = sh.docker('inspect', container_name, "--format='{{.State.StartedAt}}'").stdout.decode('utf-8').rstrip()
    return dateutil.parser.parse(started_at).strftime("%Y-%m-%d %H:%M:%S")


@pytest.fixture(scope='class')
def systemd_timeout(settings: dict) -> int:
    timeout: Optional[int] = settings.get('systemd_timeout')
    if not timeout:
        pytest.fail("property 'systemd_timeout' not found")
    return timeout


@pytest.fixture(scope='class')
def monit_timeout(settings: dict) -> int:
    timeout: Optional[int] = settings.get('monit_timeout')
    if not timeout:
        pytest.fail("property 'monit_timeout' not found")
    return timeout
