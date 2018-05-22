#!/usr/bin/env python

"""Test of the grafana-service container.

Fixtures.
"""

__author__ = 'Jean-Luc Beuchat'
__email__ = 'jean-luc.beuchat@elca.ch'
__copyright__ = 'Copyright 2018, ELCA'

import json
import pytest

from typing import Tuple


def pytest_addoption(parser):
    parser.addoption("--config-file", action="store", help="Json container configuration file ", dest="config_file")
    parser.addoption("--grafana-config-file", action="store", help="Json psql credentials file ", dest="grafana_config_file")


def get_property(dictionary: dict, key: str):
    value = dictionary.get(key)
    if not value:
        pytest.fail("Property '{}' not found".format(key))
    return value


@pytest.fixture(scope='class')
def settings(pytestconfig) -> dict:
    try:
        with open(pytestconfig.getoption('config_file')) as json_data:
            config = json.load(json_data)
    except (FileNotFoundError, IOError):
        pytest.fail('Configuration file not found')
    else:
        return config


@pytest.fixture(scope='class')
def grafana_settings(pytestconfig) -> dict:
    try:
        with open(pytestconfig.getoption('grafana_config_file')) as json_data:
            config = json.load(json_data)
    except (FileNotFoundError, IOError):
        pytest.fail('Grafana configuration file not found')
    else:
        return config


@pytest.fixture(scope='class')
def container_name(settings: dict) -> str:
    return get_property(settings, 'container_name')


@pytest.fixture(scope='class')
def systemd_timeout(settings: dict) -> int:
    return get_property(settings, 'systemd_timeout')


@pytest.fixture(scope='class')
def monit_timeout(settings: dict) -> int:
    return get_property(settings, 'monit_timeout')


@pytest.fixture(scope='class')
def docker_timeout(settings: dict) -> int:
    return get_property(settings, 'docker_timeout')


@pytest.fixture(scope='class')
def default_credentials(grafana_settings: dict) -> Tuple[str, str]:
    username = get_property(grafana_settings, 'default_user')
    password = get_property(grafana_settings, 'default_password')
    return username, password


@pytest.fixture(scope='class')
def host(grafana_settings: dict) -> str:
    return get_property(grafana_settings, 'host')


@pytest.fixture(scope='class')
def port(grafana_settings: dict) -> str:
    return get_property(grafana_settings, 'port')
