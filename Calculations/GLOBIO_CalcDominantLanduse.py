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
import GlobioModel.Core.RasterUtils as RU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_CalcDominantLanduse(CalculationBase):
  """
  Creates a raster with dominant landuse.
  """
  
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN RASTER Landuse
    IN FILE LanduseReclassLookup
    OUT RASTER DominantLanduse
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=3:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    inRasterName = args[1]
    lookupFileName = args[2]
    outRasterName = args[3]
  
    # Check arguments.
    self.checkExtent(extent)
    self.checkRaster(inRasterName)
    self.checkLookup(lookupFileName)
    self.checkRaster(outRasterName,True)

    # Get the minimum cellsize for the output raster.
    inRasterNames = [inRasterName]
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
    inRaster = self.readAndPrepareInRaster(extent,cellSize,inRasterName,"landuse")

    #-----------------------------------------------------------------------------
    # Reclass the landuse raster.
    #-----------------------------------------------------------------------------

    # 0 = not dominant, 1 = dominant.
    lookupFieldTypes = ["I","I"]
    outRaster = self.reclassUniqueValues(inRaster,
                                         lookupFileName,lookupFieldTypes,np.uint8)

    # Close and free the input raster.
    inRaster.close()
    inRaster = None
 
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
    inDir = r""
    lookupDir = r""
    outDir = r""

    pCalc = GLOBIO_CalcDominantLanduse()
    ext = GLOB.constants["world"].value
    ext = GLOB.extent_World
    #ext = GLOB.constants["europe"].value
    lu = os.path.join(inDir,"glc2000_aris.tif")
    lut = os.path.join(lookupDir,"DominantLanduse.csv") 
    out = os.path.join(outDir,"DominantLanduse.tif")
    
    if RU.rasterExists(out):
      RU.rasterDelete(out)

    pCalc.run(ext,lu,lut,out)
  except:
    Log.err()
