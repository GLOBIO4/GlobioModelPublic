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
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

from GlobioModel.Core.CalculationBase import CalculationBase
from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_CalcLanduseBiomesMSA(CalculationBase):
  """
  Calculates a raster with the MSA of landuse and biomes.
  """
  
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN RASTER Landuse
    IN RASTER Biomes
    IN FILE LanduseBiomesMSALookup_WBvert
    IN FILE LanduseBiomesMSALookup_Plants
    OUT RASTER LanduseMSA
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=5:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    luRasterName = args[1]
    bioRasterName = args[2]
    lookupFileNameWB = args[3]
    lookupFileNamePl = args[4]
    outRasterName = args[5]
  
    # Check arguments.
    self.checkExtent(extent)
    self.checkRaster(luRasterName)
    self.checkRaster(bioRasterName)
    self.checkLookup(lookupFileNameWB)
    self.checkLookup(lookupFileNamePl)
    self.checkRaster(outRasterName,True)

    # Get the minimum cellsize for the output raster.
    inRasterNames = [luRasterName,bioRasterName]
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
    # Read the biomes raster and prepare.
    #-----------------------------------------------------------------------------
  
    # Reads the biomes raster and resizes to extent and resamples to cellsize.
    bioRaster = self.readAndPrepareInRaster(extent,cellSize,bioRasterName,"biomes")

    #-----------------------------------------------------------------------------
    # Lookup the MSA value for landuse and biomes.
    #-----------------------------------------------------------------------------

    noDataValue = -999.0

    # Do lookup.
    lookupFieldTypes = ["I","I","F"]
    lookupMainFieldName = "LANDUSE"
    Log.info("Calculate MSA land use for warmblooded vertebrates...")
    outRasterWB = self.reclassUniqueValuesTwoKeys(luRaster,bioRaster,
                                          lookupFileNameWB,lookupFieldTypes,
                                          lookupMainFieldName,np.float32,noDataValue)
    maskWB = (outRasterWB.r != outRasterWB.noDataValue) & (outRasterWB.r != noDataValue)
    Log.info("Writing %s..." % (outRasterName.replace(".tif","_wbvert.tif")))
    outRasterWB.writeAs(outRasterName.replace(".tif","_wbvert.tif"))
  
    Log.info("Calculate MSA land use for plant species...")
    outRasterPl = self.reclassUniqueValuesTwoKeys(luRaster,bioRaster,
                                          lookupFileNamePl,lookupFieldTypes,
                                          lookupMainFieldName,np.float32,noDataValue)
    maskPl = (outRasterPl.r != outRasterPl.noDataValue) & (outRasterPl.r != noDataValue)
    Log.info("Writing %s..." % (outRasterName.replace(".tif","_plants.tif")))
    outRasterPl.writeAs(outRasterName.replace(".tif","_plants.tif"))
    
    # Close and free the input rasters.
    luRaster.close()
    del luRaster
    bioRaster.close()
    del bioRaster
 
    # Create the land use MSA raster.
    Log.info("Creating the final land use MSA raster...")
    
    outRaster = Raster(outRasterName)
    outRaster.initRaster(extent,cellSize,np.float32,noDataValue)

    mask = maskWB & maskPl
    outRaster.r[mask] = (outRasterWB.r[mask] + outRasterPl.r[mask]) / 2
    
    Log.info("Writing %s..." % outRasterName)
    outRaster.write()

    # Close and free the output rasters and masks
    del maskWB
    del maskPl
    del mask
    outRaster.close()
    outRasterWB.close()
    outRasterPl.close()
    del outRaster
    del outRasterWB
    del outRasterPl
      
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
    
    pCalc = GLOBIO_CalcLanduseBiomesMSA()
    ext = GLOB.extent_World
    lu = os.path.join(inDir,"glc2000_aris.tif")
    bio = os.path.join(inDir,"gmnlct_2010.tif")
    lut = os.path.join(lookupDir,"LanduseBiomesMSA.csv") 
    out = os.path.join(outDir,"LanduseBiomesMSA.tif")
    
    if RU.rasterExists(out):
      RU.rasterDelete(out)
      
    pCalc.run(ext,lu,bio,lut,out)
  except:
    Log.err()
