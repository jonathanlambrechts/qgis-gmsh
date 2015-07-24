from qgis.core import *

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
        self.lineloops = []

    def writePoint(self, pt, lc) :
        self.geof.write("Point(IP+%d) = {%.16g, %.16g, 0, %g};\n" %
            (self.ip, pt[0], pt[1], lc))
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

    def addLineFromCoords(self, pts, xform, lc) :
        if xform :
            pts = [xform.transform(x) for x in pts]
        firstp = self.ip
        id0 = self.writePointCheckLineLoops(pts[0], lc)
        if samepoint(pts[0], pts[-1]) :
            id1 = id0
        else :
            id1 = self.writePointCheckLineLoops(pts[-1], lc)
        ids = [id0] + [self.writePoint(x, lc) for x in pts[1:-1]] + [id1]
        id = self.writeLine(ids) 
        ll = lineloop(pts[0], pts[-1], id0, id1, id)
        self.lineloops = [o for o in self.lineloops if not ll.merge(o)]
        if ll.closed() :
            self.writeLineLoop(ll)
        else:
            self.lineloops.append(ll)

    def __del__(self) :
        self.geof.write("Plane Surface(IS) = {ILL:ILL+%d};\n" % (self.ill - 1))
        self.geof.write("Physical Surface(\"Domain\") = {IS};\n")
        self.geof.close()


def exportGeo(iface, filename) :
    layers = iface.mapCanvas().layers()
    crsDest = iface.mapCanvas().mapSettings().destinationCrs()
    geo = geoWriter(filename)

    for layer in layers :
        if layer.type() == QgsMapLayer.VectorLayer :
            name = layer.name()
            fields = layer.pendingFields()
            mesh_size_idx = fields.fieldNameIndex("mesh_size")
            if mesh_size_idx < 0 :
                print("Layer \'%s\' has no \'mesh_size\' field, skipping" % name)
                continue
            crsSrc = layer.crs()
            xform = QgsCoordinateTransform(crsSrc, crsDest)
            for feature in layer.getFeatures() :
                geom = feature.geometry()
                if mesh_size_idx >= 0 :
                    lc = feature[mesh_size_idx]
                if geom.type() == QGis.Polygon :
                    geo.addLineFromCoords(geom.asPolygon()[0], xform, lc)
                elif geom.type() == QGis.Line :
                    lines = geom.asMultiPolyline()
                    if not lines :
                        lines = [geom.asPolyline()]
                    for line in lines :
                        geo.addLineFromCoords(line, xform, lc)
                else :
                    print("unknown feature type\n")
                    continue
