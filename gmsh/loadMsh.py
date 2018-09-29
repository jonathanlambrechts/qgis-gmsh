# author  : Jonathan Lambrechts jonathan.lambrechts@uclouvain.be
# licence : GPLv2 (see LICENSE.md)

from PyQt5.QtCore import Qt,QDir,QThread,QFileInfo,QFile
from PyQt5 import QtWidgets
from qgis.core import QgsProject,QgsFields,QgsVectorFileWriter,QgsPointXY,QgsFeature,QgsWkbTypes,QgsGeometry,QgsCoordinateReferenceSystem,QgsVectorLayer
from . import gmshType
import os
from . import tools
from qgis.gui import QgsProjectionSelectionWidget

def loadMsh(filename, crs, outputdir):
    progress = QtWidgets.QProgressDialog("Converting GMSH mesh...", "Abort", 0, 100)
    progress.setMinimumDuration(1000)
    progress.setWindowModality(Qt.WindowModal)
    QDir().mkpath(outputdir)
    fin = open(filename, "r");
    l = fin.readline()
    useFormat3 = False
    vertices = {}
    physicalNames = {}
    entityPhysical = {}
    physicalWriter = {}
    entityWriter = {}
    def abort() :
        for writer in physicalWriter.values() :
            QgsVectorFileWriter.deleteShapeFile(writer.path + ".shp")
            QFile.remove(writer.path + ".cpg")
    while l != "" :
        w = l.split()
        if w[0] == "$MeshFormat":
            l = fin.readline().split()
            if int(float(l[0])) == 3:
                useFormat3 = True
            elif int(float(l[0])) == 2 :
                useFormat3 = False 
            else :
                raise ValueError("cannot read mesh format " + l[0])
            l = fin.readline()
        elif w[0] == "$PhysicalNames" :
            n = int(fin.readline())
            for i in range(n) :
                dim, tag, name = fin.readline().split()
                physicalNames[(int(dim), int(tag))] = name[1:-1]
            fin.readline()
        elif w[0] == "$Entities" and useFormat3:
            ns = list(int(fin.readline()) for i in range(4))
            for dim in range (4) :
                for i in range(ns[dim]) :
                    l = fin.readline().split()
                    j, nbnd = int(l[0]), int(l[1])
                    nphys = int(l[2+nbnd])
                    entityPhysical[(dim, j)] = int(l[2+nbnd+nphys]) if nphys > 0 else None
        elif w[0] == "$Nodes" :
            n = int(fin.readline())
            for i in range(n) :
                if i % 1000 == 0 :
                    QtWidgets.QApplication.processEvents()
                    progress.setValue((7 * i)/n)
                    if progress.wasCanceled():
                        abort()
                        return
                if useFormat3 :
                    j, x, y, z  = fin.readline().split()[:4]
                else :
                    (j, x, y, z) = fin.readline().split()
                vertices[int(j)] = [float(x), float(y), float(z), int(j)]
        elif w[0] == "$Elements" :
            n = int(fin.readline())
            for i in range(n) :
                if i % 100 == 0 :
                    QtWidgets.QApplication.processEvents()
                    if progress.wasCanceled():
                        abort()
                        return
                if i % 1000 == 0 :
                    progress.setValue(7 + (93 * i)/n)
                l = fin.readline().split()
                if useFormat3 :
                    j, t, e, nf = int(l[0]), int(l[1]), int(l[2]), int(l[3])
                    nv = gmshType.Type[t].numVertices
                    evertices = [vertices[int(i)] for i in l[4:4+nv]]
                    partition = [int(i) for i in l[5 + nv : 5 + nv + int(l[4 + nv])]] if nf > nv else []
                else :
                    j, t, nf, p, e = int(l[0]), int(l[1]), int(l[2]), int(l[3]), int(l[4])
                    evertices = [vertices[int(i)] for i in l[3 + nf:]]
                    partition = [int(i) for i in l[6 : 6 + int(l[5])]] if nf > 2 else []
                edim = gmshType.Type[t].baseType.dimension
                writer = entityWriter.get((edim, e), None)
                if writer is None :
                    if useFormat3 :
                        if (edim, e) in entityPhysical :
                            p = entityPhysical[(edim, e)]
                        else :
                            p = 0
                    writer = physicalWriter.get((edim, p), None)
                    if writer is None :
                        fields = QgsFields()
                        ltype = [QgsWkbTypes.Point, QgsWkbTypes.LineString, QgsWkbTypes.Polygon][edim]
                        name = physicalNames.get((edim, p), None)
                        if name is None :
                            name = ["points", "lines", "elements"][edim] + ("_" + str(p) if p >= 0 else "")
                            physicalNames[(edim, p)] = name
                        path = os.path.join(outputdir, name)
                        writer = QgsVectorFileWriter(path, "system", fields, ltype, crs,driverName="ESRI Shapefile")
                        writer.path = path
                        physicalWriter[(edim, p)] = writer
                    entityWriter[(edim, e)] = writer
                points = list([QgsPointXY(v[0], v[1]) for v in evertices])
                if edim == 0 :
                    geom = QgsGeometry.fromPointXY(points[0])
                elif edim == 1 :
                    geom = QgsGeometry.fromPolylineXY(points)
                elif edim == 2 :
                    v = evertices[0]
                    points.append(QgsPointXY(v[0], v[1]))
                    geom = QgsGeometry.fromPolygonXY([points])
                feature = QgsFeature()
                feature.setGeometry(geom)
                writer.addFeature(feature)
        l = fin.readline()

    group = QgsProject.instance().layerTreeRoot().addGroup("mesh")
    paths = []
    for writer in physicalWriter.values() :
        paths.append(writer.path + ".shp")
        del writer
    QThread.sleep(1)
    progress.setValue(100)
    for path in paths :
        l = QgsVectorLayer(path, QFileInfo(path).baseName(), "ogr")
        QgsProject.instance().addMapLayer(l, False)
        group.addLayer(l) 


