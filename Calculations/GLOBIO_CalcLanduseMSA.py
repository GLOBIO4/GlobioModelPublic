# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 30 aug 2017, ES, ARIS B.V.
#           - Version 4.0.7
#           - Added use of Monitor.
#-------------------------------------------------------------------------------

import os
import numpy as np

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

from GlobioModel.Core.CalculationBase import CalculationBase
from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_CalcLanduseMSA(CalculationBase):
  """
  Calculates a raster with the MSA of landuse.
  """
  
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN RASTER Landuse
    IN FILE LanduseMSALookup_WBvert
    IN FILE LanduseMSALookup_Plants
    OUT RASTER LanduseMSA
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=4:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    luRasterName = args[1]
    lookupFileNameWB = args[2]
    lookupFileNamePl = args[3]
    outRasterName = args[4]
  
    # Check arguments.
    self.checkExtent(extent)
    self.checkRaster(luRasterName)
    self.checkLookup(lookupFileNameWB)
    self.checkLookup(lookupFileNamePl)
    self.checkRaster(outRasterName,True)

    # Get the minimum cellsize for the output raster.
    inRasterNames = [luRasterName]
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
    # Read the landuse raster and prepare.
    #-----------------------------------------------------------------------------
  
    # Reads the landuse raster and resizes to extent and resamples to cellsize.
    luRaster = self.readAndPrepareInRaster(extent,cellSize,luRasterName,"landuse")

    #-----------------------------------------------------------------------------
    # Lookup the MSA value for landuse.
    #-----------------------------------------------------------------------------

    noDataValue = -999.0

    # Do lookup.
    lookupFieldTypes = ["I","F"]
    outRasterWB = self.reclassUniqueValues(luRaster,lookupFileNameWB,lookupFieldTypes,
                                           np.float32, noDataValue)
    maskWB = (outRasterWB.r != outRasterWB.noDataValue) & (outRasterWB.r != noDataValue)
    Log.info("Writing %s..." % (outRasterName.replace(".tif","_wbvert.tif")))
    outRasterWB.writeAs(outRasterName.replace(".tif","_wbvert.tif"))
     
    outRasterPl = self.reclassUniqueValues(luRaster,lookupFileNamePl,lookupFieldTypes,
                                           np.float32, noDataValue)
    maskPl = (outRasterPl.r != outRasterPl.noDataValue) & (outRasterPl.r != noDataValue)
    Log.info("Writing %s..." % (outRasterName.replace(".tif","_plants.tif")))
    outRasterPl.writeAs(outRasterName.replace(".tif","_plants.tif"))
        
    # Create the land use MSA raster.
    Log.info("Creating the land use MSA raster...")
    outRaster = Raster(outRasterName)
    outRaster.initRaster(extent,cellSize,np.float32,noDataValue)
   
    mask = maskWB & maskPl
    outRaster.r[mask] = (outRasterWB.r[mask]+ outRasterPl.r[mask])/2

    # Close and free the input rasters.
    luRaster.close()
    luRaster = None
    
    del maskWB
    del maskPl
    del mask
 
    # Save the output raster.
    Log.info("Writing %s..." % outRasterName)
    outRaster.write()
	      
    # Close and free the output raster.
    outRaster.close()
    outRaster = None
    outRasterWB.close()
    outRasterWB = None   
    outRasterPl.close()
    outRasterPl = None
      
    # Show used memory and disk space.
    MON.showMemDiskUsage()

    self.showEndMsg()

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  try:
    inDir = r""
    lookupDir = r""
    outDir = r""

    pCalc = GLOBIO_CalcLanduseMSA()

    ext = [-40,-39,5,6] #GLOB.constants["world"].value
    lu = os.path.join(inDir,"ESACCI_LC_1992_v207.tif")
    luwb = os.path.join(lookupDir,"LanduseMSA_v11_WBvert.csv")
    lupl = os.path.join(lookupDir,"LanduseMSA_v11_Plants.csv")
    msa = os.path.join(outDir,"LandUseMSA_test.tif")
    
    if RU.rasterExists(msa):
      RU.rasterDelete(msa)
      
    pCalc.run(ext,lu,luwb,lupl,msa)
    
  except:
    Log.err()
