# SPDX-License-Identifier: MIT

import logging
import sched
import time

from typing import Any, ClassVar, Dict, List, Tuple

from ratbag_emu.actuator import Actuator
from ratbag_emu.endpoint import Endpoint
from ratbag_emu.firmware import Firmware
from ratbag_emu.hw_component import HWComponent
from ratbag_emu.util import EventData, ms2s


class Device(object):
    '''
    Represents a real device

    :param name:    Device name
    :param info:    Bus information (bus, vid, pid)
    :param rdescs:  Array of report descriptors
    '''
    device_list: ClassVar[List[str]] = []

    def __init__(self, name: str, info: Tuple[int, int, int],
                 rdescs: List[List[int]]):
        self.__logger = logging.getLogger('ratbag-emu.device')
        self._name = name
        self._info = info
        self._rdescs = rdescs

        self.endpoints = []
        for i, r in enumerate(rdescs):
            self.endpoints.append(Endpoint(self, r, i))

        self.report_rate = 100
        self.fw = Firmware(self)
        self.hw: Dict[str, HWComponent] = {}
        self.actuators: List[Actuator] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def info(self) -> Tuple[int, int, int]:
        return self._info

    @property
    def event_nodes(self) -> List[str]:
        return [node for endpoint in self.endpoints for node in endpoint.device_nodes]

    @property
    def hidraw_nodes(self) -> List[str]:
        return [node for endpoint in self.endpoints for node in endpoint.hidraw_nodes]

    @property
    def rdescs(self) -> List[List[int]]:
        return self._rdescs

    @property
    def actuators(self) -> List[Actuator]:
        return self._actuators

    @actuators.setter
    def actuators(self, val: List[Actuator]) -> None:
        # Make sure we don't have actuators which will act on the same keys
        seen: List[str] = []
        for keys in [a.keys for a in val]:
            for el in keys:
                assert el not in seen
                seen.append(el)

        self._actuators = val

    def destroy(self) -> None:
        for endpoint in self.endpoints:
            endpoint.destroy()

    def transform_action(self, data: Dict[str, Any]) -> Dict[str, Any]:
        '''
        Transforms high-level action according to the actuators

        A high-level action will have the x, y values in mm. This values will
        be converted to dots by the device actuators (in this case, the
        sensor/dpi actuator)

        :param action:  high-level action
        '''
        hid_data: Dict[str, Any] = {}

        for actuator in self.actuators:
            hid_data.update(actuator.transform(data.copy()))

        return hid_data

    def send_hid_action(self, action: object) -> None:
        '''
        Sends a HID action

        We assume there's only one endpoint for each type of action (mouse,
        keyboard, button, etc.) so we send the action to all endpoints. The
        endpoint will only act on the action if it supports it.

        :param action:  HID action
        '''
        for endpoint in self.endpoints:
            endpoint.send(endpoint.create_report(action))

    def simulate_action(self, action: Dict[str, Any]) -> None:
        '''
        Simulates action

        Translates physical values according to the device properties and
        converts action into HID reports.

        :param action:  high-level action
        :param type:    HID report type
        '''

        packets: List[EventData] = []

        report_count = int(round(ms2s(action['duration']) * self.report_rate))

        if not report_count:
            report_count = 1

        action_scheduler = sched.scheduler(time.time, time.sleep)

        hid_action = self.transform_action(action['data'])

        for endpoint in self.endpoints:
            for i in range(report_count):
                packets.append(EventData())

            endpoint.populate_hid_data(hid_action, packets)

            next_time = 0.0
            for packet in packets:
                action_scheduler.enter(next_time, 1, endpoint.send, kwargs={
                                       'data': endpoint.create_report(packet)})
                next_time += 1 / self.report_rate

        action_scheduler.run()
