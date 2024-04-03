# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
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
class GLOBIO_CalcAquaticRiverFRHLUMSA(CalculationBase):
  """
  Creates a raster with the landuse MSA for rivers.
  """
  
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN RASTER FRHLU
    IN RASTER RiverFractions
    IN FLOAT FACTOR_A
    OUT RASTER RiverFRHLUMSA
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=5:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    frhluRasterName = args[2]
    riverFractionsRasterName = args[3]
    FACTOR_A = args[4]
    outRasterName = args[5]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkRaster(frhluRasterName)
    self.checkRaster(riverFractionsRasterName)
    self.checkFloat(FACTOR_A,-100.0,100.0)
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
    riverFractionsRaster = self.readAndPrepareInRaster(extent,cellSize,riverFractionsRasterName,"river fractions")

    # Create the mask. Select fraction > 0.0.
    Log.info("Selecting river fractions...")
    fracMask = (riverFractionsRaster.r > 0.0)

    # Close and free the fractions raster.
    riverFractionsRaster.close()
    riverFractionsRaster = None

    #-----------------------------------------------------------------------------
    # Read the FRHLU raster, prepare and select.
    #-----------------------------------------------------------------------------
  
    # Reads the raster and resizes to extent and resamples to cellsize.
    frhluRaster = self.readAndPrepareInRaster(extent,cellSize,frhluRasterName,"FRHLU")

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
    # Calculate river FRHLU MSA.
    #-----------------------------------------------------------------------------

    # Get data mask.
    dataMask = frhluRaster.getDataMask()
  
    # Combine masks.
    dataMask = np.logical_and(fracMask,dataMask)

    # Cleanup mask.
    fracMask = None
    
    # MSA = 1.0 - a * FRHLU
    outRaster.r[dataMask] = frhluRaster.r[dataMask]
    outRaster.r[dataMask] *= FACTOR_A
    outRaster.r[dataMask] *= -1.0
    outRaster.r[dataMask] += 1.0
    
    # Cleanup mask.
    dataMask = None
    
    #-----------------------------------------------------------------------------
    # Save output.
    #-----------------------------------------------------------------------------
    
    # Save the MSA raster for river FRHLU.
    Log.info("Writing MSA for river FRHLU...")
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

    pCalc = GLOBIO_CalcAquaticRiverFRHLUMSA()
    
    ext = GLOB.extent_World
    cs = GLOB.cellSize_30sec
    lu = os.path.join(inDir,"frhlu.tif")
    frac = os.path.join(inDir,"river_fractions.tif")
    F_A = 0.70
    out = os.path.join(outDir,"river_frhlu_msa.tif")

    if RU.rasterExists(out):
      RU.rasterDelete(out)
    
    pCalc.run(ext,cs,lu,frac,F_A,out)
  except:
    Log.err()
