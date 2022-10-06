# author  : Jonathan Lambrechts jonathan.lambrechts@uclouvain.be
# licence : GPLv2 (see LICENSE.md)

from PyQt5.QtCore import Qt, QProcess, QProcessEnvironment
from PyQt5 import QtWidgets
from PyQt5.QtGui import QIcon
from qgis.gui import QgsProjectionSelectionTreeWidget
from qgis.core import *
import sys


class RunPipDialog(QtWidgets.QDialog) :

    def __init__(self, mainWindow) :
        super(RunPipDialog, self).__init__(mainWindow)
        self.setWindowTitle("Installing GMSH python module")
        layout = QtWidgets.QVBoxLayout()
        self.textWidget = QtWidgets.QPlainTextEdit()
        self.textWidget.setReadOnly(True)
        layout.addWidget(self.textWidget)
        hlayout = QtWidgets.QHBoxLayout()
        layout.addLayout(hlayout)
        hlayout.addStretch(1)
        self.closeBtn = QtWidgets.QPushButton("Close")
        self.closeBtn.clicked.connect(self.close)
        hlayout.addWidget(self.closeBtn)
        self.resize(600, 200)
        self.setLayout(layout)


    def onStdOut(self) :
        while self.p.canReadLine() :
            txt = str(self.p.readLine().data(),"utf8")
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
        if state != 0 :
            self.log("Gmsh installation failed.", "red")
        else :
            self.log("Gmsh successfully installed.", "green")
        self.closeBtn.show()
        self.closeBtn.setFocus()

    def onError(self, state):
        self.log("Gmsh installation failed.", "red")

    def exec_(self, args) :
        self.p = QProcess()
        self.p.setProcessChannelMode(QProcess.MergedChannels)
        self.p.readyReadStandardOutput.connect(self.onStdOut)
        self.p.error.connect(self.onError)
        self.p.finished.connect(self.onFinished)
        self.textWidget.clear()
        self.args = args
        self.closeBtn.hide()
        self.show()
        env = QProcessEnvironment.systemEnvironment()
        env.remove("TERM")
        self.p.setProcessEnvironment(env)
        self.p.start(args[0], args[1:])
        super(RunPipDialog, self).exec_()

def install_gmsh_if_needed(mainWindow):
    try :
        import gmsh
        return True
    except:
        RunPipDialog(mainWindow).exec_([sys.executable, '-m', 'pip', 'install', 'gmsh'])
    finally:
        try :
            import gmsh
            return True
        except :
            return False


class TitleLayout(QtWidgets.QVBoxLayout) :

    def __init__(self, title, widget, parent) :
        super(TitleLayout, self).__init__()
        parent.addLayout(self)
        self.label = QtWidgets.QLabel("<b>" + title + "</b>")
        self.addWidget(self.label)
        self.addWidget(widget)


class FileSelectorLayout(QtWidgets.QVBoxLayout) :

    def __init__(self, title, mainWindow, action, ext, parent, txt = None) :
        super(FileSelectorLayout, self).__init__()
        self.action = action
        self.ext = ext
        self.title = title
        parent.addLayout(self)
        self.addWidget(QtWidgets.QLabel("<b>" + title + "</b>"))
        self.mainWindow = mainWindow
        layout = QtWidgets.QHBoxLayout()
        self.addLayout(layout)
        fileButton = QtWidgets.QPushButton("");
        fileButton.setIcon(QIcon.fromTheme("document-open"))
        fileButton.clicked.connect(self.browseFile)
        self.fileWidget = QtWidgets.QLineEdit()
        self.fileWidget.setText(txt)
        layout.addWidget(self.fileWidget)
        layout.addWidget(fileButton)

    def browseFile(self) :
        if self.action == "save" :
            filename,_ = QtWidgets.QFileDialog.getSaveFileName(self.mainWindow,
                self.title, filter=self.ext)
        elif self.action == "opendir" :
            filename = QtWidgets.QFileDialog.getExistingDirectory(self.mainWindow,
                self.title)
        else :
            filename,_ = QtWidgets.QFileDialog.getOpenFileName(self.mainWindow,
                self.title, filter=self.ext)
        if filename :
            self.setFile(filename)

    def setFile(self, filename):
        self.fileWidget.setText(filename)

    def getFile(self) :
        return self.fileWidget.text()


class CancelRunLayout(QtWidgets.QHBoxLayout) :

    def __init__(self, dialog, runTitle, runCallback, parent) :
        super(CancelRunLayout, self).__init__()
        parent.addLayout(self)
        self.addStretch(1)
        cancelButton = QtWidgets.QPushButton("Cancel")
        cancelButton.clicked.connect(dialog.close)
        self.addWidget(cancelButton, 0)
        self.runButton = QtWidgets.QPushButton(runTitle)
        self.runButton.clicked.connect(runCallback)
        self.addWidget(self.runButton, 0)

    def setFocus(self) :
        self.runButton.setFocus()

