import QtQuick 2.1
import QtQuick.Controls 2.0
import QtQuick.Layouts 1.1
import QtQuick.Window 2.1

import UM 1.5 as UM
import Cura 1.0 as Cura

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

            UM.Label
            {
                id: pageTitle
                text: catalog.i18nc("@title", "Connect to fabWeaver")
                wrapMode: Text.WordWrap
                font.pointSize: 18
            }
        }

        UM.Label
        {
            id: pageDescription
            width: parent.width
            wrapMode: Text.WordWrap
            text: catalog.i18nc("@label", "Select your fabWeaver instance from the list below.")
        }

        Row
        {
            spacing: UM.Theme.getSize("default_lining").width

            Cura.SecondaryButton
            {
                id: addButton
                text: catalog.i18nc("@action:button", "Add");
                onClicked:
                {
                    manualInstanceDialog.showDialog("", "", "80");
                }
            }

            Cura.SecondaryButton
            {
                id: editButton
                text: catalog.i18nc("@action:button", "Edit")
                enabled: base.selectedInstance != null && base.selectedInstance.getProperty("manual") == "true"
                onClicked:
                {
                    manualInstanceDialog.showDialog(
                        base.selectedInstance.name,
                        base.selectedInstance.ipAddress,
                        base.selectedInstance.port
                    );
                }
            }

            Cura.SecondaryButton
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

            Rectangle
            {
                width: Math.floor(parent.width * 0.4)
                height: base.height - (parent.y + UM.Theme.getSize("default_margin").height)

                color: UM.Theme.getColor("main_background")
                border.width: UM.Theme.getSize("default_lining").width
                border.color: UM.Theme.getColor("thick_lining")

                ListView
                {
                    id: listview
                    clip: true
                    ScrollBar.vertical: UM.ScrollBar {}

                    anchors.fill: parent
                    anchors.margins: UM.Theme.getSize("default_lining").width
                    
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
                    currentIndex: activeIndex
                    onCurrentIndexChanged:
                    {
                        base.selectedInstance = listview.model[currentIndex];
                    }
                    
                    Component.onCompleted: manager.startDiscovery()

                    delegate: Rectangle
                    {
                        height: childrenRect.height
                        color: ListView.isCurrentItem ? UM.Theme.getColor("text_selection") : UM.Theme.getColor("main_background")
                        width: parent.width
                        UM.Label
                        {
                            anchors.left: parent.left
                            anchors.leftMargin: UM.Theme.getSize("default_margin").width
                            anchors.right: parent.right
                            text: listview.model[index].name
                            elide: Text.ElideRight
                            font.italic: listview.model[index].key == manager.instanceId
                            wrapMode: Text.NoWrap
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

            Column
            {
                width: Math.floor(parent.width * 0.6)
                spacing: UM.Theme.getSize("default_margin").height
                UM.Label
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
                    UM.Label
                    {
                        width: Math.floor(parent.width * 0.2)
                        wrapMode: Text.WordWrap
                        text: catalog.i18nc("@label", "Address")
                    }
                    UM.Label
                    {
                        width: Math.floor(parent.width * 0.75)
                        wrapMode: Text.WordWrap
                        text: base.selectedInstance ? "%1:%2".arg(base.selectedInstance.ipAddress).arg(String(base.selectedInstance.port)) : ""
                    }
                    UM.Label
                    {
                        width: Math.floor(parent.width * 0.2)
                        wrapMode: Text.WordWrap
                        text: catalog.i18nc("@label", "Version")
                    }
                    UM.Label
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

                    Cura.SecondaryButton
                    {
                        text: catalog.i18nc("@action", "Open in browser...")
                        onClicked: manager.openWebPage(base.selectedInstance.baseURL)
                    }

                    Cura.SecondaryButton
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

    ManualInstanceDialog
    {
        id: manualInstanceDialog
    }
}
