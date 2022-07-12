from contextlib import nullcontext
from pickle import FALSE
from UM.i18n import i18nCatalog
from UM.Logger import Logger
from UM.Signal import signalemitter
from UM.Message import Message
from UM.Mesh.MeshWriter import MeshWriter
from UM.PluginRegistry import PluginRegistry

from cura.CuraApplication import CuraApplication

from .WebcamsModel import WebcamsModel

from cura.PrinterOutput.GenericOutputController import GenericOutputController
from cura.PrinterOutput.PrinterOutputDevice import ConnectionState
from cura.PrinterOutput.Models.PrinterOutputModel import PrinterOutputModel
from cura.PrinterOutput.Models.PrintJobOutputModel import PrintJobOutputModel
from cura.PrinterOutput.Models.MaterialOutputModel import MaterialOutputModel

from cura.PrinterOutput.NetworkedPrinterOutputDevice import NetworkedPrinterOutputDevice

USE_QT5 = False
try:
    from PyQt6.QtNetwork import QHttpPart, QNetworkRequest, QNetworkAccessManager
    from PyQt6.QtNetwork import QNetworkReply, QSslConfiguration, QSslSocket
    from PyQt6.QtCore import QUrl, QTimer, pyqtSignal, pyqtProperty, pyqtSlot #, QCoreApplication
    from PyQt6.QtGui import QDesktopServices    #, QImage

    QNetworkAccessManagerOperations = QNetworkAccessManager.Operation
    QNetworkRequestKnownHeaders = QNetworkRequest.KnownHeaders
    QNetworkRequestAttributes = QNetworkRequest.Attribute
    QNetworkReplyNetworkErrors = QNetworkReply.NetworkError
    QSslSocketPeerVerifyModes = QSslSocket.PeerVerifyMode

except ImportError:

    from PyQt5.QtNetwork import QHttpPart, QNetworkRequest, QNetworkAccessManager
    from PyQt5.QtNetwork import QNetworkReply, QSslConfiguration, QSslSocket
    from PyQt5.QtCore import QUrl, QTimer, pyqtSignal, pyqtProperty, pyqtSlot   #, QCoreApplication
    from PyQt5.QtGui import QDesktopServices

    QNetworkAccessManagerOperations = QNetworkAccessManager
    QNetworkRequestKnownHeaders = QNetworkRequest
    QNetworkRequestAttributes = QNetworkRequest
    QNetworkReplyNetworkErrors = QNetworkReply
    QSslSocketPeerVerifyModes = QSslSocket

    USE_QT5 = True

import json
import os.path
from time import time
import base64
from io import StringIO, BytesIO
from enum import IntEnum

from typing import cast, Any, Callable, Dict, List, Optional, Union, TYPE_CHECKING
if TYPE_CHECKING:
    from UM.Scene.SceneNode import SceneNode  # For typing.
    from UM.FileHandler.FileHandler import FileHandler  # For typing.

i18n_catalog = i18nCatalog("cura")

##  The current processing state of the backend.
#   This shadows PrinterOutputDevice.ConnectionState because its spelling changed
#   between Cura 4.0 beta 1 and beta 2


class UnifiedConnectionState(IntEnum):
    try:
        Closed = ConnectionState.Closed
        Connecting = ConnectionState.Connecting
        Connected = ConnectionState.Connected
        Busy = ConnectionState.Busy
        Error = ConnectionState.Error
    except AttributeError:
        Closed = ConnectionState.closed          # type: ignore
        Connecting = ConnectionState.connecting  # type: ignore
        Connected = ConnectionState.connected    # type: ignore
        Busy = ConnectionState.busy              # type: ignore
        Error = ConnectionState.error            # type: ignore


