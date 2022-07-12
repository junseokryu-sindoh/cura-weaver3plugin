import UM 1.2 as UM
import Cura 1.0 as Cura

import QtQuick 2.2
import QtQuick.Controls 2.0

Item
{
    id: base

    property bool printerConnected: Cura.MachineManager.printerOutputDevices.length != 0
    property bool fabWeaverConnected: printerConnected && Cura.MachineManager.printerOutputDevices[0].toString().indexOf("FabWeaverOutputDevice") == 0

    Cura.SecondaryButton
    {
        objectName: "openFabWeaverButton"
        height: UM.Theme.getSize("save_button_save_to_button").height
        tooltip: catalog.i18nc("@info:tooltip", "Open the fabWeaver web interface")
        text: catalog.i18nc("@action:button", "web Monitor")
        onClicked: manager.openWebPage(Cura.MachineManager.printerOutputDevices[0].baseURL)
        visible: fabWeaverConnected
    }

    UM.I18nCatalog{id: catalog; name:"fabWeaver"}
}