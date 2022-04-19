# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
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
#           - JM testing SVN dynamic headers
#
# TODO:     20210114
#           - Use of CalculationBase.createRegionMask().
#           - Use of CalculationBase.setRegionRasterFilter() (ie. setRegionRasterNoData).
#           - Use of CalculationBase.setRegionRasterExclude().
#-------------------------------------------------------------------------------

import os
import numpy as np
import scipy.ndimage

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON
from GlobioModel.Common.Timer import Timer
import GlobioModel.Common.Utils as Utils

# WEL NODIG IVM FOUTMELDING IN VARIABLES!!!!!!!!!!!!!
import GlobioModel.Core.AppUtils as AppUtils

from GlobioModel.Core.CalculationBase import CalculationBase
from GlobioModel.LanduseAllocation.ClaimFile import ClaimFile
from GlobioModel.LanduseAllocation.LanduseType import LanduseType
from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_CalcDiscreteLanduseAllocation(CalculationBase):
  """
  Calculates a discrete landuse allocation.
  """

  #-------------------------------------------------------------------------------
  def __init__(self):

    # Call parent __init__()    
    super(GLOBIO_CalcDiscreteLanduseAllocation,self).__init__()

    self.nrCols = 0
    self.nrRows = 0
    self.maxSuitability = 1.0
    self.calcMaxSuitabilityFlag = False
    
    #-------------------------------------------------------------------------------
    # Set internal settings.    
    #-------------------------------------------------------------------------------

    self.mtimer = None

    self.debug = False
    #self.debug = True

    self.debugResultArray = False

    self.debugPrintTestInfo1 = False
    
    self.debug1 = False
    self.debug2 = False
    self.debug3 = False
    self.debug4 = False
    self.maskedArrays = False
    
    #self.showProgress = False
    self.showProgress = True

    self.test = False

    #-------------------------------------------------------------------------------
    # Define sort method.
    #-------------------------------------------------------------------------------

    # quicksort,mergesort,heapsort
    #self.sortKind = "quicksort"
    self.sortKind = "mergesort"

    #-------------------------------------------------------------------------------
    # Define land use codes.
    #-------------------------------------------------------------------------------

    self.landuseTypes = []

  #-------------------------------------------------------------------------------
  # Creates a land use type and adds it to the list. 
  def addLanduseType(self,code,name):
    luType = LanduseType(name,code)
    self.landuseTypes.append(luType) 

  #-------------------------------------------------------------------------------
  # Calculates the semi random noise for the specified extent.
  # Using this method the resampled raster always has different cell values
  # compared with the not-resampled raster (wrld vs eu).
  # REMARK: This method takes less memory.
  #def addSemiRandomNoise_NoResample(self,inRaster):
  def addSemiRandomNoise_NoResample(self,inRaster,landuseCode):
    
    # Set seed.
    seed = 12345
    
    #---------------------------------------------------------------------------
    # Calculate minimum value.
    #---------------------------------------------------------------------------
    
    # Filter small values.
    # Prevent stripes with pasture and forestry.
    minLimit = 1.0e-10
    
    # Get mask for cells which are no nodata.
    dataMask = (inRaster.getDataMask() & (inRaster.r > minLimit))

    # Get unique values and sort.
    uniqueArr = np.unique(inRaster.r[dataMask])
    sortedArr = np.sort(uniqueArr)
    
    # Get the delta's.
    edgeArr = np.ediff1d(sortedArr)

    # Sort the delta's ascending.    
    sortedEdgeArr = np.sort(edgeArr)

    # Get smallest delta.
    d = 1e-50

    #JH: also randomize when suitability rasters consists of 0s and 1s only
    if sortedEdgeArr.size==1:
      m = 1
    else:
      m = sortedEdgeArr[0] 
      if m < d:
        m = sortedEdgeArr[1] 

    # Calculate max delta.
    maxDelta = m * 0.9
         
    #---------------------------------------------------------------------------
    # Generate random raster.
    #---------------------------------------------------------------------------

    # Get world extent.
    #extentWrld = GLOB.constants["world"].value

    # Calculate number of cols and rows.
    nrCols, nrRows = RU.calcNrColsRowsFromExtent(inRaster.extent,inRaster.cellSize)

    # Generate a raster with values between 0.0 and 1.0.
    np.random.seed(seed=seed)
    randRas = np.random.random((nrRows,nrCols))   # pylint: disable=no-member
    
    # Randomize maxdelta.
    randRas *= maxDelta

    # Save temp raster?
    if GLOB.saveTmpData:
      tmpName = "tmp_random_"+str(landuseCode)+".tif"
      Log.info("- Writing random values: "+tmpName)
      self.writeTmpRaster(randRas,tmpName)

    # Add noise to inRaster.
    inRaster.r += randRas

    return 

  #-------------------------------------------------------------------------------
  # Calculates the semi random noise by first creating a world raster and
  # next resample to the specified extent.
  # Using this method the resampled raster should always have the same cell
  # values as the raster which is not resamples (wrld vs eu).
  # REMARK: This method takes much memory.
  def addSemiRandomNoise(self,inRaster,landuseCode):
    
    # Set seed.
    seed = 12345
    
    #---------------------------------------------------------------------------
    # Calculate minimum value.
    #---------------------------------------------------------------------------
    
    # Filter small values.
    # Prevent stripes with pasture and forestry.
    minLimit = 1.0e-10
    
    # Get mask for cells which are no nodata.
    dataMask = (inRaster.getDataMask() & (inRaster.r > minLimit))

    # Get unique values and sort.
    uniqueArr = np.unique(inRaster.r[dataMask])
    sortedArr = np.sort(uniqueArr)
    
    # Get the delta's.
    edgeArr = np.ediff1d(sortedArr)

    # Sort the delta's ascending.    
    sortedEdgeArr = np.sort(edgeArr)

    # Get smallest delta.
    d = 1e-50
    m = sortedEdgeArr[0] 
    if m < d:
      m = sortedEdgeArr[1] 

    # Calculate max delta.
    maxDelta = m * 0.9
         
    #---------------------------------------------------------------------------
    # Generate random raster.
    #---------------------------------------------------------------------------

    # Get world extent.
    #extentWrld = GLOB.constants["world"].value
    extentWrld = GLOB.extent_World

    # Calculate number of cols and rows.
    nrCols, nrRows = RU.calcNrColsRowsFromExtent(extentWrld,inRaster.cellSize)

    # Generate raster with values between 0.0 and 1.0.
    np.random.seed(seed=seed)
    randRas = np.random.random((nrRows,nrCols))        # pylint: disable=no-member

    # Create raster.
    dataType = np.float32
    noDataValue = RU.getNoDataValue(dataType)
    wrldRandRaster = Raster()
    wrldRandRaster.initRasterEmpty(extentWrld,inRaster.cellSize,dataType,noDataValue)
    wrldRandRaster.r = randRas

    #---------------------------------------------------------------------------
    # Resize extent to raster extent.
    #---------------------------------------------------------------------------
    
    # Resize raster to inRaster extent.
    randomRaster = wrldRandRaster.resize(inRaster.extent)
    
    # Cleanup wrldRandRaster.
    wrldRandRaster.close()
    wrldRandRaster = None

    # Randomize maxdelta.
    randomRaster.r *= maxDelta

    # Save temp raster?
    if GLOB.saveTmpData:
      tmpName = "tmp_random_"+str(landuseCode)+".tif"
      Log.info("- Writing random values: "+tmpName)
      self.writeTmpRaster(randomRaster,tmpName)
    
    # Add noise to inRaster.
    inRaster.r += randomRaster.r

    return 

  #-------------------------------------------------------------------------------
  # Calculates sum of areas per region and writes to csv file.
  # Use np.float64 to prevent oveflow.
  def calcRegionAreas(self,csvFileName,regions,regionRaster,areaRaster):
    # Calculate sum of areas per region.    
    areaSum = scipy.ndimage.labeled_comprehension(areaRaster.r,regionRaster.r,regions,np.sum,np.float64,0)
    # Combine regions and areas in an array of region/area tuples.
    regionAreas = zip(regions,areaSum)
    areaSum = None
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
  def calcRegionLandcoverAreas(self,csvFileName,landcoverRasterName,
                               regions,regionRaster,areaRaster):
    # Reads the land-cover raster and resizes to extent and resamples to cellsize.
    landcoverRaster = self.readAndPrepareInRaster(self.extent,self.cellSize,
                                                  landcoverRasterName,"land-cover")
    # Calulate areas.
    regionLandcoverAreas = []
    # Loop regions.
    for region in regions:
      # Create region mask.
      regionMask = (regionRaster.r == region)
      # Get landcover types in region.
      lcTypes = np.unique(landcoverRaster.r[regionMask])
      # Calculate sum of areas per landcover type.
      areaSum = scipy.ndimage.labeled_comprehension(areaRaster.r[regionMask],
                                                    landcoverRaster.r[regionMask],
                                                    lcTypes,np.sum,np.float64,0)
      # Fill an array with current region.
      tmpRegions = len(areaSum) * [region]    
      # Combine region, landcover and areas in an array of region/landcover/area tuples.
      tmpAreaSum = zip(tmpRegions,lcTypes,areaSum)
      # Add to list.
      regionLandcoverAreas.extend(tmpAreaSum)

    # Cleanup.
    regionMask = None
    lcTypes = None
    areaSum = None
    tmpRegions = None   
    tmpAreaSum = None

    # Close and free the land-cover raster.
    landcoverRaster.close()
    landcoverRaster = None
      
    # Create file content.
    lines = []
    lines.append("region;landcover;area")
    for regionLandcoverArea in regionLandcoverAreas:
      lines.append("{};{};{}".format(*regionLandcoverArea))
    # Write to file.
    Utils.fileWrite(csvFileName,lines)
    # Free areas and lines.
    regionLandcoverAreas = None
    lines = None

  #-------------------------------------------------------------------------------
  # Calculates sum of areas per region and landuse type and writes to csv file.
  # Use np.float64 to prevent overflow.
  def calcRegionLanduseAreas(self,csvFileName,landusePriorityCodes,
                             regionRasterName,regionFilter,regionExcludeFilter,
                             landuseRaster):
    
    # Reads the regions raster and resizes to extent and resamples to cellsize.
    regionRaster = self.readAndPrepareInRaster(self.extent,self.cellSize,
                                               regionRasterName,"region",silent=True)
    # Need to filter the regions?
    if len(regionFilter) > 0:
      # Set nodata in region raster outside the regions in regionFilter.  
      self.setRegionRasterNoData(regionRaster,regionFilter)
    # Need to exclude regions?
    if len(regionExcludeFilter) > 0:
      # Set nodata in region raster which should be excluded.  
      self.setRegionRasterExclude(regionRaster,regionExcludeFilter)
    # Create a list of unique regions from the region raster.
    regionList = self.createRegionListFromRegionRaster(regionRaster)
    # Remove regions with no claim.
    regionList = self.checkRegionsAndClaims(regionList,landusePriorityCodes)
    # Add region nodata value.
    regionList.append(int(regionRaster.noDataValue))
    
    # Create the cell area raster.
    areaRaster = self.createAreaRaster(self.extent,self.cellSize)
    
    regionLanduseAreas = []
    # Loop regions.
    for region in regionList:
      # Create region mask.
      regionMask = (regionRaster.r == region)
      # Get landuse types in region.
      luTypes = np.unique(landuseRaster.r[regionMask])
      # Calculate sum of areas per landuse type.
      areaSum = scipy.ndimage.labeled_comprehension(areaRaster.r[regionMask],
                                                    landuseRaster.r[regionMask],
                                                    luTypes,np.sum,np.float64,0)
      # Fill an array with current region.
      tmpRegions = len(areaSum) * [region]    
      # Combine region, landuse and areas in an array of region/landuse/area tuples.
      tmpAreaSum = zip(tmpRegions,luTypes,areaSum)
      # Add to list.
      regionLanduseAreas.extend(tmpAreaSum)

    # Cleanup.
    regionMask = None
    areaSum = None
    tmpRegions = None   
    tmpAreaSum = None

    # Close and free the region and area raster.
    regionRaster.close()
    regionRaster = None
    areaRaster.close()
    areaRaster = None
      
    # Create file content.
    lines = []
    lines.append("region;landuse;area")
    for regionLanduseArea in regionLanduseAreas:
      lines.append("{};{};{}".format(*regionLanduseArea))

    # Write to file.
    Utils.fileWrite(csvFileName,lines)
    # Free areas and lines.
    regionLanduseAreas = None
    lines = None

  #-------------------------------------------------------------------------------
  # Checks if the codeList is a list of valid integer landuse codes.
  def checkLanduseCodes(self,codeList,errNotSpecified,errInvalid,optional=False):
    if (optional) and (codeList==""):
      # No checks needed.
      return
    if codeList=="":
      Err.raiseGlobioError(errNotSpecified)
    # Get codes.
    codes = self.splitIntegerList(codeList)
    for code in codes:
      # Get land-use type?
      luType = self.getLanduseTypeByCode(code)
      # No land-use type found?
      if luType is None:
        Err.raiseGlobioError(errInvalid,code)

  #-----------------------------------------------------------------------------
  # Checks regions and claims. Removes regions from the list with no claim.
  def checkRegionsAndClaims(self,regionList,landusePriorityCodes):
    # Copy all regions.
    notFoundRegions = regionList[:]
    # Loop landuse types.
    for landuseCode in landusePriorityCodes:
      # Get landuse type.
      landuseType = self.getLanduseTypeByCode(landuseCode)
      # Loop regions.
      for region in regionList:
        # Check region claim.
        if region in landuseType.claims:
          # Found, remove from list.
          if region in notFoundRegions:
            notFoundRegions.remove(region)
    # Copy all regions.
    newRegionList = regionList[:]
    # Check not found regions.
    for region in notFoundRegions:
      # Show message.
      Log.info("  Skipping region '%s'. No region claims available!" % region)
      # Remove from original list.
      if region in newRegionList:
        newRegionList.remove(region)
    # Return new list.
    return newRegionList

  #-----------------------------------------------------------------------------
  # Creates the area raster.
  def createAreaRaster(self,extent,cellSize):
    if self.test:
      Log.info("SETTING TEST AREA's...")
      areaRaster = self.createTestCellAreaRaster(extent,cellSize)
    else:
      areaRaster = Raster()
      self.dbgPrint("- Create areaRas...")
      areaRaster.initRasterCellAreas(extent,cellSize)
      self.dbgInfo()
    return areaRaster

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
  def createTestCellAreaRaster(self,extent,cellSize):
    areaRaster = Raster()
    areaRaster.initRasterEmpty(extent,cellSize,np.float32,0.0)
    areaRaster.r = np.array([
      1.0, 1.0, 1.0, 1.0, 1.0, 1.0,
      2.0, 2.0, 2.0, 2.0, 2.0, 2.0,
      2.0, 2.0, 2.0, 2.0, 2.0, 2.0,
      1.0, 1.0, 1.0, 1.0, 1.0, 1.0,
    ]).reshape(self.nrRows,self.nrCols)
    return areaRaster

  #-------------------------------------------------------------------------------
  # Show debug message.
  def dbgPrint(self,s,indent="  "):
    if not self.debug:
      return
    if self.mtimer is None:
      self.mtimer = Timer()
    Log.info("%s# %s" % (indent,s))

  #-------------------------------------------------------------------------------
  # Show debug info.
  def dbgPrintTestInfo1(self,currClaim,insertIdx,cumAreaRas,currSuitSortIds,selectedAreaRas):
    if not self.debugPrintTestInfo1:
      return
    Log.info("################")
    Log.info("Search for claim opp.: %s" %currClaim)
    Log.info("Insert index: %s" % insertIdx)
    Log.info("len(cumAreaRas): %s" % len(cumAreaRas))
    Log.info("len(currSuitSortIds): %s" % len(currSuitSortIds))
    Log.info("################")
    if insertIdx < len(currSuitSortIds):
      Log.info("cumAreaRas[currSuitSortIds[insertIdx]]: %s" % cumAreaRas[currSuitSortIds[insertIdx]])
    if insertIdx-1 < len(currSuitSortIds):
      Log.info("cumAreaRas[currSuitSortIds[insertIdx-1]]: %s" % cumAreaRas[currSuitSortIds[insertIdx-1]])
    Log.info("cumAreaRas[currSuitSortIds[insertIdx-10:insertIdx+10]]: %s" % cumAreaRas[currSuitSortIds[insertIdx-10:insertIdx+10]])
    if insertIdx < len(currSuitSortIds):
      Log.info("np.sum(selectedAreaRas[currSuitSortIds[:insertIdx]]): %s" % np.sum(selectedAreaRas[currSuitSortIds[:insertIdx]]))
    if insertIdx-1 < len(currSuitSortIds):
      Log.info("np.sum(selectedAreaRas[currSuitSortIds[:insertIdx-1]]): %s" % np.sum(selectedAreaRas[currSuitSortIds[:insertIdx-1]]))
    Log.info("################")

  #-------------------------------------------------------------------------------
  # Show debug message and additional memory info.
  def dbgInfo(self,indent="  "):
    if not self.debug:
      return
    # Initialize timer.
    if self.mtimer is None:
      self.mtimer = Timer()

    # Get currently used memory.
    memUsed = Utils.memPhysicalUsed()
    
    # No start memory detected?
    if self.startMemUsed < 0:
      # Set start memory to currently used memory.
      self.startMemUsed = memUsed
      # Show memory data.
      memTotal = Utils.memPhysicalTotal()
      Log.info("%s# - Memory total: %s" % (indent,Utils.bytesToStr(memTotal)))
      memUsed = Utils.memPhysicalUsed()
      Log.info("%s# - Memory in use: %s" % (indent,Utils.bytesToStr(memUsed)))
      memAvail = Utils.memPhysicalAvailable()
      Log.info("%s# - Memory available: %s" % (indent,Utils.bytesToStr(memAvail)))
    else:
      timeStr = self.mtimer.elapsedStr()
      # Calculate real memory used.
      memUsed = memUsed - self.startMemUsed
      # Update max memory used.
      if memUsed > self.maxMemUsed:
        self.maxMemUsed = memUsed
      # Convert memory used to string with proper units.
      memStr = Utils.bytesToStr(memUsed)
      # Show memory used.
      Log.info("%s# - Memory used: %s (%s)" % (indent,memStr,timeStr))

  #-------------------------------------------------------------------------------
  def getLanduseTypeByCode(self,code):
    for luType in self.landuseTypes:
      if luType.code == code:
        return luType
    return None 

  #-------------------------------------------------------------------------------
  def getLanduseTypeByName(self,name):
    for luType in self.landuseTypes:
      if luType.name == name:
        return luType
    return None 

  #-------------------------------------------------------------------------------
  #  Read the landuse claims and reclass.
  def readLanduseClaimsAndReclass(self,claimFileName,claimLookupFileName,
                                  claimLanduseFieldName,claimRegionFieldName,
                                  claimAreaFieldName):
    # Read the claims.
    claimFile = ClaimFile()
    claimFile.read(claimFileName,claimLanduseFieldName,claimRegionFieldName,claimAreaFieldName)
    # Need to reclass landuse types?
    if self.isValueSet(claimLookupFileName):
      # Reclass the landuse types.
      claimLookupFieldTypes = ["S","S"]
      claimFile.reclassRowValue(claimLanduseFieldName,claimLookupFileName,claimLookupFieldTypes)
      # Summarize area.    
      claimFile.aggregateRowValue(claimAreaFieldName)
    return claimFile

  #-------------------------------------------------------------------------------
  def recalculateLanduseClaims(self,claimAreaMultiplierLanduseCodes,claimAreaMultipliers):
    # Loop land-use codes.
    for i in range(len(claimAreaMultiplierLanduseCodes)):
      # Get land-use code.
      landuseCode = claimAreaMultiplierLanduseCodes[i]
      # Get land-use type.
      landuseType = self.getLanduseTypeByCode(landuseCode)
      # Found?
      if not landuseType is None:
        # Get multiplier.
        claimAreaMultiplier = claimAreaMultipliers[i]
        # Loop claim regions.
        for region in landuseType.claims:
          area = landuseType.claims[region]
          area = area * claimAreaMultiplier
          landuseType.claims[region] = area
          
  #-------------------------------------------------------------------------------
  # Bind the claim area to the landuse types.
  def setLanduseClaims(self,claimFile):
    # Loop claimfile rows.
    for row in claimFile.rows:
      # Get the landuse name.
      landuseName = claimFile.landuse(row)
      # Get the landuse type.
      luType = self.getLanduseTypeByName(landuseName)
      # Found?
      if not luType is None:
        # Get region.
        region = claimFile.region(row)
        # Get area.
        area = claimFile.area(row)
        # Add region and area.
        luType.claims[region] = area

  #-------------------------------------------------------------------------------
  # Bindt the suitability rasters to the landuse types.
  def setLanduseSuitabilityRasters(self,suitRasterCodes,suitRasterNames):
    # Loop suitability raster codes.
    i = 0
    for i in range(len(suitRasterCodes)):
      # Get the landuse code.
      landuseCode = suitRasterCodes[i]
      # Get the landuse type.
      luType = self.getLanduseTypeByCode(landuseCode)
      # Found?
      if not luType is None:
        # Get raster name.
        rasName = suitRasterNames[i]
        # Set the raster name.
        luType.suitRasterName = rasName

  #-------------------------------------------------------------------------------
  def setLanduseTypes(self,codeList,nameList):
    codes = self.splitIntegerList(codeList)
    names = self.splitStringList(nameList)
    for i in range(len(codes)):
      self.addLanduseType(codes[i],names[i])

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
  def toLinux(self,winDir):
    winDir = winDir.replace("G:\\Data\\Globio4LA","")
    return winDir.replace("\\","/")

  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent  
    IN CELLSIZE CellSize 
    IN STRING LanduseCodes 
    IN STRING LanduseNames 
    IN STRING LandusePriorityCodes 
    IN RASTER Landcover 
    IN RASTER Regions 
    IN STRING RegionFilter 
    IN STRING RegionExcludeFilter 
    IN RASTER Landuse 
    IN STRING LanduseReplaceWithLandcoverCodes 
    IN STRING LanduseReplaceCode 
    IN STRING LanduseUndefinedCode 
    IN RASTER NotAllocatableAreas 
    IN RASTER PAReduceFactor 
    IN STRING SuitRasterCodes 
    IN RASTERLIST SuitRasterNames 
    IN FILE ClaimFileName 
    IN STRING ClaimLanduseFieldName 
    IN STRING ClaimRegionFieldName 
    IN STRING ClaimAreaFieldName 
    IN FILE claimLookup 
    IN STRING ClaimAreaMultiplierLanduseCodes 
    IN STRING ClaimAreaMultipliers 
    IN RASTER CellAreas 
    IN BOOLEAN AddNoiseFlag 
    OUT FILE OutRegionAreasFileName 
    OUT FILE OutRegionLandcoverAreasFileName 
    OUT FILE OutRegionLanduseAreasFileName 
    OUT RASTER OutAllocatedLanduse
    """
    self.run_v20(*args)

  #-------------------------------------------------------------------------------
  # v1 : Versie tot 13 oktober, met oude landcover kaart.
  # v2 : Versie na 13 oktober, met o.a. ESA landcover kaart.
  #      Regions zonder claims worden nu eerst verwijderd.
  # v3 : Nu met rasters van landcover-landuse, protected areas, not-allocatable.
  # v4 : Met ClaimAreaMultiplier.
  # v5 : Met correctie gebieden buiten de regio's.
  #      Met landuseUndefinedCodeStr.
  #      Zonder resizeResample!
  #      Met RegionExcludeFilter.
  # v7 : Kopie van run_v5.
  #      Met berekening van oppervlaktes.
  # v8 : Nu met areas in csv files.
  # v9 : Nu met semi-random noise.
  # v10: Zonder masked_array.
  # v11: Nu met eerst pa, dan add noise.
  # v12: Nu met areaRaster.
  #      Aangepast ivm. cumsum.
  #      Nu met extra controles
  #      Nu met addNoise vlag.
  # v13: Nu met saveMemoryUsage.
  # v15: Nu met debug2.
  #      Nu met self.maskedArrays.
  # v16: Geen land-cover vulling voor pasture en forestry.
  # v17: Nu met landuseReplaceWithLandcoverCodes.
  #      Nu met claimAreaMultiplier per landuse-type.
  #      Nu met claimAreaMultipliers ipv. claimAreaMultiplier.
  #      Nu met regionCalculationClustersStr.
  # v18: Aangepast ivm. problemen met 10sec.
  #      Nu met sortKind.
  # v19: Opgeschoond.
  #      Nu met saveArrayToCSV.
  #      Nu met calc*_v19.
  #      Nu met debug1.
  #      PAReduceFactor is nu optioneel.
  #      Nu met nieuwe pa op basis van de fgdb.
  # v20: Opgeschoond.
  #      regionCalculationClustersStr verwijderd.
  #      Nu met landuseReplaceCodesStr.
  #      Nu met landuseReplaceWithCodeStr.
  #      Nu met addRandomNoise_NoResample.
  def run_v20(self,*args):
  
    # Show start message.
    self.showStartMsg(args)

    # Check number of arguments.
    if len(args)<=29:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)

    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    landuseCodesStr = args[2]
    landuseNamesStr = args[3]
    landusePriorityCodesStr = args[4]
    landcoverRasterName = args[5]
    regionRasterName = args[6]
    regionFilterStr = args[7]
    regionExcludeFilterStr = args[8]
    landuseRasterName = args[9]
    landuseReplaceCodesStr = args[10]
    landuseReplaceWithCodeStr = args[11]
    landuseUndefinedCodeStr = args[12]
    notAllocatableAreasRasterName = args[13]
    paReduceFactorRasterName = args[14]
    suitRasterCodesStr = args[15]
    suitRasterNamesStr = args[16]
    claimFileName = args[17]
    claimLanduseFieldName = args[18]
    claimRegionFieldName = args[19]
    claimAreaFieldName = args[20]
    claimLookupFileName = args[21]
    claimAreaMultiplierLanduseCodesStr = args[22]
    claimAreaMultipliersStr = args[23]
    areaRasterName = args[24]
    addNoise = args[25]
    outRegionAreasFileName = args[26]
    outRegionLandcoverAreasFileName = args[27]
    outRegionLanduseAreasFileName = args[28]
    outRasterName = args[29]

    # Check arguments.
    self.checkExtent(extent)
    if cellSize > 0:
      self.checkCellSize(cellSize)
    self.checkIntegerList(landuseCodesStr)
    self.checkListCount(landuseNamesStr,landuseCodesStr,"land-use names")
    self.setLanduseTypes(landuseCodesStr,landuseNamesStr)
    self.checkLanduseCodes(landusePriorityCodesStr,
                           Err.NoLandusePriorityCodesSpecified,
                           Err.InvalidLandusePriorityCode1)
    self.checkRaster(landcoverRasterName)
    self.checkRaster(regionRasterName)
    self.checkIntegerList(regionFilterStr,optional=True)
    self.checkIntegerList(regionExcludeFilterStr,optional=True)
    self.checkRaster(landuseRasterName)
    self.checkLanduseCodes(landuseReplaceCodesStr,
                           Err.NoLanduseReplaceCodesSpecified,
                           Err.InvalidLanduseReplaceCodes1)
    self.checkLanduseCodes(landuseReplaceWithCodeStr,
                           Err.NoLanduseReplaceWithCodeSpecified,
                           Err.InvalidLanduseReplaceWithCode1)
    self.checkLanduseCodes(landuseUndefinedCodeStr,
                           Err.NoLanduseUndefinedCodeSpecified,
                           Err.InvalidLanduseUndefinedCode1)
    self.checkRaster(notAllocatableAreasRasterName)
    self.checkRaster(paReduceFactorRasterName,False,True)
    self.checkLanduseCodes(suitRasterCodesStr,
                           Err.NoSuitabilityRasterCodesSpecified,
                           Err.InvalidSuitabilityRasterCode1)
    self.checkListCount(suitRasterNamesStr,suitRasterCodesStr,"rasters")
    self.checkRasterList(suitRasterNamesStr)
    self.checkFile(claimFileName)
    self.checkFieldName(claimLanduseFieldName,"landuse")
    self.checkFieldName(claimRegionFieldName,"region")
    self.checkFieldName(claimAreaFieldName,"area")
    self.checkFile(claimLookupFileName,optional=True)
    self.checkLanduseCodes(claimAreaMultiplierLanduseCodesStr,
                           Err.NoClaimAreaMultiplierLanduseCodesSpecified,
                           Err.InvalidClaimAreaMultiplierLanduseCode1,optional=True)
    self.checkListCount(claimAreaMultipliersStr,claimAreaMultiplierLanduseCodesStr,"claim area multipliers")
    self.checkFloatList(claimAreaMultipliersStr,optional=True)
    self.checkBoolean(addNoise)
    self.checkRaster(areaRasterName,optional=True)
    self.checkFile(outRegionAreasFileName,asOutput=True,optional=True)
    self.checkFile(outRegionLandcoverAreasFileName,asOutput=True,optional=True)
    self.checkFile(outRegionLanduseAreasFileName,asOutput=True,optional=True)
    self.checkRaster(outRasterName,asOutput=True)

    # Convert code and names to arrays.
    landusePriorityCodes = self.splitIntegerList(landusePriorityCodesStr)
    regionFilter = self.splitIntegerList(regionFilterStr)
    regionExcludeFilter = self.splitIntegerList(regionExcludeFilterStr)
    suitRasterCodes = self.splitIntegerList(suitRasterCodesStr)
    suitRasterNames = self.splitStringList(suitRasterNamesStr)
    landuseReplaceCodes = self.splitIntegerList(landuseReplaceCodesStr)
    landuseReplaceWithCode = int(landuseReplaceWithCodeStr)
    landuseUndefinedCode = int(landuseUndefinedCodeStr)
    claimAreaMultiplierLanduseCodes = self.splitIntegerList(claimAreaMultiplierLanduseCodesStr)
    claimAreaMultipliers = self.splitFloatList(claimAreaMultipliersStr)

    # Fill list with raster names.
    inRasterNames = [landcoverRasterName,notAllocatableAreasRasterName,
                     paReduceFactorRasterName,regionRasterName]
    inRasterNames.extend(suitRasterNames)

    # Get the minimum cellsize for the output raster.
    if cellSize <= 0:
      cellSize = self.getMinimalCellSize(inRasterNames)
      Log.info("Using cellsize: %s" % cellSize)

    # Align extent.
    extent = RU.alignExtent(extent,cellSize)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.nrCols,self.nrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)
    self.outDir = os.path.dirname(outRasterName)

    # Enable monitor en show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    #-----------------------------------------------------------------------------
    # Set the landuse type suitability raster names.
    #-----------------------------------------------------------------------------

    self.setLanduseSuitabilityRasters(suitRasterCodes,suitRasterNames)
    
    #-----------------------------------------------------------------------------
    # Read the landuse claims and reclass.
    #-----------------------------------------------------------------------------

    claimFile = self.readLanduseClaimsAndReclass(claimFileName,claimLookupFileName,
                                                 claimLanduseFieldName,
                                                 claimRegionFieldName,
                                                 claimAreaFieldName)

    #-----------------------------------------------------------------------------
    # Set the land-use type claims.
    #-----------------------------------------------------------------------------

    # Set the landuse claims.
    self.setLanduseClaims(claimFile)

    # Free claimfile.
    claimFile = None

    #-----------------------------------------------------------------------------
    # Recalulate land-use type claims.
    #-----------------------------------------------------------------------------

    # Increase or decrease claim area?
    if self.isValueSet(claimAreaMultipliers):
      Log.info("Recalculating land-use claims...")
      self.recalculateLanduseClaims(claimAreaMultiplierLanduseCodes,claimAreaMultipliers)

    #-----------------------------------------------------------------------------
    # Read the not-allocatable areas raster and prepare.
    #-----------------------------------------------------------------------------
  
    # Reads the not-allocatable areas raster and resizes to extent and resamples to cellsize.
    notAllocRaster = self.readAndPrepareInRaster(extent,cellSize,notAllocatableAreasRasterName,"not-allocatable areas")

    ########### FOR TESTING.
    self.writeTmpRaster(notAllocRaster,"tmp_not_alloc.tif","- Writing not-allocatable areas")

    #-----------------------------------------------------------------------------
    # Create allocatable areas mask.
    #-----------------------------------------------------------------------------

    Log.info("Creating allocatable areas mask...")

    # Select allocatable areas, so where not-allocatable cells are not 1.
    allocatableMask = (notAllocRaster.r != 1)

    # Check allocatable mask.
    if np.sum(allocatableMask) == 0:
      Log.info("  No allocatable areas found.")
      exit(0)

    ########### FOR TESTING.
    if GLOB.saveTmpData:
      allocMaskRaster = Raster()
      allocMaskRaster.initRasterLike(notAllocRaster,False,np.uint8)
      allocMaskRaster.r = allocatableMask
      self.writeTmpRaster(allocMaskRaster,"tmp_allocmask.tif","- Writing allocatable mask")
      allocMaskRaster.close()
      allocMaskRaster = None

    # Free not-allocatable areas raster.    
    notAllocRaster.close()
    notAllocRaster = None

    #-----------------------------------------------------------------------------
    # Read the protected areas raster and prepare.
    #-----------------------------------------------------------------------------

    # Need to use protected areas raster?
    paReduceFactorRaster = None
    if self.isValueSet(paReduceFactorRasterName):
      
      # Reads the protected areas raster and resizes to extent and resamples to cellsize.
      # High protection is 0.0, no protection is 1.0.
      paReduceFactorRaster = self.readAndPrepareInRaster(extent,cellSize,paReduceFactorRasterName,"protected areas reduce factor")

      ########### FOR TESTING.
      self.writeTmpRaster(paReduceFactorRaster,"tmp_pa_red_factor.tif","- Writing protected areas")
        
    #-----------------------------------------------------------------------------
    # Read the regions raster and prepare.
    #-----------------------------------------------------------------------------

    # Reads the regions raster and resizes to extent and resamples to cellsize.
    regionRaster = self.readAndPrepareInRaster(extent,cellSize,regionRasterName,"region")

    ########### FOR TESTING.
    self.writeTmpRaster(regionRaster,"tmp_regions.tif","- Writing regions")

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

    #-----------------------------------------------------------------------------
    # Check regions and claims.
    #-----------------------------------------------------------------------------

    # Remove regions with no claim.
    Log.info("Checking regions and claims...")
    regionList = self.checkRegionsAndClaims(regionList,landusePriorityCodes)

    Log.info("Using regions: %s" % regionList)

    #-----------------------------------------------------------------------------
    # Create the area raster.
    #-----------------------------------------------------------------------------

    # Need to create a area raster?
    if not self.isValueSet(areaRasterName):
      # Create the cell area raster.
      Log.info("Calculating cell area's...")
      areaRaster = self.createAreaRaster(self.extent,self.cellSize)
    else:
      # Read the cell area raster.
      areaRaster = self.readAndPrepareInRaster(extent,cellSize,areaRasterName,"areas")
 
    ########### FOR TESTING.
    self.writeTmpRaster(areaRaster,"tmp_areas.tif","- Writing areas")

    #-----------------------------------------------------------------------------
    # Calculate region areas.
    #-----------------------------------------------------------------------------

    # Need to calculte region areas?
    if self.isValueSet(outRegionAreasFileName):
      Log.info("Calculating region areas in km2...")
      self.calcRegionAreas(outRegionAreasFileName,regionList,regionRaster,areaRaster)
    
    #-----------------------------------------------------------------------------
    # Calculate region/landcover areas.
    #-----------------------------------------------------------------------------

    # Need to calculte region/landcover areas?
    if self.isValueSet(outRegionLandcoverAreasFileName):
      Log.info("Calculating region/landcover areas in km2...")
      self.calcRegionLandcoverAreas(outRegionLandcoverAreasFileName,
                                    landcoverRasterName,
                                    regionList,regionRaster,areaRaster)

    #-----------------------------------------------------------------------------
    # Create output raster.
    #-----------------------------------------------------------------------------

    # Create the output raster.
    outRaster = Raster(outRasterName)
    outRaster.initRaster(extent,cellSize,np.uint8,0)

    ##############################################################################
    # Calculate discrete landuse allocation.
    ##############################################################################

    #-----------------------------------------------------------------------------
    # Loop landuse types.
    #-----------------------------------------------------------------------------

    for landuseCode in landusePriorityCodes:

      # Get landuse type.
      landuseType = self.getLanduseTypeByCode(landuseCode)

      # No suitability rastername, then skip.        
      if landuseType.suitRasterName == "":
        continue
 
      # Show progress.
      if self.showProgress:
        Log.info("Processing %s (%s)..." % (landuseType.name,landuseType.code))

      #-----------------------------------------------------------------------------
      # Read the landuse suitability and prepare.
      #-----------------------------------------------------------------------------
  
      # Reads the regions raster and resizes to extent and resamples to cellsize.
      currSuitRaster = self.readAndPrepareInRaster(extent,cellSize,
                            landuseType.suitRasterName,
                            landuseType.name + " suitability","- ")

      ########### FOR TESTING.
      self.dbgPrintMinMaxNoData(currSuitRaster,"suitability")
      self.dbgPrintArray("currSuitRaster",currSuitRaster.r)
      self.writeTmpRaster(currSuitRaster,"tmp_suit_%s.tif" % landuseCode,"- Writing landuse suitability")

      #-----------------------------------------------------------------------------
      # Reduce the suitability in protected areas.
      #-----------------------------------------------------------------------------

      # Need to use a raster with protected areas?
      if not paReduceFactorRaster is None:
        
        # Multiply the original suitability with the reduce factor for
        # protected areas, i.e. high protection is 0.0, no protection is 1.0.
        Log.info("- Adding protected areas...")
        currSuitRaster.r *= paReduceFactorRaster.r

        ########### FOR TESTING.
        self.dbgPrintMinMaxNoData(currSuitRaster,"suitability*pa")
        self.dbgPrintArray("currSuitRaster*pa",currSuitRaster.r)
        self.writeTmpRaster(currSuitRaster,"tmp_suitprot_%s.tif" % landuseCode,"- Writing landuse suitability with pa")
     
      #-----------------------------------------------------------------------------
      # Add semi-random noise (in the  protected areas too).
      #-----------------------------------------------------------------------------
      
      # Need to add semi-random noise?
      if addNoise:
        # Add noise.
        Log.info("- Adding semi-random noise...")
        #self.addSemiRandomNoise(currSuitRaster,landuseCode)
        #self.addSemiRandomNoise_NoResample(currSuitRaster)
        self.addSemiRandomNoise_NoResample(currSuitRaster,landuseCode)

        ########### FOR TESTING.
        self.dbgPrintMinMaxNoData(currSuitRaster,"suitability+noise")
        self.dbgPrintArray("currSuitRaster+noise",currSuitRaster.r)
        self.writeTmpRaster(currSuitRaster,"tmp_suitprot_%s.tif" % landuseCode,"- Writing landuse suitability with pa and noise")
      
      #-----------------------------------------------------------------------------
      # Loop regions.
      #-----------------------------------------------------------------------------
      for region in regionList:

        # Show progress.
        if self.showProgress:
          Log.info("- Processing region %s..." % region)

        #-----------------------------------------------------------------------------
        # Check region claim.
        #-----------------------------------------------------------------------------
        if not region in landuseType.claims:
          Log.info("    Skipping region '%s'. No region claim available for '%s'!" % (region,landuseType.name))
          continue
        
        #-----------------------------------------------------------------------------
        # Select the cells which are allocatable for the current land-use type.
        # These are the cells which:
        # - falls within the region.
        # - are no not-allocatable areas.
        # - are not yet allocated by previous processed landuse types.
        #-----------------------------------------------------------------------------

        #-----------------------------------------------------------------------------
        # Select current region.
        #-----------------------------------------------------------------------------

        # Select the cells in the current region.
        currSuitMask = (regionRaster.r == region)

        # Check regions.
        if np.sum(currSuitMask) == 0:
          Log.info("    No region cels found.")
          continue

        ########### FOR TESTING.
        self.dbgPrintArray("currSuitMask - region",currSuitMask)

        #-----------------------------------------------------------------------------
        # Select allocatable cells.
        #-----------------------------------------------------------------------------

        # Refine region mask with allocatable cells.
        currSuitMask = np.logical_and(currSuitMask,allocatableMask)

        # Check allocatable cells.
        if np.sum(currSuitMask) == 0:
          Log.info("    No allocatable cells in regio found.")
          continue

        ########### FOR TESTING.
        self.dbgPrintArray("currSuitMask - allocatableMask",currSuitMask)

        #-----------------------------------------------------------------------------
        # Select free cells.
        #-----------------------------------------------------------------------------

        # Select the output cells which are not allocated by previous processed landuse types.
        currSuitMask = np.logical_and(currSuitMask,(outRaster.r == outRaster.noDataValue))

        # Check free cells.
        if np.sum(currSuitMask) == 0:
          Log.info("    No free cells in regio found.")
          continue

        ########### FOR TESTING.
        self.dbgPrintArray("currSuitMask outRaster.noDataValue",currSuitMask)

        #-----------------------------------------------------------------------------
        # Select valid suitability cells, i.e. allocatable cells.
        #-----------------------------------------------------------------------------

        # Select suitability.
        selectedCurrSuitRas = currSuitRaster.r[currSuitMask]

        ########### FOR TESTING.
        self.dbgPrintArray("selectedCurrSuitRas",selectedCurrSuitRas)
  
        #-----------------------------------------------------------------------------
        # Sort the suitability of the allocatable cells.
        #-----------------------------------------------------------------------------

        # Calculate *-1 to sort from high to low.
        selectedCurrSuitRas *= -1.0

        # Sort suitability from high to low.
        #Log.info("- Sorting suitability (%s)..." % self.sortKind)
        currSuitSortIds = np.argsort(selectedCurrSuitRas,kind=self.sortKind)

        ########### FOR TESTING.
        self.dbgPrintArray("currSuitSortIds",currSuitSortIds)
        self.dbgPrintArray("selectedCurrSuitRas[currSuitSortIds]",selectedCurrSuitRas[currSuitSortIds])
        self.dbgPrintArray("selectedCurrSuitRas[currSuitSortIds[-20:]]",selectedCurrSuitRas[currSuitSortIds[-20:]])

        # Cleanup maskedCurrSuitRas.
        selectedCurrSuitRas = None

        #-----------------------------------------------------------------------------
        # Select valid area cells, i.e. with same mask as for suitability.
        #-----------------------------------------------------------------------------

        # Select areas.
        selectedAreaRas = areaRaster.r[currSuitMask]
  
        ########### FOR TESTING.
        self.dbgPrintArray("selectedAreaRas",selectedAreaRas)
        self.dbgPrintArray("selectedAreaRas[currSuitSortIds]",selectedAreaRas[currSuitSortIds])

        #-----------------------------------------------------------------------------
        # Calculate the cummulated area of the selected and sorted cells.
        #-----------------------------------------------------------------------------

        # Set cumsum datatype. Cellsize less than 30sec, use float64.
        #if self.cellSize < GLOB.constants["30sec"].value:
        if self.cellSize < GLOB.cellSize_30sec:
          cumsumDataType = np.float64
        else:
          cumsumDataType = np.float32
        
        # Calculate the cummulative area.
        cumAreaRas = np.cumsum(selectedAreaRas[currSuitSortIds],dtype=cumsumDataType)

        ########### FOR TESTING.
        self.dbgPrintArray("cumAreaRas",cumAreaRas)

        #-----------------------------------------------------------------------------
        # Select area cells up to the landuse claim area.
        #-----------------------------------------------------------------------------

        # Get the current landuse claim.
        currClaim = landuseType.claims[region]
        #JM
        Log.info("   Current claim for region is %s" % (str(currClaim)))
                  
        # Get the index of the cell which claim area <= cum area.
        insertIdx = np.searchsorted(cumAreaRas,currClaim,side='right')
        
        ########### FOR TESTING.
        self.dbgPrintTestInfo1(currClaim,insertIdx,cumAreaRas,currSuitSortIds,selectedAreaRas)

        #JH
        # Calculate the total area and report whether the claim is fully allocated.
        totAreaRas = np.sum(selectedAreaRas[currSuitSortIds],dtype=cumsumDataType)
        if totAreaRas>=currClaim:
            Log.info("   100% of claim is allocated")
        else:
            Log.info("   Only %s%% of claim is allocated" % (str(round((totAreaRas/currClaim*100),1))))

        # Free landuse cumulative area's.
        cumAreaRas  = None
  
        # Free masked area's.
        selectedAreaRas  = None
  
        #-----------------------------------------------------------------------------
        # Create masked output array.
        #-----------------------------------------------------------------------------
  
        # Select output cells.
        selectedOutRas = outRaster.r[currSuitMask]
  
        ########### FOR TESTING.
        self.dbgPrintArray("selectedOutRas",selectedOutRas)
  
        # Update output raster with land-use.
        selectedOutRas[currSuitSortIds[:insertIdx]] = landuseType.code
  
        ########### FOR TESTING.
        self.dbgPrintArray("maskedOutRas code",selectedOutRas)
  
        # Update output raster.
        outRaster.r[currSuitMask] = selectedOutRas

        # Free sorted ids.
        currSuitSortIds  = None
  
        # Free suitability mask.
        currSuitMask  = None
      
      # Close and free landuse suitability raster.
      currSuitRaster.close()
      currSuitRaster = None

    # Close and free the cell area raster.
    areaRaster.close()
    areaRaster = None

    # Close and free the protected areas reduce factor raster.
    if not paReduceFactorRaster is None:
      paReduceFactorRaster.close()
      paReduceFactorRaster = None

    #-----------------------------------------------------------------------------
    # Resolve undefined areas, i.e. not-overlapping areas of regions and
    # not-allocatable areas.
    #-----------------------------------------------------------------------------

    Log.info("Resolving undefined areas...")

    # Select allocatable areas which are outside the regions.
    undefinedMask = (allocatableMask & (regionRaster.r == regionRaster.noDataValue))

    # Fill output with the undefined code.
    outRaster.r[undefinedMask] = landuseUndefinedCode

    # Free masks.
    allocatableMask = None
    undefinedMask = None

    # Close and free the region raster.
    regionRaster.close()
    regionRaster = None

    #-----------------------------------------------------------------------------
    # Resolve not-allocated areas, fill current land-use areas with replace code.
    #-----------------------------------------------------------------------------

    # Get replace land-use type.
    relaceLanduseType = self.getLanduseTypeByCode(landuseReplaceWithCode)
 
    Log.info("Resolve not-allocated areas, filling with '%s'..." % relaceLanduseType.name)

    # Reads the land-use raster and resizes to extent and resamples to cellsize.
    landuseRaster = self.readAndPrepareInRaster(extent,cellSize,landuseRasterName,"land-use")

    # Loop landuse types.
    for landuseCode in landuseReplaceCodes:
      # Select current land-use areas which are not allocated.
      notAllocatedMask = ((landuseRaster.r==landuseCode) & (outRaster.r == outRaster.noDataValue))
      # Fill output with land-use replace code.
      outRaster.r[notAllocatedMask] = landuseReplaceWithCode

    # Close and free the current land-use raster.
    landuseRaster.close()
    landuseRaster = None

    #-----------------------------------------------------------------------------
    # Resolve not-allocated areas, fill areas with land-cover.
    #-----------------------------------------------------------------------------

    Log.info("Resolve not-allocated areas, filling with land-cover...")

    # Reads the land-cover raster and resizes to extent and resamples to cellsize.
    landcoverRaster = self.readAndPrepareInRaster(extent,cellSize,landcoverRasterName,"land-cover")

    ########### FOR TESTING.
    self.dbgPrintArray("landcoverRaster",landcoverRaster.r)

    # Select areas which are not allocated.
    notAllocatedMask = (outRaster.r == outRaster.noDataValue)
    
    # Fill output with land-cover.
    outRaster.r[notAllocatedMask] = landcoverRaster.r[notAllocatedMask]

    # Close and free the land-cover raster.
    landcoverRaster.close()
    landcoverRaster = None

    #-----------------------------------------------------------------------------
    # Save the output raster.
    #-----------------------------------------------------------------------------

    # Save the output raster.
    Log.info("Writing %s..." % outRasterName)
    outRaster.write()

    ########### FOR TESTING.
    self.dbgPrintArray("output",outRaster.r)
         
    #-----------------------------------------------------------------------------
    # Calculate region/landuse areas.
    #-----------------------------------------------------------------------------

    # Need to calculte region/landuse areas?
    if self.isValueSet(outRegionLanduseAreasFileName):
      Log.info("Calculating region/landuse areas in km2...")
      self.calcRegionLanduseAreas(outRegionLanduseAreasFileName,
                                  landusePriorityCodes,
                                  regionRasterName,regionFilter,regionExcludeFilter,
                                  outRaster)
        
    #-----------------------------------------------------------------------------
    # Cleanup.
    #-----------------------------------------------------------------------------
           
    # Close and free the output raster.
    outRaster.close()
    outRaster = None

    # Show used memory and disk space.
    MON.showMemDiskUsage()

    self.showEndMsg()

  #-------------------------------------------------------------------------------
  # v2 : Nu met meer invoer uit ref. En uitvoer naar landalloc.
  # v7 : Kopie van test_v5_loop_v2.
  #      Nu met outVersion en outSubVersion.
  # v8 : Nu met land_alloc_vX.tif.
  #      Nu met areas in csv files.
  # v9 : Nu met semi-random noise.
  # v10: Zonder masked_array.
  # v11: Nu met eerst pa, dan add noise.
  #      Versie 4.0.5
  #      Andere claim dir.
  #      Nu met saveAreas en linux.
  # v12: Nu met areaRaster.
  #      Nu met addNoise vlag.
  #      Nu met landcoverRefVersion en regionRefVersion.
  # v12_1215: Nu met areaRaster.
  #      Gebruikt suit_20161214
  # v13: Nu met saveMemoryUsage.
  #      Nu met extra calc area vlaggen.
  #      addSemiRandomNoise aangepast.
  # v15: Nu met debug2.
  #      Nu met self.maskedArrays.
  # v16: Geen land-cover vulling voor pasture en forestry.
  # v17: Nu met landuseReplaceWithLandcoverCodes.
  #      Nu met claimAreaMultiplier per landuse-type.
  #      Nu met claimAreaMultipliers ipv. claimAreaMultiplier.
  #      Nu met regionCalculationClustersStr.
  # v18: Aangepast ivm. problemen met 10sec.
  #      Nu met sortKind.
  # v19: Opgeschoond.
  #      Nu met saveArrayToCSV.
  #      Nu met calc*_v19.
  #      Nu met debug1.
  #      PAReduceFactor is nu optioneel.
  #      Nu met nieuwe pa op basis van de fgdb.
  #      Nu met usePaReduceFactor.
  #      Nu met use10secAll.
  # v20: Opgeschoond.
  #      regionCalculationClustersStr verwijderd.
  #      Nu met landuseReplaceCodesStr.
  #      Nu met landuseReplaceWithCodeStr.
  # v20b:Opgeschoond.
  #      use10secAll verwijderd.
  #      usePaReduceFactorNew verwijderd.
  #      useSuitWithNoise verwijderd.
  #      saveAsReference added.
  def test_v20b(self):
        
    if not self.test:
      self.debug = False
      self.debugPrintArray = False
      self.debugResultArray = False
      
    #self.debug = True
    #GLOB.saveTmpData = True

    if self.debug:
      GLOB.SHOW_TRACEBACK_ERRORS = True

    #-----------------------------------------------------------------------------
    # SETTINGS.
    #-----------------------------------------------------------------------------
    
    #############################################
    outVersion = "20170316"

    # Bij 10sec wordt de oorspronkelijke esa tif gebruikt
    # en de 30sec region tif.
    landcoverRefVersion = "20170116"
    regionRefVersion = landcoverRefVersion
    paRefVersion = "20170118"
    suitRefVersion = "20170315"
    claimRefVersion = "20161214"

    # Output.
    cellSizeName = "30sec"
    extentName = "eu"
    GLOB.saveTmpData = False
    linux = True
    saveRegionAreas = False
    saveLandcoverAreas = False
    saveLanduseAreas = True
    landusePriorityCodesStr = "1|2|3|4"
    landuseReplaceCodesStr = "1|2|3|4"
    outSubVersionInt = 1
    claimAreaMultiplierLanduseCodes = [""]
    claimAreaMultipliers = [""]
    regionFilter = ""
    usePaReduceFactor = True
    addNoise = False
    saveAsReference = True

    outSubVersionInt = 2
    addNoise = True

    extentName = "wrld"
    outSubVersionInt = 1
    addNoise = False

    outSubVersionInt = 2
    addNoise = True

    cellSizeName = "10sec"
    extentName = "wrld"
    outSubVersionInt = 1
    addNoise = False

    outSubVersionInt = 2
    addNoise = True

    #-----------------------------------------------------------------------------
    # INPUT SETTINGS.
    #-----------------------------------------------------------------------------

    inCellSizeName = cellSizeName
    inExtentName = "wrld"

    #-----------------------------------------------------------------------------
    # OUTPUT SETTINGS.
    #-----------------------------------------------------------------------------

    if saveAsReference:
      outDirType = "referentie"
    else:
      outDirType = "out"
    outDirTemplate = r"G:\Data\Globio4LA\data\%s\v405\%s_%s\landalloc"

    #-----------------------------------------------------------------------------
    # Setting variables.
    #-----------------------------------------------------------------------------
    
    inLandcoverDir = r"G:\Data\Globio4LA\data\referentie\v405\%s_%s\in_%s" % (inCellSizeName,inExtentName,landcoverRefVersion)
    inRegionDir = r"G:\Data\Globio4LA\data\referentie\v405\%s_%s\in_%s" % (inCellSizeName,inExtentName,regionRefVersion)
    inClaimDir = r"G:\Data\Globio4LA\data\referentie\v405\lookup\in_%s" % (claimRefVersion)
    inSuitDir = r"G:\Data\Globio4LA\data\referentie\v405\%s_%s\suit_%s" % (inCellSizeName,inExtentName,suitRefVersion)
    inLanduseDir = inSuitDir
    inNotAllocDir = inLanduseDir
    inPaDir = r"G:\Data\Globio4LA\data\referentie\v405\%s_%s\in_%s" % (inCellSizeName,inExtentName,paRefVersion)
    areaDir = ""

    if cellSizeName == "10sec":
      # Gebruik originele esa landcover.
      inLandcoverDir = r"G:\Data\Globio4LA\data\web_20161104\esa"
      # Gebruik 30sec region.
      inRegionDir = r"G:\Data\Globio4LA\data\referentie\v405\30sec_wrld\in_%s" % (regionRefVersion)

#    # 10sec en 10sec pa en suit invoer? 
#    if (cellSizeName=="10sec") and (use10secAll):
#      inCellSizeName = "10sec"
#      suitRefVersion = "20170116"
#      paRefVersion = "20170118"
#      inSuitDir = r"G:\Data\Globio4LA\data\referentie\v405\%s_%s\suit_%s" % (inCellSizeName,inExtentName,suitRefVersion)
#      inLanduseDir = inSuitDir
#      inNotAllocDir = inSuitDir
#      inPaDir = r"G:\Data\Globio4LA\data\referentie\v405\%s_%s\in_%s" % (inCellSizeName,inExtentName,paRefVersion)

    # Linux?
    if linux:
      print("Linux")
      inLandcoverDir = self.toLinux(inLandcoverDir)
      inRegionDir = self.toLinux(inRegionDir)
      inClaimDir = self.toLinux(inClaimDir)
      inLanduseDir = self.toLinux(inLanduseDir)
      inNotAllocDir = self.toLinux(inNotAllocDir)
      inPaDir = self.toLinux(inPaDir)
      inSuitDir = self.toLinux(inSuitDir)
      outDirTemplate = self.toLinux(outDirTemplate)
      
    # Set extent and cellsize.
    try:
      extent = GLOB.constants[extentName].value
    except:
      pass
    if extentName == "braz":
      extent = [-80,-60,-30,10]
    cellSize = GLOB.constants[cellSizeName].value
      
    #for claimAreaMultiplier in claimAreaMultipliers:
    for i in range(len(claimAreaMultipliers)):

      claimAreaMultiplierLanduseCodesStr = claimAreaMultiplierLanduseCodes[i]
      claimAreaMultipliersStr = claimAreaMultipliers[i]
      
      outDir = outDirTemplate % (outDirType,cellSizeName,extentName)
      
      if outVersion != "":
        outDir = outDir + "_" + outVersion

      # Default settings for 30sec wrld.
      landuseCodesStr = "1|2|3|4|5|6"
      landuseNamesStr = "urban|crop|pasture|forestry|secondary vegetation|undefined"
      landcoverRasterName = "esa_lc_2010.tif"
      regionRasterName = "imgregions27.tif"
      regionExcludeFilter = ""
      landuseRasterName = "landcover_landuse.tif"
      landuseReplaceWithCodeStr = "5"
      landuseUndefinedCodeStr = "6"
      notAllocatableAreasRasterName = "not_allocatable_areas.tif"
      paReduceFactorRasterName = "pa_reduce_factor.tif"
      suitUrbanRasterName = "suit_urban.tif"
      suitCropRasterName = "suit_crop.tif"
      suitPastureRasterName = "suit_pasture.tif"
      suitForestryRasterName = "suit_forestry.tif"      
      claimFileName = "Claims_2050.csv"
      claimLanduseFieldName = "AggLUClass"
      claimRegionFieldName = "IMGREGCD"
      claimAreaFieldName = "totalArea"
      claimLookupFileName = "LanduseClassToLanduseType.csv"
      areaRasterName = ""
      if saveRegionAreas:
        outRegionAreasFileName = "regio_areas.csv"
        if outSubVersionInt > 0:
          outRegionAreasFileName = self.fileNameSetVersion(outRegionAreasFileName,outSubVersionInt)
      else:
        outRegionAreasFileName = ""
      if saveLandcoverAreas:
        outRegionLandcoverAreasFileName = "regio_landcover_areas.csv"
        if outSubVersionInt > 0:
          outRegionLandcoverAreasFileName = self.fileNameSetVersion(outRegionLandcoverAreasFileName,outSubVersionInt)
      else:
        outRegionLandcoverAreasFileName = ""
      if saveLanduseAreas:
        outRegionLanduseAreasFileName = "regio_landuse_areas.csv"
        if outSubVersionInt > 0:
          outRegionLanduseAreasFileName = self.fileNameSetVersion(outRegionLanduseAreasFileName,outSubVersionInt)
      else:
        outRegionLanduseAreasFileName = ""
      outRasterName = "landuse_alloc.tif"
      if outSubVersionInt > 0:
        # Set version.
        outRasterName = self.fileNameSetVersion(outRasterName,outSubVersionInt)

      # Modify settings for 10sec or eu.
      if cellSizeName == "10sec":
        landcoverRasterName = "ESACCI-LC-L4-LCCS-Map-300m-P5Y-2010-v1.6.1.tif"
      if extentName == "eu":
        regionExcludeFilter = "7|16|17"
      if extentName == "braz":
        regionExcludeFilter = "3|4|6"

      # Add paths.
      landcoverRasterName = os.path.join(inLandcoverDir,landcoverRasterName)
      regionRasterName = os.path.join(inRegionDir,regionRasterName)
      landuseRasterName = os.path.join(inLanduseDir,landuseRasterName)
      notAllocatableAreasRasterName = os.path.join(inNotAllocDir,notAllocatableAreasRasterName)
      if usePaReduceFactor:
        paReduceFactorRasterName = os.path.join(inPaDir,paReduceFactorRasterName)
      else:
        paReduceFactorRasterName = ""
      suitCropRasterName = os.path.join(inSuitDir,suitCropRasterName)
      suitPastureRasterName = os.path.join(inSuitDir,suitPastureRasterName)
      suitForestRasterName = os.path.join(inSuitDir,suitForestryRasterName)
      suitUrbanRasterName = os.path.join(inSuitDir,suitUrbanRasterName)
      claimFileName = os.path.join(inClaimDir,claimFileName)
      claimLookupFileName = os.path.join(inClaimDir,claimLookupFileName)
      if areaRasterName != "":
        areaRasterName = os.path.join(areaDir,areaRasterName)
      if outRegionAreasFileName != "":
        outRegionAreasFileName = os.path.join(outDir,outRegionAreasFileName)
      if outRegionLandcoverAreasFileName != "":
        outRegionLandcoverAreasFileName = os.path.join(outDir,outRegionLandcoverAreasFileName)
      if outRegionLanduseAreasFileName != "":
        outRegionLanduseAreasFileName = os.path.join(outDir,outRegionLanduseAreasFileName)
      outRasterName = os.path.join(outDir,outRasterName)
  
      # Concatenate suitability raster names.
      suitRasterCodesStr = "1|2|3|4"
      suitRasterNamesStr = "|".join([suitUrbanRasterName,suitCropRasterName,
                                     suitPastureRasterName,suitForestRasterName])
  
      # Create directory.
      if not os.path.isdir(outDir):
        os.makedirs(outDir)

      # Check output area files.
      for fileName in [outRegionAreasFileName,outRegionLandcoverAreasFileName,outRegionLanduseAreasFileName]:
        if (fileName != "") and (os.path.isfile(fileName)):
          os.remove(fileName)
  
      # Check output raster.
      if RU.rasterExists(outRasterName):
        RU.rasterDelete(outRasterName)
  
      # Run.
      self.run_v20(extent,cellSize,
                  landuseCodesStr,landuseNamesStr,
                  landusePriorityCodesStr,
                  landcoverRasterName,
                  regionRasterName,regionFilter,regionExcludeFilter,      
                  landuseRasterName,
                  landuseReplaceCodesStr,landuseReplaceWithCodeStr,landuseUndefinedCodeStr,
                  notAllocatableAreasRasterName,
                  paReduceFactorRasterName,
                  suitRasterCodesStr,suitRasterNamesStr,
                  claimFileName,claimLanduseFieldName,
                  claimRegionFieldName,claimAreaFieldName,
                  claimLookupFileName,
                  claimAreaMultiplierLanduseCodesStr,
                  claimAreaMultipliersStr,
                  areaRasterName,
                  addNoise,
                  outRegionAreasFileName,
                  outRegionLandcoverAreasFileName,
                  outRegionLanduseAreasFileName,
                  outRasterName)

      outSubVersionInt = outSubVersionInt + 1

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":

  #-------------------------------------------------------------------------------
  try:
    pCalc = GLOBIO_CalcDiscreteLanduseAllocation()
    #pCalc.test = True
    pCalc.test = False
    pCalc.test_v20b()
  except:
    Log.err()
