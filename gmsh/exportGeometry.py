# author  : Jonathan Lambrechts jonathan.lambrechts@uclouvain.be
# licence : GPLv2 (see LICENSE.md)

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
import tools

def samepoint(a, b) :
    return ((a[0] - b[0])**2 + (a[1] - b[1])**2)**0.5 < 1e-8

class lineloop :
    
    def __init__(self, x0, x1, id0, id1, lineid) :
        self.id = [id0, id1]
        self.x = [x0, x1]
        self.lines = [(lineid, True)]
    
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
        self.geof.write("Line(IL+%d) = {IP+" % self.il +
            ", IP+".join([str(i) for i in pts]) + "};\n")
        self.il += 1
        return self.il - 1
    
    def writeLineLoop(self, ll) :
        strid = [("IL+"+str(i)) if o else ("-IL-"+str(i)) for i, o in ll.lines]
        self.geof.write("Line Loop(ILL+%d) = {" % self.ill +
            ", ".join(strid) + "};\n")
        self.ill += 1
        return self.ill - 1

    def addLineFromCoords(self, pts, xform, lc, physical) :
        if xform :
            pts = [xform.transform(x) for x in pts]
        firstp = self.ip
        id0 = self.writePointCheckLineLoops(pts[0], lc)
        if samepoint(pts[0], pts[-1]) :
            id1 = id0
        else :
            id1 = self.writePointCheckLineLoops(pts[-1], lc)
        ids = [id0] + [self.writePoint(x, lc) for x in pts[1:-1]] + [id1]
        lid = self.writeLine(ids) 
        if physical :
            if self.physicals.has_key(physical) :
                self.physicals[physical].append(lid)
            else :
                self.physicals[physical] = [lid]
        ll = lineloop(pts[0], pts[-1], id0, id1, lid)
        self.lineloops = [o for o in self.lineloops if not ll.merge(o)]
        if ll.closed() :
            self.writeLineLoop(ll)
        else:
            self.lineloops.append(ll)

    def setBackgroundField(self, filename) :
        self.geof.write("NF = newf;\n")
        self.geof.write("Field[NF] = Structured;\n")
        self.geof.write("Field[NF].TextFormat = 1;\n")
        self.geof.write("Field[NF].FileName = \"%s\";\n" % filename)
        self.geof.write("Background Field = NF;\n")

    def __del__(self) :
        self.geof.write("Plane Surface(IS) = {ILL:ILL+%d};\n" % (self.ill - 1))
        self.geof.write("Physical Surface(\"Domain\") = {IS};\n")
        for tag, ids in self.physicals.iteritems() :
            self.geof.write("Physical Line(\"" + tag + "\") = {" + ",".join(("IL + " + str(i)) for i in ids) + "};\n")
        self.geof.close()


def writeRasterLayer(layer, filename) :
    progress = QProgressDialog("Writing mesh size layer...", "Abort", 0, layer.width())
    progress.setMinimumDuration(0)
    progress.setWindowModality(Qt.WindowModal)
    f = open(filename, "w")
    ext = layer.extent()
    f.write("%.16g %.16g 0\n" % (ext.xMinimum(), ext.yMinimum()))
    f.write("%.16g %.16g 1\n" % (ext.width() / layer.width(), ext.height() / layer.height()))
    f.write("%d %d 1\n" % (layer.width(), layer.height()))
    block = layer.dataProvider().block(1, layer.extent(), layer.width(), layer.height())
    for j in range(layer.width()) : 
        progress.setValue(j)
        if progress.wasCanceled():
            return False
        for i in range(layer.height() -1, -1, -1) :
            f.write("%.2e " %  block.value(i, j))
        f.write("\n")
    f.close()
    return True


def exportGeo(filename, layers, sizeLayer, crs) :
    nFeatures = sum((layer.featureCount()for layer in layers))
    progress = QProgressDialog("Exporting geometry...", "Abort", 0, nFeatures)
    progress.setMinimumDuration(0)
    progress.setWindowModality(Qt.WindowModal)
    geo = geoWriter(filename)
    basename = filename[:-4] if filename[-4:] == ".geo" else filename

    if sizeLayer :
        crs = sizeLayer.crs()
    i = 0
    for layer in layers :
        name = layer.name()
        fields = layer.pendingFields()
        mesh_size_idx = fields.fieldNameIndex("mesh_size")
        physical_idx = fields.fieldNameIndex("physical")
        xform = QgsCoordinateTransform(layer.crs(), crs)
        lc = None
        physical = None
        for feature in layer.getFeatures() :
            progress.setValue(i)
            if progress.wasCanceled():
                return False
            i += 1
            geom = feature.geometry()
            if mesh_size_idx >= 0 :
                lc = feature[mesh_size_idx]
            if physical_idx >= 0 :
                physical = feature[physical_idx]
            if geom.type() == QGis.Polygon :
                geo.addLineFromCoords(geom.asPolygon()[0], xform, lc, physical)
            elif geom.type() == QGis.Line :
                lines = geom.asMultiPolyline()
                if not lines :
                    geo.addLineFromCoords(geom.asPolyline(), xform, lc, physical)
                else :
                    for line in lines :
                        geo.addLineFromCoords(line, xform, lc, physical)
    del progress
    if sizeLayer :
        if not writeRasterLayer(sizeLayer, basename + ".dat") :
            return False
        geo.setBackgroundField(basename + ".dat")
    return True


