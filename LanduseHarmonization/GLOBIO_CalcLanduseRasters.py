# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************
#-------------------------------------------------------------------------------
# Calculates rasters with landuse for different resolutions.
#
# Modified: -
#-------------------------------------------------------------------------------

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

from GlobioModel.Core.CalculationBase import CalculationBase
from GlobioModel.Core.Lookup import Lookup
from GlobioModel.Core.CalculationBase import Raster

import GlobioModel.LanduseHarmonization.LanduseHarmonizationUtils as LU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_CalcLanduseRasters(CalculationBase):
  """
  Calculates rasters with landuse for different resolutions.
  """

  #-------------------------------------------------------------------------------
  def __init__(self):

    # Call parent __init__()
    super(GLOBIO_CalcLanduseRasters,self).__init__()

    # Set internal settings.
    self.mtimer = None
    self.debug = GLOB.debug
    self.test = False

  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN STRING CellSizes
    IN DIR LandcoverDir
    IN FILE LandcoverLanduseLookup
    OUT DIR OutDir
    """

    self.showStartMsg(args)

    # Check number of arguments.
    if len(args)<=3:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)

    # Get arguments.
    cellSizeNamesStr = args[0]
    landcoverDirName = args[1]
    landcoverToLanduseFileName = args[2]
    outDirName = args[3]

    # Check arguments.
    self.checkDirectory(landcoverDirName)
    self.checkLookup(landcoverToLanduseFileName)
    # TODO: Nog iets ivm. asOutput=True
    self.checkDirectory(outDirName)

    # Convert code and names to arrays.
    cellSizeNames = self.splitStringList(cellSizeNamesStr)
    cellSizes = [GLOB.constants[c].value for c in cellSizeNames]

    # Initialize extent (always world).
    extent = GLOB.extent_World

    # Set members.
    self.extent = extent
    self.outDir = outDirName

    # TESTEN RUN
    someCellSize = True
    #oneCellSize = False
    if someCellSize:
      # No 30sec and 10sec.
      cellSizeNames = [cellSizeNames[4],cellSizeNames[5]]
      cellSizes = [cellSizes[4],cellSizes[5]]

    # Enable monitor en show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    Log.info("Creating: %s" % ",".join(cellSizeNames))

    #-----------------------------------------------------------------------------
    # Reed the landcover to landuse types.
    #-----------------------------------------------------------------------------

    Log.info("Reading landcover lookup...")

    # Read translation file with landcover codes and landuse codes.
    lookup = Lookup()
    lookup.loadCSV(landcoverToLanduseFileName,["I","I"])

    #-----------------------------------------------------------------------------
    # Create the landuse rasters.
    #-----------------------------------------------------------------------------

    # Loop the cellsizes.
    for idx,cellSize in enumerate(cellSizes):

      cellSizeName = cellSizeNames[idx]

      Log.info("Processing %s..." % cellSizeName)

      #-----------------------------------------------------------------------------
      # Read the landcover raster.
      #-----------------------------------------------------------------------------

      # Get name of new raster.
      landcoverRasterName = LU.getLandcoverRasterName(landcoverDirName,cellSize)

      # Read the landcover raster.
      landcoverRaster = Raster(landcoverRasterName)
      landcoverRaster.read(extent)

      #-----------------------------------------------------------------------------
      # Reclass landcover raster to landuse types.
      #-----------------------------------------------------------------------------

      # Get name of new raster.
      landuseRasterName = LU.getLanduseRasterName(outDirName,cellSize)

      # Create landuse raster.
      landuseRaster = Raster(landuseRasterName)
      landuseRaster.initRasterLike(landcoverRaster)

      Log.info("Reclassing landcover...")

      # Reclass landcover raster to landuse.
      for landcovCode in lookup:

        Log.info("- Processing landcover %s..." % landcovCode)

        # Select landcover cell.
        mask = (landcoverRaster.r==landcovCode)
        # Replace with landuse code.
        landuseRaster.r[mask] = lookup[landcovCode]

      Log.info("Writing landuse: %s" % landuseRasterName)

      # Write new landcover raster.
      landuseRaster.write()

      # Cleanup.
      del mask
      del landcoverRaster
      del landuseRaster

    # Show used memory and disk space.
    MON.showMemDiskUsage()

    self.showEndMsg()
