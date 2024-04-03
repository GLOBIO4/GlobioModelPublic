
# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 30 aug 2017, ES, ARIS B.V.
#           - Version 4.0.7
#           - Added use of Monitor.
# Modified: 30 dec 2020,JM
#           - From base landuseMSA module, update to include 
#             restoration of secveg (LU class 6)
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
class GLOBIO_CalcLanduseMSARestoration(CalculationBase):
  """
  Calculates a raster with the MSA of landuse, including restoration of secondary vegeatation.
  """

  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN STRING BaseYear
    IN STRING RestYear
    IN RASTER Landuse
    IN INTEGER SecVegLuClass
    IN RASTER BaseRestYears
    IN FILE LanduseMSALookup_WBvert
    IN FILE LanduseMSALookup_Plants
    IN FILE RestYearsMSALookup_plants
    IN FILE RestYearsMSALookup_wbvert
    OUT RASTER LanduseMSA
    """
    self.showStartMsg(args)

    # Check number of arguments.
    if len(args)<=10:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)

    # Get arguments.
    extent = args[0]
    baseYearInt = int(args[1])
    restYearInt = int(args[2])
    luRasterName = args[3]
    SecVegLuClass = int(args[4])
    baseRestYearsName = args[5]
    lookupFileNameWB = args[6]
    lookupFileNamePL = args[7]
    RestYearsMSALookup_plants = args[8]
    RestYearsMSALookup_wbvert = args[9]
    outRasterName = args[10]

    # Check arguments.
    self.checkExtent(extent)
    self.checkInteger(baseYearInt,0,9999999999)
    self.checkInteger(restYearInt,0,9999999999)
    self.checkRaster(luRasterName)
    self.checkInteger(SecVegLuClass,0,9999999999)
    self.checkRaster(baseRestYearsName,optional=True)
    self.checkLookup(lookupFileNameWB)
    self.checkLookup(lookupFileNamePL)
    self.checkLookup(RestYearsMSALookup_plants)
    self.checkLookup(RestYearsMSALookup_wbvert)
    self.checkRaster(outRasterName,True)

    # Get the minimum cellsize for the output raster.
    inRasterNames = [luRasterName,baseRestYearsName]
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
    baseRestYearsRaster = self.readAndPrepareInRaster(extent,cellSize,baseRestYearsName,"base restoration years")

    #-----------------------------------------------------------------------------
    # Lookup the MSA value for landuse.
    #-----------------------------------------------------------------------------

    # Do lookup.
    lookupFieldTypes = ["I","F"]
    outRasterWB = self.reclassUniqueValues(luRaster,lookupFileNameWB,lookupFieldTypes,np.float32)
    outRasterPl = self.reclassUniqueValues(luRaster,lookupFileNamePL,lookupFieldTypes,np.float32)
    
    #-----------------------------------------------------------------------------
    # Restoration years update
    # Set mask of secondary vegetation and lookup the restoration MSA value
    # New restoration/abandonment taking place in between the 2 years, middle is taken for new restoration time passed
    #-----------------------------------------------------------------------------
    
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

    # Create the land use MSA raster.
    Log.info("Creating the final land use MSA raster...")
    noDataValue = -999.0
    outRaster = Raster(outRasterName)
    outRaster.initRaster(extent,cellSize,np.float32,noDataValue)

    mask = (outRasterWB.r != outRasterWB.noDataValue) & (outRasterWB.r != noDataValue)
    
    # Writing the 3 rasters to a file
    outRaster.r[mask] = (outRasterWB.r[mask])
    Log.info("Writing %s..." % (outRasterName.replace(".tif","_wbvert.tif")))
    outRaster.writeAs(outRasterName.replace(".tif","_wbvert.tif"))
    outRaster.r[mask] = (outRasterPl.r[mask])
    Log.info("Writing %s..." % (outRasterName.replace(".tif","_plants.tif")))
    outRaster.writeAs(outRasterName.replace(".tif","_plants.tif"))
    outRaster.r[mask] = (outRasterWB.r[mask] + outRasterPl.r[mask])/2
    Log.info("Writing %s..." % outRasterName)
    outRaster.writeAs(outRasterName)

    # Close and free the input rasters.
    del luRaster
    del baseRestYearsRaster
    del restYearsWB
    del restYearsPL

    del mask
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
  pass
  # try:
  #   inDir = r"Y:\data\GLOBIO\GLOBIO4\Beheer\Terra\SourceCode\GLOBIO_411_src20180925\src\Globio\Test\Calculations"
  #   lookupDir = r"Y:\data\GLOBIO\GLOBIO4\Models\Terra\Shared\LookupGlobal"
  #   outDir = r"Y:\data\GLOBIO\GLOBIO4\Beheer\Terra\SourceCode\GLOBIO_411_src20180925\src\Globio\Test\Calculations"
  #   if not os.path.isdir(outDir):
  #     outDir = r"S:\hilbersj"
  #
  #   pCalc = GLOBIO_CalcLanduseMSA()
  #
  #   ext = [-40,-39,5,6] #GLOB.constants["world"].value
  #   lu = os.path.join(inDir,"ESACCI_LC_1992_v207.tif")
  #   luwb = os.path.join(lookupDir,"LanduseMSA_v11_WBvert.csv")
  #   lupl = os.path.join(lookupDir,"LanduseMSA_v11_Plants.csv")
  #   msa = os.path.join(outDir,"LandUseMSA_test.tif")
  #
  #   if RU.rasterExists(msa):
  #     RU.rasterDelete(msa)
  #
  #   pCalc.run(ext,lu,luwb,lupl,msa)
  #
  # except:
  #   Log.err()