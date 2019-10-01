import os
import pytest

from . import TestBase, MouseData


# TODO: Restructure this so that we can easily use other devices
class TestHIDPP20(TestBase):
    shortname = 'logitech-g-pro-wireless'

    @pytest.fixture()
    def fd(self, id):
        fd = None

        # FIXME: We shouldn't hardcode the ID like this
        uhid = '/sys/devices/virtual/misc/uhid'
        for file in (os.fsencode(f).decode('utf-8') for f in os.listdir(uhid)):
            if file.startswith('0003:046D:4079.'):
                hidraw_path = f'{uhid}/{str(file)}/hidraw'
                for hidraw in (os.fsencode(f).decode('utf-8') for f in os.listdir(hidraw_path)):
                    input_path = f'{hidraw_path}/{hidraw}/device/input'
                    for input_node in (os.fsencode(f).decode('utf-8') for f in os.listdir(input_path)):
                        with open(f'{input_path}/{input_node}/uevent') as uevent_fd:
                            for line in uevent_fd:
                                if str.startswith(line, f'NAME="ratbag-emu {id} (Logitech G Pro Wireless, 0x46d:0x4079)'):
                                    fd = open(f'/dev/{hidraw}', 'r+b')

        yield fd

        if fd:
            fd.close()

    @pytest.fixture()
    def device(self, hidpp, fd):
        assert fd, 'Hidraw node not found'

        base = hidpp.hidpp_device()
        hidpp.hidpp_device_init(base, fd.fileno())

        dev = hidpp.hidpp20_device_new(base, 0xff)
        yield dev

        hidpp.hidpp20_device_destroy(dev)
