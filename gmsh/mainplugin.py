from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *

#import resources


class GmshPlugin:

    def __init__(self, iface):
        self.iface = iface

    def initGui(self):
        # create action that will start plugin configuration
        #self.action = QAction(QIcon(":/plugins/testplug/icon.png"), "Test plugin", self.iface.mainWindow())
        self.action = QAction(None, "Test plugin", self.iface.mainWindow())
        self.action.setObjectName("testAction")
        self.action.setWhatsThis("Configuration for test plugin")
        self.action.setStatusTip("This is status tip")
        QObject.connect(self.action, SIGNAL("triggered()"), self.run)

        # add toolbar button and menu item
        #self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&Test plugins", self.action)

        # connect to signal renderComplete which is emitted when canvas
        # rendering is done
        QObject.connect(self.iface.mapCanvas(), SIGNAL("renderComplete(QPainter *)"), self.renderTest)

    def unload(self):
        self.iface.removePluginMenu("&Test plugins", self.action)
        self.iface.removeToolBarIcon(self.action)
        # disconnect form signal of the canvas
        QObject.disconnect(self.iface.mapCanvas(), SIGNAL("renderComplete(QPainter *)"), self.renderTest)

    def run(self):
        # create and show a configuration dialog or something similar
        print "TestPlugin: run called!"

    def renderTest(self, painter):
        # use painter for drawing to map canvas
        print "TestPlugin: renderTest called!"

