// Copyright (c) 2019 Ultimaker B.V.
// Cura is released under the terms of the LGPLv3 or higher.

import QtQuick 2.7
import QtQuick.Controls 1.1
import QtQuick.Controls.Styles 1.1
import QtQuick.Layouts 1.1

import UM 1.2 as UM
import Cura 1.0 as Cura

import "../qml"

Item
{
    id: base
    UM.I18nCatalog { id: catalog; name: "cura"}
    height: monitorItems.height

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
        height: deviceHeader.height + exInfo.height + bedInfo.height + chamberInfo.height + spoolInfo.height
                + rect1.height + rect2.height + rect3.height + mSection1.height + mSection2.height + mItem1.height + mItem2.height + mItem3.height

        anchors.fill: parent

        property var extrudersModel: CuraApplication.getExtrudersModel()

        Cura.OutputDeviceHeader
        {
            id: deviceHeader
            //visible: activePrinter != null
            outputDevice: connectedDevice
        }

        Rectangle
        {
            id: exInfo
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
            id: rect1
            color: UM.Theme.getColor("wide_lining")
            width: parent.width
            height: UM.Theme.getSize("thick_lining").width
            //visible: activePrinter != null
        }

        Cura.HeatedBedBox
        {
            id: bedInfo
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
            id: rect2
            color: UM.Theme.getColor("wide_lining")
            width: parent.width
            height: UM.Theme.getSize("thick_lining").width
            visible: activePrinter != null
        }

        Item
        {
            id: chamberInfo
            implicitWidth: parent.width
            visible: activePrinter != null

            height:
            {
                if (visible){
                    return UM.Theme.getSize("print_setup_extruder_box").height
                } else {
                    return 0
                }
            } 

            Rectangle
            {
                color: UM.Theme.getColor("main_background")
                anchors.fill: parent

                // Chamber label.
                Label
                {
                    text: catalog.i18nc("@label", "Chamber")
                    color: UM.Theme.getColor("text")
                    font: UM.Theme.getFont("default")
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.margins: UM.Theme.getSize("default_margin").width
                }

                // Chamber Target temperature.
                Label
                {
                    id: chamberTargetTemperature
                    text: activePrinter != null ? OutputDevice.chamberTarget + "??C" : ""
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
                Label
                {
                    id: chamberCurrentTemperature
                    text: activePrinter != null ? OutputDevice.chamberCurrent + "??C" : ""
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
            id: mSection1
            label: catalog.i18nc("@label", "Active print")
            width: base.width
            visible: activePrinter != null
        }


        MonitorItem
        {
            id: mItem1
            label: catalog.i18nc("@label", "Job Name")
            value: activePrintJob != null ? activePrintJob.name : ""
            width: base.width
            visible: activePrinter != null
        }

        MonitorItem
        {
            id: mItem2
            label: catalog.i18nc("@label", "Printing Time")
            value: activePrintJob != null ? getPrettyTime(activePrintJob.timeTotal) : ""
            width: base.width
            visible: activePrinter != null
        }

        MonitorItem
        {
            id: mItem3
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
            height:
            {
                if (visible)
                {
                    return childrenRect.height
                }
                else
                {
                    return 0
                }
            }
        }

        Rectangle
        {
            id: rect3
            color: UM.Theme.getColor("main_background")
            width: parent.width
            height: UM.Theme.getSize("default_margin").width
            visible: activePrinter != null
        }


        Cura.MonitorSection
        {
            id: mSection2
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
            height:
            {
                if (visible){
                    return childrenRect.height
                } else{
                    return 0
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
                    return 115
                } else{
                    return 0
                }
            }
            
            Repeater
            {
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