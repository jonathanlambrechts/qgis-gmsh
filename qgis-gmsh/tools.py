# author  : Jonathan Lambrechts jonathan.lambrechts@uclouvain.be
# licence : GPLv2 (see LICENSE.md)

from PyQt5.QtCore import Qt, QProcess, QProcessEnvironment
from PyQt5 import QtWidgets
from PyQt5.QtGui import QIcon
from qgis.gui import QgsProjectionSelectionTreeWidget
from qgis.core import *
import sys
import glob
import os
import importlib
import urllib.request
from zipfile import ZipFile
import re
import io

if sys.platform == "win32":
    windows_install_path = os.path.dirname(__file__)+'/gmsh_install' 
    sys.path.append(windows_install_path)

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


def get_latest_gmsh_windows_version():
    with urllib.request.urlopen('http://gmsh.info/python-packages/gmsh') as url:
        data = url.read()
        last = (b"", (0,0,0))
        for i in re.findall(b'href="(.*-win_amd64.whl)"', data):
            file = i
            version = tuple(int(j) for j in file.split(b"-")[1].split(b".")[:3])
            if (version[0] > last[1][0] or (version[0] == last[1][0] and version[1] > last[1][1])
                or (version[:2] == last[1][:2] and version[2] >= last[1][2])):
                last = (file, version)
        if last[1][0] == 0:
            return None
        return "http://gmsh.info/python-packages/gmsh/"+last[0].decode()

def download_gmsh_windows(dirpath):
    progress = QtWidgets.QProgressDialog("Install gmsh python module", None, 0, 107)
    progress.setWindowModality(Qt.WindowModal)
    progress.setMinimumDuration(1000)
    progress.setValue(1)
    progress.setLabelText("Determine latest gmsh version")
    latest = get_latest_gmsh_windows_version()
    progress.setValue(2)
    progress.setLabelText(f"Download {latest.split('/')[-1]}")
    os.makedirs(dirpath, exist_ok=True)
    with urllib.request.urlopen(latest) as url:
        length = int(url.getheader("Content-Length"))
        clength = (length-1)//100+1
        with io.BytesIO() as f:
            for i in range(100):
                progress.setValue(i+3)
                f.write(url.read(clength))
            f.seek(0)
            with ZipFile(f, "r") as zfile:
                progress.setValue(progress.value()+1)
                for fname in zfile.namelist():
                    if fname == "gmsh.py" or fname[-4:] == ".dll":
                        bname = os.path.basename(fname)
                        progress.setLabelText(f"extracting {fname.split('/')[-1]}")
                        progress.setValue(progress.value()+1)
                        with open(os.path.join(dirpath, bname), "wb") as ofile:
                                with zfile.open(fname) as ifile:
                                    ofile.write(ifile.read())
                        progress.setValue(progress.value()+1)

def install_gmsh_if_needed(mainWindow):
    try :
        import gmsh
        return True
    except:
        if sys.platform == "win32":
            download_gmsh_windows(windows_install_path)
            #pythonexe = glob.glob(os.path.dirname(sys.executable)+"/../apps/Python*/python.exe")[0]
            #RunPipDialog(mainWindow).exec_([pythonexe, '-m', 'pip', 'install', '-i', 'http://gmsh.info/python-packages/', '--trusted-host=gmsh.info', 'gmsh'])
        else:
            pythonexe = sys.executable
            RunPipDialog(mainWindow).exec_([pythonexe, '-m', 'pip', 'install', 'gmsh'])
    finally:
        try :
            importlib.invalidate_caches()
            import gmsh
            return True
        except :
            raise ValueError("cannot install gmsh python module")
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

