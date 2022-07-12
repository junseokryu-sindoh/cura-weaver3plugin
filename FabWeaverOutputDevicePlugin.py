from UM.OutputDevice.OutputDevicePlugin import OutputDevicePlugin
from .FabWeaverOutputDevice import FabWeaverOutputDevice

from UM.Signal import Signal, signalemitter
from UM.Application import Application
from UM.Logger import Logger

import json
import re

from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from cura.PrinterOutput.PrinterOutputModel import PrinterOutputModel

##  This plugin handles the connection detection & creation of output device objects for FabWeaver-connected printers.
#   Zero-Conf is used to detect printers, which are saved in a dict.
#   If we discover an instance that has the same key as the active machine instance a connection is made.
@signalemitter
class FabWeaverOutputDevicePlugin(OutputDevicePlugin):
    def __init__(self) -> None:
        super().__init__()
        self._instances = {} # type: Dict[str, FabWeaverOutputDevice]

        # Because the model needs to be created in the same thread as the QMLEngine, we use a signal.
        self.addInstanceSignal.connect(self.addInstance)
        self.removeInstanceSignal.connect(self.removeInstance)
        Application.getInstance().globalContainerStackChanged.connect(self.reCheckConnections)

        # Load custom instances from preferences
        self._preferences = Application.getInstance().getPreferences()
        self._preferences.addPreference("fabWeaver/manual_instances", "{}")

        try:
            self._manual_instances = json.loads(self._preferences.getValue("fabWeaver/manual_instances"))
        except ValueError:
            self._manual_instances = {} # type: Dict[str, Any]
        if not isinstance(self._manual_instances, dict):
            self._manual_instances = {} # type: Dict[str, Any]

        self._name_regex = re.compile(r"fabWeaver instance (\".*\"\.|on )(.*)\.")

    addInstanceSignal = Signal()
    removeInstanceSignal = Signal()
    instanceListChanged = Signal()

    ##  Start looking for devices on network.
    def start(self) -> None:
        self.startDiscovery()

    def startDiscovery(self) -> None:
        # self._printers = [] # type: List[PrinterOutputModel]
        instance_keys = list(self._instances.keys())
        for key in instance_keys:
            self.removeInstance(key)

        # Add manual instances from preference
        for name, properties in self._manual_instances.items():
            additional_properties = {
                b"manual": b"true"
            } # These additional properties use bytearrays to mimick the output of zeroconf
            self.addInstance(name, properties["address"], properties["port"], additional_properties)
        self.instanceListChanged.emit()

    def addManualInstance(self, name: str, address: str, port: int, path: str, useHttps: bool = False, userName: str = "", password: str = "") -> None:
        self._manual_instances[name] = {
            "address": address,
            "port": port
        }
        self._preferences.setValue("fabWeaver/manual_instances", json.dumps(self._manual_instances))

        properties = {
            b"manual": b"true"
        }

        if name in self._instances:
            self.removeInstance(name)

        self.addInstance(name, address, port, properties)
        self.instanceListChanged.emit()

    def removeManualInstance(self, name: str) -> None:
        if name in self._instances:
            self.removeInstance(name)
            self.instanceListChanged.emit()

        if name in self._manual_instances:
            self._manual_instances.pop(name, None)
            self._preferences.setValue("fabWeaver/manual_instances", json.dumps(self._manual_instances))

    ##  Stop looking for devices on network.
    def stop(self) -> None:
        pass

    def getInstances(self) -> Dict[str, Any]:
        return self._instances

    def reCheckConnections(self) -> None:
        global_container_stack = Application.getInstance().getGlobalContainerStack()
        if not global_container_stack:
            return

        for key in self._instances:
            if key == global_container_stack.getMetaDataEntry("fabweaver_id"):
                self._instances[key].connectionStateChanged.connect(self._onInstanceConnectionStateChanged)
                self._instances[key].connect()
            else:
                if self._instances[key].isConnected():
                    self._instances[key].close()

    ##  Because the model needs to be created in the same thread as the QMLEngine, we use a signal.
    def addInstance(self, name: str, address: str, port: int, properties: Dict[bytes, bytes]) -> None:
        instance = FabWeaverOutputDevice(name, address, port, properties)
        self._instances[instance.getId()] = instance
        global_container_stack = Application.getInstance().getGlobalContainerStack()
        if global_container_stack:
            Logger.log("w", "global_container_stack is not empty")

        if global_container_stack and instance.getId() == global_container_stack.getMetaDataEntry("fabweaver_id"):
            instance.connectionStateChanged.connect(self._onInstanceConnectionStateChanged)
            instance.connect()

    def removeInstance(self, name: str) -> None:
        instance = self._instances.pop(name, None)
        if instance:
            if instance.isConnected():
                instance.connectionStateChanged.disconnect(self._onInstanceConnectionStateChanged)
                instance.disconnect()

    ##  Handler for when the connection state of one of the detected instances changes
    def _onInstanceConnectionStateChanged(self, key: str) -> None:
        if key not in self._instances:
            return

        if self._instances[key].isConnected():
            self.getOutputDeviceManager().addOutputDevice(self._instances[key])
        else:
            self.getOutputDeviceManager().removeOutputDevice(key)
