# SPDX-License-Identifier: MIT

import logging
import typing

from typing import Any, Dict, List

from ratbag_emu.hid_property import HIDProperty
from ratbag_emu.util import EventData

if typing.TYPE_CHECKING:  # pragma: no cover
    from ratbag_emu.actuator import Actuator  # noqa: F401
    from ratbag_emu.endpoint import Endpoint


class AxisProperty(HIDProperty):
    '''
    Represents an HID axis

    Transform x and y high-level actions to HID data
    '''
    def __init__(self, owner: 'Endpoint', key: str, min: int, max: int):
        super().__init__(owner, key)
        self.__logger = logging.getLogger('ratbag-emu.hid_property.axis')

        self._min = min
        self._max = max

        self.__logger.debug(f'{self._owner.name}: registered HID axis \'{key}\' (min={min}, max={max})')

    def populate(self, action: Dict[str, Any], packets: List[EventData]) -> None:
        report_count = len(packets)
        dot_buffer = real_dot_buffer = action[self.key]
        '''
        Initialize dot_buffer, real_dot_buffer and step for X and Y

        dot_buffer holds the ammount of dots left to send (kind of,
        read below).

        We actually have two variables for this, real_dot_buffer and
        dot_buffer. dot_buffer mimics the user movement and
        real_dot_buffer holds true number of dots left to send.
        When using high report rates (ex. 1000Hz) we usually don't
        have a full dot to send, that's why we need two variables. We
        subtract the step to dot_buffer at each iteration, when the
        difference between dot_buffer and real_dot_buffer is equal
        or higher than 1 dot we then send a HID report to the device
        with that difference (int! we send the int part of the
        difference) and update real_dot_buffer to include this
        changes.
        '''

        assert dot_buffer <= self._max * report_count
        step = dot_buffer / report_count

        for packet in packets:
            if not real_dot_buffer:
                break

            dot_buffer -= step
            diff = int(round(real_dot_buffer - dot_buffer))
            if abs(diff) >= 1:
                if abs(diff) > self._max:
                    diff = self._max if diff > 0 else self._min
                setattr(packet, self._key, diff)
                real_dot_buffer -= diff
