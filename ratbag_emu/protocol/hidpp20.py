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
    IRoot = 0x0000
    IFeatureSet = 0x0001
    IFeatureInfo = 0x0002
    DeviceInformation = 0x0003
    DeviceNameAndType = 0x0005
    DeviceGroups = 0x0006
    ConfigChange = 0x0020
    UniqueIdentifier = 0x0021
    WirelessSignalStrength = 0x0080
    DFUControl0 = 0x00c0
    DFUControl1 = 0x00c1
    DFU = 0x00d0


class HIDPP20Errors():
    NoError = 0
    Unknown = 1
    InvalidArgument = 2
    OutOfRange = 3
    HWError = 4
    LogitechInternal = 5
    INVALID_FEATURE_INDEX = 6
    INVALID_FUNCTION_ID = 7
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
            self.features[feature](data, ase, args)

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

