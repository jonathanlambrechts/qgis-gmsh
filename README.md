# qgis-gmsh
This is a plugin to interract with the GMSH mesh generator (http://geuz.org/gmsh).

## Installation
Copy the gmsh directory in ~/.qgis2/python/plugin/. Then enable it through the "Plugins>Manage and Install Plugins..." menu.

## Usage
Currently, the only feature is to export the project as a .geo file to be meshed with GMSH.
It is accessible through the menu "Plugins>Gmsh>Export as Geo file". All polygones, lines and multilines of the visible layers are exported if those layers contain a "mesh_size" field. This field is used to determine the size of the elements.

## References
- **Multiscale mesh generation on the sphere.** *J. Lambrechts, R. Comblen, V. Legat, C. Geuzaine and J.-F. Remacle.* Ocean Dynamics 58, 461-473, 2008.
- **QGIS Geographic Information System.** Open Source Geospatial Foundation Project. http://qgis.osgeo.org
- **Gmsh: a three-dimensional finite element mesh generator with built-in pre- and post-processing facilities.** *C. Geuzaine and J.-F. Remacle.* International Journal for Numerical Methods in Engineering 79, 1309-1331, 2009. http://geuz.org/gmsh
