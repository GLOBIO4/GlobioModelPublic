# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
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
# Step 16A
class GLOBIO_CalcAquaticFloodplainMSA(CalculationBase):
  """
  Creates a raster with the aquatic MSA for floodplains.
  """
  
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN RASTER WetlandFloodplainFRHLUMSA
    IN RASTER FloodplainAAPFDMSA
    IN RASTER FloodplainFractions
    OUT RASTER FloodplainMSA
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=5:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    wetFloodLUMSARasterName = args[2]
    floodplainAAPFDMSARasterName = args[3]
    floodplainFractionsRasterName = args[4]
    outRasterName = args[5]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkRaster(wetFloodLUMSARasterName)
    self.checkRaster(floodplainAAPFDMSARasterName)
    self.checkRaster(floodplainFractionsRasterName)
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
    floodplainFractionsRaster = self.readAndPrepareInRaster(extent,cellSize,floodplainFractionsRasterName,"floodplain fractions")

    # Create the mask. Select fraction > 0.0.
    Log.info("Selecting floodplain fractions...")
    fracMask = (floodplainFractionsRaster.r > 0.0)

    # Close and free the fractions raster.
    floodplainFractionsRaster.close()
    floodplainFractionsRaster = None

    #-----------------------------------------------------------------------------
    # Create output raster.
    #-----------------------------------------------------------------------------

    # Create the output raster.
    # Initialize with NoData.
    Log.info("Creating floodplain MSA raster...")
    noDataValue = -999.0
    outRaster = Raster(outRasterName)
    outRaster.initRaster(extent,cellSize,np.float32,noDataValue)

    #-----------------------------------------------------------------------------
    # Read and process wetland/floodplain landuse msa raster.
    #-----------------------------------------------------------------------------

    # Reads the raster and resizes to extent and resamples to cellsize.
    wetFloodLURaster = self.readAndPrepareInRaster(extent,cellSize,wetFloodLUMSARasterName,"wetland/floodplain landuse msa")

    # Get data mask.
    wfDataMask = wetFloodLURaster.getDataMask()
  
    # Combine masks.
    wfDataMask = np.logical_and(fracMask,wfDataMask)

    # Calculate.
    Log.info("Processing wetland/floodplain landuse MSA...")
    outRaster.r[wfDataMask] = wetFloodLURaster.r[wfDataMask]
    
    # Close and free the river landuse msa raster.
    wetFloodLURaster.close()
    wetFloodLURaster = None

    #-----------------------------------------------------------------------------
    # Read and process river AAPFD msa raster.
    #-----------------------------------------------------------------------------

    # Reads the raster and resizes to extent and resamples to cellsize.
    floodplainAAPFDRaster = self.readAndPrepareInRaster(extent,cellSize,floodplainAAPFDMSARasterName,"floodplain AAPFD msa")

    # Get data mask.
    fpDataMask = floodplainAAPFDRaster.getDataMask()
  
    # Combine masks.
    fpDataMask = np.logical_and(fracMask,fpDataMask)
    fpDataMask = np.logical_and(fpDataMask,wfDataMask)

    # Calculate.
    Log.info("Processing floodplain AAPFD MSA...")
    outRaster.r[fpDataMask] *= floodplainAAPFDRaster.r[fpDataMask]

    # Set nodata.
    outRaster.r[~fpDataMask] = floodplainAAPFDRaster.noDataValue
    
    # Close and free the floodplain AAPFD msa raster.
    floodplainAAPFDRaster.close()
    floodplainAAPFDRaster = None

    #-----------------------------------------------------------------------------
    # Write output raster.
    #-----------------------------------------------------------------------------
        
    # Save the river MSA raster.
    Log.info("Writing floodplain MSA raster...")
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
    
    inDir = r""
    
    outDir = r""

    pCalc = GLOBIO_CalcAquaticFloodplainMSA()
    
    #ext = GLOB.constants["world"].value
    ext = GLOB.extent_Europe
    cs = GLOB.cellSize_30sec

    lu = os.path.join(inDir,"wetlandfloodplain_lu_msa.tif")
    aa = os.path.join(inDir,"floodplain_aapfd_msa.tif")
    frac = os.path.join(inDir,"floodplain_fractions.tif")
    out = os.path.join(outDir,"floodplain_msa.tif")

    if RU.rasterExists(out):
      RU.rasterDelete(out)

    pCalc.run(ext,cs,lu,aa,frac,out)
  except:
    MON.cleanup()
    Log.err()
