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
# Step 7
class GLOBIO_CalcAquaticFloodplainAAPFDMSA(CalculationBase):
  """
  Creates a raster with the AAPFD MSA for floodplains.
  """
  
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN RASTER AAPFD
    IN RASTER FloodplainFractions
    IN FLOAT FACTOR_A
    IN FLOAT FACTOR_B
    IN FLOAT FACTOR_C
    IN FLOAT FACTOR_D
    OUT RASTER FloodplainAAPFDMSA
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=8:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    aapfdRasterName = args[2]
    floodFractionsRasterName = args[3]
    FACTOR_A = args[4]
    FACTOR_B = args[5]
    FACTOR_C = args[6]
    FACTOR_D = args[7]
    outRasterName = args[8]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkRaster(aapfdRasterName)
    self.checkRaster(floodFractionsRasterName)
    self.checkFloat(FACTOR_A,-100.0,100.0)
    self.checkFloat(FACTOR_B,-100.0,100.0)
    self.checkFloat(FACTOR_C,-100.0,100.0)
    self.checkFloat(FACTOR_D,-100.0,100.0)
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
    floodFractionsRaster = self.readAndPrepareInRaster(extent,cellSize,floodFractionsRasterName,"floodplain fractions")

    # Create the mask. Select fraction > 0.0.
    Log.info("Selecting floodplain fractions...")
    fracMask = (floodFractionsRaster.r > 0.0)

    # Close and free the fractions raster.
    floodFractionsRaster.close()
    floodFractionsRaster = None

    #-----------------------------------------------------------------------------
    # Read the AAPFD raster, prepare and select.
    #-----------------------------------------------------------------------------
  
    # Reads the raster and resizes to extent and resamples to cellsize.
    aapfdRaster = self.readAndPrepareInRaster(extent,cellSize,aapfdRasterName,"AAPFD")

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
    # Calculate floodplain AAPFD MSA.
    #-----------------------------------------------------------------------------

    # Get data mask.
    dataMask = aapfdRaster.getDataMask()
  
    # Combine masks.
    dataMask = np.logical_and(fracMask,dataMask)

    # Cleanup mask.
    fracMask = None
    
    # MSA = a * exp(b / (log10(aapfd+d) + c)
    outRaster.r[dataMask] = aapfdRaster.r[dataMask]
    outRaster.r[dataMask] += FACTOR_D
    outRaster.r[dataMask] = np.log10(outRaster.r[dataMask])
    outRaster.r[dataMask] += FACTOR_C
    outRaster.r[dataMask] = FACTOR_B / outRaster.r[dataMask]
    outRaster.r[dataMask] = np.exp(outRaster.r[dataMask])
    outRaster.r[dataMask] *= FACTOR_A
    
    # Cleanup mask.
    dataMask = None
    
    #-----------------------------------------------------------------------------
    # Save output.
    #-----------------------------------------------------------------------------
    
    # Save the MSA raster for floodplain AAPFD.
    Log.info("Writing MSA for floodplain AAPFD...")
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

    pCalc = GLOBIO_CalcAquaticFloodplainAAPFDMSA()
    
    ext = GLOB.extent_World
    cs = GLOB.cellSize_30sec
    aa = os.path.join(inDir,"aapfd.tif")
    frac = os.path.join(inDir,"floodplain_fractions.tif")
    F_A = 0.3518
    F_B = 0.5885
    F_C = 1.5636
    F_D = 0.1
    out = os.path.join(outDir,"floodplain_aapfd_msa.tif")

    if RU.rasterExists(out):
      RU.rasterDelete(out)
    
    pCalc.run(ext,cs,aa,frac,F_A,F_B,F_C,F_D,out)
  except:
    Log.err()
