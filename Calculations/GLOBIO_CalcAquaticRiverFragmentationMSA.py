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
class GLOBIO_CalcAquaticRiverFragmentationMSA(CalculationBase):
  """
  Creates a raster with the aquatic MSA for river fragmentation.
  """
  
  #-------------------------------------------------------------------------------
  # DepthThreshold is a positive number.
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN RASTER DamDownstreamDistance
    IN RASTER DamUpstreamDistance
    IN RASTER RiverFragmentLength
    IN RASTER DamDensity
    IN RASTER RCI
    IN RASTER RiverFractions
    IN FLOAT FACTOR_A
    IN FLOAT FACTOR_B
    IN FLOAT FACTOR_C
    IN FLOAT FACTOR_D
    IN FLOAT FACTOR_E
    IN FLOAT FACTOR_F
    OUT RASTER RiverFragmentationMSA
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=14:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    damDownDistRasterName = args[2]
    damUpDistRasterName = args[3]
    rivLengthRasterName = args[4]
    damDensRasterName = args[5]
    rciRasterName = args[6]
    rivFractionsRasterName = args[7]
    FACTOR_A = args[8]
    FACTOR_B = args[9]
    FACTOR_C = args[10]
    FACTOR_D = args[11]
    FACTOR_E = args[12]
    FACTOR_F = args[13]
    outRasterName = args[14]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkRaster(damDownDistRasterName)
    self.checkRaster(damUpDistRasterName)
    self.checkRaster(rivLengthRasterName)
    self.checkRaster(damDensRasterName)
    self.checkRaster(rciRasterName)
    self.checkRaster(rivFractionsRasterName)
    self.checkFloat(FACTOR_A,-100.0,100.0)
    self.checkFloat(FACTOR_B,-100.0,100.0)
    self.checkFloat(FACTOR_C,-100.0,100.0)
    self.checkFloat(FACTOR_D,-100.0,100.0)
    self.checkFloat(FACTOR_E,-100.0,100.0)
    self.checkFloat(FACTOR_F,-100.0,100.0)
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
    rivFractionsRaster = self.readAndPrepareInRaster(extent,cellSize,rivFractionsRasterName,"river fractions")

    # Create the mask. Select fraction > 0.0.
    Log.info("Selecting river fractions...")
    fracMask = (rivFractionsRaster.r > 0.0)

    # Close and free the fractions raster.
    rivFractionsRaster.close()
    rivFractionsRaster = None

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
    # Calculate fragmentation MSA.
    #-----------------------------------------------------------------------------

    # Set calculation parameters.
    rasterNames = [damDownDistRasterName,damUpDistRasterName,
                   rivLengthRasterName,damDensRasterName,rciRasterName]
    rasterDescrs = ["downstream dam distance","upstream dam distance",
                   "river length","dam density","rci"]
    rasterFacts = [FACTOR_B,FACTOR_C,FACTOR_D,FACTOR_E,FACTOR_E]

    # Calculate constant factor.
    outRaster.r[fracMask] = FACTOR_A

    # Loop rasters.
    for i in range(len(rasterNames)):

      # Get rastername, description and factor.
      rasterName = rasterNames[i]
      rasterDescr = rasterDescrs[i]
      rasterFact = rasterFacts[i]

      # Reads the raster and resizes to extent and resamples to cellsize.
      raster = self.readAndPrepareInRaster(extent,cellSize,rasterName,rasterDescr)
    
      # Get data mask.
      dataMask = raster.getDataMask()
    
      # Combine masks.
      dataMask = np.logical_and(fracMask,dataMask)

      # Calculate.
      outRaster.r[dataMask] += rasterFact * raster.r[dataMask]
      
      # Cleanup raster.
      raster.close()
      raster = None
      
      # Cleanup mask.
      dataMask = None
    
    # Cleanup mask.
    fracMask = None

    #-----------------------------------------------------------------------------
    # Save output.
    #-----------------------------------------------------------------------------
    
    # Save the MSA raster for river fragmentation.
    Log.info("Writing MSA for river fragmentation...")
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

    # Enable the monitor.    
    GLOB.monitorEnabled = True

    inDir = r"G:\data\Globio4LA\data\referentie\v4012\30sec_wrld\in_20181026"
    outDir = r"C:\Temp\_Globio4\out"
    if not os.path.isdir(outDir):
      outDir = r"G:\data\Globio4LA\data\kanweg\20181031_v1"

    pCalc = GLOBIO_CalcAquaticRiverFragmentationMSA()
    
    #ext = GLOB.constants["world"].value
    ext = GLOB.extent_Europe
    cs = GLOB.cellSize_30sec    
    down = os.path.join(inDir,"downstream_dam_dist.tif")
    up = os.path.join(inDir,"upstream_dam_dist.tif")
    riv = os.path.join(inDir,"riversegments_length.tif")
    den = os.path.join(inDir,"dam_density.tif")
    rci = os.path.join(inDir,"rci.tif")
    frac = os.path.join(inDir,"river_fractions.tif")
    F_A = 0.52
    F_B = 0.0
    F_C = 0.0
    F_D = 0.0
    F_E = 0.0
    F_F = 0.0
    out = os.path.join(outDir,"river_frag_msa.tif")
   
    if RU.rasterExists(out):
      RU.rasterDelete(out)
    
    pCalc.run(ext,cs,down,up,riv,den,rci,frac,F_A,F_B,F_C,F_D,F_E,F_F,out)
  except:
    MON.cleanup()
    Log.err()
