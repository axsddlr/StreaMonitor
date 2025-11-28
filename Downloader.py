import os
import sys
import streamonitor.config as config
from streamonitor.managers.httpmanager import HTTPManager
from streamonitor.managers.climanager import CLIManager
from streamonitor.managers.zmqmanager import ZMQManager
from streamonitor.managers.outofspace_detector import OOSDetector
from streamonitor.clean_exit import CleanExit
import streamonitor.sites  # must have

        
def is_docker():
    """Check if the application is running inside a Docker container."""
    if os.path.exists('/.dockerenv'):
        return True

    path = '/proc/self/cgroup'
    if os.path.isfile(path):
        try:
            with open(path, 'r') as f:
                return any('docker' in line for line in f)
        except (IOError, OSError):
            pass

    return False


def main():
    if not OOSDetector.disk_space_good():
        print(OOSDetector.under_threshold_message)
        sys.exit(1)

    streamers = config.loadStreamers()

    clean_exit = CleanExit(streamers)

    oos_detector = OOSDetector(streamers)
    oos_detector.start()

    if not is_docker():
        console_manager = CLIManager(streamers)
        console_manager.start()

    zmq_manager = ZMQManager(streamers)
    zmq_manager.start()

    http_manager = HTTPManager(streamers)
    http_manager.start()


main()
