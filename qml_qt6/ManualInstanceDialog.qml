import QtQuick 2.15
import QtQuick.Controls 2.0

import UM 1.5 as UM
import Cura 1.0 as Cura

UM.Dialog
{
    id: manualInstanceDialog
    property string oldName
    property alias nameText: nameField.text
    property alias addressText: addressField.text
    property alias portText: portField.text

    title: catalog.i18nc("@title:window", "Manually added fabWeaver instance")

    buttonSpacing: UM.Theme.getSize("default_margin").width
    minimumWidth: 400 * screenScaleFactor
    minimumHeight: 300 * screenScaleFactor
    width: minimumWidth
    height: minimumHeight

    property int firstColumnWidth: Math.floor(width * 0.3) - 2 * margin
    property int secondColumnWidth: Math.floor(width * 0.7) - 2 * margin

    signal showDialog(string name, string address, string port)
    onShowDialog:
    {
        oldName = name;
        nameText = name;
        nameField.selectAll();
        nameField.focus = true;

        addressText = address;
        portText = port;

        manualInstanceDialog.show();
    }

    onAccepted:
    {
        if(oldName != nameText)
        {
            manager.removeManualInstance(oldName);
        }
        if(portText == "")
        {
            portText = "80";
        }
        manager.setManualInstance(
            nameText,
            addressText,
            parseInt(portText),
            "/",
            false,
            "",
            "",
        );
    }

    Column {
        anchors.fill: parent
        spacing: UM.Theme.getSize("default_margin").height

        Grid
        {
            columns: 2
            width: parent.width
            verticalItemAlignment: Grid.AlignVCenter
            rowSpacing: UM.Theme.getSize("default_lining").height
            columnSpacing: UM.Theme.getSize("default_margin").width

            UM.Label
            {
                text: catalog.i18nc("@label","Instance Name")
                width: manualInstanceDialog.firstColumnWidth
            }

            Cura.TextField
            {
                id: nameField
                maximumLength: 20
                width: manualInstanceDialog.secondColumnWidth
                validator: RegularExpressionValidator
                {
                    regularExpression: /[a-zA-Z0-9\.\-\_\:\[\]]*/
                }
            }

            UM.Label
            {
                text: catalog.i18nc("@label","IP Address")
                width: manualInstanceDialog.firstColumnWidth
            }

            Cura.TextField
            {
                id: addressField
                maximumLength: 253
                width: manualInstanceDialog.secondColumnWidth
                validator: RegularExpressionValidator
                {
                    regularExpression: /[a-zA-Z0-9\.\-\_\:\/\@]*/
                }
            }

            UM.Label
            {
                text: catalog.i18nc("@label","Port Number")
                width: manualInstanceDialog.firstColumnWidth
            }

            Cura.TextField
            {
                id: portField
                maximumLength: 5
                width: manualInstanceDialog.secondColumnWidth
                validator: RegularExpressionValidator
                {
                    regularExpression: /[0-9]*/
                }
            }
        }
    }

    rightButtons: [
        Cura.SecondaryButton {
            text: catalog.i18nc("@action:button","Cancel")
            onClicked:
            {
                manualInstanceDialog.reject()
                manualInstanceDialog.hide()
            }
        },
        Cura.SecondaryButton {
            text: catalog.i18nc("@action:button", "Ok")
            onClicked:
            {
                manualInstanceDialog.accept()
                manualInstanceDialog.hide()
            }
            enabled: manualInstanceDialog.nameText.trim() != "" && manualInstanceDialog.addressText.trim() != ""
        }
    ]
}
