# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#----------------------------------------------------------------------------------
# Script to obtain percentiles of MSA values in a region: JH, PBL
# -For years after 2015 percentiles of differences are obtained
#----------------------------------------------------------------------------------

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
class GLOBIO_CalcMSAregion_percentile(CalculationBase):
  """
  Calculates MSA percentiles per region
  """

  nrCols = 0
  nrRows = 0

  #-------------------------------------------------------------------------------
  # Calculates percentiles of MSA per region and writes to csv file.
  # Use np.float64 to prevent oveflow.
  def calcRegionMSAAreas(self,csvFileName,MSARaster,regions,regionRaster):
               
    mask = ((MSARaster.r != MSARaster.noDataValue) & (MSARaster.r >= -1) & (MSARaster.r <= 1))

    # Calculate 5th and 95th percentile of areas per region. 
    def fn_5(x):
      return np.percentile(x, 5)
    def fn_95(x):
      return np.percentile(x, 95)    
    
    # 5th percentile
    areaSum_easy5 = scipy.ndimage.labeled_comprehension(MSARaster.r[mask],regionRaster.r[mask],regions,fn_5,np.float64,0)
    print(areaSum_easy5)
    
    # 95th percentile
    areaSum_easy95 = scipy.ndimage.labeled_comprehension(MSARaster.r[mask],regionRaster.r[mask],regions,fn_95,np.float64,0)
    print(areaSum_easy95)
    
    # Combine regions and areas in an array of region/area tuples.
    regionAreas = zip(regions,areaSum_easy5,areaSum_easy95)
    areaSum_easy5 = None
    areaSum_easy95 = None
    mask = None
    
    # Create file content.
    lines = []
    lines.append("region;percentile5;percentile95")
    for regionArea in regionAreas:
      lines.append("{};{};{}".format(*regionArea))
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
    IN RASTER MSARaster2015
    IN RASTER MSARasterSSP1
    IN RASTER MSARasterSSP3
    IN RASTER MSARasterSSP5
    OUT FILE OutRegionMSAAreasFileName2015 
    OUT FILE OutRegionMSAAreasFileNameSSP1 
    OUT FILE OutRegionMSAAreasFileNameSSP3 
    OUT FILE OutRegionMSAAreasFileNameSSP5 
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=14:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)

    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    areaRasterName = args[2]
    LandUseRasterName = args[3]
    regionRasterName = args[4]
    regionFilterStr = args[5]
    regionExcludeFilterStr = args[6]
    MSARasterName2015 = args[7]
    MSARasterNameSSP1 = args[8]
    MSARasterNameSSP3 = args[9]
    MSARasterNameSSP5 = args[10]
    outRegionMSAAreasFileName2015 = args[11]
    outRegionMSAAreasFileNameSSP1 = args[12]
    outRegionMSAAreasFileNameSSP3 = args[13]
    outRegionMSAAreasFileNameSSP5 = args[14]
    
    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkRaster(areaRasterName)
    self.checkRaster(LandUseRasterName)
    self.checkRaster(regionRasterName)
    self.checkIntegerList(regionFilterStr,optional=True)
    self.checkIntegerList(regionExcludeFilterStr,optional=True)
    self.checkRaster(MSARasterName2015)
    self.checkRaster(MSARasterNameSSP1)
    self.checkRaster(MSARasterNameSSP3)
    self.checkRaster(MSARasterNameSSP5)
    self.checkFile(outRegionMSAAreasFileName2015,asOutput=True)
    self.checkFile(outRegionMSAAreasFileNameSSP1,asOutput=True)
    self.checkFile(outRegionMSAAreasFileNameSSP3,asOutput=True)
    self.checkFile(outRegionMSAAreasFileNameSSP5,asOutput=True)
    
    # Convert code and names to arrays.
    regionFilter = self.splitIntegerList(regionFilterStr)
    regionExcludeFilter = self.splitIntegerList(regionExcludeFilterStr)
    
    # Align extent.
    extent = RU.alignExtent(extent,cellSize)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.nrCols,self.nrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)
    self.outDir = os.path.dirname(outRegionMSAAreasFileName2015)
    
    # Enable monitor and show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)
    
    # Create a list with all msa rasters.
    msaRasterNames = [MSARasterName2015,MSARasterNameSSP1,MSARasterNameSSP3,MSARasterNameSSP5]
    msaOutFileNames = [outRegionMSAAreasFileName2015,outRegionMSAAreasFileNameSSP1,outRegionMSAAreasFileNameSSP3,outRegionMSAAreasFileNameSSP5]
    
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
        
        msaRasterName = msaRasterNames[i]
        msaOutFileName = msaOutFileNames[i]
          
        # Need to calculte region areas?
        msaRaster2015 = self.readAndPrepareInRaster(extent,cellSize,msaRasterName,"msa 2015")
    	
        #-----------------------------------------------------------------------------
        # Calculate region/MSA areas.
        #-----------------------------------------------------------------------------
           
        # Need to calculte region/landcover areas?      
        if self.isValueSet(msaOutFileName):        
            Log.info("Calculating region/MSA areas in km2...")       
            self.calcRegionMSAAreas(msaOutFileName,
                                    msaRaster2015,
                                    regionList,regionRaster)

      else:
      
        msaRasterName = msaRasterNames[i]
        msaOutFileName = msaOutFileNames[i]
        
        # Need to calculte region areas?
        msaRaster = self.readAndPrepareInRaster(extent,cellSize,msaRasterName,"msa raster")

        # Create raster with default MSA value 1.
        noDataValue = -999.0
        MSARasterdiff = Raster()
        MSARasterdiff.initRaster(extent,cellSize,np.float32,noDataValue)
        MSARasterdiff.r = (msaRaster.r - msaRaster2015.r)
    
        #-----------------------------------------------------------------------------
        # Calculate region/MSA areas.
        #-----------------------------------------------------------------------------
           
        # Need to calculte region/landcover areas?      
        if self.isValueSet(msaOutFileName):        
            Log.info("Calculating region/MSA areas in km2...")       
            self.calcRegionMSAAreas(msaOutFileName,
                                    MSARasterdiff,
                                    regionList,regionRaster)
            
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":

  try:
    inDir = r""
    lookupDir = r""
    outDir = r""

    pCalc = GLOBIO_CalcMSAregion_percentile()

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
