import QtQuick 2.7
import QtQuick.Controls 2.3
import QtQuick.Controls.Styles 1.4
import QtQuick.Layouts 1.3

import UM 1.3 as UM
import Cura 1.0 as Cura
import FabWeaverPlugin 1.0 as FabWeaverPlugin
import "."

Component{
    id: fabWeaverMonitor

    Item
    {
        id: mainMonitor
        property var webcamsModel: OutputDevice != null ? OutputDevice.webcamsModel : null
        property int activeIndex: 0

        FabWeaverPlugin.NetworkMJPGImage
        {
            id: cameraImage

            source: (OutputDevice != null && activeIndex < webcamsModel.count) ? webcamsModel.items[activeIndex].stream_url : ""
            rotation: (OutputDevice != null && activeIndex < webcamsModel.count) ? webcamsModel.items[activeIndex].rotation : 0
            mirror: (OutputDevice != null && activeIndex < webcamsModel.count) ? webcamsModel.items[activeIndex].mirror : false

            property real maximumWidthMinusSidebar: maximumWidth - sidebar.width - 2 * UM.Theme.getSize("default_margin").width
            property real maximumZoom: 2
            property bool rotatedImage: (rotation / 90) % 2
            property bool proportionalHeight:
            {
                if (imageHeight == 0 || maximumHeight == 0)
                {
                    return true;
                }
                if (!rotatedImage)
                {
                    return (imageWidth / imageHeight) > (maximumWidthMinusSidebar / maximumHeight);
                }
                else
                {
                    return (imageWidth / imageHeight) > (maximumHeight / maximumWidthMinusSidebar);
                }
            }
            property real _width:
            {
                if (!rotatedImage)
                {
                    return Math.min(maximumWidthMinusSidebar, imageWidth * screenScaleFactor * maximumZoom);
                }
                else
                {
                    return Math.min(maximumHeight, imageWidth * screenScaleFactor * maximumZoom);
                }
            }
            property real _height:
            {
                if (!rotatedImage)
                {
                    return Math.min(maximumHeight, imageHeight * screenScaleFactor * maximumZoom);
                }
                else
                {
                    return Math.min(maximumWidth, imageHeight * screenScaleFactor * maximumZoom);
                }
            }
            property bool visible_stream:false

            width: proportionalHeight ? _width : imageWidth * _height / imageHeight
            height: !proportionalHeight ? _height : imageHeight * _width / imageWidth
            anchors.horizontalCenter: horizontalCenterItem.horizontalCenter
            anchors.verticalCenter: parent.verticalCenter

            //visible: getActiveStageisMonitor();
            Component.onCompleted:
            {
                visible_stream = visible;
                if (visible) {
                    startStream();
                }
            }
            onVisibleChanged:
            {
                if (visible != visible_stream)
                {
                    if (visible) {
                        startStream();
                    } else {
                        stopStream();
                    }
                    visible_stream = visible;
                }
            }
        }

        Item
        {
            id: horizontalCenterItem
            anchors.left: parent.left
            anchors.right: sidebar.left
        }

        Cura.RoundedRectangle
        {
            id: sidebar
            width: UM.Theme.getSize("print_setup_widget").width
            height: parent.height - actionsPanel.height
            anchors
            {
                right: parent.right
                rightMargin: UM.Theme.getSize("default_margin").height
                top: parent.top
                topMargin: UM.Theme.getSize("default_margin").height
                bottom: actionsPanel.top
            }

            border.width: UM.Theme.getSize("default_lining").width
            border.color: UM.Theme.getColor("lining")
            color: UM.Theme.getColor("main_background")

            cornerSide: Cura.RoundedRectangle.Direction.Left
            radius: UM.Theme.getSize("default_radius").width

            ScrollView{
                id: scrollview
                clip : true
                width: parent.width
                height : parent.height
                contentHeight: printMonitor.height
                
                ScrollBar.vertical.policy: (ScrollBar.vertical.size < 1.0) ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
                ScrollBar.vertical.implicitWidth: (ScrollBar.vertical.size < 1.0) ? UM.Theme.getSize("scrollbar").width + ScrollBar.vertical.leftPadding + ScrollBar.vertical.rightPadding : 0
                //ScrollBar.vertical.minimumSize: orientation === Qt.Horizontal ? height / width : width / height

                ScrollBar.vertical.background: Rectangle
                {
                    implicitWidth: UM.Theme.getSize("scrollbar").width

                    radius: implicitWidth / 2
                    color: UM.Theme.getColor("scrollbar_background")
                }

                ScrollBar.vertical.contentItem: Rectangle
                {
                    implicitWidth: UM.Theme.getSize("scrollbar").width

                    radius: implicitWidth / 2
                    color: parent.pressed ? UM.Theme.getColor("scrollbar_handle_down") : parent.hovered ? UM.Theme.getColor("scrollbar_handle_hover") : UM.Theme.getColor("scrollbar_handle")
                    Behavior on color { ColorAnimation { duration: 50; } }
                }

                anchors{
                    top: parent.top
                    topMargin: UM.Theme.getSize("default_margin").height
                    bottom: parent.bottom
                    bottomMargin: UM.Theme.getSize("default_margin").height
                    right: parent.right
                    rightMargin: (UM.Theme.getSize("default_margin").width / 4)
                }

                MonitorSidebar {
                    id: printMonitor
                    width: parent.width
                    //height: MonitorSidebar.height  //base.height
                    anchors
                    {
                        left: parent.left
                        leftMargin: UM.Theme.getSize("default_margin").width
                        right: parent.right
                        rightMargin: UM.Theme.getSize("default_margin").width
                    }
                }
            }
        }

        Cura.RoundedRectangle
        {
            id: actionsPanel

            border.width: UM.Theme.getSize("default_lining").width
            border.color: UM.Theme.getColor("lining")
            color: UM.Theme.getColor("main_background")

            cornerSide: Cura.RoundedRectangle.Direction.Left
            radius: UM.Theme.getSize("default_radius").width

            anchors
            {
                bottom: parent.bottom
                bottomMargin: UM.Theme.getSize("default_margin").height
                right: parent.right
                rightMargin: UM.Theme.getSize("default_margin").height
            }

            width: UM.Theme.getSize("print_setup_widget").width
            height: monitorButton.height + UM.Theme.getSize("default_margin").height

            Cura.MonitorButton
            {
                id: monitorButton
                width: parent.width
                anchors.top: parent.top
                anchors.topMargin: UM.Theme.getSize("default_margin").height
            }
        }
    }
}