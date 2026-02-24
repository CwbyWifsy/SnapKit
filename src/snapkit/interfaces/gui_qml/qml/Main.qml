import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import Qt.labs.folderlistmodel
import "components"

ApplicationWindow {
    id: window
    visible: true
    width: 1460
    height: 900
    minimumWidth: 1180
    minimumHeight: 700
    title: "SnapKit"
    color: c("windowBg")
    palette.window: c("panel")
    palette.base: c("inputBg")
    palette.text: c("textPrimary")
    palette.button: c("panelSoft")
    palette.buttonText: c("textPrimary")
    palette.highlight: c("navActive")
    palette.highlightedText: c("textPrimary")

    property string currentViewId: "local_scan"
    property bool gridMode: true
    property bool darkMode: true
    property string toastText: ""
    property bool toastError: false
    property int renameItemId: -1
    property int customIconItemId: -1
    property real savedGridContentY: 0
    property real savedListContentY: 0
    property bool pendingRestoreScroll: false
    property string quickSourceMode: "local"
    property string quickPickTargetField: "target"
    property string imageBrowserFolderUrl: ""
    property string imageCurrentUrl: ""
    property string imageBrowserTitle: "图片浏览"

    property var darkPalette: ({
        "windowBg": "#1f2126",
        "gradA": "#23252b",
        "gradB": "#1f2228",
        "gradC": "#1b1e23",
        "panel": "#1d2026",
        "panelSoft": "#242931",
        "body": "#1a1e24",
        "card": "#21262d",
        "border": "#3a414b",
        "textPrimary": "#f3f5f8",
        "textSecondary": "#c3cad4",
        "textMuted": "#9aa4b2",
        "inputBg": "#2a3038",
        "inputBorder": "#4b5664",
        "inputFocus": "#5f9bd6",
        "navHover": "#2d3440",
        "navActive": "#2f74c0",
        "toastOkBg": "#1f4b3a",
        "toastOkBorder": "#5fc89a",
        "toastErrBg": "#5a2a34",
        "toastErrBorder": "#d97a92",
        "popupBg": "#252b34",
        "popupBorder": "#4f5d6e"
    })

    property var lightPalette: ({
        "windowBg": "#f4f7fc",
        "gradA": "#f8fbff",
        "gradB": "#eef4fb",
        "gradC": "#e7eff9",
        "panel": "#ffffff",
        "panelSoft": "#f7f9fd",
        "body": "#edf2f9",
        "card": "#ffffff",
        "border": "#d3dde9",
        "textPrimary": "#172131",
        "textSecondary": "#4b5f78",
        "textMuted": "#6d7f97",
        "inputBg": "#ffffff",
        "inputBorder": "#c4d3e6",
        "inputFocus": "#0a84ff",
        "navHover": "#eef4ff",
        "navActive": "#dcecff",
        "toastOkBg": "#def6eb",
        "toastOkBorder": "#5aaf82",
        "toastErrBg": "#fde7ec",
        "toastErrBorder": "#d97a92",
        "popupBg": "#ffffff",
        "popupBorder": "#c7d6e9"
    })

    function c(key) {
        var palette = darkMode ? darkPalette : lightPalette
        return palette[key] || "#ff00ff"
    }

    function refreshKeepScroll() {
        savedGridContentY = gridView.contentY
        savedListContentY = listView.contentY
        pendingRestoreScroll = true
        if (appVm) {
            appVm.refresh(currentViewId, searchInput.text)
        }
    }

    function normalizePath(rawPath) {
        if (!rawPath || rawPath.length === 0) {
            return ""
        }
        var value = rawPath.trim()
        if (value.startsWith("\"") && value.endsWith("\"")) {
            value = value.substring(1, value.length - 1)
        }
        var comma = value.indexOf(",")
        if (comma > 1) {
            value = value.substring(0, comma)
        }
        var lower = value.toLowerCase()
        var exeWithArgs = lower.indexOf(".exe ")
        if (exeWithArgs > 0) {
            value = value.substring(0, exeWithArgs + 4)
        }
        return value
    }

    function parentFolder(pathValue) {
        var clean = normalizePath(pathValue)
        if (clean.length === 0) {
            return ""
        }
        var normalized = clean.replace(/\//g, "\\")
        var lower = normalized.toLowerCase()
        if (lower.endsWith(".exe") || lower.endsWith(".lnk")) {
            var idx = normalized.lastIndexOf("\\")
            if (idx > 2) {
                return normalized.substring(0, idx)
            }
        }
        return normalized
    }

    function toFileUrl(pathValue) {
        if (!pathValue || pathValue.length === 0) {
            return ""
        }
        var slash = pathValue.replace(/\\/g, "/")
        if (/^[a-zA-Z]:\//.test(slash)) {
            return "file:///" + slash
        }
        if (slash.startsWith("/")) {
            return "file://" + slash
        }
        return ""
    }

    function fileUrlToPath(urlValue) {
        if (!urlValue || urlValue.length === 0) {
            return ""
        }
        var text = urlValue.toString ? urlValue.toString() : urlValue
        if (!text.startsWith("file:///")) {
            return text
        }
        var decoded = decodeURIComponent(text.substring(8))
        return decoded.replace(/\//g, "\\")
    }

    function pathToImageUrl(pathValue) {
        if (!pathValue || pathValue.length === 0) {
            return ""
        }
        var normalized = pathValue.replace(/\//g, "\\")
        return toFileUrl(normalized)
    }

    function defaultQuickTypeIndex() {
        if (currentViewId === "local_scan") {
            return 0
        }
        if (currentViewId === "not_installed") {
            return 1
        }
        if (currentViewId === "resource_url") {
            return 2
        }
        if (currentViewId === "resource_document") {
            return 3
        }
        if (currentViewId === "resource_image") {
            return 4
        }
        if (currentViewId === "resource_video") {
            return 5
        }
        return 1
    }

    function quickTargetPlaceholder(typeIndex) {
        if (typeIndex === 0) {
            return "本地可执行文件路径（.exe/.lnk）"
        }
        if (typeIndex === 1) {
            return "下载链接（可选）"
        }
        if (typeIndex === 2) {
            return "https://..."
        }
        if (quickSourceMode === "network") {
            return "https://...（网络文件地址）"
        }
        return "本地文件或文件夹路径"
    }

    function quickUsesSourceMode(typeIndex) {
        return typeIndex >= 3
    }

    function isImagePath(value) {
        var lowered = (value || "").toLowerCase()
        return lowered.endsWith(".png") || lowered.endsWith(".jpg")
            || lowered.endsWith(".jpeg") || lowered.endsWith(".bmp")
            || lowered.endsWith(".gif") || lowered.endsWith(".webp")
    }

    function openImageResource(itemId, kind, sourcePath, title) {
        if (currentViewId !== "resource_image" || kind !== "resource" || !sourcePath) {
            if (appVm) {
                appVm.activate(itemId)
            }
            return
        }

        var raw = sourcePath.trim()
        if (raw.length === 0) {
            if (appVm) {
                appVm.activate(itemId)
            }
            return
        }

        imageBrowserTitle = title || "图片浏览"
        var lowered = raw.toLowerCase()
        if (lowered.startsWith("http://") || lowered.startsWith("https://")) {
            if (!isImagePath(raw)) {
                if (appVm) {
                    appVm.activate(itemId)
                }
                return
            }
            imageBrowserFolderUrl = ""
            imageCurrentUrl = raw
            imageBrowserPopup.open()
            return
        }

        var normalized = raw
        if (normalized.startsWith("\"") && normalized.endsWith("\"")) {
            normalized = normalized.substring(1, normalized.length - 1)
        }
        normalized = normalized.replace(/\//g, "\\")
        if (isImagePath(normalized)) {
            imageBrowserFolderUrl = toFileUrl(parentFolder(normalized))
            imageCurrentUrl = toFileUrl(normalized)
            imageBrowserPopup.open()
            return
        }

        imageBrowserFolderUrl = toFileUrl(normalized)
        imageCurrentUrl = ""
        imageBrowserPopup.open()
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: c("gradA") }
            GradientStop { position: 0.58; color: c("gradB") }
            GradientStop { position: 1.0; color: c("gradC") }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredWidth: 292
            Layout.fillHeight: true
            color: c("panel")
            border.color: c("border")
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 16

                Rectangle {
                    Layout.fillWidth: true
                    height: 94
                    radius: 18
                    color: c("panelSoft")
                    border.color: c("border")
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 12

                        Rectangle {
                            width: 52
                            height: 52
                            radius: 14
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0.0; color: "#2ba1ff" }
                                GradientStop { position: 1.0; color: "#57c7ff" }
                            }
                        }

                        ColumnLayout {
                            spacing: 2
                            Label {
                                text: "SnapKit"
                                color: c("textPrimary")
                                font.pixelSize: 30
                                font.family: "Segoe UI Variable Display"
                                font.weight: Font.Black
                            }
                            Label {
                                text: "Personal Toolbox"
                                color: c("textMuted")
                                font.pixelSize: 13
                            }
                        }
                        Item { Layout.fillWidth: true }
                    }
                }

                ListModel {
                    id: navModel
                    ListElement { title: "核心功能"; viewId: ""; section: true }
                    ListElement { title: "本地应用"; viewId: "local_scan"; section: false }
                    ListElement { title: "已收藏"; viewId: "installed"; section: false }
                    ListElement { title: "待安装软件"; viewId: "not_installed"; section: false }
                    ListElement { title: "资源库"; viewId: ""; section: true }
                    ListElement { title: "图片素材"; viewId: "resource_image"; section: false }
                    ListElement { title: "视频文件"; viewId: "resource_video"; section: false }
                    ListElement { title: "文档记录"; viewId: "resource_document"; section: false }
                    ListElement { title: "资源网站"; viewId: "resource_url"; section: false }
                }

                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: navModel
                    spacing: 8
                    clip: true

                    delegate: Item {
                        width: ListView.view.width
                        height: section ? 34 : 48

                        Label {
                            visible: section
                            anchors.verticalCenter: parent.verticalCenter
                            text: title
                            color: c("textMuted")
                            font.pixelSize: 12
                            font.bold: true
                            leftPadding: 10
                        }

                        Rectangle {
                            visible: !section
                            anchors.fill: parent
                            radius: 12
                            color: currentViewId === viewId ? c("navActive") : (navMouse.containsMouse ? c("navHover") : "transparent")
                            border.width: currentViewId === viewId ? 0 : 1
                            border.color: c("border")

                            Behavior on color {
                                ColorAnimation { duration: 130 }
                            }

                            Label {
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.left: parent.left
                                anchors.leftMargin: 18
                                text: title
                                color: currentViewId === viewId ? c("textPrimary") : c("textSecondary")
                                font.pixelSize: 17
                                font.family: "Microsoft YaHei UI"
                                font.weight: currentViewId === viewId ? Font.DemiBold : Font.Normal
                            }

                            MouseArea {
                                id: navMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: {
                                    currentViewId = viewId
                                    if (appVm) {
                                        appVm.refresh(viewId, searchInput.text)
                                    }
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 70
                    radius: 14
                    color: c("panelSoft")
                    border.color: c("border")
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 10

                        Rectangle {
                            width: 36
                            height: 36
                            radius: 18
                            color: "#365173"
                            Label {
                                anchors.centerIn: parent
                                text: "A"
                                color: c("textPrimary")
                                font.pixelSize: 15
                                font.bold: true
                            }
                        }

                        ColumnLayout {
                            spacing: 2
                            Label {
                                text: "本地用户"
                                color: c("textPrimary")
                                font.pixelSize: 14
                            }
                            Label {
                                text: "v2.0.0-qml"
                                color: c("textMuted")
                                font.pixelSize: 11
                            }
                        }

                        Item { Layout.fillWidth: true }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: c("body")

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 30
                spacing: 18

                Rectangle {
                    Layout.fillWidth: true
                    height: 84
                    radius: 16
                    color: c("panelSoft")
                    border.color: c("border")
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 14

                        TextField {
                            id: searchInput
                            Layout.fillWidth: true
                            placeholderText: "快速搜索应用、文件、网页..."
                            color: c("textPrimary")
                            placeholderTextColor: c("textMuted")
                            font.pixelSize: 16
                            leftPadding: 14
                            rightPadding: 14
                            background: Rectangle {
                                radius: 12
                                color: c("inputBg")
                                border.color: searchInput.activeFocus ? c("inputFocus") : c("inputBorder")
                                border.width: searchInput.activeFocus ? 2 : 1
                            }
                            onTextEdited: searchDebounce.restart()
                        }

                        ComboBox {
                            id: localFilterCombo
                            Layout.preferredWidth: 160
                            visible: currentViewId === "local_scan"
                            model: ["全部", "已收藏", "未收藏"]
                            onCurrentIndexChanged: {
                                if (visible && appVm) {
                                    appVm.setLocalFilter(currentIndex, currentViewId, searchInput.text)
                                }
                            }
                        }

                        Button {
                            text: "扫描应用"
                            Layout.preferredWidth: 112
                            onClicked: appVm.scanAndRefresh(currentViewId, searchInput.text)
                        }

                        Rectangle {
                            Layout.preferredWidth: 154
                            height: 46
                            radius: 10
                            color: c("card")
                            border.color: c("border")
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 4
                                spacing: 6

                                Button {
                                    Layout.fillWidth: true
                                    text: "网格"
                                    onClicked: gridMode = true
                                    highlighted: gridMode
                                }
                                Button {
                                    Layout.fillWidth: true
                                    text: "列表"
                                    onClicked: gridMode = false
                                    highlighted: !gridMode
                                }
                            }
                        }

                        Button {
                            text: darkMode ? "切到白天" : "切到夜间"
                            Layout.preferredWidth: 122
                            onClicked: darkMode = !darkMode
                        }

                        Button {
                            text: "+ 快速添加"
                            Layout.preferredWidth: 148
                            onClicked: {
                                quickTypeCombo.currentIndex = defaultQuickTypeIndex()
                                quickSourceMode = "local"
                                quickModeCombo.currentIndex = 0
                                quickNameInput.text = ""
                                quickTargetInput.text = ""
                                quickIconInput.text = ""
                                quickNoteInput.text = ""
                                quickAddPopup.open()
                            }
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Label {
                        text: appVm ? appVm.pageTitle : ""
                        color: c("textPrimary")
                        font.pixelSize: 52
                        font.family: "Microsoft YaHei UI"
                        font.weight: Font.ExtraBold
                    }
                    Label {
                        text: appVm ? appVm.pageSubtitle : ""
                        color: c("textSecondary")
                        font.pixelSize: 18
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 20
                    color: c("card")
                    border.color: c("border")
                    border.width: 1

                    StackLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        currentIndex: gridMode ? 0 : 1

                        GridView {
                            id: gridView
                            clip: true
                            cellWidth: 214
                            cellHeight: 240
                            model: appVm ? appVm.model : null
                            cacheBuffer: 600
                            boundsBehavior: Flickable.DragAndOvershootBounds
                            flickDeceleration: 2300
                            maximumFlickVelocity: 6200

                            delegate: AppCard {
                                width: 198
                                height: 224
                                darkMode: window.darkMode
                                onActivated: function(id, kind, sourcePath) {
                                    openImageResource(id, kind, sourcePath, title)
                                }
                                onActionRequested: function(id, actionName) {
                                    if (appVm) {
                                        appVm.action(id, actionName)
                                    }
                                    if (actionName === "delete") {
                                        refreshKeepScroll()
                                    }
                                }
                                onRenameRequested: function(id, currentName) {
                                    renameItemId = id
                                    renameInput.text = currentName
                                    renamePopup.open()
                                }
                                onCustomIconRequested: function(id, sourcePath) {
                                    customIconItemId = id
                                    var folder = parentFolder(sourcePath)
                                    var folderUrl = toFileUrl(folder)
                                    if (folderUrl.length > 0) {
                                        iconPicker.currentFolder = folderUrl
                                    }
                                    iconPicker.open()
                                }
                            }

                            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                            WheelHandler {
                                target: null
                                acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
                                onWheel: function(event) {
                                    var dy = event.angleDelta.y !== 0 ? event.angleDelta.y : event.pixelDelta.y
                                    if (dy !== 0) {
                                        gridView.flick(0, dy * 10)
                                        event.accepted = true
                                    }
                                }
                            }
                        }

                        ListView {
                            id: listView
                            clip: true
                            spacing: 10
                            model: appVm ? appVm.model : null
                            cacheBuffer: 500
                            boundsBehavior: Flickable.DragAndOvershootBounds
                            flickDeceleration: 2300
                            maximumFlickVelocity: 6200

                            delegate: AppRow {
                                width: ListView.view.width
                                darkMode: window.darkMode
                                onActivated: function(id, kind, sourcePath) {
                                    openImageResource(id, kind, sourcePath, title)
                                }
                                onActionRequested: function(id, actionName) {
                                    if (appVm) {
                                        appVm.action(id, actionName)
                                    }
                                    if (actionName === "delete") {
                                        refreshKeepScroll()
                                    }
                                }
                                onRenameRequested: function(id, currentName) {
                                    renameItemId = id
                                    renameInput.text = currentName
                                    renamePopup.open()
                                }
                                onCustomIconRequested: function(id, sourcePath) {
                                    customIconItemId = id
                                    var folder = parentFolder(sourcePath)
                                    var folderUrl = toFileUrl(folder)
                                    if (folderUrl.length > 0) {
                                        iconPicker.currentFolder = folderUrl
                                    }
                                    iconPicker.open()
                                }
                            }

                            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                            WheelHandler {
                                target: null
                                acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
                                onWheel: function(event) {
                                    var dy = event.angleDelta.y !== 0 ? event.angleDelta.y : event.pixelDelta.y
                                    if (dy !== 0) {
                                        listView.flick(0, dy * 10)
                                        event.accepted = true
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        anchors.centerIn: parent
                        width: 180
                        height: 48
                        radius: 12
                        color: c("panel")
                        border.color: c("border")
                        border.width: 1
                        visible: appVm ? appVm.busy : false

                        Label {
                            anchors.centerIn: parent
                            text: "加载中..."
                            color: c("textSecondary")
                            font.pixelSize: 14
                        }
                    }
                }
            }
        }
    }

    Timer {
        id: searchDebounce
        interval: 220
        repeat: false
        onTriggered: {
            if (appVm) {
                appVm.refresh(currentViewId, searchInput.text)
            }
        }
    }

    Rectangle {
        id: toast
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 18
        radius: 10
        color: toastError ? c("toastErrBg") : c("toastOkBg")
        border.width: 1
        border.color: toastError ? c("toastErrBorder") : c("toastOkBorder")
        visible: toastText.length > 0
        height: 44
        width: Math.min(parent.width * 0.8, toastLabel.implicitWidth + 26)
        opacity: visible ? 1 : 0

        Behavior on opacity {
            NumberAnimation { duration: 120 }
        }

        Label {
            id: toastLabel
            anchors.centerIn: parent
            text: toastText
            color: c("textPrimary")
            font.pixelSize: 14
        }
    }

    Timer {
        id: toastTimer
        interval: 2100
        repeat: false
        onTriggered: toastText = ""
    }

    Popup {
        id: renamePopup
        modal: true
        focus: true
        width: 380
        height: 188
        anchors.centerIn: parent
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            radius: 12
            color: c("popupBg")
            border.width: 1
            border.color: c("popupBorder")
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 12

            Label {
                text: "重命名"
                color: c("textPrimary")
                font.pixelSize: 20
                font.bold: true
            }

            TextField {
                id: renameInput
                Layout.fillWidth: true
                placeholderText: "输入新名称"
            }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                Button {
                    text: "取消"
                    onClicked: renamePopup.close()
                }
                Button {
                    text: "保存"
                    onClicked: {
                        appVm.renameItem(renameItemId, renameInput.text)
                        renamePopup.close()
                        refreshKeepScroll()
                    }
                }
            }
        }
    }

    FolderListModel {
        id: imageFolderModel
        folder: imageBrowserFolderUrl
        showDirs: false
        showFiles: true
        nameFilters: ["*.png", "*.jpg", "*.jpeg", "*.bmp", "*.gif", "*.webp"]
    }

    Popup {
        id: imageBrowserPopup
        modal: true
        focus: true
        width: Math.min(window.width - 80, 1260)
        height: Math.min(window.height - 80, 760)
        anchors.centerIn: parent
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            radius: 12
            color: c("popupBg")
            border.width: 1
            border.color: c("popupBorder")
        }

        onOpened: {
            if (imageCurrentUrl.length === 0 && imageFolderModel.count > 0) {
                imageCurrentUrl = pathToImageUrl(imageFolderModel.get(0, "filePath"))
            }
        }

        RowLayout {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 14

            Rectangle {
                Layout.preferredWidth: 320
                Layout.fillHeight: true
                radius: 10
                color: c("panelSoft")
                border.width: 1
                border.color: c("border")
                visible: imageBrowserFolderUrl.length > 0

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 10

                    Label {
                        text: imageBrowserTitle
                        color: c("textPrimary")
                        font.pixelSize: 18
                        font.bold: true
                    }

                    GridView {
                        id: imageThumbs
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        cellWidth: 94
                        cellHeight: 112
                        model: imageFolderModel
                        clip: true

                        delegate: Rectangle {
                            width: 84
                            height: 102
                            radius: 8
                            property string thumbUrl: pathToImageUrl(filePath)
                            color: imageCurrentUrl === thumbUrl ? c("navActive") : c("card")
                            border.width: 1
                            border.color: c("border")

                            Column {
                                anchors.fill: parent
                                anchors.margins: 6
                                spacing: 4

                                Image {
                                    width: 72
                                    height: 72
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    source: thumbUrl
                                    fillMode: Image.PreserveAspectFit
                                    smooth: true
                                }

                                Label {
                                    width: parent.width
                                    text: fileName
                                    color: c("textSecondary")
                                    font.pixelSize: 11
                                    elide: Text.ElideRight
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                acceptedButtons: Qt.LeftButton
                                onClicked: imageCurrentUrl = thumbUrl
                                onDoubleClicked: fullImagePopup.open()
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 10
                color: c("card")
                border.width: 1
                border.color: c("border")

                Item {
                    anchors.fill: parent
                    anchors.margins: 8

                    Image {
                        id: imagePreview
                        anchors.fill: parent
                        source: imageCurrentUrl
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                        cache: false
                        visible: imageCurrentUrl.length > 0
                    }

                    Label {
                        anchors.centerIn: parent
                        visible: imageCurrentUrl.length === 0
                        text: imageBrowserFolderUrl.length > 0 ? "该目录没有可预览图片" : "未选择图片"
                        color: c("textMuted")
                        font.pixelSize: 16
                    }

                    MouseArea {
                        anchors.fill: parent
                        enabled: imageCurrentUrl.length > 0
                        acceptedButtons: Qt.LeftButton
                        onDoubleClicked: fullImagePopup.open()
                    }
                }
            }
        }
    }

    Popup {
        id: fullImagePopup
        modal: true
        focus: true
        x: 0
        y: 0
        width: window.width
        height: window.height
        padding: 0
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle { color: "#cc000000" }

        Image {
            anchors.fill: parent
            anchors.margins: 24
            source: imageCurrentUrl
            fillMode: Image.PreserveAspectFit
            smooth: true
            cache: false
        }
    }

    Popup {
        id: quickAddPopup
        modal: true
        focus: true
        width: 560
        height: 430
        anchors.centerIn: parent
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            radius: 12
            color: c("popupBg")
            border.width: 1
            border.color: c("popupBorder")
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 12

            Label {
                text: "快速添加"
                color: c("textPrimary")
                font.pixelSize: 22
                font.bold: true
            }

            ComboBox {
                id: quickTypeCombo
                Layout.fillWidth: true
                model: ["本地应用", "待安装软件", "资源网站", "文档资源", "图片资源", "视频资源"]
                onCurrentIndexChanged: {
                    if (!quickUsesSourceMode(currentIndex)) {
                        quickSourceMode = "local"
                        if (quickModeCombo) {
                            quickModeCombo.currentIndex = 0
                        }
                    }
                }
            }

            TextField {
                id: quickNameInput
                Layout.fillWidth: true
                placeholderText: quickTypeCombo.currentIndex === 0
                    ? "应用名称（可选，不填默认取文件名）"
                    : "名称（可选，留空自动推断）"
            }

            RowLayout {
                Layout.fillWidth: true

                TextField {
                    id: quickTargetInput
                    Layout.fillWidth: true
                    placeholderText: quickTargetPlaceholder(quickTypeCombo.currentIndex)
                }

                Button {
                    visible: quickTypeCombo.currentIndex === 0
                    text: "选程序"
                    onClicked: {
                        quickPickTargetField = "target"
                        quickPathPicker.title = "选择程序文件"
                        quickPathPicker.nameFilters = ["Executables (*.exe *.lnk *.bat *.cmd)"]
                        quickPathPicker.open()
                    }
                }

                Button {
                    visible: quickUsesSourceMode(quickTypeCombo.currentIndex) && quickSourceMode === "local"
                    text: "选文件"
                    onClicked: {
                        quickPickTargetField = "target"
                        quickPathPicker.title = "选择本地文件"
                        quickPathPicker.nameFilters = ["All files (*)"]
                        quickPathPicker.open()
                    }
                }

                Button {
                    visible: quickUsesSourceMode(quickTypeCombo.currentIndex) && quickSourceMode === "local"
                    text: "选文件夹"
                    onClicked: {
                        quickPickTargetField = "target"
                        quickFolderPicker.open()
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                visible: quickTypeCombo.currentIndex === 0

                TextField {
                    id: quickIconInput
                    Layout.fillWidth: true
                    placeholderText: "图标来源（可选，支持 exe/ico/png）"
                }

                Button {
                    text: "选图标"
                    onClicked: {
                        quickPickTargetField = "icon"
                        quickPathPicker.title = "选择图标来源"
                        quickPathPicker.nameFilters = ["Icon sources (*.exe *.ico *.png *.jpg *.jpeg *.bmp)"]
                        quickPathPicker.open()
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                visible: quickUsesSourceMode(quickTypeCombo.currentIndex)

                Label {
                    text: "资源来源"
                    color: c("textSecondary")
                }

                ComboBox {
                    id: quickModeCombo
                    Layout.preferredWidth: 170
                    model: ["本地文件/文件夹", "网络地址(URL)"]
                    onCurrentIndexChanged: quickSourceMode = currentIndex === 0 ? "local" : "network"
                    Component.onCompleted: currentIndex = 0
                }
            }

            TextArea {
                id: quickNoteInput
                Layout.fillWidth: true
                Layout.fillHeight: true
                wrapMode: TextEdit.Wrap
                placeholderText: "备注（可选）"
            }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                Button {
                    text: "取消"
                    onClicked: quickAddPopup.close()
                }
                Button {
                    text: "添加"
                    onClicked: {
                        appVm.quickAdd(
                            quickTypeCombo.currentIndex,
                            quickNameInput.text,
                            quickTargetInput.text,
                            quickNoteInput.text,
                            quickIconInput.text,
                            quickSourceMode,
                            currentViewId,
                            searchInput.text
                        )
                        quickAddPopup.close()
                    }
                }
            }
        }
    }

    FileDialog {
        id: quickPathPicker
        title: "选择文件"
        fileMode: FileDialog.OpenFile
        nameFilters: ["All files (*)"]
        onAccepted: {
            var value = fileUrlToPath(selectedFile)
            if (quickPickTargetField === "icon") {
                quickIconInput.text = value
            } else {
                quickTargetInput.text = value
            }
        }
    }

    FolderDialog {
        id: quickFolderPicker
        title: "选择文件夹"
        onAccepted: {
            quickTargetInput.text = fileUrlToPath(selectedFolder)
        }
    }

    FileDialog {
        id: iconPicker
        title: "选择软件可执行文件"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Executable files (*.exe)"]
        onAccepted: {
            if (customIconItemId >= 0) {
                var iconUrl = selectedFile.toString ? selectedFile.toString() : selectedFile
                appVm.setCustomIcon(customIconItemId, iconUrl)
                refreshKeepScroll()
                customIconItemId = -1
            }
        }
        onRejected: customIconItemId = -1
    }

    Connections {
        target: appVm ? appVm : null
        function onNotification(level, message) {
            toastError = level === "error"
            toastText = message
            toastTimer.restart()
        }
        function onListLoaded() {
            if (!pendingRestoreScroll) {
                return
            }
            pendingRestoreScroll = false

            var gridMax = Math.max(0, gridView.contentHeight - gridView.height)
            var listMax = Math.max(0, listView.contentHeight - listView.height)
            gridView.contentY = Math.max(0, Math.min(savedGridContentY, gridMax))
            listView.contentY = Math.max(0, Math.min(savedListContentY, listMax))
        }
    }
}



