# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************

import os
import numpy as np

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

from GlobioModel.Core.CalculationBase import CalculationBase
from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_CalcAquaticReservoirMSA(CalculationBase):
  """
  Creates a raster with the aquatic MSA for reservoirs.
  """
  
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN RASTER ShallowReservoirFractions
    IN RASTER DeepReservoirFractions
    IN FLOAT RESERVOIR_MSA
    OUT RASTER ReservoirMSA
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=5:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    reservShallRasterName = args[2]
    reservDeepRasterName = args[3]
    RESERVOIR_MSA = args[4]
    outRasterName = args[5]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkRaster(reservShallRasterName)
    self.checkRaster(reservDeepRasterName)
    self.checkFloat(RESERVOIR_MSA,0.0,1.0)
    self.checkRaster(outRasterName,True)

    # Align extent.
    extent = RU.alignExtent(extent,cellSize)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.outDir = os.path.dirname(outRasterName)

    # Enable monitor en show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    #-----------------------------------------------------------------------------
    # Read the fractions raster, prepare and select.
    #-----------------------------------------------------------------------------
  
    # Reads the raster and resizes to extent and resamples to cellsize.
    reservShallRaster = self.readAndPrepareInRaster(extent,cellSize,reservShallRasterName,"shallow reservoir fractions")

    # Create the mask. Select fraction > 0.0.
    Log.info("Selecting shallow reservoir fractions...")
    fracMask = (reservShallRaster.r > 0.0)

    # Close and free the fractions raster.
    reservShallRaster.close()
    reservShallRaster = None

    #-----------------------------------------------------------------------------
    # Read the fractions raster, prepare and select.
    #-----------------------------------------------------------------------------
  
    # Reads the raster and resizes to extent and resamples to cellsize.
    reservDeepRaster = self.readAndPrepareInRaster(extent,cellSize,reservDeepRasterName,"deep reservoir fractions")

    # Create the mask. Select fraction > 0.0.
    Log.info("Selecting deep reservoir fractions...")
    
    fracMask = np.logical_or(fracMask,(reservDeepRaster.r > 0.0))

    # Close and free the fractions raster.
    reservDeepRaster.close()
    reservDeepRaster = None

    #-----------------------------------------------------------------------------
    # Create output raster.
    #-----------------------------------------------------------------------------

    # Create MSA raster.
    # Initialize with NoData.
    Log.info("Creating MSA raster...")
    noDataValue = -999.0
    outRaster = Raster(outRasterName)
    outRaster.initRaster(extent,cellSize,np.float32,noDataValue)

    #-----------------------------------------------------------------------------
    # Calculate reservoir MSA.
    # This MSA is valid for both reservoir subtype fractions!!!
    #-----------------------------------------------------------------------------

    # MSA = a
    outRaster.r[fracMask] = RESERVOIR_MSA
    
    # Cleanup mask.
    fracMask = None
    
    #-----------------------------------------------------------------------------
    # Save output.
    #-----------------------------------------------------------------------------
    
    # Save the MSA raster for wetland/floodplain FRHLU.
    Log.info("Writing MSA for reservoirs...")
    outRaster.write()

    # Cleanup.
    outRaster.close()
    outRaster = None
          
    # Show used memory and disk space.
    MON.showMemDiskUsage()

    self.showEndMsg()

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  try:
    outDir = r"C:\Temp\_Globio4\out"
    if not os.path.isdir(outDir):
      outDir = r"G:\Data\out_v3"
    inDir = outDir

    pCalc = GLOBIO_CalcAquaticReservoirMSA()
    
    ext = GLOB.extent_World
    cs = GLOB.cellSize_30sec
    shalFrac = os.path.join(inDir,"shallow_reservoir_fractions.tif")
    deepFrac = os.path.join(inDir,"deep_reservoir_fractions.tif")
    F_A = 0.01
    out = os.path.join(outDir,"reservoir_msa.tif")

    if RU.rasterExists(out):
      RU.rasterDelete(out)
    
    pCalc.run(ext,cs,shalFrac,deepFrac,F_A,out)
  except:
    Log.err()
