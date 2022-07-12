import os, json

from . import FabWeaverOutputDevicePlugin
from . import DiscoverFabWeaverAction
from . import NetworkMJPGImage
from . import Installer 

from UM.Version import Version
from UM.Application import Application
from UM.Logger import Logger

try:
    from PyQt6.QtQml import qmlRegisterType
except ImportError:
    from PyQt5.QtQml import qmlRegisterType

try:
    _installer = Installer.Installer()
    _installResource = True
except ImportError:
    _installResource = False
    Logger.log("w", "Could not import Installer")

def getMetaData():
    return {}

def register(app):
    if _installResource :
        _installer.installFiles()
     
    qmlRegisterType(NetworkMJPGImage.NetworkMJPGImage, "FabWeaverPlugin", 1, 0, "NetworkMJPGImage")

    return {
        "output_device": FabWeaverOutputDevicePlugin.FabWeaverOutputDevicePlugin(),
        "machine_action": DiscoverFabWeaverAction.DiscoverFabWeaverAction(),
    }
