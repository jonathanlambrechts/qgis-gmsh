VERS=$1
if [ -z "$VERS" ]; then
  echo "specify the version"
  exit
fi
git tag $VERS
zip gmsh.zip gmsh-$VERS/*.py gmsh/metadata.txt gmsh/LICENSE.md
echo "upload manually gmsh-$VERS.zip to http://plugins.qgis.org/plugins/gmsh/version/add/"
