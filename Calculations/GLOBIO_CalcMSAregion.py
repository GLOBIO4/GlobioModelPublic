# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 1 feb 2017, ES, ARIS B.V.
#           - Version 4.0.5
#           - Added nodata argument when calling reclassUniqueValues.
#           14 aug 2017, ES, ARIS B.V.
#           - Version 4.0.6
#           - run() doc-string modified because of "RegionExcudeFilter".
#           30 aug 2017, ES, ARIS B.V.
#           - Version 4.0.7
#           - addSemiRandomNoise_NoResample added.
#           - run_v20 modified, now using addSemiRandomNoise_NoResample.
#           - Added use of Monitor.
#           - saveMemoryUsage removed.
#           13 sep 2017, ES, ARIS B.V.
#           - Version 4.0.9
#           - run_v20() modified, enableLogToFile removed.
#-------------------------------------------------------------------------------

import os
import numpy as np
import scipy.ndimage

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON
import GlobioModel.Common.Utils as Utils

# WEL NODIG IVM FOUTMELDING IN VARIABLES!!!!!!!!!!!!!
import GlobioModel.Core.AppUtils as AppUtils

from GlobioModel.Core.CalculationBase import CalculationBase
from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_CalcMSAregion(CalculationBase):
  """
  Calculates area-weighted MSA average per region
  """

  nrCols = 0
  nrRows = 0

  #-------------------------------------------------------------------------------
  # Calculates sum of areas per region and writes to csv file.
  # Use np.float64 to prevent oveflow.
  def calcRegionAreas(self,csvFileName,regions,regionRaster,areaRaster):
    
    overflow_factor = 1000000
    
    noDataValue = -999.0
    areaRaster_cor = Raster()
    areaRaster_cor.initRaster(self.extent,self.cellSize,np.float32,noDataValue,0)

    areaRaster_cor.r = np.rint(areaRaster.r*overflow_factor)

    # Calculate sum of areas per region.    
    areaSum = scipy.ndimage.labeled_comprehension(areaRaster_cor.r,regionRaster.r,regions,np.sum,np.float64,0)
    areaSum = areaSum/overflow_factor
    print(areaSum)
    # Combine regions and areas in an array of region/area tuples.
    regionAreas = zip(regions,areaSum)
    areaSum = None
    overflow_factor = None
    
    areaRaster_cor.close()
    areaRaster_cor = None
    
    # Create file content.
    lines = []
    lines.append("region;area")
    for regionArea in regionAreas:
      lines.append("{};{}".format(*regionArea))
    # Write to file.
    Utils.fileWrite(csvFileName,lines)
    # Free areas and lines.
    regionAreas = None
    lines = None

  #-------------------------------------------------------------------------------
  # Calculates sum of areas per region and landcover type and writes to csv file.
  # Use np.float64 to prevent oveflow.
  def calcRegionLandUseAreas(self,csvFileName,LandUseRasterName,
                               regions,regionRaster,areaRaster):
    
    overflow_factor = 1000000
    
    noDataValue = -999.0
    areaRaster_cor = Raster()
    areaRaster_cor.initRaster(self.extent,self.cellSize,np.float32,noDataValue,0)
  
    areaRaster_cor.r = np.rint(areaRaster.r*overflow_factor)
    
    # Reads the land-cover raster and resizes to extent and resamples to cellsize.
    LandUseRaster = self.readAndPrepareInRaster(self.extent,self.cellSize,
                                                  LandUseRasterName,"land-cover")
    # Calulate areas.
    regionLandUseAreas = []
    # Loop regions.
    for region in regions:
      # Create region mask.
      regionMask = (regionRaster.r == region)
      # Get landcover types in region.
      lcTypes = np.unique(LandUseRaster.r[regionMask])
      # Calculate sum of areas per landcover type.
      areaSum = scipy.ndimage.labeled_comprehension(areaRaster_cor.r[regionMask],
                                                    LandUseRaster.r[regionMask],
                                                    lcTypes,np.sum,np.float64,0)
      
      #areaSum = [x/overflow_factor for x in areaSum]

      # Fill an array with current region.
      tmpRegions = len(areaSum) * [region]    
      # Combine region, landcover and areas in an array of region/landcover/area tuples.
      tmpAreaSum = zip(tmpRegions,lcTypes,areaSum)
      # Add to list.
      regionLandUseAreas.extend(tmpAreaSum)

    # Cleanup.
    regionMask = None
    lcTypes = None
    areaSum = None
    tmpRegions = None   
    tmpAreaSum = None
    overflow_factor = None
    
    # Close and free rasters.
    LandUseRaster.close()
    LandUseRaster = None
    areaRaster_cor.close()
    areaRaster_cor = None
      
    # Create file content.
    lines = []
    lines.append("region;landcover;area")
    for regionLandUseArea in regionLandUseAreas:
      lines.append("{};{};{}".format(*regionLandUseArea))
    # Write to file.
    Utils.fileWrite(csvFileName,lines)
    # Free areas and lines.
    regionLandUseAreas = None
    lines = None
    
  #-------------------------------------------------------------------------------
  # Calculates sum of areas per region and writes to csv file.
  # Use np.float64 to prevent oveflow.
  def calcRegionMSAAreas(self,csvFileName,msaRasterName,regions,regionRaster,areaRaster):
       
    # Reads the land-cover raster and resizes to extent and resamples to cellsize.
    MSARaster = self.readAndPrepareInRaster(self.extent,self.cellSize,
                                            msaRasterName,"msa raster")
    
    #noDataValue = -999.0
    #MSAarearaster = Raster("MSA Area raster")
    #MSAarearaster.initRaster(self.extent,self.cellSize,np.float32,noDataValue,0) 
           
    mask = (MSARaster.r == MSARaster.noDataValue)
    MSARaster.r[mask] = 0
    #MSAarearaster.r[mask] = (MSARaster.r[mask]*areaRaster_cor.r[mask]).astype(int)
    
    overflow_factor = 1000000
    
    noDataValue = -999.0
    areaRaster_cor = Raster()
    areaRaster_cor.initRaster(self.extent,self.cellSize,np.float32,noDataValue,0)
 
    areaRaster_cor.r = np.rint(areaRaster.r*overflow_factor*MSARaster.r)

    # Calculate sum of areas per region.    
    areaSum = scipy.ndimage.labeled_comprehension(areaRaster_cor.r,regionRaster.r,regions,np.sum,np.float64,0)
    #areaSum = [x/overflow_factor for x in areaSum]
    print(areaSum)
    
    # Combine regions and areas in an array of region/area tuples.
    regionAreas = zip(regions,areaSum)
    areaSum = None
    mask = None
    
     # Close and free rasters.   
    MSARaster.close()
    MSARaster = None
    areaRaster_cor.close()
    areaRaster_cor = None
    overflow_factor = None
    
    # Create file content.
    lines = []
    lines.append("region;area")
    for regionArea in regionAreas:
      lines.append("{};{}".format(*regionArea))
    # Write to file.
    Utils.fileWrite(csvFileName,lines)
    # Free areas and lines.
    regionAreas = None
    lines = None    

  #-----------------------------------------------------------------------------
  # Creates a list of regions from the region raster.
  def createRegionListFromRegionRaster(self,regionRaster):
    # Get unique values from region raster.
    regionList = np.unique(regionRaster.r)
    # Get valid regions.
    regionList = regionList[(regionList!=regionRaster.noDataValue)]
    return regionList.tolist()

  #-------------------------------------------------------------------------------
  # Create a mask of regions.
  # regionRaster is a Raster() object.
  # regionFilter is a list of integer codes.
  def createRegionMask(self,regionRaster,regionFilter):
    # No filter.
    if len(regionFilter)==0:
      # Select all.
      mask = regionRaster.getDataMask()
    else:
      mask = None
      # Select from list.
      for region in regionFilter:
        if mask is None:
          mask = (regionRaster.r == region)
        else:
          mask = np.logical_or(mask,(regionRaster.r == region))
    return mask

  #-------------------------------------------------------------------------------
  # Set nodata in region raster which should be excluded.  
  def setRegionRasterExclude(self,regionRaster,regionExcludeFilter):
    # Need to exclude regions?
    if len(regionExcludeFilter) > 0:
      # Create a mask for unwanted regions.
      regionMask = self.createRegionMask(regionRaster,regionExcludeFilter)
      # Set unwanted regions to NoData. 
      regionRaster.r[regionMask] = regionRaster.noDataValue
      # Free the masked regions.
      regionMask = None
    # Save temp raster?
    if GLOB.saveTmpData:
      tmpName = "tmp_selected_excl_regions.tif"
      Log.info("- Writing after excluding regions: "+tmpName)
      self.writeTmpRaster(regionRaster,tmpName)

  #-------------------------------------------------------------------------------
  # Set nodata in region raster outside the regions in regionFilter.  
  def setRegionRasterNoData(self,regionRaster,regionFilter):
    # Need to filter the regions?
    if len(regionFilter) > 0:
      # Create a mask for unwanted regions.
      regionMask = self.createRegionMask(regionRaster,regionFilter)
      # Set unwanted regions to NoData. 
      regionRaster.r[~regionMask] = regionRaster.noDataValue     # pylint: disable=invalid-unary-operand-type
      # Free the masked regions.
      regionMask = None
    # Save temp raster?
    if GLOB.saveTmpData:
      tmpName = "tmp_selected_regions.tif"
      Log.info("- Writing selected regions: "+tmpName)
      self.writeTmpRaster(regionRaster,tmpName)

  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN RASTER AreaRaster
    IN RASTER LandUse
    IN RASTER RegionRaster
    IN STRING RegionFilter 
    IN STRING RegionExcludeFilter
    IN RASTER MSARaster
    IN RASTER LURasterSplit
    IN RASTER HERasterSplit
    IN RASTER NDepRasterSplit
    IN RASTER CCRasterSplit
    IN RASTER IDRasterSplit
    IN RASTER IFRasterSplit
    OUT FILE OutRegionAreasFileName 
    OUT FILE OutRegionLandUseAreasFileName 
    OUT FILE OutRegionMSAAreasFileName 
    OUT FILE OutRegionLUAreasFileName 
    OUT FILE OutRegionHEAreasFileName 
    OUT FILE OutRegionNDepAreasFileName 
    OUT FILE OutRegionCCAreasFileName 
    OUT FILE OutRegionIDAreasFileName 
    OUT FILE OutRegionIFAreasFileName 
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=21:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)

    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    areaRasterName = args[2]
    LandUseRasterName = args[3]
    regionRasterName = args[4]
    regionFilterStr = args[5]
    regionExcludeFilterStr = args[6]
    MSARasterName = args[7]
    landuseMSAName = args[8]
    humanEncMSAName = args[9]
    nDepMSAName = args[10]
    climChangeMSAName = args[11]
    infraDistMSAName = args[12]
    infraFragMSAName = args[13]
    outRegionAreasFileName = args[14]
    outRegionLandUseAreasFileName = args[15]
    outRegionMSAAreasFileName = args[16]
    outRegionMSALU = args[17]
    outRegionMSAHE = args[18]
    outRegionMSAND = args[19]
    outRegionMSACC = args[20]
    outRegionMSAID = args[21]
    outRegionMSAIF = args[22]
    
    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkRaster(areaRasterName)
    self.checkRaster(LandUseRasterName)
    self.checkRaster(regionRasterName)
    self.checkIntegerList(regionFilterStr,optional=True)
    self.checkIntegerList(regionExcludeFilterStr,optional=True)
    self.checkRaster(MSARasterName)
    self.checkRaster(landuseMSAName,optional=True)
    self.checkRaster(humanEncMSAName,optional=True)
    self.checkRaster(nDepMSAName,optional=True)
    self.checkRaster(climChangeMSAName,optional=True)
    self.checkRaster(infraDistMSAName,optional=True)
    self.checkRaster(infraFragMSAName,optional=True)
    self.checkFile(outRegionAreasFileName,asOutput=True,optional=True)
    self.checkFile(outRegionLandUseAreasFileName,asOutput=True,optional=True)
    self.checkFile(outRegionMSAAreasFileName,asOutput=True,optional=True)
    self.checkFile(outRegionMSALU,asOutput=True,optional=True)
    self.checkFile(outRegionMSAHE,asOutput=True,optional=True)
    self.checkFile(outRegionMSAND,asOutput=True,optional=True)
    self.checkFile(outRegionMSACC,asOutput=True,optional=True)
    self.checkFile(outRegionMSAID,asOutput=True,optional=True)
    self.checkFile(outRegionMSAIF,asOutput=True,optional=True)
    
    # Convert code and names to arrays.
    regionFilter = self.splitIntegerList(regionFilterStr)
    regionExcludeFilter = self.splitIntegerList(regionExcludeFilterStr)
    
    # Align extent.
    extent = RU.alignExtent(extent,cellSize)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.nrCols,self.nrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)
    self.outDir = os.path.dirname(outRegionMSAAreasFileName)
    
    # Enable monitor and show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)
    
    # Create a list with all msa rasters.
    msaRasterNames = [MSARasterName,landuseMSAName,humanEncMSAName,
                      nDepMSAName,climChangeMSAName,
                      infraDistMSAName,infraFragMSAName]
    msaOutFileNames = [outRegionMSAAreasFileName,outRegionMSALU,outRegionMSAHE,
                       outRegionMSAND,outRegionMSACC,
                       outRegionMSAID,outRegionMSAIF]
    
    #-----------------------------------------------------------------------------
    # Create the area raster.
    #-----------------------------------------------------------------------------

    # Need to create a area raster?
    if not self.isValueSet(areaRasterName):
      # Create the cell area raster.
      Log.info("Calculating cell area's...")
      areaRaster = Raster()
      areaRaster.initRasterCellAreas(extent,cellSize)
      return areaRaster
    else:
      # Read the cell area raster.
      areaRaster = self.readAndPrepareInRaster(extent,cellSize,areaRasterName,"areas")
    
    #-----------------------------------------------------------------------------
    # Read the regions raster and prepare.
    #-----------------------------------------------------------------------------

    # Reads the regions raster and resizes to extent and resamples to cellsize.
    regionRaster = self.readAndPrepareInRaster(extent,cellSize,regionRasterName,"region")

    #-----------------------------------------------------------------------------
    # Filter regions.
    #-----------------------------------------------------------------------------

    # Need to filter the regions?
    if self.isValueSet(regionFilter):
      Log.info("Filtering regions...")
      # Set nodata in region raster outside the regions in regionFilter.  
      self.setRegionRasterNoData(regionRaster,regionFilter)

    #-----------------------------------------------------------------------------
    # Filter excluded regions.
    #-----------------------------------------------------------------------------

    # Need to exclude regions?
    if self.isValueSet(regionExcludeFilter):
      Log.info("Excluding regions...")
      # Set nodata in region raster which should be excluded.  
      self.setRegionRasterExclude(regionRaster,regionExcludeFilter)

    #-----------------------------------------------------------------------------
    # Create a list of regions.
    #-----------------------------------------------------------------------------

    # Create a list of unique regions from the region raster.
    regionList = self.createRegionListFromRegionRaster(regionRaster)
    
    print(regionList)

    #-----------------------------------------------------------------------------
    # Calculate region areas.
    #-----------------------------------------------------------------------------

    Log.info("Calculating regional MSA contributions...")
    for i in range(len(msaRasterNames)):
             
      if i == 0:
          
        # Need to calculte region areas?
        if self.isValueSet(outRegionAreasFileName):            
          Log.info("Calculating region areas in km2...")
          self.calcRegionAreas(outRegionAreasFileName,regionList,regionRaster,areaRaster)
    
        #-----------------------------------------------------------------------------
        # Calculate region/landcover areas.
        #-----------------------------------------------------------------------------

        # Need to calculte region/landcover areas?
        if self.isValueSet(outRegionLandUseAreasFileName):             
          Log.info("Calculating region/landcover areas in km2...")
          self.calcRegionLandUseAreas(outRegionLandUseAreasFileName,
                                      LandUseRasterName,
                                      regionList,regionRaster,areaRaster)

      #-----------------------------------------------------------------------------
      # Calculate region/MSA areas.
      #-----------------------------------------------------------------------------
        
      msaRasterName = msaRasterNames[i]
      msaOutFileName = msaOutFileNames[i]

      # Need to calculte region/landcover areas?
      if self.isValueSet(msaOutFileName):
        Log.info("Calculating region/MSA areas in km2...")
        self.calcRegionMSAAreas(msaOutFileName,
                                msaRasterName,
                                regionList,regionRaster,areaRaster)    
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":

  try:
    inDir = r"Y:\data\GLOBIO\GLOBIO4\Beheer\Terra\SourceCode\GLOBIO_411_src20180925\src\Globio\Test\Calculations"
    lookupDir = r"Y:\data\GLOBIO\GLOBIO4\Models\Terra\Shared\LookupGlobal"
    outDir = r"Y:\data\GLOBIO\GLOBIO4\Beheer\Terra\SourceCode\GLOBIO_411_src20180925\src\Globio\Test\Calculations"
    if not os.path.isdir(outDir):
      outDir = r"S:\hilbersj"

    pCalc = GLOBIO_CalcMSAregion()

    ext = [-40,-39,5,6] #GLOB.constants["world"].value
    lu = os.path.join(inDir,"ESACCI_LC_1992_v207.tif")
    luwb = os.path.join(lookupDir,"LanduseMSA_v11_WBvert.csv")
    luin = os.path.join(lookupDir,"LanduseMSA_v11_Invert.csv")
    lupl = os.path.join(lookupDir,"LanduseMSA_v11_Plants.csv")
    msa = os.path.join(outDir,"LandUseMSA_test.tif")
    
    if RU.rasterExists(msa):
      RU.rasterDelete(msa)
      
    pCalc.run(ext,lu,luwb,luin,lupl,msa)
    
  except:
    Log.err()
