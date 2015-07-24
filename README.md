# qgis-gmsh
This is a plugin to interract with the GMSH mesh generator (http://geuz.org/gmsh).

## Installation
Copy the gmsh directory in ~/.qgis2/python/plugin/. Then enable it through the "Plugins>Manage and Install Plugins..." menu.

## Usage
Currently, the only feature is to export the project as a .geo file to be meshed with GMSH.
It is accessible through the menu "Plugins>Gmsh>Export as Geo file". All polygones, lines and multilines of the visible layers are exported if those layers contain a "mesh_size" field. This field is used to determine the size of the elements.
