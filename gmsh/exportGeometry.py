# author  : Jonathan Lambrechts jonathan.lambrechts@uclouvain.be
# licence : GPLv2 (see LICENSE.md)

from PyQt5.QtCore import Qt
from PyQt5 import QtWidgets
from qgis.core import *
from qgis.gui import QgsProjectionSelectionWidget
from . import tools
import struct

def samepoint(a, b) :
    return ((a[0] - b[0])**2 + (a[1] - b[1])**2)**0.5 < 1e-8

class lineloop :
    
    def __init__(self, x0, x1, id0, id1, lids) :
        self.id = [id0, id1]
        self.x = [x0, x1]
        self.lines = [(lid, True) for lid in lids]
    
    def reverse(self) :
        self.lines = [(id, not flag) for id, flag in self.lines[::-1]]
        self.id.reverse()
        self.x.reverse()

    def merge(self, o) :
        if self.id[1] == o.id[1] or self.id[0] == o.id[0]:
            self.reverse()
        if self.id[1] == o.id[0] :
            self.id[1] = o.id[1]
            self.x[1] = o.x[1]
            self.lines = self.lines + o.lines
            return True
        if self.id[0] == o.id[1] :
            self.id[0] = o.id[0]
            self.x[0] = o.x[0]
            self.lines = o.lines + self.lines
            return True
        return False
    
    def closed(self) :
        return self.id[0] == self.id[1]


class geoWriter :

    def __init__(self, filename) :
        self.ip = 0
        self.il = 0
        self.ill = 0
        self.geof = open(filename, "w")
        self.geof.write("IP = newp;\n")
        self.geof.write("IL = newl;\n")
        self.geof.write("IS = news;\n")
        self.geof.write("ILL = newll;\n")
        self.physicals = {}
        self.lineloops = []
        self.lineInSurface = []
        self.pointInSurface = []
        self.surfaceInSurface = []
        self.physicalsInnerSurface = {}

    def writePoint(self, pt, lc) :
        if lc is not None :
            self.geof.write("Point(IP+%d) = {%.16g, %.16g, 0, %g};\n" %
                    (self.ip, pt[0], pt[1], lc))
        else :
            self.geof.write("Point(IP+%d) = {%.16g, %.16g, 0};\n" %
                    (self.ip, pt[0], pt[1]))
        self.ip += 1
        return self.ip - 1

    def writePointCheckLineLoops(self, pt, lc) :
        for ll in self.lineloops :
            if samepoint(ll.x[0], pt) :
                return ll.id[0]
            if samepoint(ll.x[1], pt) :
                return ll.id[1]
        return self.writePoint(pt, lc)

    def writeLine(self, pts) :
        self.geof.write("Spline(IL+%d) = {IP+" % self.il +
            ", IP+".join([str(i) for i in pts]) + "};\n")
        self.il += 1
        return self.il - 1
    
    def writeLineLoop(self, ll) :
        strid = [("IL+"+str(i)) if o else ("-IL-"+str(i)) for i, o in ll.lines]
        self.geof.write("Line Loop(ILL+%d) = {" % self.ill +
            ", ".join(strid) + "};\n")
        self.ill += 1
        return self.ill - 1

    def addPointFromCoordInside(self, pt, xform, lc) :
        if xform :
            pt = xform.transform(pt)
        id0 = self.writePointCheckLineLoops(pt, lc)
        self.pointInSurface += [id0]

    def addLineFromCoords(self, pts, xform, lc, physical, inside, forceAllBnd) :
        if xform :
            pts = [xform.transform(x) for x in pts]
        firstp = self.ip
        id0 = self.writePointCheckLineLoops(pts[0], lc)
        if samepoint(pts[0], pts[-1]) :
            id1 = id0
        else :
            id1 = self.writePointCheckLineLoops(pts[-1], lc)
        ids = [id0] + [self.writePoint(x, lc) for x in pts[1:-1]] + [id1]
        if forceAllBnd :
            lids = [self.writeLine((ids[i],ids[i+1])) for i in range(len(ids)-1)]
        else :
            lids = [self.writeLine(ids)] 

        if physical :
            for lid in lids :
                if physical in self.physicals :
                    self.physicals[physical].append(lid)
                else :
                    self.physicals[physical] = [lid]
        ll = lineloop(pts[0], pts[-1], id0, id1, lids)
        if inside and not ll.closed():
                self.lineInSurface += lids
                self.pointInSurface += ids
        if not inside or ll.closed() :
            self.lineloops = [o for o in self.lineloops if not ll.merge(o)]
            if ll.closed() :
                self.writeLineLoop(ll)
            else:
                self.lineloops.append(ll)
            if inside:
                if physical :
                    if physical in self.physicalsInnerSurface :
                        self.physicalsInnerSurface[physical].append(len(self.surfaceInSurface))
                    else :
                        self.physicalsInnerSurface[physical] = [len(self.surfaceInSurface)]
                self.surfaceInSurface.append(ll)

    def setBackgroundField(self, filename) :
        self.geof.write("NF = newf;\n")
        self.geof.write("Field[NF] = Structured;\n")
        self.geof.write("Field[NF].TextFormat = 0;\n")
        self.geof.write("Field[NF].FileName = \"%s\";\n" % filename)
        self.geof.write("Background Field = NF;\n")

    def __del__(self) :
        self.geof.write("Plane Surface(IS) = {ILL:ILL+%d};\n" % (self.ill - 1))
        self.geof.write("Physical Surface(\"Domain\") = {IS};\n")
        for iS, innerS in enumerate(self.surfaceInSurface):
            ill = self.writeLineLoop(innerS)
            self.geof.write("Plane Surface(IS+%d) = {ILL+%d};\n"%(iS+1,ill))
        for iS in range(len(self.surfaceInSurface)+1):
            if self.lineInSurface :
                self.geof.write("Line {" + ",".join(["IP+%d" % i for i in self.lineInSurface]) + "} In Surface{IS+%d};\n"%(iS))
            if self.pointInSurface :
                self.geof.write("Point {" + ",".join(["IL+%d" % i for i in self.pointInSurface]) + "} In Surface{IS+%d};\n"%(iS))
        print(self.physicalsInnerSurface)
        for tag, ids in self.physicalsInnerSurface.items() :
            print(tag,ids)
            self.geof.write("Physical Surface(\"" + tag + "\") = {" + ",".join(("IS + " + str(i+1)) for i in ids) + "};\n")
        for tag, ids in self.physicals.items() :
            self.geof.write("Physical Line(\"" + tag + "\") = {" + ",".join(("IL + " + str(i)) for i in ids) + "};\n")
        self.geof.close()


