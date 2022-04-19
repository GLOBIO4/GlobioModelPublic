# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: -
#-------------------------------------------------------------------------------

import os

import GlobioModel.Core.RasterUtils as RU

import GlobioModel.Common.Utils as UT

#-------------------------------------------------------------------------------
# Returns a default rastername based on the specified cellsize and version.
def getCellAreaRasterName(cellAreaDir: str,cellSize: float,version: int=2):
  cellSizeName = RU.cellSizeToCellSizeName(cellSize)
  rasterName = "cellarea_km2_v%s_%s.tif" % (version,cellSizeName)
  rasterName = os.path.join(cellAreaDir,rasterName)
  return rasterName

#-------------------------------------------------------------------------------
# Returns a default rastername based on the specified cellsize.
def getLandcoverRasterName(landcoverDir: str,cellSize: float):
  if (landcoverDir=="") or (UT.sameText(landcoverDir,"NONE")):
    return "NONE"
  cellSizeName = RU.cellSizeToCellSizeName(cellSize)
  rasterName = "landcover_%s.tif" % cellSizeName
  rasterName = os.path.join(landcoverDir,rasterName)
  return rasterName

#-------------------------------------------------------------------------------
# Returns a default rastername based on the specified cellsize.
def getLanduseRasterName(landuseDir: str,cellSize: float):
  if (landuseDir=="") or (UT.sameText(landuseDir,"NONE")):
    return "NONE"
  cellSizeName = RU.cellSizeToCellSizeName(cellSize)
  rasterName = "landuse_%s.tif" % cellSizeName
  rasterName = os.path.join(landuseDir,rasterName)
  return rasterName

#-------------------------------------------------------------------------------
# Returns a default rastername based on the specified cellsize.
def getSemiRandomNoiseRasterName(semiRandomNoiseDir: str,cellSize: float):
  cellSizeName = RU.cellSizeToCellSizeName(cellSize)
  rasterName = "semi_random_noise_%s.tif" % cellSizeName
  rasterName = os.path.join(semiRandomNoiseDir,rasterName)
  return rasterName
