# author  : Jonathan Lambrechts jonathan.lambrechts@uclouvain.be
# licence : GPLv2 (see LICENSE.md)

from PyQt5.QtCore import Qt,QDir,QThread,QFileInfo,QFile
from PyQt5 import QtWidgets
from qgis.core import QgsProject,QgsFeature,QgsGeometry,QgsCoordinateReferenceSystem,QgsVectorLayer
from qgis import processing
import os
from . import tools
from qgis.gui import QgsProjectionSelectionWidget
import numpy as np

def loadMsh(filename, crs):
    import gmsh
    progress = QtWidgets.QProgressDialog("Reading mesh...", "Abort", 0, 30)
    progress.setMinimumDuration(1000)
    progress.setWindowModality(Qt.WindowModal)
    gmsh.initialize()
    progress.setValue(1)
    QtWidgets.QApplication.processEvents()
    if progress.wasCanceled(): return
    gmsh.open(filename)
    progress.setValue(10)
    QtWidgets.QApplication.processEvents()
    nodes_tag, nodes_xyz, _ = gmsh.model.mesh.get_nodes()
    nodes_xyz = nodes_xyz.reshape(-1, 3)
    nodes_order = nodes_tag.argsort()
    paths = []
    elements = {}
    written = []
    def get_xyz(e):
        return nodes_xyz[nodes_order[np.searchsorted(nodes_tag, e, sorter=nodes_order)]]
    def get_entity(edim, etag, els):
        QtWidgets.QApplication.processEvents()
        if progress.wasCanceled(): return
        if edim == 0:
            els.append(get_xyz(gmsh.model.mesh.get_elements_by_type(15, etag)[1]))
        if edim == 1:
            els.append(get_xyz(gmsh.model.mesh.get_elements_by_type(1, etag)[1].reshape(-1,2)))
        if edim == 2:
            els.append(get_xyz(gmsh.model.mesh.get_elements_by_type(2, etag)[1].reshape(-1,3)))
            els.append(get_xyz(gmsh.model.mesh.get_elements_by_type(3, etag)[1].reshape(-1,4)))
    loaded_entities = []
    for pdim, ptag in gmsh.model.get_physical_groups():
        if pdim > 2: continue
        name = gmsh.model.get_physical_name(pdim, ptag)
        if name is None:
            name = "physical_"+str(pdim)+"_"+str(ptag)
        els = []
        for etag in gmsh.model.get_entities_for_physical_group(pdim, ptag):
            get_entity(pdim, etag, els)
            loaded_entities.append((pdim,etag))
            elements[name] = (pdim, els)
    for edim, etag in gmsh.model.get_entities():
        if edim > 2: continue
        if (edim,etag) in loaded_entities: continue
        name = "entity_"+str(edim)+"_"+str(etag)
        els = []
        get_entity(edim, etag, els)
        elements[name] = (edim, els)
    progress.setValue(20)
    progress.setLabelText("Writing elements...")

    group = QgsProject.instance().layerTreeRoot().addGroup(QFileInfo(filename).baseName())
    dtypes = [np.dtype([("o",np.byte), ("t",np.uint32),("x",np.float64,2)], align=False),
              np.dtype([("o",np.byte), ("t",np.uint32), ("n",np.uint32),("x",np.float64,(2,2))], align=False),
              np.dtype([("o",np.byte), ("t",np.uint32), ("n",np.uint32), ("m",np.uint32),("x",np.float64,(4,2))], align=False)]
    for name, (pdim, elements) in elements.items():
        QtWidgets.QApplication.processEvents()
        if progress.wasCanceled(): return
        if pdim != 2 and pdim != 1: continue
        layer = QgsVectorLayer(["MultiPoint","MultiLineString","MultiPolygon"][pdim],name,"memory")
        layer.setCrs(crs)
        prov = layer.dataProvider()

        for els in elements:
            if els.shape[0] == 0: continue
            wkbn = np.empty(els.shape[0], dtype=dtypes[pdim])
            wkbn["o"][:] = 1
            wkbn["t"][:] = pdim+1
            if pdim == 2:
                wkbn["n"][:] = 1
                wkbn["m"][:] = 4
                wkbn["x"][:,:3,:] = els[:,:,:2]
                wkbn["x"][:,3,:] = els[:,0,:2]
            elif pdim == 1:
                wkbn["n"][:] = 2
                wkbn["x"][:,:,:] = els[:,:,:2]
            else:
                wkbn["x"][:,:] = els[:,0,:2]
            wkb = b'\x01'+np.array((pdim+4,els.shape[0]),np.uint32).tobytes()+wkbn.tobytes()
            geom = QgsGeometry()
            geom.fromWkb(wkb)
            feature = QgsFeature()
            feature.setGeometry(geom)
            prov.addFeature(feature)
        QtWidgets.QApplication.processEvents()
        if progress.wasCanceled(): return
        layer.updateExtents()
        alg = processing.run("qgis:multiparttosingleparts",{'INPUT': layer, 'OUTPUT': 'TEMPORARY_OUTPUT'})
        layer = alg['OUTPUT']
        layer.setName(name)
        layer = QgsProject.instance().addMapLayer(layer, False)
        group.addLayer(layer) 
    progress.setValue(30)
    return