def writeRasterLayer(layer, filename) :
    progress = QtWidgets.QProgressDialog("Writing mesh size layer...", "Abort", 0, layer.width())
    progress.setMinimumDuration(0)
    progress.setWindowModality(Qt.WindowModal)
    progress.setValue(0)
    f = open(filename, "wb")
    ext = layer.extent()
    dx = ext.width() / layer.width()
    dy = ext.height() / layer.height()
    f.write(struct.pack("3d", ext.xMinimum() + 0.5 * dx, ext.yMinimum() + 0.5 * dy, 0))
    f.write(struct.pack("3d", dx, dy, 1))
    f.write(struct.pack("3i", layer.width(), layer.height(), 1))
    block = layer.dataProvider().block(1, layer.extent(), layer.width(), layer.height())
    for j in range(layer.width()) : 
        progress.setValue(j)
        if progress.wasCanceled():
            return False
        v = list([block.value(i, j) for i in range(layer.height() -1, -1, -1)])
        f.write(struct.pack("{}d".format(len(v)), *v))
    f.close()
    return True


def exportGeo(filename, layers, insideLayers, sizeLayer, crs, forceAllBnd) :
    nFeatures = sum((layer.featureCount()for layer in layers))
    progress = QtWidgets.QProgressDialog("Exporting geometry...", "Abort", 0, nFeatures)
    progress.setMinimumDuration(0)
    progress.setWindowModality(Qt.WindowModal)
    geo = geoWriter(filename)
    basename = filename[:-4] if filename[-4:] == ".geo" else filename

    if sizeLayer :
        crs = sizeLayer.crs()
    def addLayer(layer, progress, inside) :
        name = layer.name()
        fields = layer.fields()
        mesh_size_idx = fields.indexFromName("mesh_size")
        physical_idx = fields.indexFromName("physical")
        xform = QgsCoordinateTransform(layer.crs(), crs,QgsProject.instance())
        lc = None
        physical = None
        for feature in layer.getFeatures() :
            progress.setValue(progress.value() + 1)
            if progress.wasCanceled():
                return False
            geom = feature.geometry()
            if geom is None :
                continue
            if mesh_size_idx >= 0 :
                lc = feature[mesh_size_idx]
            if physical_idx >= 0 :
                physical = feature[physical_idx]
            if geom.type() == QgsWkbTypes.PolygonGeometry :
                polys = geom.asMultiPolygon()
                if not polys :
                    for loop in geom.asPolygon() :
                        geo.addLineFromCoords(loop, xform, lc, physical, inside, forceAllBnd)
                else:
                    for poly in polys:
                        for loop in poly :
                            geo.addLineFromCoords(loop, xform, lc, physical, inside, forceAllBnd)
            elif geom.type() == QgsWkbTypes.LineGeometry :
                lines = geom.asMultiPolyline()
                if not lines :
                    geo.addLineFromCoords(geom.asPolyline(), xform, lc, physical, inside, forceAllBnd)
                else :
                    for line in lines :
                        geo.addLineFromCoords(line, xform, lc, physical, inside, forceAllBnd)
            elif geom.type() == QgsWkbTypes.PointGeometry :
                point = geom.asPoint()
                progress.setValue(progress.value() + 1)
                geo.addPointFromCoordInside(point, xform, lc)
    for l in layers :
        addLayer(l, progress, False)
    for l in insideLayers :
        addLayer(l, progress, True)
    del progress
    if sizeLayer :
        if not writeRasterLayer(sizeLayer, basename + ".dat") :
            return False
        geo.setBackgroundField(basename + ".dat")
    return True


