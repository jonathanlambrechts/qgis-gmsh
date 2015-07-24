from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *

#import resources
import exportGeo


class GmshPlugin:

    def __init__(self, iface):
        self.iface = iface

    def initGui(self):
        #self.action = QAction(QIcon(":/plugins/testplug/icon.png"), "Test plugin", self.iface.mainWindow())
        self.action = QAction("Export as Geo file", self.iface.mainWindow())
        self.action.setObjectName("GMSHExportGeo")
        self.action.setWhatsThis("Export current map as as .geo file. All polygones, lines and multilines of the visible layers are exported if they contain a \"mesh_size\" field. This field is used to determine the size of the elements. The generated file can be meshed by GMSH (http://geuz.org/gmsh).")
        self.action.setStatusTip("Export current map as as .geo file.")
        QObject.connect(self.action, SIGNAL("triggered()"), self.runGeo)

        # add toolbar button and menu item
        #self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&Gmsh", self.action)

    def unload(self):
        self.iface.removePluginMenu("&Gmsh", self.action)
        self.iface.removeToolBarIcon(self.action)

    def runGeo(self):
        filename = QFileDialog.getSaveFileName(self.iface.mainWindow(), "Save File")
        if filename :
            exportGeo.exportGeo(self.iface, filename)


