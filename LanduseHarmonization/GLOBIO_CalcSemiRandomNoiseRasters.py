# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Calculates rasters with semi-random noise for different resolutions.
# The generated rasters contains float values between 0.0 and 1.0.
#
# Modified: -
#-------------------------------------------------------------------------------

import numpy as np

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

from GlobioModel.Core.CalculationBase import CalculationBase
from GlobioModel.Core.CalculationBase import Raster
import GlobioModel.Core.RasterUtils as RU

import GlobioModel.LanduseHarmonization.LanduseHarmonizationUtils as LU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_CalcSemiRandomNoiseRasters(CalculationBase):
  """
  Calculates rasters with semi-random noise for different resolutions.
  The generated rasters contains float values between 0.0 and 1.0.
  """
  #-------------------------------------------------------------------------------
  def __init__(self):

    # Call parent __init__()
    super(GLOBIO_CalcSemiRandomNoiseRasters,self).__init__()

    # Set internal settings.
    self.mtimer = None
    self.debug = GLOB.debug
    self.test = False

  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN STRING CellSizes
    OUT DIR OutDir
    """
    self.showStartMsg(args)

    # Check number of arguments.
    if len(args)<=1:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)

    # Get arguments.
    cellSizeNamesStr = args[0]
    outDirName = args[1]

    # Check arguments.
    self.checkDirectory(outDirName)

    # Convert codes and names to arrays.
    cellSizeNames = self.splitStringList(cellSizeNamesStr)

    # Get cellsizes.
    cellSizes = [GLOB.constants[c].value for c in cellSizeNames]

    # Initialize extent (always world).
    extent = GLOB.extent_World

    # Set members.
    self.extent = extent
    self.outDir = outDirName

    # Enable monitor en show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    Log.info("Creating: %s" % ",".join(cellSizeNames))

    # Create noise rasters.
    for idx,cellSize in enumerate(cellSizes):

      cellSizeName = cellSizeNames[idx]

      Log.info("Processing %s..." % cellSizeName)

      # Get raster filename.
      rasterName = LU.getSemiRandomNoiseRasterName(self.outDir,cellSize)

      # Overwrite.
      if RU.rasterExists(rasterName):
        RU.rasterDelete(rasterName)

      # Create raster and initialize.
      raster = Raster(rasterName)
      noDataValue = 0.0
      raster.initDataset(extent,cellSize,np.float32,noDataValue)

      # Set seed.
      seed = 12345
      RU.semiRandomNoiseSeed(seed)

      # Generate rows and write.
      for r in range(raster.nrRows):
        # Generate row with values between 0.0 and 1.0.
        row = RU.semiRandomNoiseGet(raster.nrCols,1)
        #print(row)
        raster.writeRow(r,row)

      # Cleanup.
      del raster

      #break

    # Show used memory and disk space.
    MON.showMemDiskUsage()

    self.showEndMsg()