class Dialog(QtWidgets.QDialog) :

    def __init__(self, mainWindow, iface, meshDialog) :
        super(Dialog, self).__init__(mainWindow)
        self.meshDialog = meshDialog
        self.setWindowTitle("Generate a Gmsh geometry file")
        layout = QtWidgets.QVBoxLayout()
        self.geometrySelector = QtWidgets.QListWidget()
        tools.TitleLayout("Mesh Boundaries", self.geometrySelector, layout)
        self.forceAllBndButton = QtWidgets.QCheckBox("Force all boundary points")
        layout.addWidget(self.forceAllBndButton)
        self.insideSelector = QtWidgets.QListWidget()
        tools.TitleLayout("Forced line and points inside the domain", self.insideSelector, layout)
        self.meshSizeSelector = QtWidgets.QComboBox(self)
        self.meshSizeSelector.currentIndexChanged.connect(self.onMeshSizeSelectorActivated)
        tools.TitleLayout("Mesh size layer", self.meshSizeSelector, layout)
        self.projectionButton = QgsProjectionSelectionWidget()
        tools.TitleLayout("Projection", self.projectionButton, layout).label
        self.projectionLabel = QtWidgets.QLabel()
        layout.addWidget(self.projectionLabel)
        self.projectionLabel.hide()
        self.outputFile = tools.FileSelectorLayout("Output file", iface.mainWindow(), "save", "*.geo", layout)
        self.outputFile.fileWidget.textChanged.connect(self.validate)
        self.geometrySelector.itemChanged.connect(self.validate)
        self.runLayout = tools.CancelRunLayout(self, "Generate geometry file", self.saveGeo, layout)
        self.setLayout(layout)
        self.forceAllBndButton.stateChanged.connect(self.validate)
        self.iface = iface
        self.resize(max(450, self.width()), self.height())

    def validate(self) :
        outputFile = self.outputFile.getFile()
        something = False
        activeLayers = []
        for i in range(self.geometrySelector.count()) :
            item = self.geometrySelector.item(i)
            if item.checkState() == Qt.Checked :
                activeLayers += [item.data(Qt.UserRole).id()]
        for i in range(self.insideSelector.count()) :
            item = self.insideSelector.item(i)
            if item.data(Qt.UserRole).id() in activeLayers :
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            else :
                item.setFlags(item.flags() | Qt.ItemIsEnabled)

        self.runLayout.runButton.setEnabled(bool(outputFile != "" and  activeLayers))

    def saveGeo(self) :
        filename = self.outputFile.getFile()
        ignoredLayers = []
        insideLayers = []
        activeLayers = []
        for i in range(self.geometrySelector.count()) :
            item = self.geometrySelector.item(i)
            itemi = self.insideSelector.item(i)
            if item.checkState() == Qt.Checked :
                activeLayers += [item.data(Qt.UserRole)]
            elif itemi.checkState() == Qt.Checked:
                insideLayers += [item.data(Qt.UserRole)]
            else :
                ignoredLayers += [item.data(Qt.UserRole)]
        meshSizeLayer = self.meshSizeSelector.itemData(self.meshSizeSelector.currentIndex())
        crs = self.projectionButton.crs()
        if meshSizeLayer :
            crs = meshSizeLayer.crs()
        forceAllBnd = self.forceAllBndButton.isChecked()
        proj = QgsProject.instance()
        proj.writeEntry("gmsh", "geo_file", filename)
        proj.writeEntry("gmsh", "ignored_boundary_layers", "%%".join((l.id() for l in ignoredLayers)))
        proj.writeEntry("gmsh", "inside_layers", "%%".join((l.id() for l in insideLayers)))
        proj.writeEntry("gmsh", "projection",crs.authid())
        proj.writeEntry("gmsh", "mesh_size_layer", "None" if meshSizeLayer is None else meshSizeLayer.id())
        proj.writeEntry("gmsh", "force_all_boundary_points", "True" if forceAllBnd else "False")
        status = exportGeo(filename, activeLayers, insideLayers, meshSizeLayer, crs, forceAllBnd)
        self.close()
        if status :
            self.meshDialog.exec_()

    def onMeshSizeSelectorActivated(self, idx) :
        layer = self.meshSizeSelector.itemData(idx)
        if layer is None :
            self.projectionLabel.hide()
            self.projectionButton.show()
        else :
            self.projectionButton.hide()
            self.projectionLabel.show()
            self.projectionLabel.setText("%s" % (layer.crs().description()))

    def exec_(self) :
        proj = QgsProject.instance()
        self.outputFile.setFile(proj.readEntry("gmsh", "geo_file", "")[0])
        ignoredLayers = set(proj.readEntry("gmsh", "ignored_boundary_layers", "")[0].split("%%"))
        insideLayers = set(proj.readEntry("gmsh", "inside_layers", "")[0].split("%%"))
        meshSizeLayerId = proj.readEntry("gmsh", "mesh_size_layer", "None")[0]
        projid = proj.readEntry("gmsh", "projection", "")[0]
        forceAllBnd = proj.readEntry("gmsh","force_all_boundary_points", "False")[0] == "True"
        self.forceAllBndButton.setCheckState(Qt.Checked if forceAllBnd else Qt.Unchecked)
        crs = None
        if projid :
            crs = QgsCoordinateReferenceSystem(projid)
        if crs is None or not crs.isValid():
            crs = QgsCoordinateReferenceSystem("EPSG:4326")
        self.projectionButton.setCrs(crs)
        layers = [tree_layer.layer() for tree_layer in QgsProject.instance().layerTreeRoot().findLayers()]
        self.geometrySelector.clear()
        self.insideSelector.clear()
        self.meshSizeSelector.clear()
        self.meshSizeSelector.addItem("None", None)
        for layer in layers :
            if layer.type() == QgsMapLayer.VectorLayer :
                item = QtWidgets.QListWidgetItem(layer.name(), self.geometrySelector)
                item.setData(Qt.UserRole, layer)
                item.setFlags(item.flags() & ~ Qt.ItemIsSelectable)
                item.setCheckState(Qt.Unchecked if (layer.id() in ignoredLayers or layer.id() in insideLayers) else Qt.Checked)
                item = QtWidgets.QListWidgetItem(layer.name(), self.insideSelector)
                item.setData(Qt.UserRole, layer)
                item.setFlags(item.flags() & ~ Qt.ItemIsSelectable)
                item.setCheckState(Qt.Checked if layer.id() in insideLayers else Qt.Unchecked)
            if layer.type() == QgsMapLayer.RasterLayer :
                self.meshSizeSelector.addItem(layer.name(), layer)
                if layer.id() == meshSizeLayerId :
                    self.meshSizeSelector.setCurrentIndex(self.meshSizeSelector.count() - 1)
        self.runLayout.setFocus()
        self.validate()
        super(Dialog, self).exec_()


def createAction(iface, meshDialog) :
    dialog = Dialog(iface.mainWindow(), iface, meshDialog)
    action = QtWidgets.QAction("Generate a Gmsh geometry file", iface.mainWindow())
    action.dialog = dialog
    action.setObjectName("GMSHExportGeo")
    action.setWhatsThis("Generate a Gmsh geometry file (.geo). Polygones, lines and multilines can be exported. The mesh size can be specified either by a \"mesh_size\" field on the featres or by a raster layer. The generated file can be meshed with Gmsh (http://geuz.org/gmsh).")
    action.setStatusTip("Generate a Gmsh geometry file (.geo).")
    action.triggered.connect(dialog.exec_)
    return action


