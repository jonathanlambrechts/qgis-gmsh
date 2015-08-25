from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
import shlex
import os

import tools

class RunGmshDialog(QDialog) :

    def __init__(self, mainWindow, loadMshDialog) :
        super(RunGmshDialog, self).__init__(mainWindow)
        self.setWindowTitle("Running Gmsh")
        layout = QVBoxLayout()
        self.textWidget = QPlainTextEdit()
        self.textWidget.setReadOnly(True)
        layout.addWidget(self.textWidget)
        hlayout = QHBoxLayout()
        layout.addLayout(hlayout)
        hlayout.addStretch(1)
        self.loadMshBtn = QPushButton("Load mesh file")
        self.loadMshBtn.clicked.connect(self.close)
        self.loadMshBtn.clicked.connect(loadMshDialog.exec_)
        self.closeBtn = QPushButton("Close")
        self.closeBtn.clicked.connect(self.close)
        hlayout.addWidget(self.loadMshBtn)
        hlayout.addWidget(self.closeBtn)
        self.killBtn = QPushButton("Kill")
        self.killBtn.clicked.connect(self.killp)
        hlayout.addWidget(self.killBtn)
        self.resize(600, 600)
        self.setLayout(layout)

    def killp(self) :
        self.p.kill()
        self.log("Killed", "red")
        self.killed = True

    def onStdOut(self) :
        while self.p.canReadLine() :
            txt = str(self.p.readLine())[:-1]
            if txt.startswith("Error   : ") or txt.startswith("Fatal   : "):
                self.log(txt[10:], "red")
            elif txt.startswith("Warning : ") :
                self.log(txt[10:], "orange")
            elif txt.startswith("Info    : Running") :
                self.log(txt[10:], "black")
            elif txt.startswith("Info    : ") :
                self.log(txt[10:])
            else :
                self.log(txt)

    def log(self, msg, color = None):
        scroll = self.textWidget.verticalScrollBar()
        scrollToEnd = scroll.value() == scroll.maximum()
        if color is not None :
            self.textWidget.appendHtml("<b> <font color=%s>" % color + msg + "</b></font>")
        else :
            self.textWidget.appendHtml(msg)
        if scrollToEnd :
            scroll.setValue(scroll.maximum())

    def onFinished(self, state) :
        if not self.killed :
            if state != 0 :
                self.log("An error occured.", "red")
            else :
                self.log("Gmsh finished.", "green")
                self.loadMshBtn.show()
        self.closeBtn.show()
        self.closeBtn.setFocus()
        self.killBtn.hide()

    def onError(self, state):
        if self.killed :
            return
        if state == QProcess.FailedToStart :
            self.log("Cannot start gmsh executable : " + self.args[0], "red")
        elif state == QProcess.Crashed :
            self.log("Gmsh crashed.", "red")
        else :
            self.log("Unkown gmsh error.", "red")

    def exec_(self, args) :
        self.p = QProcess()
        self.p.setProcessChannelMode(QProcess.MergedChannels)
        self.p.readyReadStandardOutput.connect(self.onStdOut)
        self.p.error.connect(self.onError)
        self.p.finished.connect(self.onFinished)
        self.textWidget.clear()
        self.args = args
        self.closeBtn.hide()
        self.loadMshBtn.hide()
        self.killed = False
        self.killBtn.show()
        self.killBtn.setFocus()
        self.show()
        env = QProcessEnvironment.systemEnvironment()
        env.remove("TERM")
        self.p.setProcessEnvironment(env)
        self.p.start(args[0], args[1:])
        super(RunGmshDialog, self).exec_()


