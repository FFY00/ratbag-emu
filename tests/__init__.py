# SPDX-License-Identifier: MIT

import fcntl
import os
import sys
import shutil
import subprocess
import threading
import warnings

import pytest
import requests
import libevdev

from time import sleep, strftime
from pathlib import Path

f = os.readlink(__file__) if os.path.islink(__file__) else __file__
path = os.path.realpath(os.path.join(f, "..", "..", "src"))

if path not in sys.path:
    sys.path.insert(0, path)

import ratbag_emu

from ratbag_emu.util import MM_TO_INCH
from ratbag_emu.protocol.base import MouseData


class Client(object):
    def __init__(self, url='http://localhost:8080'):
        self.url = url

    def get(self, path):
        return requests.get(f'{self.url}{path}')

    def post(self, path, data=None, json=None):
        return requests.post(f'{self.url}{path}',
                             data=data,
                             json=json)

    def delete(self, path):
        return requests.delete(f'{self.url}{path}')

    def put(self, path, data=None, json=None):
        return requests.put(f'{self.url}{path}',
                            data=data,
                            json=json)


class MouseData(object):
    '''
    Holds event data
    '''

    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

    @staticmethod
    def from_mm(dpi, x=0, y=0):
        return MouseData(x=int(x * MM_TO_INCH * dpi),
                         y=int(y * MM_TO_INCH * dpi))


class TestBase(object):
    def reload_udev_rules(self):
        subprocess.run('udevadm control --reload-rules'.split())

    @pytest.fixture(scope='session', autouse=True)
    def udev_rules(self):
        rules_file = '61-ratbag-emu-ignore-test-devices.rules'
        rules_dir = Path('/run/udev/rules.d')

        rules_src = Path('rules.d') / rules_file
        rules_dest = rules_dir / rules_file

        rules_dir.mkdir(exist_ok=True)
        shutil.copyfile(rules_src, rules_dest)
        self.reload_udev_rules()

        yield

        if rules_dest.is_file():
            rules_dest.unlink()
            self.reload_udev_rules()

    @pytest.fixture(autouse=True, scope='session')
    def server(self):
        p = None
        logs = f'ratbag-emu-log-{strftime("%Y-%m-%d_%H-%M")}'
        with open(f'{logs}-stdout.txt', 'w') as stdout, \
             open(f'{logs}-stderr.txt', 'w') as stderr:
            try:
                try:
                    args = ['uwsgi', '--http', ':8080',
                                     '--plugin', 'python',
                                     '--wsgi-file', f'{os.path.dirname(f)}/../ratbag_emu/__main__.py',
                                     '--enable-threads']
                    p = subprocess.Popen(args, stdout=stdout, stderr=stderr)
                except FileNotFoundError:
                    args = ['/usr/bin/env', 'python3', '-m', 'ratbag_emu']
                    p = subprocess.Popen(args, stdout=stdout, stderr=stderr)
                sleep(2)
                yield
            finally:
                if p:
                    p.kill()

    @pytest.fixture(autouse=True, scope='session')
    @pytest.mark.usesfixtures('server')
    def client(self):
        yield Client()

    def add_device(self, client, hw_settings={}, name=None):
        data = {}
        if name:
            data['shortname'] = name
        else:
            data['hw_settings'] = hw_settings
        response = client.post('/devices/add', json=data)
        assert response.status_code == 201
        return response.json()['id']

    def simulate(self, client, id, data):
        response = client.get(f'/devices/{id}')
        assert response.status_code == 200

        input_nodes = response.json().get('input_nodes', {})

        # Open the event nodes
        event_nodes = []
        for node in set(input_nodes):
            fd = open(node, 'rb')
            fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NONBLOCK)
            event_nodes.append(libevdev.Device(fd))

        events = []
        def collect_events(stop):
            nonlocal events
            while not stop.is_set():
                for node in event_nodes:
                    events += list(node.events())

        stop_event_thread = threading.Event()
        event_thread = threading.Thread(target=collect_events, args=(stop_event_thread,))
        event_thread.start()

        response = client.post(f'/devices/{id}/event', json=data)
        assert response.status_code == 200

        sleep(1)
        stop_event_thread.set()
        event_thread.join()

        for node in event_nodes:
            node.fd.close()

        received = MouseData()
        for e in events:
            if e.matches(libevdev.EV_REL.REL_X):
                received.x += e.value
            elif e.matches(libevdev.EV_REL.REL_Y):
                received.y += e.value

        return received