class Dialog(QtWidgets.QDialog) :

    def __init__(self, mainWindow, iface) :
        super(Dialog, self).__init__(mainWindow)
        self.setWindowTitle("Convert a Gmsh mesh file into shapefiles")
        self.setMinimumWidth(800)
        layout = QtWidgets.QVBoxLayout()
        self.inputMsh = tools.FileSelectorLayout("Mesh file",
            mainWindow, "open", "*.msh", layout)
        self.projectionButton = QgsProjectionSelectionWidget()
        tools.TitleLayout("Projection", self.projectionButton, layout).label
        self.outputDir = tools.FileSelectorLayout("Output directory",
            mainWindow, "opendir", "", layout)
        self.importShpBox = QtWidgets.QCheckBox("Open generated files")
        layout.addWidget(self.importShpBox)
        self.inputMsh.fileWidget.textChanged.connect(self.onInputFileChange)
        self.inputMsh.fileWidget.textChanged.connect(self.validate)
        self.outputDir.fileWidget.textChanged.connect(self.validate)
        self.runLayout = tools.CancelRunLayout(self, "Convert", self.loadMsh, layout)
        self.runLayout.runButton.setEnabled(False)
        self.setLayout(layout)
        self.setMaximumHeight(self.height())
        self.resize(max(400, self.width()), self.height())
        self.validate()

    def onInputFileChange(self, text) :
        if (self.outputDir.getFile() == "" or self.autoShapeName) and text.endswith(".msh") :
            self.outputDir.setFile(text[:-4]+"_shp")

    def validate(self) :
        inF = self.inputMsh.getFile()
        outF = self.outputDir.getFile()
        self.autoShapeName = inF.endswith(".msh") and outF == inF[:-4] + "_shp"
        if os.path.isfile(inF) and outF != "" :
            self.runLayout.runButton.setEnabled(True)
        else :
            self.runLayout.runButton.setEnabled(False)

    def loadMsh(self) :
        self.close()
        inputFile = self.inputMsh.getFile()
        outputDir = self.outputDir.getFile()
        crs = self.projectionButton.crs()
        importShp = self.importShpBox.checkState() == Qt.Checked
        proj = QgsProject.instance()
        proj.writeEntry("gmsh", "msh_file", inputFile)
        proj.writeEntry("gmsh", "shp_directory", outputDir)
        proj.writeEntry("gmsh", "projection", crs.authid())
        proj.writeEntry("gmsh", "import_shp", importShp)
        loadMsh(self.inputMsh.getFile(), crs, self.outputDir.getFile())

    def exec_(self) :
        proj = QgsProject.instance()
        self.outputDir.setFile(proj.readEntry("gmsh", "shp_directory", "")[0])
        self.inputMsh.setFile(proj.readEntry("gmsh", "msh_file", "")[0])
        self.importShpBox.setCheckState(Qt.Checked if proj.readBoolEntry("gmsh", "import_shp", True)[0] else Qt.Unchecked)
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
    action = QtWidgets.QAction("Convert a Gmsh mesh file into shapefiles", iface.mainWindow())
    action.dialog = dialog
    action.setWhatsThis("Convert a 2D Gmsh mesh file (.msh) into shapefiles (.shp). One shapefile is generated by physical tag in the mesh file.")
    action.setStatusTip("Convert a 2D Gmsh mesh file (.msh) into shapefiles (.shp). One shapefile is generated by physical tag in the mesh file.")
    action.setObjectName("GMSHImportMSH")
    action.triggered.connect(dialog.exec_)
    return action

