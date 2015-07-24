# qgis-gmsh
This is a plugin to interract with the GMSH mesh generator (http://geuz.org/gmsh).

## installation
Copy all files in ~/.qgis2/python/plugin/gmsh.

## usage
The only feature is to export current map as as .geo file to be meshed by GMSH.
It is accessible through the menu Plugin>Gmsh>Export as Geo file". All polygones, lines and multilines of the visible layers are exported if they contain a "mesh_size" field. This field is used to determine the size of the elements.
