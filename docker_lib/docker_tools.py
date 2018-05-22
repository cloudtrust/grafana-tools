#!/usr/bin/env python

__author__ = 'Jean-Luc Beuchat'
__email__ = 'jean-luc.beuchat@elca.ch'
__copyright__ = 'Copyright 2018, ELCA'


import datetime
import dateutil.parser
import sh
import time

from typing import Tuple


class Container:

    @staticmethod
    def _wait_until(container_name: str, status: str, timeout: int) -> None:
        counter = 0
        while True:
            time.sleep(1)
            counter = counter + 1
            if status in Container.status(container_name):
                return
            if counter > timeout:
                raise TimeoutError

    @staticmethod
    def started_at(container_name: str) -> Tuple[str, float]:
        state_started_at: str = sh.docker('inspect', container_name,
                                          "--format='{{.State.StartedAt}}'").stdout.decode('utf-8').rstrip()
        started_at: datetime.datetime = dateutil.parser.parse(state_started_at)
        return started_at.strftime('%Y-%m-%d %H:%M:%S'), started_at.timestamp()

    @staticmethod
    def start(container_name: str, timeout: int) -> None:
        sh.docker('start', container_name)
        Container._wait_until(container_name, 'running', timeout)

    @staticmethod
    def restart(container_name: str, timeout: int) -> None:
        sh.docker('restart', container_name)
        Container._wait_until(container_name, 'running', timeout)

    @staticmethod
    def stop(container_name: str, timeout: int) -> None:
        sh.docker('stop', container_name)
        Container._wait_until(container_name, 'exited', timeout)

    @staticmethod
    def status(container_name: str) -> str:
        current_status = sh.docker('inspect', container_name,
                                   "--format='{{.State.Status}}'").stdout.decode('utf-8')
        return current_status
