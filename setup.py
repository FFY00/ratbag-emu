# SPDX-License-Identifier: MIT

from setuptools import setup
from os import path


here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='ratbag-emu',
    version='0.0.1',
    description='HID emulation stack',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/libratbag/ratbag-emu',
    author='Filipe Laíns',
    author_email='lains@archlinux.org',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Topic :: System :: Emulators',
        'Topic :: System :: Hardware :: Hardware Drivers',
        'Topic :: Operating System Kernels :: Linux',
    ],
    keywords='setuptools libratbag hardware mouse uhid emulation',
    project_urls={
        'Bug Reports': 'https://github.com/libratbag/ratbag-emu/issues',
        'Source': 'https://github.com/libratbag/ratbag-emu',
    },

    packages=[
        'ratbag_emu',
        'ratbag_emu.actuators',
    ],
    install_requires=['hid-tools'],
    tests_require=[
        'pytest',
        'libevdev',
        'pyudev'
    ],
)
