# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 10 may 2017, ES, ARIS B.V.
#           - Version 4.0.6
#           - Statistics modified.
#           17 nov 2020, ES, ARIS B.V.
#           - Version 4.0.16
#           - run modified.
#-------------------------------------------------------------------------------

import os
import numpy as np

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

from GlobioModel.Core.CalculationBase import CalculationBase
import GlobioModel.Core.RasterUtils as RU
from GlobioModel.Workers.RasterFunc import RasterFunc

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_ZonalMean(CalculationBase):
  """
  Calculates the zonal mean.
  """
  
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN RASTER ZoneRaster
    IN RASTER InRaster
    OUT RASTER MeanRaster
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=3:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    zoneRasterName = args[1]
    inRasterName = args[2]
    outRasterName = args[3]
  
    # Check arguments.
    self.checkExtent(extent)
    self.checkRaster(zoneRasterName)
    self.checkRaster(inRasterName)
    self.checkRaster(outRasterName,True)

    # Get the minimum cellsize for the output raster.
    inRasterNames = [zoneRasterName,inRasterName]
    cellSize = self.getMinimalCellSize(inRasterNames)
    Log.info("Using cellsize: %s" % cellSize)

    # Align extent.
    extent = RU.alignExtent(extent,cellSize)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.outDir = os.path.dirname(outRasterName)

    # Enable monitor en show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    #-----------------------------------------------------------------------------
    # Read the zone raster and prepare.
    #-----------------------------------------------------------------------------

    # Reads the raster and resizes to extent and resamples to cellsize.
    zoneRaster = self.readAndPrepareInRaster(extent,cellSize,zoneRasterName,"zone")

    #-----------------------------------------------------------------------------
    # Read the input raster and prepare.
    #-----------------------------------------------------------------------------

    # Reads the landuse raster and resizes to extent and resamples to cellsize.
    inRaster = self.readAndPrepareInRaster(extent,cellSize,inRasterName,"input")

    #-----------------------------------------------------------------------------
    # Calculate zonal mean.
    #
    # Using scipy.ndimage.labeled_comprehension() is very slow (>58h) for 30sec
    # rasters (under linux).
    #-----------------------------------------------------------------------------

    Log.info("Calculating zonal mean...")

    # Create raster worker.
    # 20201117
    #rw = RasterFunc()
    rw = RasterFunc(-1)
    rw.debug = self.debugPrint
    
    Log.info("  Using: %s cores" % (rw.nrOfCores))

    # Calculate dam density per catchment.
    meanDict,_,_ = rw.zonalMean(extent,cellSize,zoneRaster,inRaster)
    
    # Clean up.
    inRaster.close()
    inRaster = None

    #-----------------------------------------------------------------------------
    # Create zonal mean raster.
    #-----------------------------------------------------------------------------

    Log.info("Creating zonal mean raster...")

    # Label the catchments with the density values.
    outRaster = rw.label(extent,cellSize,zoneRaster,meanDict,np.float32)

    # Clean up.
    zoneRaster.close()
    zoneRaster = None
    meanDict = None

    #-----------------------------------------------------------------------------
    # Writing zonal mean raster.
    #-----------------------------------------------------------------------------

    Log.info("Writing zonal mean raster...")

    # Write output.
    outRaster.writeAs(outRasterName)

    # Clean up.
    outRaster.close()
    outRaster = None

    # Show used memory and disk space.
    MON.showMemDiskUsage()

    self.showEndMsg()

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  
  try:
    pass
  except:
    MON.cleanup()
    Log.err()
