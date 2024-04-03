# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Calculates the claims per landuse type per region in 2015 based on a
# (ESA) landcover map.
# Landcover types are translated to GLOBIO landuse types.
#
# Creates a CSV file with the following structure:
# region;landuse;area_km2
# 7;0;504554.53125
# 7;1;4643.12451171875
# 7;2;107579.84375
# 7;3;42573.14453125
# 7;4;20550.734375
# 11;0;2298705.25
# 11;1;100823.9921875
# ...
#
# Modified: -
#-------------------------------------------------------------------------------

import os

import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

from GlobioModel.Core.Arguments import Arguments
from GlobioModel.Core.CalculationBase import CalculationBase
from GlobioModel.Core.Lookup import Lookup
from GlobioModel.Core.CalculationBase import Raster
import GlobioModel.Core.RasterUtils as RU
import GlobioModel.Core.RegionUtils as RGU

import GlobioModel.Common.Utils as UT

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_CalcReferenceClaims(CalculationBase):
  """
  Calculates the claims per landuse type per region in 2015 based on a
  (ESA) landcover map.
  Landcover types are translated to IMAGE landuse types.
  """

  # Cell area version.
  cellAreaVersion = 2

  claimRegionFieldName = "region"
  claimLanduseFieldName = "landuse"
  claimAreaFieldName = "area_km2"
  claimLandcoverFieldName = "landcover"

  #-------------------------------------------------------------------------------
  def __init__(self):

    # Call parent __init__()
    super(GLOBIO_CalcReferenceClaims,self).__init__()

    # Set internal settings.
    self.debug = GLOB.debug

  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN RASTER Landcover
    IN FILE LandcoverLanduseLookup
    IN RASTER Regions
    IN STRING RegionFilter
    IN STRING RegionExcludeFilter
    IN RASTER CellAreaKM2
    OUT FILE ReferenceClaims
    """
    self.showStartMsg(args)

    # Create argument checker.
    pArgs = Arguments(args)
    
    # Get arguments.
    extent = pArgs.next()
    cellSize = pArgs.next()
    landcovRasterName = pArgs.next()
    landcovToLanduseFileName = pArgs.next()
    regionRasterName = pArgs.next()
    regionFilterStr = pArgs.next()
    regionExcludeFilterStr = pArgs.next()
    cellAreaKM2RasterName = pArgs.next()
    outFileName = pArgs.next()

    # Check number of arguments.
    pArgs.check(self.name)

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkRaster(landcovRasterName)
    self.checkLookup(landcovToLanduseFileName)
    self.checkRaster(regionRasterName)
    self.checkIntegerList(regionFilterStr,optional=True)
    self.checkIntegerList(regionExcludeFilterStr,optional=True)
    self.checkRaster(cellAreaKM2RasterName)
    self.checkLookup(outFileName,True)

    # Convert code and names to arrays.
    regionFilter = self.splitIntegerList(regionFilterStr)
    regionExcludeFilter = self.splitIntegerList(regionExcludeFilterStr)

    # Align extent.
    extent = RU.alignExtent(extent,cellSize)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.outDir = os.path.dirname(outFileName)

    # Enable monitor en show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    #-----------------------------------------------------------------------------
    # Read the landcover raster (in its original resolution).
    #-----------------------------------------------------------------------------

    # Read the landcover raster and resizes to extent and resamples to cellsize.
    landcovRaster = self.readAndPrepareInRaster_V2(extent,cellSize,
                                                   landcovRasterName,"landcover",
                                                   calcSumDiv=False)

    #-----------------------------------------------------------------------------
    # Reclass landcover raster to landuse types.
    #-----------------------------------------------------------------------------

    Log.info("Reading landcover lookup...")

    # Read translation file with landcover codes and landuse codes.
    lookup = Lookup()
    lookup.loadCSV(landcovToLanduseFileName,["I","I"])

    ### DEBUG
    # if self.debug:
    #   lookup.show()

    # Create new landuse raster.
    landuseRaster = Raster()
    landuseRaster.initRasterLike(landcovRaster)

    Log.info("Reclassing landcover...")

    # Reclass landcover raster to landuse.
    for landcovCode in lookup:
      Log.info("- Processing landcover %s..." % landcovCode)
      # Select landcover cell.
      mask = (landcovRaster.r==landcovCode)
      # Replace with landuse code.
      landuseRaster.r[mask] = lookup[landcovCode]

    # TODO: Handling NoData?

    # Cleanup.
    del mask
    del landcovRaster

    #-----------------------------------------------------------------------------
    # Read the region raster.
    #-----------------------------------------------------------------------------

    # Read the region raster and resizes to extent and resamples to cellsize.
    regionRaster = self.readAndPrepareInRaster_V2(extent,cellSize,
                                                  regionRasterName,"regions",
                                                  calcSumDiv=False)

    #-----------------------------------------------------------------------------
    # Filter regions.
    #-----------------------------------------------------------------------------

    Log.info("Filtering regions...")

    # Filter the regions, i.e. set to noData.
    RGU.filterRegionRaster(regionRaster,regionFilter,regionExcludeFilter)

    Log.info("Getting region codes...")

    # Create a list of unique regions from the region raster.
    regionCodes = RGU.createRegionListFromRegionRaster(regionRaster,includeNoDataValue=False)

    Log.info("Nr. of regions found: %s" % len(regionCodes))

    #-----------------------------------------------------------------------------
    # Read the area raster and prepare.
    #-----------------------------------------------------------------------------

    # Read the area raster.
    areaRaster = self.readAndPrepareInRaster_V2(extent,cellSize,
                                                cellAreaKM2RasterName,"areas",
                                                calcSumDiv=True)

    #-----------------------------------------------------------------------------
    # Calculate the claims per region per landuse type.
    #-----------------------------------------------------------------------------

    Log.info("Calculating region landuse claims...")

    # Calculate the claims per region per landuse type (km2). Returns a
    # list of "region;landuse;area_km2" values.
    fieldNames = [self.claimRegionFieldName,self.claimLanduseFieldName,
                  self.claimAreaFieldName]
    claimAreaLines = RGU.calcRegionLanduseAreas(regionRaster,
                                                areaRaster,
                                                landuseRaster,
                                                regionCodes,
                                                fieldNames)

    Log.dbg(claimAreaLines)

    # Cleanup.
    del regionRaster
    del landuseRaster
    del areaRaster

    Log.info("Writing region landuse claims...")

    # Write calculated claim areas to CSV.
    if os.path.isfile(outFileName):
      os.remove(outFileName)
    UT.fileWrite(outFileName,claimAreaLines)

    # Cleanup.
    del claimAreaLines

    # Show used memory and disk space.
    MON.showMemDiskUsage()

    self.showEndMsg()
