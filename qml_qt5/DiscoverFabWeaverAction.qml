import UM 1.2 as UM
import Cura 1.0 as Cura

import QtQuick 2.2
import QtQuick.Controls 1.1

import FabWeaverPlugin 1.0 as FabWeaverPlugin

Cura.MachineAction
{
    id: base
    anchors.fill: parent;
    property var selectedInstance: null
    property string activeMachineId:
    {
        if (Cura.MachineManager.activeMachineId != undefined)
        {
            return Cura.MachineManager.activeMachineId;
        }
        else if (Cura.MachineManager.activeMachine !== null)
        {
            manager.changeStage();
            return Cura.MachineManager.activeMachine.id;
        }

        CuraApplication.log("There does not seem to be an active machine");
        return "";
    }

    Column
    {
        anchors.fill: parent;
        id: discoverFabWeaverAction

        spacing: UM.Theme.getSize("default_margin").height
        width: parent.width

        SystemPalette { id: palette }
        UM.I18nCatalog { id: catalog; name:"cura" }

        Item
        {
            width: parent.width
            height: pageTitle.height

            Label
            {
                id: pageTitle
                text: catalog.i18nc("@title", "Connect to fabWeaver")
                wrapMode: Text.WordWrap
                font.pointSize: 18
            }
        }

        Label
        {
            id: pageDescription
            width: parent.width
            wrapMode: Text.WordWrap
            text: catalog.i18nc("@label", "Select your fabWeaver instance from the list below.")
        }

        Row
        {
            spacing: UM.Theme.getSize("default_lining").width

            Button
            {
                id: addButton
                text: catalog.i18nc("@action:button", "Add");
                onClicked:
                {
                    manualPrinterDialog.showDialog("", "", "80");
                }
            }

            Button
            {
                id: editButton
                text: catalog.i18nc("@action:button", "Edit")
                enabled: base.selectedInstance != null && base.selectedInstance.getProperty("manual") == "true"
                onClicked:
                {
                    manualPrinterDialog.showDialog(
                        base.selectedInstance.name,
                        base.selectedInstance.ipAddress,
                        base.selectedInstance.port
                    );
                }
            }

            Button
            {
                id: removeButton
                text: catalog.i18nc("@action:button", "Remove")
                enabled: base.selectedInstance != null && base.selectedInstance.getProperty("manual") == "true"
                onClicked: manager.removeManualInstance(base.selectedInstance.name)
            }
        }

        Row
        {
            width: parent.width
            spacing: UM.Theme.getSize("default_margin").width

            Item
            {
                width: Math.floor(parent.width * 0.4)
                height: base.height - parent.y

                ScrollView
                {
                    id: objectListContainer
                    frameVisible: true
                    width: parent.width
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: UM.Theme.getSize("default_margin").height

                    Rectangle
                    {
                        parent: viewport
                        anchors.fill: parent
                        color: palette.light
                    }

                    ListView
                    {
                        id: listview
                        model: manager.discoveredInstances

                        onModelChanged:
                        {
                            var selectedId = manager.instanceId;
                            for(var i = 0; i < model.length; i++) {
                                if(model[i].getId() == selectedId)
                                {
                                    currentIndex = i;
                                    return
                                }
                            }
                            currentIndex = -1;
                        }
                        width: parent.width
                        currentIndex: activeIndex
                        onCurrentIndexChanged:
                        {
                            base.selectedInstance = listview.model[currentIndex];
                        }
                        
                        Component.onCompleted: manager.startDiscovery()

                        delegate: Rectangle
                        {
                            height: childrenRect.height
                            color: ListView.isCurrentItem ? palette.highlight : index % 2 ? palette.base : palette.alternateBase
                            width: parent.width
                            Label
                            {
                                anchors.left: parent.left
                                anchors.leftMargin: UM.Theme.getSize("default_margin").width
                                anchors.right: parent.right
                                text: listview.model[index].name
                                color: parent.ListView.isCurrentItem ? palette.highlightedText : palette.text
                                elide: Text.ElideRight
                                font.italic: listview.model[index].key == manager.instanceId
                            }

                            MouseArea
                            {
                                anchors.fill: parent;
                                onClicked:
                                {
                                    if(!parent.ListView.isCurrentItem)
                                    {
                                        parent.ListView.view.currentIndex = index;
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Column
            {
                width: Math.floor(parent.width * 0.6)
                spacing: UM.Theme.getSize("default_margin").height
                Label
                {
                    visible: base.selectedInstance != null
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: base.selectedInstance ? base.selectedInstance.name : ""
                    font.pointSize: 16
                    elide: Text.ElideRight
                }
                Grid
                {
                    visible: base.selectedInstance != null
                    width: parent.width
                    columns: 2
                    rowSpacing: UM.Theme.getSize("default_lining").height
                    verticalItemAlignment: Grid.AlignVCenter
                    Label
                    {
                        width: Math.floor(parent.width * 0.2)
                        wrapMode: Text.WordWrap
                        text: catalog.i18nc("@label", "Address")
                    }
                    Label
                    {
                        width: Math.floor(parent.width * 0.75)
                        wrapMode: Text.WordWrap
                        text: base.selectedInstance ? "%1:%2".arg(base.selectedInstance.ipAddress).arg(String(base.selectedInstance.port)) : ""
                    }
                    Label
                    {
                        width: Math.floor(parent.width * 0.2)
                        wrapMode: Text.WordWrap
                        text: catalog.i18nc("@label", "Version")
                    }
                    Label
                    {
                        width: Math.floor(parent.width * 0.75)
                        wrapMode: Text.WordWrap
                        text: base.selectedInstance ? base.selectedInstance.fabWeaverVersion : ""
                    }
                }

                Flow
                {
                    visible: base.selectedInstance != null
                    spacing: UM.Theme.getSize("default_margin").width

                    Button
                    {
                        text: catalog.i18nc("@action", "Open in browser...")
                        onClicked: manager.openWebPage(base.selectedInstance.baseURL)
                    }

                    Button
                    {
                        text:
                        {
                            if (base.selectedInstance != null)
                            {
                                if (base.selectedInstance.getId() == manager.instanceId)
                                {
                                    return catalog.i18nc("@action:button", "Disconnect")
                                }
                            }
                            return  catalog.i18nc("@action:button", "Connect")
                        }
                        enabled: base.selectedInstance != null
                        onClicked:
                        {
                            if(base.selectedInstance.getId() == manager.instanceId) {
                                manager.setInstanceId("")
                            }
                            else
                            {
                                manager.setInstanceId(base.selectedInstance.getId())
                            }
                            completed()
                         }
                    }
                }
             }
        }
    }

    UM.Dialog
    {
        id: manualPrinterDialog
        property string oldName
        property alias nameText: nameField.text
        property alias addressText: addressField.text
        property alias portText: portField.text

        title: catalog.i18nc("@title:window", "Manually added fabWeaver instance")

        minimumWidth: 400 * screenScaleFactor
        minimumHeight: 160 * screenScaleFactor
        width: minimumWidth
        height: minimumHeight

        signal showDialog(string name, string address, string port)
        onShowDialog:
        {
            oldName = name;
            nameText = name;
            nameField.selectAll();
            nameField.focus = true;

            addressText = address;
            portText = port;

            manualPrinterDialog.show();
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

                Label
                {
                    text: catalog.i18nc("@label","Instance Name")
                    width: Math.floor(parent.width * 0.4)
                }

                TextField
                {
                    id: nameField
                    maximumLength: 20
                    width: Math.floor(parent.width * 0.6)
                    validator: RegExpValidator
                    {
                        regExp: /[a-zA-Z0-9\.\-\_\:\[\]]*/
                    }
                }

                Label
                {
                    text: catalog.i18nc("@label","IP Address")
                    width: Math.floor(parent.width * 0.4)
                }

                TextField
                {
                    id: addressField
                    maximumLength: 253
                    width: Math.floor(parent.width * 0.6)
                    validator: RegExpValidator
                    {
                        regExp: /[0-9\.]*/
                    }
                }

                Label
                {
                    text: catalog.i18nc("@label","Port Number")
                    width: Math.floor(parent.width * 0.4)
                }

                TextField
                {
                    id: portField
                    maximumLength: 5
                    width: Math.floor(parent.width * 0.6)
                    validator: RegExpValidator
                    {
                        regExp: /[0-9]*/
                    }
                }
            }
        }

        rightButtons: [
            Button {
                text: catalog.i18nc("@action:button","Cancel")
                onClicked:
                {
                    manualPrinterDialog.reject()
                    manualPrinterDialog.hide()
                }
            },
            Button {
                text: catalog.i18nc("@action:button", "Ok")
                onClicked:
                {
                    manualPrinterDialog.accept()
                    manualPrinterDialog.hide()
                }
                enabled: manualPrinterDialog.nameText.trim() != "" && manualPrinterDialog.addressText.trim() != ""
                isDefault: true
            }
        ]
    }
}
