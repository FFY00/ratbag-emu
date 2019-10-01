# SPDX-License-Identifier: MIT

import logging
import random

from collections import namedtuple

from .base import BaseDevice
from ratbag_emu.util import pack_be_u16, unpack_be_u16

logger = logging.getLogger('ratbagemu.protocol.hidpp20')


class HIDPP20Report():
    ReportType = 0
    Device = 1
    Feature = 2
    ASE = 3
    Arguments = 4


class HIDPP20ReportType():
    Short = 0x10
    Long = 0x11
    ShortSize = 7
    LongSize = 20


class HIDPP20Features():
    # Important
    IRoot = 0x0000
    IFeatureSet = 0x0001
    IFeatureInfo = 0x0002
    # Common
    DeviceInformation = 0x0003
    DeviceNameAndType = 0x0005
    DeviceGroups = 0x0006
    DeviceFriendlyName = 0x0007
    KeepAlive = 0x0008
    ConfigChange = 0x0020
    UniqueIdentifier = 0x0021
    TargetSoftware = 0x0030
    WirelessSignalStrength = 0x0080
    DFULiteControl = 0x00c0
    DFUControlUnsigned = 0x00c1
    DFUControlSigned = 0x00c2
    DFU = 0x00d0
    BatteryUnifiedLevelStatus = 0x1000
    BatteryVoltage = 0x1001
    ChargingControl = 0x1010
    LedSwControl = 0x1300
    ChangeHost = 0x1814
    Backlight1 = 0x1981
    Backlight2 = 0x1982
    PresenterControl = 0x1a00
    KeyboardMouseReprogramable1 = 0x1b00
    KeyboardMouseReprogramable2 = 0x1b01
    KeyboardMouseReprogramable3 = 0x1b02
    KeyboardMouseReprogramable4 = 0x1b03
    KeyboardMouseReprogramable5 = 0x1b04
    ReportHIDUsages = 0x1bc0
    PersistentRemappableAction = 0x1c00
    WirelessDeviceStatus = 0x1d4b
    RemainingPairings = 0x1df0
    # Mouse
    SwapLeftRightButton = 0x2001
    ButtonSwapControl = 0x2005
    PointerAxesOrientation = 0x2006
    VerticalScrolling = 0x2100
    SmartShiftWheel = 0x2110
    HiResScrolling = 0x2120
    HiResWheel = 0x2121
    RatchetWheel = 0x2130
    ThumbWheel = 0x2150
    MousePointer = 0x2200
    AdjustableDPI = 0x2201
    PointerMotionScalling = 0x2205
    SensorAngleSnapping = 0x2230
    SurfaceTuning = 0x2240
    HybridTrackingEngine = 0x2400
    # Keyboard
    FnInversion = 0x40a0
    FnInversionWithDefaultState = 0x40a2
    FnInversionMultiHost = 0x40a3
    Encryption = 0x4100
    LockKeyState = 0x4220
    SolarDashboard = 0x4301
    KeyboardLayout = 0x4520
    DisableKeys = 0x4521
    DisableKeysByUsage = 0x4522
    DualPlatform = 0x4530
    KeyboardInternationalLayouts = 0x4540
    Crown = 0x4600
    # Touchpad
    TouchpadFwItems = 0x6010
    TouchpadSwItems = 0x6011
    TouchpadWin8FwItems = 0x6012
    TapEnable = 0x6020
    TapEnableExtended = 0x6021
    CursorBalistic = 0x6030
    TouchpadResolutionDivider = 0x6040
    TouchpadRawXY = 0x6100
    TouchMouseRawTouchPoints = 0x6110
    BTTouchMouseSettings = 0x6120
    Gestures1 = 0x6500
    Gestures2 = 0x6501
    # Gaming
    GamingGKeys = 0x8010
    GamingMKeys = 0x8020
    MacroRecordKey = 0x8030
    BrightnessControl = 0x8040
    AdjustableReportRate = 0x8060
    ColorLEDEffects = 0x8070
    RGBEffects = 0x8071
    PerformanceModeControl = 0x8090
    OnboardProfiles = 0x8100
    MouseButtonSpy = 0x8110

