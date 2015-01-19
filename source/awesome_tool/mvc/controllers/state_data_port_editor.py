
from utils import log
logger = log.get_logger(__name__)

import gtk
from gtkmvc import Controller
from mvc.controllers.input_data_port_list import DataPortListController
from gtkmvc import Observer


class StateDataPortEditorController(Controller, Observer):

    #model will be a container state model
    def __init__(self, model, view):
        """Constructor
        """
        Controller.__init__(self, model, view)
        self.input_data_port_list_controller = DataPortListController(model, view.input_port_list_view, "input")
        self.output_data_port_list_controller = DataPortListController(model, view.output_port_list_view, "output")


    def register_view(self, view):

        view['state_dataport_editor'].connect('destroy', gtk.main_quit)

    #TODO: separate functions for inputs and outputs
    @Observer.observe("state", after=True)
    def assign_notification_state(self, model, prop_name, info):
        print "call_notification - AFTER:\n-%s\n-%s\n-%s\n-%s\n" %\
              (prop_name, info.instance, info.method_name, info.result)
        model.update_input_data_port_list_store()

