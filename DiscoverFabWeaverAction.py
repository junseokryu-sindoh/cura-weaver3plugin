from operator import truediv
from UM.i18n import i18nCatalog
from UM.Logger import Logger
from UM.Settings.DefinitionContainer import DefinitionContainer
from UM.Settings.ContainerRegistry import ContainerRegistry

from cura.CuraApplication import CuraApplication
from cura.MachineAction import MachineAction

USE_QT5 = False
try:
    from PyQt6.QtCore import pyqtSignal, pyqtProperty, pyqtSlot, QUrl, QObject  #, QTimer
    from PyQt6.QtGui import QDesktopServices

except ImportError:
    from PyQt5.QtCore import pyqtSignal, pyqtProperty, pyqtSlot, QUrl, QObject  #, QTimer
    from PyQt5.QtGui import QDesktopServices
    USE_QT5 = True

from .FabWeaverOutputDevicePlugin import FabWeaverOutputDevicePlugin

import os.path

from typing import cast, Any, List, Optional

catalog = i18nCatalog("cura")


class DiscoverFabWeaverAction(MachineAction):
    def __init__(self, parent: QObject = None) -> None:
        super().__init__("DiscoverFabWeaverAction", catalog.i18nc("@action", "Connect fabWeaver"))

        self._application = CuraApplication.getInstance()
        self._network_plugin = None  # type: Optional[FabWeaverOutputDevicePlugin]

        qml_folder = "qml_qt6" if not USE_QT5 else "qml_qt5"
        self._qml_url = os.path.join(qml_folder, "DiscoverFabWeaverAction.qml")

        self._additional_components = None  # type:Optional[QObject]

        ContainerRegistry.getInstance().containerAdded.connect(self._onContainerAdded)
        self._application.engineCreatedSignal.connect(self._createAdditionalComponentsView)

    @pyqtSlot()
    def startDiscovery(self) -> None:
        if not self._plugin_id:
            return
        if not self._network_plugin:
            self._network_plugin = cast(FabWeaverOutputDevicePlugin, self._application.getOutputDeviceManager().getOutputDevicePlugin(self._plugin_id))
            if not self._network_plugin:
                return
            self._network_plugin.addInstanceSignal.connect(self._onInstanceDiscovery)
            self._network_plugin.removeInstanceSignal.connect(self._onInstanceDiscovery)
            self._network_plugin.instanceListChanged.connect(self._onInstanceDiscovery)
            self.instancesChanged.emit()
        else:
            # Restart bonjour discovery
            self._network_plugin.startDiscovery()

    def _onInstanceDiscovery(self, *args) -> None:
        self.instancesChanged.emit()

    @pyqtSlot(str)
    def removeManualInstance(self, name: str) -> None:
        if not self._network_plugin:
            return

        self._network_plugin.removeManualInstance(name)

    @pyqtSlot(str, str, int, str, bool, str, str)
    def setManualInstance(self, name: str, address: str, port: int, path: str, useHttps: bool, userName: str = "", password: str = "") -> None:
        if not self._network_plugin:
            return

        # This manual printer could replace a current manual printer
        self._network_plugin.removeManualInstance(name)

        self._network_plugin.addManualInstance(name, address, port, path, useHttps, userName, password)

    def _onContainerAdded(self, container: "ContainerInterface") -> None:
        # Add this action as a supported action to all machine definitions
        if (
            isinstance(container, DefinitionContainer) and
            container.getMetaDataEntry("type") == "machine" and
            container.getMetaDataEntry("supports_usb_connection")
        ):

            self._application.getMachineActionManager().addSupportedAction(container.getId(), self.getKey())

    instancesChanged = pyqtSignal()
    instanceIdChanged = pyqtSignal()

    @pyqtProperty("QVariantList", notify=instancesChanged)
    def discoveredInstances(self) -> List[Any]:
        if self._network_plugin:
            instances = list(self._network_plugin.getInstances().values())
            instances.sort(key=lambda k: k.name)
            return instances
        else:
            return []

    @pyqtSlot(str)
    def setInstanceId(self, key: str) -> None:
        global_container_stack = self._application.getGlobalContainerStack()
        if key == "":
            key2 = global_container_stack.getMetaDataEntry("fabweaver_id")
            self._network_plugin._instances[key2]._fabWeaver_version = ""
            self._network_plugin._instances[key2].additionalDataChanged.emit()

        if global_container_stack:
            global_container_stack.setMetaDataEntry("fabweaver_id", key)
        
        if self._network_plugin:
            # Ensure that the connection states are refreshed.
            self._network_plugin.reCheckConnections()
    
        self.instanceIdChanged.emit()

    @pyqtProperty(str, notify=instanceIdChanged)
    def instanceId(self) -> str:
        global_container_stack = self._application.getGlobalContainerStack()
        if not global_container_stack:
            return ""

        return global_container_stack.getMetaDataEntry("fabweaver_id", "")

    selectedInstanceSettingsChanged = pyqtSignal()

    @pyqtSlot(str)
    def openWebPage(self, url: str) -> None:
        QDesktopServices.openUrl(QUrl(url))

    # @pyqtSlot(result=str)
    # def getActiveStage(self) -> str:
    #     stage = CuraApplication.getInstance().getController().getActiveStage().getId()
    #     return stage.getId()

    @pyqtSlot(result=bool)
    def getEnableConnect(self) -> bool:
        stage = CuraApplication.getInstance().getController().getActiveStage().getId()
        if stage == "MonitorStage":
            return False
        return True

    @pyqtSlot()
    def changeStage(self) -> None:
        if CuraApplication.getInstance().getController().getActiveStage().getId() == "MonitorStage":
            CuraApplication.getInstance().getController().setActiveStage("PrepareStage")

    def _createAdditionalComponentsView(self) -> None:
        Logger.log("d", "Creating additional ui components for FabWeaver connected printers.")

        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qml", "FabWeaverComponents.qml")
        self._additional_components = self._application.createQmlComponent(path, {"manager": self})
        if not self._additional_components:
            Logger.log("w", "Could not create additional components for FabWeaver connected printers.")
            return

        self._application.addAdditionalComponent("monitorButtons", self._additional_components.findChild(QObject, "openFabWeaverButton"))