class HIDPP20Errors():
    NoError = 0
    Unknown = 1
    InvalidArgument = 2
    OutOfRange = 3
    HWError = 4
    LogitechInternal = 5
    InvalidFeatureIndex = 6
    InvalidFunctionId = 7
    Busy = 8
    Unsupported = 9


HIDPP20Entity = namedtuple('HIDPP20Entity', ['type', 'fwName', 'revision',
                           'build', 'active', 'trPid', 'extraVer'])


class HIDPP20Device(BaseDevice):
    def __init__(self):
        assert hasattr(self, 'feature_table'), 'Feature table missing'

        for attr in ['feature_version', 'entities']:
            if not hasattr(self, attr):
                setattr(self, attr, [])

        if not hasattr(self, 'version_major') or not hasattr(self, 'version_minor'):
            self.version_major = 2
            self.version_minor = 0

        super().__init__({}, self.name, self.info, self.rdescs,
                         self.shortname)

        # Protocol declarations
        self.Report = HIDPP20Report
        self.ReportType = HIDPP20ReportType
        self.Features = HIDPP20Features
        self.Errors = HIDPP20Errors

        self.report_size = {
            self.ReportType.Short: self.ReportType.ShortSize,
            self.ReportType.Long: self.ReportType.LongSize
        }

        # Function mapping
        self.features = {
            self.Features.IRoot: self.IRoot,
            self.Features.IFeatureSet: self.IFeatureSet,
            self.Features.IFeatureInfo: self.IFeatureInfo,
            self.Features.DeviceInformation: self.DeviceInformation,
            self.Features.BatteryVoltage: self.BatteryVoltage,
        }

        self.events = {}

        self.expecting_reply = False

    #
    # Interface functions
    #
    def protocol_send(self, report_type, device, feature, ase, sw_id, args):
        data = [0] * self.report_size[report_type]
        data[self.Report.ReportType] = report_type
        data[self.Report.Device] = device
        data[self.Report.Feature] = feature
        data[self.Report.ASE] = ase << 4 + sw_id
        for i in range(len(args)):
            data[self.Report.Arguments + i] = args[i]

        super().send_raw(data)

    def protocol_reply(self, data, args):
        assert len(data) >= self.Report.Arguments + len(args), 'Report too small to send the arguments'

        for i in range(len(args)):
            data[self.Report.Arguments + i] = args[i]

        super().send_raw(data)

    def protocol_error(self, data, error):
        super().send_raw([
            self.ReportType.Short,
            data[self.Report.Device],
            0x8f,
            data[self.Report.Feature],
            data[self.Report.ASE],
            error,
            0
        ])

    #
    # Logic definition
    #
    def protocol_receive(self, data, size, rtype):
        if data[self.Report.ReportType] not in [self.ReportType.Short, self.ReportType.Long]:
            return

        report_type = data[self.Report.ReportType]
        feature = self.feature_table[data[self.Report.Feature]]
        ase = data[self.Report.ASE] >> 4
        args = data[self.Report.Arguments:]

        assert report_type in self.report_size, f'Invalid report type ({report_type:2x})'

        assert len(data) == self.report_size[report_type], 'Wrong report size.' \
            f'Expected {self.report_size[report_type]}, got {len(data)}'

        # Event
        if self.expecting_reply:
            return
        # Function
        else:
            logger.debug(f'Got feature {feature:04x}, ASE {ase}')
            try:
                self.features[feature](data, ase, args)
            except KeyError:
                logger.debug(f"Feature {feature:04x} hasn't been implemented. Ignoring...")

    #
    # Event definitions
    #

    #
    # Feature definitions
    #
    def IRoot(self, data, ase, args):
        # featIndex, featType, featVer = getFeature(featId)
        if ase == 0:
            featId = unpack_be_u16(args[:2])

            logger.debug(f'getFeature({featId:04x}) = {self.feature_table.index(featId)}')
            self.protocol_reply(data, [self.feature_table.index(featId), 0, self.feature_version.get(featId, 0)])

        # protocolNum, targetSw, pingData = getProtocolVersion(0, 0, pingData)
        elif ase == 1:
            pingData = args[2]

            logger.debug(f'getProtocolVersion() = (version) {self.version_major}.{self.version_minor}, (pingData) {pingData}')
            self.protocol_reply(data, [self.version_major, self.version_minor, pingData])

    def IFeatureSet(self, data, ase, args):
        # count = getCount()
        if ase == 0:
            logger.debug(f'getCount() = {len(self.feature_table)}')
            self.protocol_reply(data, [len(self.feature_table) - 1])

        # featureID, featureType, featureVersion = getFeatureID(featureIndex)
        elif ase == 1:
            featureIndex = args[0]

            if featureIndex >= len(self.feature_table):
                logger.debug(f'getFeatureID({featureIndex}) = ERR_OUT_OF_RANGE')
                self.protocol_error(data, self.Errors.OutOfRange)
                return

            featId = self.feature_table[featureIndex]
            logger.debug(f'getFeatureID({featureIndex}) = {featId:04x}')
            self.protocol_reply(data, pack_be_u16(featId) + [0, self.feature_version.get(featId, 0)])

    def IFeatureInfo(self, data, ase, args):
        return

    def DeviceInformation(self, data, ase, args):
        # entityCnt, unitId, transport, modelId, extendedModelId = getDeviceInfo()
        if ase == 0:
            reply = [
                # entityCnt
                len(self.entities),
                # unitId
                0xAA,
                0xBB,
                # transport
                0x00,
                0x06,  # USB/eQUAD
                # modelId (FIXME: Add modelId value)
                0x00,
                0x00,
                # extendedModelId (should not matter, we will keep it at 0)
                0x00,
            ]
            logger.debug(f'FIXME: add modelId')
            logger.debug(f'getDeviceInfo() = (entityCnt) {reply[0]}, (unitId) {pack_be_u16(reply[1], reply[2])}, '
                '(transport) USB/eQUAD, (modelId) {pack_be_u16(reply[5], reply[6])}, (extendedModelId) {reply[7]}')
            self.protocol_reply(data, reply)

        # type, fwName, rev, build, active, trPid, extraVer = getFwInfo(entityIdx)
        elif ase == 1:
            entityIdx = args[0]

            if entityIdx >= len(self.entities):
                logger.debug(f'getFwInfo({entityIdx}) = ERR_OUT_OF_RANGE')
                self.protocol_error(data, self.Errors.OutOfRange)
                return

            entity = self.entities[entityIdx]

            reply = [entity.type]
            reply += [char for char in entity.fwName[:3]]
            reply += [int(entity.fwName[3:])]
            reply += [entity.revision]
            reply += pack_be_u16(entity.build)
            reply += [entity.active]
            reply += pack_be_u16(entity.trPid)
            reply += [entity.extraVer[0]]
            reply += [entity.extraVer[5]]

            logger.debug(f'getFwInfo({entityIdx}) = {entity}')
            self.protocol_reply(data, reply)

    def BatteryVoltage(self, data, ase, args):
        # batteryVoltage, batteryStatus = getBatteryInfo()
        if ase == 0:
            voltage = 4000
            flags = 2 # Discharging

            logger.debug(f'getBatteryInfo() = (batteryVoltage) {voltage}, (batteryStatus) {flags}')
            self.protocol_reply(data, pack_be_u16(voltage) + [flags])

        # showBatteryStatus()
        elif ase == 1:
            # This function display the battery information in the physical device
            pass

