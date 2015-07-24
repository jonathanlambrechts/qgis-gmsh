# qgis-gmsh
This is a plugin to interract with the GMSH mesh generator (see http://geuz.org/gmsh).
The only feature is to export current map as as .geo file. All polygones, lines and multilines of the visible layers are exported if they contain a \"mesh_size\" field. This field is used to determine the size of the elements. The generated file can be meshed by GMSH.