class MeshDialog(QDialog) :

    def __init__(self, mainWindow, iface, loadMshDialog) :
        super(MeshDialog, self).__init__(mainWindow)
        self.setWindowTitle("Mesh a Gmsh geometry file")
        layout = QVBoxLayout()
        self.gmshExe = tools.FileSelectorLayout("Gmsh executable",
            mainWindow, "open", "", layout, "")
        self.inputGeo = tools.FileSelectorLayout("Input geometry file",
            mainWindow, "open", "*.geo", layout)
        self.outputMsh = tools.FileSelectorLayout("Output mesh file",
            mainWindow, "save", "*.msh", layout)
        self.inputGeo.fileWidget.textChanged.connect(self.onInputFileChange)
        self.inputGeo.fileWidget.textChanged.connect(self.validate)
        self.outputMsh.fileWidget.textChanged.connect(self.validate)
        self.gmshExe.fileWidget.textChanged.connect(self.validate)
        self.algoSelector = QComboBox(self)
        self.algoSelector.addItem("Mesh Adapt", "meshadapt")
        self.algoSelector.addItem("Delaunay", "del2d")
        self.algoSelector.addItem("Frontal", "front2d")
        tools.TitleLayout("Meshing algorithm", self.algoSelector, layout)
        self.epslc1d = QLineEdit()
        self.epslc1d.setText("1e-3")
        validator = QDoubleValidator()
        validator.setNotation(QDoubleValidator.ScientificNotation)
        self.epslc1d.setValidator(validator)
        tools.TitleLayout("1D mesh size integration precision", self.epslc1d, layout)
        self.commandLine = QLineEdit()
        tools.TitleLayout("Additional command line arguments", self.commandLine, layout)
        self.runLayout = tools.CancelRunLayout(self,"Mesh", self.mesh, layout)
        self.runLayout.runButton.setEnabled(False)
        self.setLayout(layout)
        self.setMaximumHeight(self.height())
        self.runGmshDialog = RunGmshDialog(iface.mainWindow(), loadMshDialog)
        self.resize(max(400, self.width()), self.height())

    def onInputFileChange(self, text) :
        if (self.outputMsh.getFile() == "" or self.autoMshName) and text.endswith(".geo") :
            self.outputMsh.setFile(text[:-4]+".msh")

    def validate(self) :
        gmshExe = self.gmshExe.getFile()
        inputGeo = self.inputGeo.getFile()
        outputMsh = self.outputMsh.getFile()
        self.autoMshName = inputGeo.endswith(".geo") and (outputMsh == inputGeo[:-4] + ".msh" or outputMsh == "")
        if os.path.isfile(inputGeo) and os.path.isfile(gmshExe) and outputMsh != "":
            self.runLayout.runButton.setEnabled(True)
        else :
            self.runLayout.runButton.setEnabled(False)

    def mesh(self) :
        self.close()
        settings = QSettings()
        settings.setValue("gmsh/executable", self.gmshExe.getFile())
        algo = self.algoSelector.itemData(self.algoSelector.currentIndex())
        proj = QgsProject.instance()
        proj.writeEntry("gmsh", "geo_file", self.inputGeo.getFile())
        proj.writeEntry("gmsh", "msh_file", self.outputMsh.getFile())
        proj.writeEntry("gmsh", "algorithm", self.algoSelector.currentText())
        proj.writeEntry("gmsh", "epslc1d", self.epslc1d.text())
        proj.writeEntry("gmsh", "extraargs", self.commandLine.text())
        proj.writeEntry("gmsh", "auto_msh_name", self.autoMshName)
        args = [self.gmshExe.getFile(), "-2", self.inputGeo.getFile(),
            "-algo", algo,
            "-epslc1d", self.epslc1d.text()] + shlex.split(self.commandLine.text())
        self.runGmshDialog.exec_(args)

    def exec_(self) :
        proj = QgsProject.instance()
        settings = QSettings()
        self.gmshExe.setFile(settings.value("gmsh/executable", "gmsh"))
        self.outputMsh.setFile(proj.readEntry("gmsh", "msh_file", "")[0])
        self.inputGeo.setFile(proj.readEntry("gmsh", "geo_file", "")[0])
        idx = self.algoSelector.findText(proj.readEntry("gmsh", "algorithm", "Frontal")[0])
        self.algoSelector.setCurrentIndex(idx)
        self.epslc1d.setText(proj.readEntry("gmsh", "epslc1d", "1e-3")[0])
        self.commandLine.setText(proj.readEntry("gmsh", "extraargs", "")[0])
        self.runLayout.setFocus()
        self.autoMshName = proj.readBoolEntry("gmsh", "auto_msh_name", True)[0]
        self.validate()
        super(MeshDialog, self).exec_()


def createAction(iface, loadMshDialog) :
    dialog = MeshDialog(iface.mainWindow(), iface, loadMshDialog)
    action = QAction("Mesh a Gmsh geometry file", iface.mainWindow())
    action.dialog = dialog
    action.setObjectName("GMSHMesh")
    action.setWhatsThis("Call Gmsh (http://geuz.org/gmsh) to mesh a geometry (.geo) file.")
    action.setStatusTip("Call Gmsh (http://geuz.org/gmsh) to mesh a geometry (.geo) file.")
    QObject.connect(action, SIGNAL("triggered()"), dialog.exec_)
    return action
