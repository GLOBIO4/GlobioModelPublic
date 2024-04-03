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
# Step 9
class GLOBIO_CalcAquaticWetlandFloodplainFRHLUMSA(CalculationBase):
  """
  Creates a raster with the aquatic landuse MSA for wetlands and floodplains.
  """
  
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN RASTER FRHLU
    IN RASTER WetlandFractions
    IN RASTER FloodplainFractions
    IN FLOAT FACTOR_A
    OUT RASTER FloodplainFRHLUMSA
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=5:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    frhluRasterName = args[2]
    wetlandFractionsRasterName = args[3]
    floodplainFractionsRasterName = args[4]
    FACTOR_A = args[5]
    outRasterName = args[6]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkRaster(frhluRasterName)
    self.checkRaster(wetlandFractionsRasterName)
    self.checkRaster(floodplainFractionsRasterName)
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
    wetlandFractionsRaster = self.readAndPrepareInRaster(extent,cellSize,wetlandFractionsRasterName,"wetland fractions")

    # Create the mask. Select fraction > 0.0.
    Log.info("Selecting wetland fractions...")
    wetlandFracMask = (wetlandFractionsRaster.r > 0.0)

    # Close and free the fractions raster.
    wetlandFractionsRaster.close()
    wetlandFractionsRaster = None

    #-----------------------------------------------------------------------------
    # Read the fractions raster, prepare and select.
    #-----------------------------------------------------------------------------
  
    # Reads the raster and resizes to extent and resamples to cellsize.
    floodplainFractionsRaster = self.readAndPrepareInRaster(extent,cellSize,floodplainFractionsRasterName,"floodplain fractions")

    # Create the mask. Select fraction > 0.0.
    Log.info("Selecting floodplain fractions...")
    floodplainFracMask = (floodplainFractionsRaster.r > 0.0)

    # Close and free the fractions raster.
    floodplainFractionsRaster.close()
    floodplainFractionsRaster = None

    #-----------------------------------------------------------------------------
    # Combine wetland and floodplain masks.
    #-----------------------------------------------------------------------------
  
    # Combine masks.
    fracMask = np.logical_or(wetlandFracMask,floodplainFracMask)

    # Cleanup masks.
    wetlandFracMask = None
    floodplainFracMask = None

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
    
    # Save the MSA raster for wetland/floodplain FRHLU.
    Log.info("Writing MSA for wetland/floodplain FRHLU...")
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

    pCalc = GLOBIO_CalcAquaticWetlandFloodplainFRHLUMSA()
    
    ext = GLOB.extent_World
    cs = GLOB.cellSize_30sec    
    lu = os.path.join(inDir,"frhlu.tif")
    wfrac = os.path.join(inDir,"wetland_fractions.tif")
    ffrac = os.path.join(inDir,"floodplain_fractions.tif")
    F_A = 0.87
    out = os.path.join(outDir,"wetlandfloodplain_frhlu_msa.tif")

    if RU.rasterExists(out):
      RU.rasterDelete(out)
    
    pCalc.run(ext,cs,lu,wfrac,ffrac,F_A,out)
  except:
    Log.err()
