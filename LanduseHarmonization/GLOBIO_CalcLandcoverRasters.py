# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************
#-------------------------------------------------------------------------------
# Calculates rasters with landcover for different resolutions.
#
# Modified: -
#-------------------------------------------------------------------------------

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

from GlobioModel.Core.CalculationBase import CalculationBase

import GlobioModel.LanduseHarmonization.LanduseHarmonizationUtils as LU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_CalcLandcoverRasters(CalculationBase):
  """
  Calculates rasters with landcover for different resolutions.
  """

  #-------------------------------------------------------------------------------
  def __init__(self):

    # Call parent __init__()
    super(GLOBIO_CalcLandcoverRasters,self).__init__()

    # Set internal settings.
    self.mtimer = None
    self.debug = GLOB.debug
    self.test = False

    # Set cellAreaVerion.
    self.cellAreaVersion = 2

  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN STRING CellSizes
    IN RASTER Landcover
    OUT DIR OutDir
    """

    self.showStartMsg(args)

    # Check number of arguments.
    if len(args)<=2:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)

    # Get arguments.
    cellSizeNamesStr = args[0]
    landcoverRasterName = args[1]
    outDirName = args[2]

    # Check arguments.
    self.checkRaster(landcoverRasterName)
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
    #oneCellSize = True
    oneCellSize = False
    if oneCellSize:
      # 1 cellsize.
      cellSizeNames = [cellSizeNames[0]]
      cellSizes = [cellSizes[0]]

    # Enable monitor en show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    Log.info("Creating: %s" % ",".join(cellSizeNames))

    #-----------------------------------------------------------------------------
    # Create the landcover rasters.
    #-----------------------------------------------------------------------------

    # Loop the cellsizes.
    for idx,cellSize in enumerate(cellSizes):

      cellSizeName = cellSizeNames[idx]

      Log.info("Processing %s..." % cellSizeName)

      # Read the landcover raster.
      landcoverRaster = self.readAndPrepareInRaster_V2(extent,cellSize,
                                                     landcoverRasterName,"landcover",
                                                     calcSumDiv=False)

      # Get name of new raster.
      newLandcoverRasterName = LU.getLandcoverRasterName(outDirName,cellSize)

      Log.info("Writing new landcover: %s" % newLandcoverRasterName)

      # Write new landcover raster.
      landcoverRaster.writeAs(newLandcoverRasterName)

      # Cleanup.
      del landcoverRaster

    # Show used memory and disk space.
    MON.showMemDiskUsage()

    self.showEndMsg()
