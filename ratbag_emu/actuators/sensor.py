# SPDX-License-Identifier: MIT

from typing import Any, Dict

from ratbag_emu.actuator import Actuator
from ratbag_emu.util import mm2inch


class SensorActuator(Actuator):
    '''
    Represents the sensor/dpi actuator

    Transform x and y values based on the DPI value.
    '''
    def __init__(self, dpi: int):
        super().__init__()
        self._keys = ['x', 'y']
        self.dpi = dpi

    def transform(self, action: Dict[str, Any]) -> Dict[str, Any]:
        hid_action = action.copy()

        for key in self._keys:
            if key in hid_action:
                hid_action[key] = int(round(mm2inch(action[key]) * self.dpi))
        return hid_action
