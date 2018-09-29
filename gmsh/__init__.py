# author  : Jonathan Lambrechts jonathan.lambrechts@uclouvain.be
# licence : GPLv2 (see LICENSE.md)

def classFactory(iface) :
    from .mainPlugin import GmshPlugin
    return GmshPlugin(iface)
