import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    required property int itemId
    required property string title
    required property string subtitle
    required property string badge
    required property string kind
    required property string iconSource
    required property bool isPinned
    required property string installLocation
    required property bool darkMode

    signal activated(int itemId, string kind, string sourcePath)
    signal actionRequested(int itemId, string actionName)
    signal renameRequested(int itemId, string currentName)
    signal customIconRequested(int itemId, string sourcePath)

    property color rowBg: darkMode ? "#1f252d" : "#ffffff"
    property color rowBgHover: darkMode ? "#29303a" : "#f3f7fd"
    property color rowBorder: darkMode ? "#37414d" : "#d5dfe9"
    property color rowBorderHover: darkMode ? "#5f9bd6" : "#0a84ff"
    property color textPrimary: darkMode ? "#f0f4fb" : "#182131"
    property color textSecondary: darkMode ? "#adbac9" : "#5f6f85"

    radius: 14
    color: rowMouse.containsMouse ? rowBgHover : rowBg
    border.width: 1
    border.color: rowMouse.containsMouse ? rowBorderHover : rowBorder
    height: 88

    Behavior on color { ColorAnimation { duration: 120 } }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 14

        Rectangle {
            width: 44
            height: 44
            radius: 10
            color: darkMode ? "#2c4058" : "#dce9f9"
            border.width: 1
            border.color: darkMode ? "#4f77a5" : "#9fbde4"

            Text {
                anchors.centerIn: parent
                text: root.title.length > 0 ? root.title.charAt(0).toUpperCase() : "?"
                color: darkMode ? "#95cdff" : "#277fd8"
                font.pixelSize: 18
                font.weight: Font.DemiBold
                visible: iconImage.status !== Image.Ready || root.iconSource.length === 0
            }

            Image {
                id: iconImage
                anchors.fill: parent
                anchors.margins: 1
                source: root.iconSource
                visible: status === Image.Ready && root.iconSource.length > 0
                fillMode: Image.PreserveAspectCrop
                smooth: true
                sourceSize.width: 48
                sourceSize.height: 48
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2

            Label {
                Layout.fillWidth: true
                text: root.title
                color: textPrimary
                font.pixelSize: 17
                font.family: "Microsoft YaHei UI"
                font.weight: Font.DemiBold
                elide: Text.ElideRight
            }

            Label {
                Layout.fillWidth: true
                text: root.subtitle
                color: textSecondary
                font.pixelSize: 13
                font.family: "Segoe UI"
                elide: Text.ElideRight
            }
        }

        Rectangle {
            radius: 7
            width: Math.max(90, badgeText.implicitWidth + 16)
            height: 26
            color: root.kind === "resource" ? (darkMode ? "#1e4d70" : "#d9edff") : (darkMode ? "#22563f" : "#dff6e8")
            border.width: 1
            border.color: root.kind === "resource" ? (darkMode ? "#4db5ff" : "#5ba5e6") : (darkMode ? "#55d39a" : "#57b889")

            Label {
                id: badgeText
                anchors.centerIn: parent
                text: root.badge
                color: root.kind === "resource" ? (darkMode ? "#9bd8ff" : "#2f6da8") : (darkMode ? "#9cf3c7" : "#2e7e59")
                font.pixelSize: 11
                font.weight: Font.Bold
            }
        }
    }

    MouseArea {
        id: rowMouse
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onDoubleClicked: root.activated(root.itemId, root.kind, root.installLocation)
        onPressed: function(mouse) {
            if (mouse.button === Qt.RightButton) {
                contextMenu.popup()
            }
        }
    }

    Menu {
        id: contextMenu
        width: 190
        padding: 6

        background: Rectangle {
            radius: 10
            color: darkMode ? "#22272f" : "#f8fbff"
            border.width: 1
            border.color: darkMode ? "#485463" : "#cad8ea"
        }

        delegate: MenuItem {
            id: menuDelegate
            implicitHeight: 34
            leftPadding: 12
            rightPadding: 12

            contentItem: Text {
                text: menuDelegate.text
                color: menuDelegate.enabled
                    ? (darkMode ? "#e9eef7" : "#162130")
                    : (darkMode ? "#6f7883" : "#9ea9b8")
                font.pixelSize: 13
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }

            background: Rectangle {
                radius: 7
                color: menuDelegate.highlighted
                    ? (darkMode ? "#334150" : "#dcecff")
                    : "transparent"
            }
        }

        MenuItem {
            text: root.kind === "wish" || root.kind === "resource" ? "打开" : "启动"
            onTriggered: root.actionRequested(root.itemId, "launch")
        }
        MenuItem {
            visible: root.kind === "local" || root.kind === "pinned"
            text: "管理员启动"
            onTriggered: root.actionRequested(root.itemId, "admin_launch")
        }
        MenuSeparator {}
        MenuItem {
            visible: root.kind !== "wish" && !root.installLocation.toLowerCase().startsWith("http")
            text: "打开文件夹"
            onTriggered: root.actionRequested(root.itemId, "open_folder")
        }
        MenuItem {
            text: "卸载"
            enabled: root.kind === "local" || root.kind === "pinned"
            onTriggered: root.actionRequested(root.itemId, "uninstall")
        }
        MenuItem {
            visible: root.kind === "local"
            text: root.isPinned ? "取消收藏" : "加入收藏"
            onTriggered: root.actionRequested(root.itemId, root.isPinned ? "unpin" : "pin")
        }
        MenuItem {
            visible: root.kind === "pinned"
            text: "移出收藏"
            onTriggered: root.actionRequested(root.itemId, "unpin")
        }
        MenuItem {
            visible: root.kind === "local" || root.kind === "pinned"
            text: "自定义图标"
            onTriggered: root.customIconRequested(root.itemId, root.installLocation)
        }
        MenuSeparator {}
        MenuItem {
            text: "重命名"
            onTriggered: root.renameRequested(root.itemId, root.title)
        }
        MenuItem {
            visible: root.kind !== "pinned"
            text: "删除"
            onTriggered: root.actionRequested(root.itemId, "delete")
        }
    }
}