@signalemitter
class FabWeaverOutputDevice(NetworkedPrinterOutputDevice):
    def __init__(self, instance_id: str, address: str, port: int, properties: dict, **kwargs) -> None:
        super().__init__(device_id=instance_id, address=address, properties=properties, **kwargs)

        self._address = address
        self._port = port
        self._path = properties.get(b"path", b"/").decode("utf-8")
        if self._path[-1:] != "/":
            self._path += "/"
        self._id = instance_id
        self._properties = properties  # Properties dict as provided by zero conf

        self._printer_model = ""
        self._printer_name = ""

        self._fabWeaver_version = self._properties.get(b"version", b"").decode("utf-8")

        self._gcode_stream = StringIO()  # type: Union[StringIO, BytesIO]

        # We start with a single extruder, but update this when we get data from fabWeaver
        self._number_of_extruders_set = True  # False
        self._number_of_extruders = 2  # 1

        # Try to get version information from plugin.json
        plugin_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugin.json")
        try:
            with open(plugin_file_path) as plugin_file:
                plugin_info = json.load(plugin_file)
                plugin_version = plugin_info["version"]
        except:
            # The actual version info is not critical to have so we can continue
            plugin_version = "Unknown"
            Logger.logException("w", "Could not get version information for the plugin")
        application = CuraApplication.getInstance()
        self._user_agent = ("%s/%s %s/%s" % (
            application.getApplicationName(),
            application.getVersion(),
            "FabWeaverPlugin",
            plugin_version
        ))  # NetworkedPrinterOutputDevice defines this as string, so we encode this later

        self._api_prefix = "api/v1/"

        self._protocol = "https" if properties.get(b'useHttps') == b"true" else "http"
        self._base_url = "%s://%s:%d%s" % (self._protocol, self._address, self._port, self._path)
        self._api_url = self._base_url + self._api_prefix
        
        self._file_name = ""

        self._basic_auth_data = None
        self._basic_auth_string = ""
        basic_auth_username = properties.get(b"userName", b"").decode("utf-8")
        basic_auth_password = properties.get(b"password", b"").decode("utf-8")
        if basic_auth_username and basic_auth_password:
            data = base64.b64encode(("%s:%s" % (basic_auth_username, basic_auth_password)).encode()).decode("utf-8")
            self._basic_auth_data = ("basic %s" % data).encode()
            self._basic_auth_string = "%s:%s" % (basic_auth_username, basic_auth_password)

        # In Cura 4.x, the monitor item shows the camera stream as well as the monitor sidebar
        qml_folder = "qml_qt6" if not USE_QT5 else "qml_qt5"
        self._monitor_view_qml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), qml_folder, "FabWeaverMonitor.qml")

        self.setPriority(2)  # Make sure the output device gets selected above local file output
        self.setName(self._id)
        self.setShortDescription(i18n_catalog.i18nc("@action:button", "Print with fabWeaver"))
        self.setDescription(i18n_catalog.i18nc("@properties:tooltip", "Print with fabWeaver"))
        self.setIconName("print")
        self.setConnectionText(i18n_catalog.i18nc("@info:status", "Connected to fabWeaver on {0}").format(self._id))

        self._post_gcode_reply = None

        self._progress_message = None  # type: Optional[Message]
        self._error_message = None  # type: Optional[Message]

        # TODO; Add preference for update intervals
        self._update_fast_interval = 2000
        self._update_slow_interval = 10000
        self._update_timer = QTimer()
        self._update_timer.setInterval(self._update_fast_interval)
        self._update_timer.setSingleShot(False)
        self._update_timer.timeout.connect(self._update)

        self._webcams_model = WebcamsModel(self._protocol, self._address, self.port, self._basic_auth_string)

        self._output_controller = GenericOutputController(self)
        self._output_controller.can_control_manually = False
        self._output_controller.can_pre_heat_hotends = False
        self._output_controller.can_pre_heat_bed = False
        
        self._polling_end_points = ["printer"]

        self._printer_available = False
        self._spoolData =  None
        self._openSpool = False
        self._chamberCurrent = 0
        self._chamberTarget = 0


    def getProperties(self) -> Dict[bytes, bytes]:
        return self._properties

    @pyqtSlot(str, result=str)
    def getProperty(self, key: str) -> str:
        key_b = key.encode("utf-8")
        if key_b in self._properties:
            return self._properties.get(key_b, b"").decode("utf-8")
        else:
            return ""

    ##  Get the unique key of this machine
    #   \return key String containing the key of the machine.
    @pyqtSlot(result=str)
    def getId(self) -> str:
        return self._id

    ##  Name of the instance (as returned from the zeroConf properties)
    @pyqtProperty(str, constant=True)
    def name(self) -> str:
        return self._name

    additionalDataChanged = pyqtSignal()

    ##  Version (as returned from the zeroConf properties or from /api/version)
    @pyqtProperty(str, notify=additionalDataChanged)
    def fabWeaverVersion(self) -> str:
        return self._fabWeaver_version

    @pyqtProperty(str, notify=additionalDataChanged)
    def printerName(self) -> str:
        return self._printer_name

    @pyqtProperty(str, notify=additionalDataChanged)
    def printerModel(self) -> str:
        return self._printer_model

    ## IPadress of this instance
    @pyqtProperty(str, constant=True)
    def ipAddress(self) -> str:
        return self._address

    ## IPadress of this instance
    @pyqtProperty(str, notify=additionalDataChanged)
    def address(self) -> str:
        return self._address

    ## port of this instance
    @pyqtProperty(int, constant=True)
    def port(self) -> int:
        return self._port

    ## path of this instance
    @pyqtProperty(str, constant=True)
    def path(self) -> str:
        return self._path

    ## absolute url of this instance
    @pyqtProperty(str, constant=True)
    def baseURL(self) -> str:
        return self._base_url

    @pyqtProperty("QVariant", constant=True)
    def webcamsModel(self) -> WebcamsModel:
        return self._webcams_model

    def _update(self) -> None:
        for end_point in self._polling_end_points:
            self.get(end_point, self._onRequestFinished)

    @pyqtProperty("QVariant", notify=additionalDataChanged)
    def spoolData(self):
        return self._spoolData

    @pyqtProperty(int, notify=additionalDataChanged)
    def chamberCurrent(self) -> int:
        return self._chamberCurrent

    @pyqtProperty(int, notify=additionalDataChanged)
    def chamberTarget(self) -> int:
        return self._chamberTarget

    @pyqtProperty(bool, notify=additionalDataChanged)
    def isOpenSpool(self) -> bool:
        return self._openSpool

    def close(self) -> None:
        self._update_timer.stop()

        self.setConnectionState(cast(ConnectionState, UnifiedConnectionState.Closed))
        if self._progress_message:
            self._progress_message.hide()
            self._progress_message = None  # type: Optional[Message]
        if self._error_message:
            self._error_message.hide()
            self._error_message = None  # type: Optional[Message]

        self._polling_end_points = [point for point in self._polling_end_points if not point.startswith("files/")]

    ##  Start requesting data from the instance
    def connect(self) -> None:
        self._createNetworkManager()

        self.setConnectionState(cast(ConnectionState, UnifiedConnectionState.Connecting))
        self._update()  # Manually trigger the first update, as we don't want to wait a few secs before it starts.

        Logger.log("d", "Connection with instance %s with url %s started", self._id, self._base_url)
        self._update_timer.start()

        self._last_response_time = None  # type: Optional[float]
        self._setAcceptsCommands(False)
        self.setConnectionText(i18n_catalog.i18nc("@info:status", "Connecting to fabWeaver on {0}").format(self._id))

        webcam_data = {'flipH': True, 'flipV': True, 'rotate90': False}
        webcam_data['streamUrl'] = self._webcam_url = "%s://%s:8080/?action=stream" % (self._protocol, self._address)
        webcam_data['name'] = 'test'
        self._webcams_model.deserialise([webcam_data])

    ##  Stop requesting data from the instance
    def disconnect(self) -> None:
        Logger.log("d", "Connection with instance %s with url %s stopped", self._id, self._base_url)
        self.close()

    def pausePrint(self) -> None:
        self._sendJobCommand("Pause")

    def resumePrint(self) -> None:
        if not self._printers[0].activePrintJob:
            Logger.log("e", "There is no active printjob to resume")
            return
        
        if self._printers[0].activePrintJob.state == "paused":
            self._sendJobCommand("Resume")
        else:
            self._sendJobCommand("Pause")

    def cancelPrint(self) -> None:
        self._sendJobCommand("Stop")

    def requestWrite(self, nodes: List["SceneNode"], file_name: Optional[str] = None, limit_mimetypes: bool = False,
                     file_handler: Optional["FileHandler"] = None, filter_by_machine: bool = False, **kwargs) -> None:
        global_container_stack = CuraApplication.getInstance().getGlobalContainerStack()
        if not global_container_stack or not self.activePrinter:
            Logger.log("e", "There is no active printer to send the print")
            return

        # Make sure post-processing plugin are run on the gcode
        self.writeStarted.emit(self)

        gcode_writer = cast(MeshWriter, PluginRegistry.getInstance().getPluginObject("GCodeWriter"))
        self._gcode_stream = StringIO()

        if not gcode_writer.write(self._gcode_stream, None):
            Logger.log("e", "GCodeWrite failed: %s" % gcode_writer.getInformation())
            return

        if self._error_message:
            self._error_message.hide()
            self._error_message = None  # type: Optional[Message]

        if self._progress_message:
            self._progress_message.hide()
            self._progress_message = None  # type: Optional[Message]

        error_string = ""
        if self.activePrinter.state not in ["idle", ""]:
            Logger.log("d", "Tried starting a print, but current state is %s" % self.activePrinter.state)
            if self.activePrinter.state == "offline":
                error_string = i18n_catalog.i18nc("@info:status", "The printer is offline. Unable to start a new job.")
            else:
                error_string = i18n_catalog.i18nc("@info:status", "fabWeaver is busy. Unable to start a new job.")
        else:
            self._update() # check current _printer_available
            if not self._printer_available:
                Logger.log("d", "Tried starting a print, but current printer is not available")
                error_string = i18n_catalog.i18nc("@info:status", "is not available. Unable to start a new job.")

        if error_string:
            if self._error_message:
                self._error_message.hide()
            self._error_message = Message(error_string, title=i18n_catalog.i18nc("@label", "fabWeaver error"))
            self._error_message.show()
            return

        self._sendPrintJob()

    def _sendPrintJob(self) -> None:
        global_container_stack = CuraApplication.getInstance().getGlobalContainerStack()
        if not global_container_stack:
            return

        CuraApplication.getInstance().getController().setActiveStage("MonitorStage")
        # cancel any ongoing preheat timer before starting a print
        try:
            self._printers[0].stopPreheatTimers()
        except AttributeError:
            # stopPreheatTimers was added after Cura 3.3 beta
            pass

        self._progress_message = Message(
            i18n_catalog.i18nc("@info:status", "Sending data to fabWeaver"),
            title=i18n_catalog.i18nc("@label", "fabWeaver"),
            progress=-1, lifetime=0, dismissable=False, use_inactivity_timer=False
        )
        self._progress_message.addAction(
            "cancel", i18n_catalog.i18nc("@action:button", "Cancel"), "",
            i18n_catalog.i18nc("@action:tooltip", "Abort the printjob")
        )

        self._progress_message.actionTriggered.connect(self._cancelSendGcode)
        self._progress_message.show()

        print_info = CuraApplication.getInstance().getPrintInformation()
        job_name = print_info.jobName.strip()
        if job_name == "":
            job_name = "untitled_print"
        extension = "gcode"
        self._file_name = "%s.%s" % (os.path.basename(job_name), extension)

        ##  Create parts (to be placed inside multipart)
        gcode_body = self._gcode_stream.getvalue()
        if isinstance(gcode_body, str):
            # encode StringIO result to bytes
            gcode_body = gcode_body.encode()

        try:
            self._post_gcode_reply = self.post("resources/" + self._file_name  + "?override=true", gcode_body,
            on_finished=self._onUploadFinished, on_progress=self._onUploadProgress)
        except Exception as e:
            self._progress_message.hide()
            self._error_message = Message(
                i18n_catalog.i18nc("@info:status", "Unable to send data to fabWeaver."),
                title=i18n_catalog.i18nc("@label", "fabWeaver error")
            )
            self._error_message.show()
            Logger.log("e", "An exception occurred in network connection: %s" % str(e))

        self._gcode_stream = StringIO()  # type: Union[StringIO, BytesIO]

    def _cancelSendGcode(self, message: Message, action_id: str) -> None:
        self._progress_message = None  # type:Optional[Message]
        if message:
            message.hide()

        if self._post_gcode_reply:
            Logger.log("d", "Stopping upload because the user pressed cancel.")
            try:
                self._post_gcode_reply.uploadProgress.disconnect(self._onUploadProgress)
            except TypeError:
                pass  # The disconnection can fail on mac in some cases. Ignore that.

            self._post_gcode_reply.abort()
            self._post_gcode_reply = None  # type:Optional[QNetworkReply]

            self.delete("resources/" + self._file_name, on_finished=self._onDeleteFinished)

    def _sendJobCommand(self, command: str) -> None:
        self._sendCommandToApi("printer/control", command)
        Logger.log("d", "Sent job command to fabWeaver instance: %s", command)

    def _sendCommandToApi(self, end_point: str, commands: Union[Dict[str, Any], str, List[str]]) -> None:
        if isinstance(commands, dict):
            data = json.dumps(commands)
        elif isinstance(commands, list):
            data = json.dumps({"op": commands})#commands": commands})
        else:
            data = json.dumps({"op": commands})#command": commands})
        self.post(end_point, data, self._onRequestFinished)

    ##  Handler for all requests that have finished.
    def _onRequestFinished(self, reply: QNetworkReply) -> None:
        if reply.error() == QNetworkReplyNetworkErrors.TimeoutError:
            Logger.log("w", "Received a timeout on a request to the instance")
            self._connection_state_before_timeout = self._connection_state
            self.setConnectionState(cast(ConnectionState, UnifiedConnectionState.Error))
            return

        if self._connection_state_before_timeout and reply.error() == QNetworkReplyNetworkErrors.NoError:
            #  There was a timeout, but we got a correct answer again.
            if self._last_response_time:
                Logger.log("d", "We got a response from the instance after %s of silence", time() - self._last_response_time)
            self.setConnectionState(self._connection_state_before_timeout)
            self._connection_state_before_timeout = None

        if reply.error() == QNetworkReplyNetworkErrors.NoError:
            self._last_response_time = time()

        http_status_code = reply.attribute(QNetworkRequestAttributes.HttpStatusCodeAttribute)
        if not http_status_code:
            # Received no or empty reply
            return

        if reply.operation() == QNetworkAccessManagerOperations.GetOperation:
            if self._api_prefix + "printer" in reply.url().toString():  # Status update from /printer.
                if not self._printers:
                    self._createPrinterList()

                # fabWeaver instance has a single printer.
                printer = self._printers[0]
                if not printer:
                    Logger.log("e", "There is no active printer")
                    return
                update_pace = self._update_slow_interval

                if http_status_code == 200:
                    update_pace = self._update_fast_interval

                    if not self.acceptsCommands:
                        self._setAcceptsCommands(True)
                        self.setConnectionText(i18n_catalog.i18nc("@info:status", "Connected to fabWeaver on {0}").format(self._id))

                    if self._connection_state == UnifiedConnectionState.Connecting:
                        self.setConnectionState(cast(ConnectionState, UnifiedConnectionState.Connected))
                    try:
                        json_data = json.loads(bytes(reply.readAll()).decode("utf-8"))
                    except json.decoder.JSONDecodeError:
                        Logger.log("w", "Received invalid JSON from fabWeaver instance.")
                        json_data = {}

                    if "display_name" in json_data:
                        self._printer_name = json_data["display_name"]

                    if "model" in json_data:
                        self._printer_model = json_data["model"]

                    if "fdm" in json_data:
                        if "nozzle" in json_data["fdm"]:
                            if not self._number_of_extruders_set:
                                self._number_of_extruders = len(json_data["fdm"]["nozzle"])

                                if self._number_of_extruders > 1:
                                    # Recreate list of printers to match the new _number_of_extruders
                                    self._createPrinterList()
                                    printer = self._printers[0]

                                if self._number_of_extruders > 0:
                                    self._number_of_extruders_set = True

                            self._openSpool = json_data["open_material"]
                            self._spoolData = json_data["fdm"]["spool"]
                            self._chamberCurrent = json_data["fdm"]["chamber_temperature"]
                            self._chamberTarget = json_data["fdm"]["chamber_temperature_target"]

                            # Check for hotend temperatures
                            for index in range(0, self._number_of_extruders):
                                extruder = printer.extruders[index]
                                hotend_temperatures = json_data["fdm"]["nozzle"][index]
                                target_temperature = hotend_temperatures["temperature_target"] if hotend_temperatures["temperature_target"] is not None else -1
                                actual_temperature = hotend_temperatures["temperature"] if hotend_temperatures["temperature"] is not None else -1
                                extruder.updateTargetHotendTemperature(target_temperature)
                                extruder.updateHotendTemperature(actual_temperature)

                                isLoadedSpool = hotend_temperatures["spool_connect"] if hotend_temperatures["spool_connect"] is not None else -1
                                if isLoadedSpool == 1 :
                                    loaded_spoolno = hotend_temperatures["loaded_spoolno"] if hotend_temperatures["loaded_spoolno"] is not None else -1
                                    if loaded_spoolno >= 0 and loaded_spoolno < 4 :
                                        loaded_spool = json_data["fdm"]["spool"][loaded_spoolno]
                                        material = loaded_spool["material"] if loaded_spool["material"] is not None else -1
                                        color = loaded_spool["filament_color"] if loaded_spool["filament_color"] is not None else -1
                                        materialOutModel = MaterialOutputModel(guid = "", type = material, color = color, brand = "Generic", name = "Sindoh")
                                        extruder.updateActiveMaterial(materialOutModel)

                        # Check for bed temperatures
                        if "bed_temperature" in json_data["fdm"]:
                            actual_temperature = json_data["fdm"]["bed_temperature"] if json_data["fdm"]["bed_temperature"] is not None else -1
                            printer.updateBedTemperature(actual_temperature)
                        else:
                            printer.updateBedTemperature(-1)

                        if "bed_temperature_target" in json_data["fdm"]:
                            target_temperature = json_data["fdm"]["bed_temperature_target"] if json_data["fdm"]["bed_temperature_target"] is not None else -1
                            printer.updateTargetBedTemperature(target_temperature)
                        else:
                            printer.updateTargetBedTemperature(0)

                    # status
                    printer_state = "offline"
                    print_job_state = "offline"
                    if "status" in json_data:
                        state = json_data["status"]
                        if state == "error":
                            printer_state = "error"
                            print_job_state = "error"
                        elif state == "pausing":
                            printer_state = "paused"
                            print_job_state = "pausing"
                        elif state == "paused":
                            printer_state = "paused"
                            print_job_state = "paused"
                        elif state == "printing":
                            printer_state = "printing"
                            print_job_state = "printing"
                        elif state == "endingAlert":
                            printer_state = "printing"
                            print_job_state = "wait_cleanup"
                        elif state == "ready":
                            printer_state = "idle"
                            print_job_state = "ready"
                        elif state == "resuming":
                            printer_state = "printing"
                            print_job_state = "resuming"
                        elif state == "preparing":
                            printer_state = "printing"
                            print_job_state = "preparing"
                        elif state == "chamberHeating" or state == "cancelablePreparing":
                            printer_state = "printing"
                            print_job_state = "pre_print"
                        elif state == "cancelling":
                            printer_state = "printing"
                            print_job_state = "abort"
                        elif state == "jobExtruderJog":
                            printer_state = "printing"
                            print_job_state = "notPrintable"
                        elif state == "notPrintableScreen" or state == "noSpool" or state == "notLoaded" or state == "levelingNeeded" or state == "updating" or \
                        state == "restoring" or state == "loading" or state == "unloading" or state == "swUpdate" or state == "install" or state == "extruderJog" or\
                        state == "topDoorOpen" or state == "frontDoorOpen" or state == "userPopup" or state == "zoffset" or state == "cartridgeChanging" or \
                        state == "noFilament" or state == "xyzJog" or state == "nozzleCleaning" or state == "leveling" or state == "warning" or state == "userPopup" :
                            printer_state = "aborted"
                            print_job_state = "abort"
                        elif state == "unknown":
                            pass
                        else:
                            Logger.log("w", "Encountered unexpected printer, job state: %s" % state)

                    printer.updateState(printer_state)

                    if printer.activePrintJob is None:
                        print_job = PrintJobOutputModel(output_controller=self._output_controller)
                        printer.updateActivePrintJob(print_job)
                    else:
                        print_job = printer.activePrintJob

                    print_job.updateState(print_job_state)

                    # print_time = json_data["job_running_time"]
                    # completion = json_data["job_progress"]
                    # print_time_left = json_data["job_left_time"]
                    # if print_time:
                    #     print_job.updateTimeElapsed(print_time)

                    #     print_time_left = json_data["job_left_time"]
                    #     if print_time_left:  # not 0 or None or ""
                    #         print_job.updateTimeTotal(print_time + print_time_left)
                    #     elif completion:  # not 0 or None or ""
                    #         print_job.updateTimeTotal(print_time / (completion / 100))
                    #     else:
                    #         print_job.updateTimeTotal(0)
                    # else:
                    #     print_job.updateTimeElapsed(0)
                    #     print_job.updateTimeTotal(0)

                    total_time = json_data["job_running_time"]
                    print_time_left = json_data["job_left_time"]
                    completion = json_data["job_progress"]
                    if total_time:
                        print_job.updateTimeTotal(total_time)
                        if print_time_left :
                            print_job.updateTimeElapsed(total_time - print_time_left)
                        elif completion :
                            print_job.updateTimeElapsed(total_time * (completion / 100))
                        else:
                            print_job.updateTimeElapsed(0)
                    else:
                        print_job.updateTimeTotal(0)
                        print_job.updateTimeElapsed(0)

                    # printer available
                    if "available" in json_data:
                        self._printer_available = True if json_data["available"] == "available" else False

                    print_job.updateName(json_data["job_name"])

                    if "version" in json_data:
                        self._fabWeaver_version = json_data["version"]
                        self.additionalDataChanged.emit()

                elif http_status_code == 401 or http_status_code == 403:
                    self._setOffline(printer, i18n_catalog.i18nc(
                        "@info:status", "fabWeaver on {0} does not allow access to the printer state").format(self._id)
                    )
                    return

                elif http_status_code == 409:
                    if self._connection_state == UnifiedConnectionState.Connecting:
                        self.setConnectionState(cast(ConnectionState, UnifiedConnectionState.Connected))

                    self._setOffline(printer, i18n_catalog.i18nc(
                        "@info:status", "The printer connected to fabWeaver on {0} is not operational").format(self._id)
                    )
                    return

                elif http_status_code == 502 or http_status_code == 503:
                    Logger.log("w", "Received an error status code: %d", http_status_code)
                    self._setOffline(printer, i18n_catalog.i18nc(
                        "@info:status", "fabWeaver on {0} is not running").format(self._id)
                    )
                    return

                else:
                    self._setOffline(printer)
                    Logger.log("w", "Received an unexpected status code: %d", http_status_code)

                if update_pace != self._update_timer.interval():
                    self._update_timer.setInterval(update_pace)

        elif reply.operation() == QNetworkAccessManagerOperations.CustomOperation:
            if self._api_prefix + "resources" in reply.url().toString():  # Result from /resources command:
                if http_status_code == 200:
                    Logger.log("d", "fabWeaver resources(file upload) command accepted")

                elif http_status_code == 406:
                    error_string = i18n_catalog.i18nc("@info:error", "resources(file upload) command: Material mismatch")
                    self._showErrorMessage(error_string)
                    return

                elif http_status_code == 400:
                    error_string = i18n_catalog.i18nc("@info:error", "resources(file upload) command: Unavailable printer")
                    self._showErrorMessage(error_string)
                    return

                else:
                    pass  # See generic error handler below

        else:
            Logger.log("d", "FabWeaverOutputDevice got an unhandled operation %s", reply.operation())

        if http_status_code >= 400:
            if http_status_code == 401 or http_status_code == 403:
                error_string = i18n_catalog.i18nc("@info:error", "You are not allowed to access fabWeaver with the configured API key.")
            else:
                # Received another error reply
                error_string = bytes(reply.readAll()).decode("utf-8")
                if not error_string:
                    error_string = reply.attribute(QNetworkRequestAttributes.HttpReasonPhraseAttribute)

            self._showErrorMessage(error_string)
            Logger.log("e", "FabWeaverOutputDevice got an error while accessing %s", reply.url().toString())
            Logger.log("e", error_string)

    def _onUploadProgress(self, bytes_sent: int, bytes_total: int) -> None:
        if not self._progress_message:
            return

        if bytes_total > 0:
            # Treat upload progress as response. Uploading can take more than 10 seconds, so if we don't, we can get
            # timeout responses if this happens.
            self._last_response_time = time()

            progress = bytes_sent / bytes_total * 100
            previous_progress = self._progress_message.getProgress()
            if progress < 100:
                if previous_progress is not None and progress > previous_progress:
                    self._progress_message.setProgress(progress)
            else:
                self._progress_message.hide()
                self._progress_message = Message(
                    i18n_catalog.i18nc("@info:status", "Storing data on fabWeaver"),
                    0, False, -1, title=i18n_catalog.i18nc("@label", "fabWeaver")
                )
                self._progress_message.show()
        else:
            self._progress_message.setProgress(0)

    def _onUploadFinished(self, reply: QNetworkReply) -> None:
        reply.uploadProgress.disconnect(self._onUploadProgress)

        if self._progress_message:
            self._progress_message.hide()
            self._progress_message = None  # type:Optional[Message]

        http_status_code = reply.attribute(QNetworkRequestAttributes.HttpStatusCodeAttribute)

        error_string = ""
        if http_status_code == 200:
            Logger.log("d", "fabWeaver resources(print) command accepted")

        elif http_status_code >= 400:
            if http_status_code == 409:
                error_string = i18n_catalog.i18nc("@info:error", "fabWeaver a file with the same name.")
            elif http_status_code == 400:
                error_string = i18n_catalog.i18nc("@info:error", "Unabailable Printer.")
            elif http_status_code == 406:
                error_string = i18n_catalog.i18nc("@info:error", "Material mismatch.")
            else:
                # Received another error reply
                error_string = bytes(reply.readAll()).decode("utf-8")
                if not error_string:
                    error_string = reply.attribute(QNetworkRequestAttributes.HttpReasonPhraseAttribute)

        # if ((http_status_code != 406) and (error_string)) :
        if (error_string) :
            self._showErrorMessage(error_string)
            Logger.log("e", "FabWeaverOutputDevice got an %d error uploading to %s", http_status_code, reply.url().toString())
            Logger.log("e", error_string)
            return

        # send print command
        self.patch("resources/" + self._file_name + "?action=print", "", on_finished=self._onRequestFinished)

    def _onDeleteFinished(self, reply: QNetworkReply) -> None:

        http_status_code = reply.attribute(QNetworkRequestAttributes.HttpStatusCodeAttribute)

        error_string = ""
        if http_status_code == 200:
            Logger.log("d", "fabWeaver resources command accepted")

        elif http_status_code >= 400:
            if http_status_code == 409:
                error_string = i18n_catalog.i18nc("@info:error", "fabWeaver a file with the same name.")
            elif http_status_code == 400:
                error_string = i18n_catalog.i18nc("@info:error", "Unabailable Printer.")
            elif http_status_code == 406:
                error_string = i18n_catalog.i18nc("@info:error", "Material mismatch.")
            else:
                # Received another error reply
                error_string = bytes(reply.readAll()).decode("utf-8")
                if not error_string:
                    error_string = reply.attribute(QNetworkRequestAttributes.HttpReasonPhraseAttribute)

        if (error_string) :
            self._showErrorMessage(error_string)
            Logger.log("e", "FabWeaverOutputDevice got an %d error uploading to %s", http_status_code, reply.url().toString())
            Logger.log("e", error_string)

        return

    # def parseSettingsData(self, json_data: Dict[str, Any]) -> None:
    #     webcam_data = []
    #     if "webcam" in json_data and "streamUrl" in json_data["webcam"]:
    #         webcam_data = [json_data["webcam"]]

    #     if "plugins" in json_data:
    #         plugin_data = json_data["plugins"]

    #         if "multicam" in plugin_data:
    #             webcam_data = plugin_data["multicam"]["multicam_profiles"]

    #     self._webcams_model.deserialise(webcam_data)

    def _createPrinterList(self) -> None:
        printer = PrinterOutputModel(output_controller=self._output_controller, number_of_extruders=self._number_of_extruders)
        printer.updateName(self.name)
        self._printers = [printer]
        self.printersChanged.emit()

    def _setOffline(self, printer: PrinterOutputModel, reason: str = "") -> None:
        if not printer:
            Logger.log("e", "There is no active printer")
            return
        if printer.state != "offline":
            printer.updateState("offline")
            if printer.activePrintJob:
                printer.activePrintJob.updateState("offline")
            self.setConnectionText(reason)
            Logger.log("w", reason)

    def _showErrorMessage(self, error_string: str) -> None:
        if self._error_message:
            self._error_message.hide()
        self._error_message = Message(error_string, title=i18n_catalog.i18nc("@label", "fabWeaver error"))
        self._error_message.show()

    def _openFabWeaver(self, message: Message, action_id: str) -> None:
        QDesktopServices.openUrl(QUrl(self._base_url))

    def _createEmptyRequest(self, target: str, content_type: Optional[str] = "application/json") -> QNetworkRequest:
        request = QNetworkRequest(QUrl(self._api_url + target))
        try:
            request.setAttribute(QNetworkRequestAttributes.FollowRedirectsAttribute, True)
        except AttributeError:
            # in Qt6, this is no longer possible (or required), see https://doc.qt.io/qt-6/network-changes-qt6.html#redirect-policies
            pass
        request.setRawHeader(b"User-Agent", self._user_agent.encode())

        if content_type is not None:
            request.setHeader(QNetworkRequestKnownHeaders.ContentTypeHeader, content_type)

        # ignore SSL errors (eg for self-signed certificates)
        ssl_configuration = QSslConfiguration.defaultConfiguration()
        ssl_configuration.setPeerVerifyMode(QSslSocketPeerVerifyModes.VerifyNone)
        request.setSslConfiguration(ssl_configuration)

        if self._basic_auth_data:
            request.setRawHeader(b"Authorization", self._basic_auth_data)

        return request

    # This is a patched version from NetworkedPrinterOutputdevice, which adds "form_data" instead of "form-data"
    def _createFormPart(self, content_header: str, data: bytes, content_type: Optional[str] = None) -> QHttpPart:
        part = QHttpPart()

        if not content_header.startswith("form-data;"):
            content_header = "form-data; " + content_header
        part.setHeader(QNetworkRequestKnownHeaders.ContentDispositionHeader, content_header)
        if content_type is not None:
            part.setHeader(QNetworkRequestKnownHeaders.ContentTypeHeader, content_type)

        part.setBody(data)
        return part

    ## Overloaded from NetworkedPrinterOutputDevice.get() to be permissive of
    #  self-signed certificates
    def get(self, url: str, on_finished: Optional[Callable[[QNetworkReply], None]]) -> None:
        self._validateManager()

        request = self._createEmptyRequest(url)
        self._last_request_time = time()

        if not self._manager:
            Logger.log("e", "No network manager was created to execute the GET call with.")
            return

        reply = self._manager.get(request)
        self._registerOnFinishedCallback(reply, on_finished)

    ## Overloaded from NetworkedPrinterOutputDevice.post() to backport https://github.com/Ultimaker/Cura/pull/4678
    #  and allow self-signed certificates
    def post(self, url: str, data: Union[str, bytes],
             on_finished: Optional[Callable[[QNetworkReply], None]],
             on_progress: Optional[Callable[[int, int], None]] = None) -> QNetworkReply:
        self._validateManager()

        request = self._createEmptyRequest(url)
        self._last_request_time = time()

        if not self._manager:
            Logger.log("e", "Could not find manager.")
            return

        body = data if isinstance(data, bytes) else data.encode()  # type: bytes
        reply = self._manager.post(request, body)
        if on_progress is not None:
            reply.uploadProgress.connect(on_progress)
        self._registerOnFinishedCallback(reply, on_finished)

        return reply

    def patch(self, url: str, data: Union[str, bytes],
             on_finished: Optional[Callable[[QNetworkReply], None]],
             on_progress: Optional[Callable[[int, int], None]] = None) -> None:
        self._validateManager()

        request = self._createEmptyRequest(url)
        self._last_request_time = time()

        if not self._manager:
            Logger.log("e", "Could not find manager.")
            return

        body = data if isinstance(data, bytes) else data.encode()  # type: bytes
        reply = self._manager.sendCustomRequest(request, b"PATCH", body)
        if on_progress is not None:
            reply.uploadProgress.connect(on_progress)
        self._registerOnFinishedCallback(reply, on_finished)

    def delete(self, url: str, on_finished: Optional[Callable[[QNetworkReply], None]]) -> None:
        """Sends a delete request to the given path.

        :param url: The path after the API prefix.
        :param on_finished: The function to be call when the response is received.
        """
        self._validateManager()

        request = self._createEmptyRequest(url)
        self._last_request_time = time()

        if not self._manager:
            Logger.log("e", "No network manager was created to execute the DELETE call with.")
            return

        reply = self._manager.deleteResource(request)
        self._registerOnFinishedCallback(reply, on_finished)