class Dialog(QtWidgets.QDialog) :

    def __init__(self, mainWindow, iface) :
        self.mainWindow = mainWindow
        super(Dialog, self).__init__(mainWindow)
        self.setWindowTitle("Convert a Gmsh mesh file into shapefiles")
        self.setMinimumWidth(800)
        layout = QtWidgets.QVBoxLayout()
        self.inputMsh = tools.FileSelectorLayout("Mesh file",
            mainWindow, "open", "*.msh", layout)
        self.projectionButton = QgsProjectionSelectionWidget()
        tools.TitleLayout("Projection", self.projectionButton, layout).label
        self.inputMsh.fileWidget.textChanged.connect(self.validate)
        self.runLayout = tools.CancelRunLayout(self, "Convert", self.loadMsh, layout)
        self.runLayout.runButton.setEnabled(False)
        self.setLayout(layout)
        self.setMaximumHeight(self.height())
        self.resize(max(400, self.width()), self.height())
        self.validate()

    def validate(self) :
        inF = self.inputMsh.getFile()
        if os.path.isfile(inF) :
            self.runLayout.runButton.setEnabled(True)
        else :
            self.runLayout.runButton.setEnabled(False)

    def loadMsh(self) :
        self.close()
        inputFile = self.inputMsh.getFile()
        crs = self.projectionButton.crs()
        proj = QgsProject.instance()
        proj.writeEntry("gmsh", "msh_file", inputFile)
        proj.writeEntry("gmsh", "projection", crs.authid())
        if not tools.install_gmsh_if_needed(self.mainWindow):
            return
        loadMsh(self.inputMsh.getFile(), crs)

    def exec_(self) :
        proj = QgsProject.instance()
        self.inputMsh.setFile(proj.readEntry("gmsh", "msh_file", "")[0])
        self.runLayout.setFocus()
        projid = proj.readEntry("gmsh", "projection", "")[0]
        crs = None
        if projid :
            crs = QgsCoordinateReferenceSystem(projid)
        if crs is None or not crs.isValid():
            crs = QgsCoordinateReferenceSystem("EPSG:4326")
        self.projectionButton.setCrs(crs)
        super(Dialog, self).exec_()


def createAction(iface) :
    dialog = Dialog(iface.mainWindow(), iface)
    action = QtWidgets.QAction("Import a Gmsh mesh file", iface.mainWindow())
    action.dialog = dialog
    action.setWhatsThis("Convert a 2D Gmsh mesh file (.msh) into shapefiles (.shp). One shapefile is generated by physical tag in the mesh file.")
    action.setStatusTip("Convert a 2D Gmsh mesh file (.msh) into shapefiles (.shp). One shapefile is generated by physical tag in the mesh file.")
    action.setObjectName("GMSHImportMSH")
    action.triggered.connect(dialog.exec_)
    return action

