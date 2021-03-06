# SPDX-License-Identifier: MIT

import os
import sys
f = os.readlink(__file__) if os.path.islink(__file__) else __file__
path = os.path.realpath(os.path.join(f, "..", "..", "src"))

if path not in sys.path:
    sys.path.insert(0, path)

import fcntl  # noqa: 402
import threading  # noqa: 402

import libevdev  # noqa: 402

import ratbag_emu  # noqa: 402

import pytest  # noqa: 402
import shutil  # noqa: 402
import subprocess  # noqa: 402

from pathlib import Path  # noqa: 402
from time import sleep  # noqa: 402

from ratbag_emu.util import EventData  # noqa: 402


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

    @pytest.fixture()
    def fd_event_nodes(self, device, endpoint=0):
        fds = []
        for node in device.event_nodes:
            fd = open(node, 'rb')
            fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NONBLOCK)
            fds.append(fd)

        yield fds

        for fd in fds:
            fd.close()

    @pytest.fixture()
    def libevdev_event_nodes(self, fd_event_nodes):
        devices = []
        for fd in fd_event_nodes:
            devices.append(libevdev.Device(fd))

        return devices

    @pytest.fixture()
    def event_data(self, libevdev_event_nodes):
        received = EventData()
        def collect_events(stop):  # noqa: 306
            nonlocal received
            while not stop.is_set():
                for evdev_device in libevdev_event_nodes:
                    for e in evdev_device.events():
                        if e.matches(libevdev.EV_REL.REL_X):
                            received.x += e.value
                        elif e.matches(libevdev.EV_REL.REL_Y):
                            received.y += e.value
                sleep(0.001)

        stop_event_thread = threading.Event()
        event_thread = threading.Thread(target=collect_events,
                                        args=(stop_event_thread,))
        event_thread.start()

        yield received

        stop_event_thread.set()
        event_thread.join()

    def simulate(self, device, events, action):
        def callback(device):
            nonlocal action
            device.simulate_action(action)

        return self.catch_evdev_events(device, events, callback, wait=action['duration']/1000 + 0.5)
