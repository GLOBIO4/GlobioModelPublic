# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Class with per landuse type:
# - name
# - code
# - claims per region (dict with region as key)
# - suitability rastername.
# - suitability raster.
#
# Modified: -
#-------------------------------------------------------------------------------

import os

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class LanduseType(object):
  
  #-------------------------------------------------------------------------------
  def __init__(self,name=None,code=None):
    if name is None:
      name = ""
    if code is None:
      code = 0
    self.name = name               # The name.
    self.code = code               # The code.
    self.claims = dict()           # Associative array with (region-area) like {25:5,26:6}.
    self.suitRasterName = None     # The suitability raster name.
    self.suitRas = None            # The suitability numpy raster.

  #-------------------------------------------------------------------------------
  def getRegions(self):
    return list(self.claims.keys())

  #-------------------------------------------------------------------------------
  def show(self,prefix=""):
    if not self.suitRasterName is None:
      suitName = os.path.basename(self.suitRasterName)
    else:
      suitName = ""
    print("%s%s(%s) - nrClaims: %s suit: %s" % (prefix,self.name,self.code,
                                                len(list(self.claims.keys())),
                                                suitName))
