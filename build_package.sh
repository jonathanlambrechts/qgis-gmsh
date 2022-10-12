VERS=$1
if [ -z "$VERS" ]; then
  echo "specify the version"
  exit
fi
git tag $VERS
zip gmsh-$VERS.zip qgis-gmsh/*.py qgis-gmsh/metadata.txt qgis-gmsh/LICENSE.md
echo "upload manually gmsh-$VERS.zip to http://plugins.qgis.org/plugins/gmsh/version/add/"
