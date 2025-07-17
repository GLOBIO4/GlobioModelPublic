# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 30 aug 2017, ES, ARIS B.V.
#           - Version 4.0.7
#           - Added use of Monitor.
# Modified: 22 aug 2023, MB
#           - From base landuseBiomesMSA module, update to include 
#             restoration of secondary vegetation (SecVegLuClass)
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
class GLOBIO_CalcLanduseBiomesMSARestoration(CalculationBase):
  """
  Calculates a raster with the MSA of landuse and biomes, including restoration 
  of secondary vegetation.
  """
  
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN STRING BaseYear
    IN STRING RestYear
    IN RASTER Landuse
    IN RASTER Biomes
    IN INTEGER SecVegLuClass
    IN RASTER BaseRestYears
    IN FILE LanduseBiomesMSALookup_WBvert
    IN FILE LanduseBiomesMSALookup_Plants
    IN FILE RestYearsMSALookup_plants
    IN FILE RestYearsMSALookup_wbvert
    OUT RASTER LanduseMSA
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=11:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    baseYearInt = int(args[1])
    restYearInt = int(args[2])
    luRasterName = args[3]
    bioRasterName = args[4]
    SecVegLuClass = int(args[5])
    baseRestYearsName = args[6]
    lookupFileNameWB = args[7]
    lookupFileNamePL = args[8]
    RestYearsMSALookup_plants = args[9]
    RestYearsMSALookup_wbvert = args[10]
    outRasterName = args[11]
  
    # Check arguments.
    self.checkExtent(extent)
    self.checkInteger(baseYearInt,0,9999999999)
    self.checkInteger(restYearInt,0,9999999999)
    self.checkRaster(luRasterName)
    self.checkRaster(bioRasterName)
    self.checkInteger(SecVegLuClass,0,9999999999)
    self.checkRaster(baseRestYearsName,optional=True)
    self.checkLookup(lookupFileNameWB)
    self.checkLookup(lookupFileNamePL)
    self.checkLookup(RestYearsMSALookup_plants)
    self.checkLookup(RestYearsMSALookup_wbvert)
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
    # Read the base rest years raster and prepare 
    #-----------------------------------------------------------------------------
    
    # Reads the baseRestYears raster and resizes to extent and resamples to cellsize.
    baseRestYearsRaster = self.readAndPrepareInRaster(extent,cellSize,baseRestYearsName,"base restoration years")
    
    #-----------------------------------------------------------------------------
    # Lookup the MSA value for landuse and biomes.
    #-----------------------------------------------------------------------------
    noDataValue = -999.0

    # Do lookup.
    lookupFieldTypes = ["I","I","F"]
    lookupMainFieldName = "LANDUSE"
    outRasterWB = self.reclassUniqueValuesTwoKeys(luRaster,bioRaster,
                                          lookupFileNameWB,lookupFieldTypes,
                                          lookupMainFieldName,np.float32,noDataValue)
    outRasterPl = self.reclassUniqueValuesTwoKeys(luRaster,bioRaster,
                                          lookupFileNamePL,lookupFieldTypes,
                                          lookupMainFieldName,np.float32,noDataValue)
  
    #-----------------------------------------------------------------------------
    # Restoration years update
    # Set mask of secondary vegetation and lookup the restoration MSA value
    # New restoration/abandonment taking place in between the 2 years, middle is taken for new restoration time passed
    #-----------------------------------------------------------------------------
    lookupFieldTypes = ["I","F"]
    Log.info("Creating the restoration years raster for secondary vegetation...")
    Log.info("...ongoing restoration...")
    restOngoing_mask = (luRaster.r == SecVegLuClass) & (baseRestYearsRaster.r > 0)
    baseRestYearsRaster.r[restOngoing_mask] = baseRestYearsRaster.r[restOngoing_mask] + int(restYearInt - baseYearInt)
    Log.info("...new restoration...")
    restNew_mask = (luRaster.r == SecVegLuClass) & (baseRestYearsRaster.r == 0)
    baseRestYearsRaster.r[restNew_mask] = baseRestYearsRaster.r[restNew_mask] + int(((restYearInt - baseYearInt) / 2) + 0.5)
    Log.info("...no restoration...")
    # Resetting the remaining cell values to zero years for all other LU classes (todo: nodata check for water seems to be not working)
    noRest_mask = (luRaster.r != SecVegLuClass) & (baseRestYearsRaster.r != baseRestYearsRaster.noDataValue)
    baseRestYearsRaster.r[noRest_mask] = 0
    
    # Link the MSA table info to the restoration rasters for WB and Pl   
    restYearsWB = self.reclassUniqueValues(baseRestYearsRaster,RestYearsMSALookup_wbvert,lookupFieldTypes,np.float32)
    restYearsPL = self.reclassUniqueValues(baseRestYearsRaster,RestYearsMSALookup_plants,lookupFieldTypes,np.float32)

    # Saving the new restoration years raster for next year runs
    Log.info("Writing %s..." % (baseRestYearsName.replace(str(baseYearInt),str(restYearInt))))
    baseRestYearsRaster.writeAs(baseRestYearsName.replace(str(baseYearInt),str(restYearInt)))

    #-----------------------------------------------------------------------------
    # Creating and updating MSA rasters
    #-----------------------------------------------------------------------------

    Log.info("Updating the land use MSA rasters for restoration...")
    # Setting the mask for updating the land use MSA rasters
    luSecveg_mask = (luRaster.r == SecVegLuClass)
    outRasterWB.r[luSecveg_mask] = restYearsWB.r[luSecveg_mask]
    outRasterPl.r[luSecveg_mask] = restYearsPL.r[luSecveg_mask]

    maskWB = (outRasterWB.r != outRasterWB.noDataValue) & (outRasterWB.r != noDataValue)
    Log.info("Writing %s..." % (outRasterName.replace(".tif","_wbvert.tif")))
    outRasterWB.writeAs(outRasterName.replace(".tif","_wbvert.tif"))

    maskPl = (outRasterPl.r != outRasterPl.noDataValue) & (outRasterPl.r != noDataValue)
    Log.info("Writing %s..." % (outRasterName.replace(".tif","_plants.tif")))
    outRasterPl.writeAs(outRasterName.replace(".tif","_plants.tif"))

    # Create the land use MSA raster.
    Log.info("Creating the final land use MSA raster...")
    
    outRaster = Raster(outRasterName)
    outRaster.initRaster(extent,cellSize,np.float32,noDataValue)

    mask = maskWB & maskPl
    outRaster.r[mask] = (outRasterWB.r[mask] + outRasterPl.r[mask])/2

    Log.info("Writing %s..." % outRasterName)
    outRaster.write()
    
    # Close and free the input rasters.
    luRaster.close()
    luRaster = None
    bioRaster.close()
    bioRaster = None
    del luRaster
    del bioRaster
    del baseRestYearsRaster
    del restYearsWB
    del restYearsPL

    del mask
    del maskWB
    del maskPl
    del luSecveg_mask
    del restOngoing_mask
    del restNew_mask
    del noRest_mask

    # Close and free the output raster.
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
    
    pCalc = GLOBIO_CalcLanduseBiomesMSARestoration()
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
