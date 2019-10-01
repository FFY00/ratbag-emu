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

    # IRoot
    def test_root_get_feature(self, client, id, hidpp, device):
        feature_index = hidpp.new_uint8_tp()
        feature_type = hidpp.new_uint8_tp()
        feature_version = hidpp.new_uint8_tp()

        # IFeatureSet
        assert not hidpp.hidpp_root_get_feature(device, 0x0001, feature_index, feature_type, feature_version)

        assert hidpp.uint8_tp_value(feature_index) == 1
        assert hidpp.uint8_tp_value(feature_type) == 0
        assert hidpp.uint8_tp_value(feature_version) == 1

        # DeviceInformation
        assert not hidpp.hidpp_root_get_feature(device, 0x0003, feature_index, feature_type, feature_version)

        assert hidpp.uint8_tp_value(feature_index) == 2
        assert hidpp.uint8_tp_value(feature_type) == 0
        assert hidpp.uint8_tp_value(feature_version) == 2

        # BatteryVoltage
        assert not hidpp.hidpp_root_get_feature(device, 0x1001, feature_index, feature_type, feature_version)

        assert hidpp.uint8_tp_value(feature_index) == 6
        assert hidpp.uint8_tp_value(feature_type) == 0
        assert hidpp.uint8_tp_value(feature_version) == 0

    '''
    FIXME: I can't seem to interface with unsigned int pointers

    def test_get_root_protocol_version(self, client, id, hidpp, device):
        major = hidpp.new_uintp()
        minor = hidpp.new_uintp()

        assert not hidpp.hidpp20_root_get_protocol_version(device, major, minor)

        assert hidpp.uintp_value(major) == 4
        assert hidpp.uintp_value(minor) == 2
    '''