class Dialog(QDialog) :

    def __init__(self, mainWindow, iface, meshDialog) :
        super(Dialog, self).__init__(mainWindow)
        self.meshDialog = meshDialog
        self.setWindowTitle("Generate a Gmsh geometry file")
        layout = QVBoxLayout()
        self.geometrySelector = QListWidget()
        tools.TitleLayout("Mesh Boundaries", self.geometrySelector, layout)
        self.meshSizeSelector = QComboBox(self)
        self.meshSizeSelector.currentIndexChanged.connect(self.onMeshSizeSelectorActivated)
        tools.TitleLayout("Mesh size layer", self.meshSizeSelector, layout)
        self.projectionButton = tools.CRSButton()
        tools.TitleLayout("Projection", self.projectionButton, layout).label
        self.projectionLabel = QLabel()
        layout.addWidget(self.projectionLabel)
        self.projectionLabel.hide()
        self.outputFile = tools.FileSelectorLayout("Output file", iface.mainWindow(), "save", "*.geo", layout)
        self.outputFile.fileWidget.textChanged.connect(self.validate)
        self.geometrySelector.itemChanged.connect(self.validate)
        self.runLayout = tools.CancelRunLayout(self, "Generate geometry file", self.saveGeo, layout)
        self.setLayout(layout)
        self.iface = iface
        self.resize(max(450, self.width()), self.height())

    def validate(self) :
        outputFile = self.outputFile.getFile()
        something = any((self.geometrySelector.item(i).checkState() == Qt.Checked for i in range(self.geometrySelector.count())))
        if outputFile != "" and something :
            self.runLayout.runButton.setEnabled(True)
        else :
            self.runLayout.runButton.setEnabled(False)

    def saveGeo(self) :
        filename = self.outputFile.getFile()
        ignoredLayers = []
        activeLayers = []
        for i in range(self.geometrySelector.count()) :
            item = self.geometrySelector.item(i)
            if item.checkState() == Qt.Checked :
                activeLayers += [item.data(Qt.UserRole)]
            else :
                ignoredLayers += [item.data(Qt.UserRole)]
        meshSizeLayer = self.meshSizeSelector.itemData(self.meshSizeSelector.currentIndex())
        crs = self.projectionButton.crs()
        if meshSizeLayer :
            crs = meshSizeLayer.crs()
        proj = QgsProject.instance()
        proj.writeEntry("gmsh", "geo_file", filename)
        proj.writeEntry("gmsh", "ignored_boundary_layers", "%%".join((l.id() for l in ignoredLayers)))
        proj.writeEntry("gmsh", "projection",crs.authid())
        proj.writeEntry("gmsh", "mesh_size_layer", "None" if meshSizeLayer is None else meshSizeLayer.id())
        status = exportGeo(filename, activeLayers, meshSizeLayer, crs)
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
        meshSizeLayerId = proj.readEntry("gmsh", "mesh_size_layer", "None")[0]
        projid = proj.readEntry("gmsh", "projection", "")[0]
        crs = None
        if projid :
            crs = QgsCoordinateReferenceSystem(projid)
        if crs is None or not crs.isValid():
            crs = QgsCoordinateReferenceSystem("EPSG:4326")
        self.projectionButton.setCrs(crs)
        layers = self.iface.legendInterface().layers()
        self.geometrySelector.clear()
        self.meshSizeSelector.clear()
        self.meshSizeSelector.addItem("None", None)
        for layer in layers :
            if layer.type() == QgsMapLayer.VectorLayer :
                item = QListWidgetItem(layer.name(), self.geometrySelector)
                item.setData(Qt.UserRole, layer)
                item.setFlags(item.flags() or ItemIsCheckable)
                item.setCheckState(Qt.Unchecked if layer.id() in ignoredLayers else Qt.Checked)
            if layer.type() == QgsMapLayer.RasterLayer :
                self.meshSizeSelector.addItem(layer.name(), layer)
                if layer.id() == meshSizeLayerId :
                    self.meshSizeSelector.setCurrentIndex(self.meshSizeSelector.count() - 1)
        self.runLayout.setFocus()
        super(Dialog, self).exec_()


def createAction(iface, meshDialog) :
    dialog = Dialog(iface.mainWindow(), iface, meshDialog)
    action = QAction("Generate a Gmsh geometry file", iface.mainWindow())
    action.dialog = dialog
    action.setObjectName("GMSHExportGeo")
    action.setWhatsThis("Generate a Gmsh geometry file (.geo). Polygones, lines and multilines can be exported. The mesh size can be specified either by a \"mesh_size\" field on the featres or by a raster layer. The generated file can be meshed with Gmsh (http://geuz.org/gmsh).")
    action.setStatusTip("Generate a Gmsh geometry file (.geo).")
    QObject.connect(action, SIGNAL("triggered()"), dialog.exec_)
    return action


