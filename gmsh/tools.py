# author  : Jonathan Lambrechts jonathan.lambrechts@uclouvain.be
# licence : GPLv2 (see LICENSE.md)

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QVBoxLayout,QHBoxLayout,QPushButton,QDialog,QLabel,QLineEdit,QFileDialog
from PyQt5.QtGui import QIcon
from qgis.gui import QgsProjectionSelectionTreeWidget
from qgis.core import *


class TitleLayout(QVBoxLayout) :

    def __init__(self, title, widget, parent) :
        super(TitleLayout, self).__init__()
        parent.addLayout(self)
        self.label = QLabel("<b>" + title + "</b>")
        self.addWidget(self.label)
        self.addWidget(widget)


class FileSelectorLayout(QVBoxLayout) :

    def __init__(self, title, mainWindow, action, ext, parent, txt = None) :
        super(FileSelectorLayout, self).__init__()
        self.action = action
        self.ext = ext
        self.title = title
        parent.addLayout(self)
        self.addWidget(QLabel("<b>" + title + "</b>"))
        self.mainWindow = mainWindow
        layout = QHBoxLayout()
        self.addLayout(layout)
        fileButton = QPushButton("");
        fileButton.setIcon(QIcon.fromTheme("document-open"))
        fileButton.clicked.connect(self.browseFile)
        self.fileWidget = QLineEdit()
        self.fileWidget.setText(txt)
        layout.addWidget(self.fileWidget)
        layout.addWidget(fileButton)

    def browseFile(self) :
        if self.action == "save" :
            filename = QFileDialog.getSaveFileName(self.mainWindow,
                self.title, filter=self.ext)
        elif self.action == "opendir" :
            filename = QFileDialog.getExistingDirectory(self.mainWindow,
                self.title)
        else :
            filename,_ = QFileDialog.getOpenFileName(self.mainWindow,
                self.title, filter=self.ext)
        if filename :
            self.setFile(filename)

    def setFile(self, filename):
        self.fileWidget.setText(filename)

    def getFile(self) :
        return self.fileWidget.text()


class CancelRunLayout(QHBoxLayout) :

    def __init__(self, dialog, runTitle, runCallback, parent) :
        super(CancelRunLayout, self).__init__()
        parent.addLayout(self)
        self.addStretch(1)
        cancelButton = QPushButton("Cancel")
        cancelButton.clicked.connect(dialog.close)
        self.addWidget(cancelButton, 0)
        self.runButton = QPushButton(runTitle)
        self.runButton.clicked.connect(runCallback)
        self.addWidget(self.runButton, 0)

    def setFocus(self) :
        self.runButton.setFocus()

