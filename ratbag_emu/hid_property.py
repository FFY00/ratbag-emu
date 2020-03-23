# SPDX-License-Identifier: MIT

import logging
import typing

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from ratbag_emu.util import EventData

if typing.TYPE_CHECKING:
    from ratbag_emu.endpoint import Endpoint  # pragma: no cover


class HIDProperty(ABC):
    '''
    Transforms high-level actions to HID data
    '''
    def __init__(self, owner: 'Endpoint', key: str) -> None:
        self.__logger = logging.getLogger('ratbag-emu.hid_property')

        self._owner = owner
        self._key = key

    @property
    def key(self) -> str:
        return self._key

    @abstractmethod
    def populate(self, action: Dict[str, Any], packets: List[EventData]) -> None:
        '''
        Populates action
        '''
