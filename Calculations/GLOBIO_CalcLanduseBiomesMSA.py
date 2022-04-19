# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
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
    IN FILE LanduseBiomesMSALookup
    OUT RASTER LanduseMSA
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=4:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    luRasterName = args[1]
    bioRasterName = args[2]
    lookupFileName = args[3]
    outRasterName = args[4]
  
    # Check arguments.
    self.checkExtent(extent)
    self.checkRaster(luRasterName)
    self.checkRaster(bioRasterName)
    self.checkLookup(lookupFileName)
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

    # Do lookup.
    lookupFieldTypes = ["I","I","F"]
    lookupMainFieldName = "LANDUSE"
    outRaster = self.reclassUniqueValuesTwoKeys(luRaster,bioRaster,
                                          lookupFileName,lookupFieldTypes,
                                          lookupMainFieldName,np.float32)
  
    # Close and free the input rasters.
    luRaster.close()
    luRaster = None
    bioRaster.close()
    bioRaster = None
 
    # Save the output raster.
    Log.info("Writing %s..." % outRasterName)
    outRaster.writeAs(outRasterName)
           
    # Close and free the output raster.
    outRaster.close()
    outRaster = None
      
    # Show used memory and disk space.
    MON.showMemDiskUsage()
    
    self.showEndMsg()

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  try:
    inDir = r"Q:\Data\Globio4\G_data\pbl\tif"
    lookupDir = r"P:\Project\Globio4\data\Lookup"
    outDir = r"C:\Temp\_Globio4\out"
    if not os.path.isdir(outDir):
      outDir = r"G:\Data\out_v3"
    
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
