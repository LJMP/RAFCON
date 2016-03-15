#!/usr/bin/env python

import logging
import os
import gtk
import signal
import traceback
import argparse
from os.path import realpath, dirname, join, exists, expanduser, expandvars, isdir

import rafcon
from rafcon.utils.config import config_path
from rafcon.utils import log
from rafcon.utils.constants import RAFCON_TEMP_PATH_STORAGE
import rafcon.utils.filesystem as filesystem

from rafcon.statemachine.config import global_config
from rafcon.statemachine.storage.storage import StateMachineStorage
from rafcon.statemachine.state_machine import StateMachine
from rafcon.statemachine.states.hierarchy_state import HierarchyState
import rafcon.statemachine.singleton as sm_singletons

from rafcon.mvc.controllers.main_window import MainWindowController
from rafcon.mvc.views.main_window import MainWindowView
import rafcon.mvc.singleton as mvc_singletons
from rafcon.mvc.config import global_gui_config
from rafcon.mvc.runtime_config import global_runtime_config

from plugins import *

try:
    from plugins.monitoring.monitoring_manager import global_monitoring_manager
    from twisted.internet import gtk2reactor
    # needed for glib.idle_add, and signals
    gtk2reactor.install()
    from twisted.internet import reactor
except ImportError, e:
    print "Monitoring plugin not found"


def setup_logger():
    import sys
    # Set the views for the loggers

    # Apply defaults to logger of gtkmvc
    for handler in logging.getLogger('gtkmvc').handlers:
        logging.getLogger('gtkmvc').removeHandler(handler)
    stdout = logging.StreamHandler(sys.stdout)
    stdout.setFormatter(logging.Formatter("%(asctime)s: %(levelname)-8s - %(name)s:  %(message)s"))
    stdout.setLevel(logging.DEBUG)
    logging.getLogger('gtkmvc').addHandler(stdout)


def state_machine_path(path):
    sm_root_file = join(path, StateMachineStorage.STATEMACHINE_FILE)
    if exists(sm_root_file):
        return path
    else:
        raise argparse.ArgumentTypeError("Failed to open {0}: {1} not found in path".format(path,
                                                                                StateMachineStorage.STATEMACHINE_FILE))


if __name__ == '__main__':
    setup_logger()
    # from rafcon.utils import log
    logger = log.get_logger("start")
    logger.info("RAFCON launcher")

    rafcon_root_path = dirname(realpath(rafcon.__file__))
    if not os.environ.get('RAFCON_PATH', None):
        # set env variable RAFCON_PATH to the root directory of RAFCON
        os.environ['RAFCON_PATH'] = rafcon_root_path

    if not os.environ.get('RAFCON_LIB_PATH', None):
        # set env variable RAFCON_LIB_PATH to the library directory of RAFCON (when not using RMPM)
        os.environ['RAFCON_LIB_PATH'] = join(dirname(rafcon_root_path), 'libraries')

    home_path = filesystem.get_home_path()

    parser = sm_singletons.argument_parser

    parser.add_argument('-n', '--new', action='store_true', help="whether to create a new state-machine")
    parser.add_argument('-o', '--open', action='store', nargs='*', type=state_machine_path, dest='sm_paths',
                        metavar='path',
                        help="specify directories of state-machines that shall be opened. Paths must contain a "
                             "statemachine.yaml file")
    parser.add_argument('-c', '--config', action='store', type=config_path, metavar='path', dest='config_path',
                        default=home_path, nargs='?', const=home_path,
                        help="path to the configuration file config.yaml. Use 'None' to prevent the generation of "
                             "a config file and use the default configuration. Default: {0}".format(home_path))
    parser.add_argument('-g', '--gui_config', action='store', type=config_path, metavar='path', dest='gui_config_path',
                        default=home_path, nargs='?', const=home_path,
                        help="path to the configuration file gui_config.yaml. Use 'None' to prevent the generation of "
                             "a config file and use the default configuration. Default: {0}".format(home_path))

    result = parser.parse_args()
    setup_config = vars(result)

    signal.signal(signal.SIGINT, sm_singletons.signal_handler)

    global_config.load(path=setup_config['config_path'])
    global_gui_config.load(path=setup_config['gui_config_path'])
    global_runtime_config.load(path=setup_config['gui_config_path'])

    # Make mvc directory the working directory
    # Needed for views, which assume to be in the mvc path and import glade files relatively
    os.chdir(join(rafcon_root_path, 'mvc'))

    # Initialize library
    sm_singletons.library_manager.initialize()

    # Set base path of global storage
    sm_singletons.global_storage.base_path = RAFCON_TEMP_PATH_STORAGE

    # Create the GUI
    main_window_view = MainWindowView()

    if setup_config['sm_paths']:
        storage = StateMachineStorage()
        for path in setup_config['sm_paths']:
            try:
                state_machine, version, creation_time = storage.load_statemachine_from_path(path)
                sm_singletons.state_machine_manager.add_state_machine(state_machine)
            except Exception as e:
                logger.error("Could not load state-machine {0}: {1}\n{2}".format(path,
                                                                                 e.message,
                                                                                 traceback.format_exc()))

    if setup_config['new']:
        root_state = HierarchyState()
        state_machine = StateMachine(root_state)
        sm_singletons.state_machine_manager.add_state_machine(state_machine)

    sm_manager_model = mvc_singletons.state_machine_manager_model

    main_window_controller = MainWindowController(sm_manager_model, main_window_view, editor_type='LogicDataGrouped')

    # Ensure that the next message is being printed (needed for LN manager to detect finished startup)
    level = logger.level
    logger.setLevel(logging.INFO)
    logger.info("Ready")
    logger.setLevel(level)

    try:
        # check if monitoring plugin is loaded
        from plugins.monitoring.monitoring_manager import global_monitoring_manager

        main_window_view.hide()
        gtk.gdk.flush()

        def initialize_monitoring_manager(some_value):

            global_monitoring_manager.initialize(setup_config)

            main_window_view.show()
            gtk.gdk.flush()

        import threading
        init_thread = threading.Thread(target=initialize_monitoring_manager, args=[5.0, ])
        init_thread.start()
        # reactor.callLater(2.0, initialize_monitoring_manager)

        if global_monitoring_manager.networking_enabled():
            # gtk.main()
            reactor.run()
        else:
            gtk.main()

    except ImportError, e:
        logger.info("Monitoring plugin not found: executing the GUI directly")
        # plugin not found
        gtk.main()

    logger.info("Joined root state")

    # If there is a running state-machine, wait for it to be finished before exiting
    sm = sm_singletons.state_machine_manager.get_active_state_machine()
    if sm:
        sm.root_state.join()

    logger.info("Exiting ...")

    # this is a ugly process shutdown method but works if gtk or twisted process are still blocking
    import os
    os._exit(0)
