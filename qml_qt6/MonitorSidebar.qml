import QtQuick 2.7
import QtQuick.Layouts 1.1
import QtQuick.Controls 2.15

import UM 1.5 as UM
import Cura 1.0 as Cura

import "../qml"

ScrollView
{
    id: base
    width: parent.width
    height: parent.height

    contentHeight: monitorItems.height

    ScrollBar.vertical: UM.ScrollBar
    {
        id: scrollbar
        parent: base.parent
        anchors
        {
            right: parent.right
            rightMargin: (UM.Theme.getSize("default_margin").width / 4)
            top: parent.top
            topMargin : UM.Theme.getSize("default_margin").height
            bottom: parent.bottom
            bottomMargin : UM.Theme.getSize("default_margin").height
        }
    }
    clip: true

    function showTooltip(item, position, text)
    {
        tooltip.text = text;
        position = item.mapToItem(base, position.x - UM.Theme.getSize("default_arrow").width, position.y);
        tooltip.show(position);
    }

    function hideTooltip()
    {
        tooltip.hide();
    }

    function strPadLeft(string, pad, length) {
        return (new Array(length + 1).join(pad) + string).slice(-length);
    }

    function getPrettyTime(time)
    {
        var hours = Math.floor(time / 3600)
        time -= hours * 3600
        var minutes = Math.floor(time / 60);
        time -= minutes * 60
        var seconds = Math.floor(time);

        var finalTime = strPadLeft(hours, "0", 2) + ":" + strPadLeft(minutes, "0", 2) + ":" + strPadLeft(seconds, "0", 2);
        return finalTime;
    }

    property var connectedDevice: Cura.MachineManager.printerOutputDevices.length >= 1 ? Cura.MachineManager.printerOutputDevices[0] : null
    property var activePrinter: connectedDevice != null ? connectedDevice.activePrinter : null
    property var activePrintJob: activePrinter != null ? activePrinter.activePrintJob: null

    Column
    {
        id: monitorItems

        UM.I18nCatalog { id: catalog; name: "cura" }

        width: parent.width

        property var extrudersModel: CuraApplication.getExtrudersModel()

        Cura.OutputDeviceHeader
        {
            //visible: activePrinter != null
            outputDevice: connectedDevice
        }

        Rectangle
        {
            color: UM.Theme.getColor("wide_lining")
            width: parent.width
            height: childrenRect.height

            Row
            {
                id: extrudersGrid
                spacing: UM.Theme.getSize("thick_lining").width
                width: parent.width

                Repeater
                {
                    id: extrudersRepeater
                    model: activePrinter != null ? activePrinter.extruders : null

                    Cura.ExtruderBox
                    {
                        color: UM.Theme.getColor("main_background")
                        width: index == machineExtruderCount.properties.value - 1 && index % 2 == 0 ? extrudersGrid.width : Math.round(extrudersGrid.width / 2 - UM.Theme.getSize("thick_lining").width / 2)
                        extruderModel: modelData
                    }
                }
            }
        }

        Rectangle
        {
            color: UM.Theme.getColor("wide_lining")
            width: parent.width
            height: UM.Theme.getSize("thick_lining").width
            //visible: activePrinter != null
        }

        Cura.HeatedBedBox
        {
            height : 50
            visible:
            {
                if(activePrinter != null && activePrinter.bedTemperature != -1)
                {
                    return true
                }
                return false
            }
            printerModel: activePrinter
        }

        Rectangle
        {
            color: UM.Theme.getColor("wide_lining")
            width: parent.width
            height: UM.Theme.getSize("thick_lining").width
            visible: activePrinter != null
        }

        Item
        {
            implicitWidth: parent.width
            height: 50
            visible: activePrinter != null

            Rectangle
            {
                color: UM.Theme.getColor("main_background")
                anchors.fill: parent

                // Chamber label.
                UM.Label
                {
                    text: catalog.i18nc("@label", "Chamber")
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.margins: UM.Theme.getSize("default_margin").width
                }

                // Chamber Target temperature.
                UM.Label
                {
                    id: chamberTargetTemperature
                    text: activePrinter != null ? OutputDevice.chamberTarget + "°C" : ""
                    font: UM.Theme.getFont("default_bold")
                    color: UM.Theme.getColor("text_inactive")
                    anchors.right: parent.right
                    anchors.rightMargin: UM.Theme.getSize("default_margin").width
                    anchors.bottom: chamberCurrentTemperature.bottom

                    //For tooltip.
                    MouseArea
                    {
                        id: chamberTargetTemperatureTooltipArea
                        hoverEnabled: true
                        anchors.fill: parent
                        onHoveredChanged:
                        {
                            if (containsMouse)
                            {
                                base.showTooltip(
                                    base,
                                    {x: 0, y: chamberTargetTemperature.mapToItem(base, 0, Math.floor(-parent.height / 4)).y},
                                    catalog.i18nc("@tooltip", "The target temperature of the chamber. The chamber will heat up or cool down towards this temperature. If this is 0, the chamber heating is turned off.")
                                );
                            }
                            else
                            {
                                base.hideTooltip();
                            }
                        }
                    }
                }

                // Chamber Current temperature.
                UM.Label
                {
                    id: chamberCurrentTemperature
                    text: activePrinter != null ? OutputDevice.chamberCurrent + "°C" : ""
                    font: UM.Theme.getFont("large_bold")
                    anchors.right: chamberTargetTemperature.left
                    anchors.top: parent.top
                    anchors.margins: UM.Theme.getSize("default_margin").width

                    //For tooltip.
                    MouseArea
                    {
                        id: chamberCurrentTemperatureTooltipArea
                        hoverEnabled: true
                        anchors.fill: parent
                        onHoveredChanged:
                        {
                            if (containsMouse)
                            {
                                base.showTooltip(
                                    base,
                                    {x: 0, y: parent.mapToItem(base, 0, Math.floor(-parent.height / 4)).y},
                                    catalog.i18nc("@tooltip", "The current temperature of the chamber.")
                                );
                            }
                            else
                            {
                                base.hideTooltip();
                            }
                        }
                    }
                }
            }
        }

        Rectangle
        {
            color: UM.Theme.getColor("wide_lining")
            width: parent.width
            height: UM.Theme.getSize("thick_lining").width
            visible: activePrinter != null
        }

        UM.SettingPropertyProvider
        {
            id: bedTemperature
            containerStack: Cura.MachineManager.activeMachine
            key: "material_bed_temperature"
            watchedProperties: ["value", "minimum_value", "maximum_value", "resolve"]
            storeIndex: 0

            property var resolve: Cura.MachineManager.activeStack != Cura.MachineManager.activeMachine ? properties.resolve : "None"
        }

        UM.SettingPropertyProvider
        {
            id: machineExtruderCount
            containerStack: Cura.MachineManager.activeMachine
            key: "machine_extruder_count"
            watchedProperties: ["value"]
        }

        Cura.MonitorSection
        {
            label: catalog.i18nc("@label", "Active print")
            width: base.width
            visible: activePrinter != null
        }

        MonitorItem
        {
            label: catalog.i18nc("@label", "Job Name")
            value: activePrintJob != null ? activePrintJob.name : ""
            width: base.width
            visible: activePrinter != null
        }

        MonitorItem
        {
            label: catalog.i18nc("@label", "Printing Time")
            value: activePrintJob != null ? getPrettyTime(activePrintJob.timeTotal) : ""
            width: base.width
            visible: activePrinter != null
        }

        MonitorItem
        {
            label: catalog.i18nc("@label", "Estimated time left")
            value: activePrintJob != null ? getPrettyTime(activePrintJob.timeTotal - activePrintJob.timeElapsed) : ""
            width: base.width
            visible:
            {
                if(activePrintJob == null)
                {
                    return false
                }
                return (activePrintJob.state == "printing" ||
                        activePrintJob.state == "resuming" ||
                        activePrintJob.state == "pausing" ||
                        activePrintJob.state == "paused")
            }
        }

        Rectangle
        {
            color: UM.Theme.getColor("wide_lining")
            width: parent.width
            height: UM.Theme.getSize("thick_lining").width
            visible: activePrinter != null
        }

        Cura.MonitorSection
        {
            label: 
            {
                if (OutputDevice.isOpenSpool == true)
                    catalog.i18nc("@label", "Open Material mode")
                else
                    catalog.i18nc("@label", "Spool Information")
            }
            width: base.width
            visible: 
            {
                if (activePrinter == null){
                    return false
                } else{
                    return true
                }
            }
        }

        Row{
            id: spoolInfo
            width: parent.width
            visible:
            {
                if ((OutputDevice.isOpenSpool == true) || (activePrinter == null)){
                    return false
                } else{
                    return true
                }
            }
            height:
            {
                if (visible){
                    return childrenRect.height  //115
                } else{
                    return 0
                }
            }

            Repeater
            {
                id: spoolRepeater
                model: 4
                Column{
                    width: Math.round( parent.width / 4)
                    property string spoolStatus: OutputDevice.spoolData[index]["status"]
                    property string textcolor:
                    {
                        if (spoolStatus == "load")
                            return UM.Theme.getColor("setting_category_text")
                        else
                            return "gray"
                    }
                    property string font:
                    {
                        if (spoolStatus == "load")
                            return UM.Theme.getFont("default_bold")
                        else
                            return UM.Theme.getFont("default")
                    }

                    Label{
                        text: "Spool "+ (index+1)
                        width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                        font: parent.font
                        color: parent.textcolor
                    }
                    ProgressBar {
                        size: 80
                        width: parent.width
                        lineWidth: 10
                        value:  (OutputDevice.spoolData[index]["filament_left"]/OutputDevice.spoolData[index]["filament_capacity"])
                        primaryColor:{
                            if (OutputDevice.spoolData[index]["filament_color"] == "#ffffff")
                                return "#f8f8f8"
                            else
                                return OutputDevice.spoolData[index]["filament_color"]
                        }
                        property string material: OutputDevice.spoolData[index]["material"]
                        secondaryColor: "#f0f0f0"
                        Text {
                            text: 
                            {
                                if ((parent.material != "") && ( parent.material != "unknown")){
                                    return (parent.material + "\n" + ((Math.round(parent.value * 10000))/100) + "%");
                                } else {
                                    return "None\n 0.00%";
                                }
                            }
                            anchors.centerIn: parent
                            horizontalAlignment: Text.AlignHCenter
                            font: parent.parent.font
                            color: parent.parent.textcolor
                        }
                    }
                    Label{
                        text:
                        {
                            if (parent.spoolStatus != ""){
                                return parent.spoolStatus;
                            } else {
                                return "not connected";
                            }

                        } 
                        color: parent.textcolor
                        width: parent.width                                    
                        horizontalAlignment: Text.AlignHCenter
                        font: parent.font
                    }
                }
            }
        }
    }

    Cura.PrintSetupTooltip
    {
        id: tooltip
    }
}