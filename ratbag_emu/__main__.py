#!/usr/bin/env python3
#
# SPDX-License-Identifier: MIT

import argparse
import logging
import os
import sys
import threading
import traceback

import connexion

from ratbag_emu.device_handler import DeviceHandler


logger = logging.getLogger('ratbagemu')
logging.basicConfig(format='%(asctime)s.%(msecs)03d %(levelname)-7s %(name)s: %(message)s',
                    level=logging.INFO,
                    datefmt='%H:%M:%S')

cur_dir = os.path.abspath(os.path.dirname(os.readlink(__file__) if os.path.islink(__file__) else __file__))

def create_server():
    server = connexion.FlaskApp(__name__,
                                specification_dir=os.path.join(cur_dir, 'openapi/'),
                                debug=False)
    server.add_api('ratbag-emu.yaml',
                    options={"swagger_ui": True},
                    arguments={'title': 'ratbag-emu'},
                    strict_validation=True,
                    validate_responses=True)
    return server


# Start handling devices
devices_thread = threading.Thread(target=DeviceHandler.handle)
devices_thread.setDaemon(True)
devices_thread.start()

# Export server for uwsgi
server = create_server()
application = server.app

if __name__ == '__main__':
    if sys.version_info < (3, 6):
        sys.exit('Python 3.6 or later required')

    desc = 'ratbag-emu is a firmware emulator for gaming mice'
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('-v', '--verbose',
                        help='Show some debugging informations',
                        action='store_true',
                        default=False)
    parser.add_argument('-p', '--port',
                        help='Webserver port',
                        type=int,
                        default=8080)
    ns = parser.parse_args()
    if ns.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    try:
        server.run(port=ns.port)
    except KeyboardInterrupt:
        pass
    except Exception:
        traceback.print_exc(file=sys.stdout)
        exit(1)
