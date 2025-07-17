# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Calculates rasters with landuse for different resolutions.
#
# Modified: -
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
# Modified: 18 jan 2021, ES, ARIS B.V.
#           - Version 4.1.1
#           - Copy of GLOBIO_CalcDiscreteLanduseAllocation, modified for
#             Landuse Harmonization (LUH).
#
# TODO:     20210114
#           - Use of CalculationBase.createRegionMask().
#           - Use of CalculationBase.setRegionRasterFilter() (ie. setRegionRasterNoData).
#           - Use of CalculationBase.setRegionRasterExclude().
#-------------------------------------------------------------------------------

import os
import numpy as np

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
from GlobioModel.Common.Timer import Timer
import GlobioModel.Common.Utils as Utils

from GlobioModel.Core.Arguments import Arguments
from GlobioModel.Core.CalculationBase import CalculationBase
from GlobioModel.Core.CSVFile import CSVFile
from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU

from GlobioModel.LanduseAllocation.LanduseTypes import LanduseTypes

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_CalcDiscreteLanduseAllocation_V2(CalculationBase):
  """
  Calculates a discrete landuse allocation.
  """

  # Cell area version.
  cellAreaVersion = 2

  # List of landuse types (codes/names).
  landuseTypes = LanduseTypes()

  #-------------------------------------------------------------------------------
  def __init__(self):

    # Call parent __init__()    
    super(GLOBIO_CalcDiscreteLanduseAllocation_V2,self).__init__()

    self.nrCols = 0
    self.nrRows = 0
    self.maxSuitability = 1.0
    self.calcMaxSuitabilityFlag = False

    self.indent = "    "

    # For use in writeTmpRaster.
    self.year = 1000

    #-------------------------------------------------------------------------------
    # Set internal settings.    
    #-------------------------------------------------------------------------------

    self.mtimer = None

    self.debug = False
    #self.debug = True

    #self.debugPrintArray = True
    self.debugPrintArray = False

    self.debugResultArray = False

    self.debugPrintTestInfo1 = False
    
    self.debug1 = False
    self.debug2 = False
    self.debug3 = False
    self.debug4 = False
    self.maskedArrays = False
    
    self.showProgress = False
    #self.showProgress = True

    self.test = False

    #-------------------------------------------------------------------------------
    # Define sort method.
    #-------------------------------------------------------------------------------

    # quicksort,mergesort,heapsort
    #self.sortKind = "quicksort"
    self.sortKind = "mergesort"

  #-------------------------------------------------------------------------------
  # Calculates the semi random noise for the specified extent.
  # Using this method the resampled raster always has different cell values
  # compared with the not-resampled raster (wrld vs eu).
  # REMARK: This method takes less memory.
  def addSemiRandomNoise_NoResample_V2(self,extent,cellSize,
                                       suitRaster,randomRasterName,landuseCode,
                                       prefix):
    
    #---------------------------------------------------------------------------
    # Calculate minimum value.
    #---------------------------------------------------------------------------
    
    # Filter small values. Prevent stripes with pasture and forestry.
    minLimit = 1.0e-10

    # Get mask for cells which are no nodata.
    dataMask = (suitRaster.getDataMask() & (suitRaster.r > minLimit))

    # Are there no mask cells found?
    if not np.any(dataMask):
      Log.info("%sNo suitability cells found for landuse code %s." % (prefix,landuseCode))
      return

    # Get unique values and sort.
    uniqueArr = np.unique(suitRaster.r[dataMask])
    sortedArr = np.sort(uniqueArr)

    # Get the delta's.
    edgeArr = np.ediff1d(sortedArr)

    # Sort the delta's ascending.
    sortedEdgeArr = np.sort(edgeArr)

    # Get smallest delta.
    d = 1e-50

    #JH: Also randomize when suitability rasters consists of 0s and 1s only.
    if sortedEdgeArr.size==1:
      m = 1
    else:
      m = sortedEdgeArr[0] 
      if m < d:
        m = sortedEdgeArr[1] 

    # Calculate max delta.
    maxDelta = m * 0.9
         
    #---------------------------------------------------------------------------
    # Read semi-random noise raster.
    #---------------------------------------------------------------------------

    # Read the semi-random noise raster and resizes to extent.
    randomRaster = self.readAndPrepareInRaster_V2(extent,cellSize,
                                                  randomRasterName,"semi-random noise",
                                                  calcSumDiv=False,
                                                  prefix=prefix+"- ")

    # Randomize maxdelta.
    randomRaster.r *= maxDelta

    # Save temp raster?
    if GLOB.saveTmpData:
      tmpName = "tmp_random_"+str(landuseCode)+".tif"
      Log.info("%s- Writing random values: %s" % (prefix,tmpName))
      self.writeTmpRaster(randomRaster.r,tmpName)

    # Add noise to suitRaster.
    suitRaster.r += randomRaster.r

    # Cleanup.
    del randomRaster

  #-----------------------------------------------------------------------------
  # Checks regions and claims. Removes regions from the list with no claim.
  def checkRegionsAndClaims(self,regionList,landusePriorityCodes,prefix):
    # Copy all regions.
    notFoundRegions = regionList[:]
    # Loop landuse types.
    for landuseCode in landusePriorityCodes:
      # Get landuse type.
      landuseType = self.landuseTypes.getLanduseTypeByCode(landuseCode)
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
      Log.info("%sSkipping region '%s'. No region claims available!" % (prefix,region))
      # Remove from original list.
      if region in newRegionList:
        newRegionList.remove(region)
    # Return new list.
    return newRegionList

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
  # Bind the claim area to the landuse types.
  # The claimfile conatains: region,landuse,area.
  def setLanduseClaims_V2(self,claimFileName,claimFileNames,claimFileTypes):
    claimFile = CSVFile()
    claimFile.read(claimFileName,claimFileNames,claimFileTypes)
    regionFieldName = claimFileNames[0]
    landuseFieldName = claimFileNames[1]
    areaFieldName = claimFileNames[2]
    # Loop claimfile rows.
    for row in claimFile.rows:
      # Get the landuse code.
      landuseCode = row[landuseFieldName]
      # Get the landuse type.
      luType = self.landuseTypes.getLanduseTypeByCode(landuseCode)
      # Found?
      if not luType is None:
        # Add region and area.
        region = row[regionFieldName]
        area = row[areaFieldName]
        luType.claims[region] = area

  #-------------------------------------------------------------------------------
  # Bindt the suitability rasters to the landuse types.
  def setLanduseSuitabilityRasters(self,suitRasterCodes,suitRasterNames):
    # Loop suitability raster codes.
    for idx,landuseCode in enumerate(suitRasterCodes):
      # Get the landuse code.
      landuseCode = suitRasterCodes[idx]
      # Get the landuse type.
      luType = self.landuseTypes.getLanduseTypeByCode(landuseCode)
      # Found?
      if not luType is None:
        # Get raster name.
        rasName = suitRasterNames[idx]
        # Set the raster name.
        luType.suitRasterName = rasName

  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    """
    self.run_v25(*args)

  #-------------------------------------------------------------------------------
  # v20: Opgeschoond.
  #      regionCalculationClustersStr verwijderd.
  #      Nu met landuseReplaceCodesStr.
  #      Nu met landuseReplaceWithCodeStr.
  #      Nu met addRandomNoise_NoResample.
  # v21: Opgeschoond.
  #      Nu met LanduseTypes.
  #      Nu met landcoverRasterName als optional.
  #      Nu met landuseRasterName als optional.
  #      Nu met notAllocatableAreasRasterName als optional.
  #      Nu met paReduceFactorRasterName als optional.
  #      Nu met cellAreaKM2Dir.
  #      Nu met semiRandomNoiseDir, wel optional.
  #      Zonder showStartMsg etc.
  # v22: Opgeschoond.
  #      Nu met year (nodig voor wegschrijven tmpdata).
  # v23: resolveLandcoverNotAllocatedAreas code verwijderd.
  #      resolveLanduseNotAllocatedAreas code verwijderd.
  #      resolveUndefinedAreas code verwijderd.
  #      outRegionAreasFileName etc. verwijderd.
  #      calcRegionAreas etc. code verwijderd.
  # v24: Met area/noise rastername.
  # v25: Now using Arguments.
  #      YearStr verwijderd.
  #
  # OPM:
  #      LandcoverRaster - nodig voor uitvoer tabel.
  #      LanduseRaster - nodig voor uitvoer tabel.
  #      LandcoverRaster - nodig voor opvullen @@@.
  #      LanduseRaster - nodig voor opvullen @@@.
  def run_v25(self,*args):

    # Show start message.
    #self.showStartMsg(args)

    # Create argument checker.
    pArgs = Arguments(args)

    # Get arguments.
    extent = pArgs.next()
    cellSize = pArgs.next()
    landuseCodesStr = pArgs.next()
    landuseNamesStr = pArgs.next()
    landusePriorityCodesStr = pArgs.next()
    landcoverRasterName = pArgs.next()
    regionRasterName = pArgs.next()
    regionFilterStr = pArgs.next()
    regionExcludeFilterStr = pArgs.next()
    landuseRasterName = pArgs.next()
    landuseReplaceCodesStr = pArgs.next()
    landuseReplaceWithCodeStr = pArgs.next()
    landuseUndefinedCodeStr = pArgs.next()
    notAllocatableAreasRasterName = pArgs.next()
    paReduceFactorRasterName = pArgs.next()
    suitRasterCodesStr = pArgs.next()
    suitRasterNamesStr = pArgs.next()
    claimFileName = pArgs.next()
    claimLanduseFieldName = pArgs.next()
    claimRegionFieldName = pArgs.next()
    claimAreaFieldName = pArgs.next()
    claimLookupFileName = pArgs.next()
    claimAreaMultiplierLanduseCodesStr = pArgs.next()
    claimAreaMultipliersStr = pArgs.next()
    cellAreaKM2RasterName = pArgs.next()
    semiRandomNoiseRasterName = pArgs.next()
    outRasterName = pArgs.next()

    # Check number of arguments.
    pArgs.check(self.name)

    # Check arguments.
    self.checkExtent(extent)
    if cellSize > 0:
      self.checkCellSize(cellSize)
    self.checkIntegerList(landuseCodesStr)
    self.checkListCount(landuseNamesStr,landuseCodesStr,"landuse names")
    self.landuseTypes.init(landuseCodesStr,landuseNamesStr)
    self.landuseTypes.checkLanduseCodes(landusePriorityCodesStr,
                           Err.NoLandusePriorityCodesSpecified,
                           Err.InvalidLandusePriorityCode1)

    self.checkRaster(landcoverRasterName,optional=True)

    self.checkRaster(regionRasterName)
    self.checkIntegerList(regionFilterStr,optional=True)
    self.checkIntegerList(regionExcludeFilterStr,optional=True)

    self.checkRaster(landuseRasterName,optional=True)

    self.landuseTypes.checkLanduseCodes(landuseReplaceCodesStr,
                           Err.NoLanduseReplaceCodesSpecified,
                           Err.InvalidLanduseReplaceCodes1)
    self.landuseTypes.checkLanduseCodes(landuseReplaceWithCodeStr,
                           Err.NoLanduseReplaceWithCodeSpecified,
                           Err.InvalidLanduseReplaceWithCode1)
    self.landuseTypes.checkLanduseCodes(landuseUndefinedCodeStr,
                           Err.NoLanduseUndefinedCodeSpecified,
                           Err.InvalidLanduseUndefinedCode1)

    self.checkRaster(notAllocatableAreasRasterName,optional=True)
    self.checkRaster(paReduceFactorRasterName,optional=True)

    self.landuseTypes.checkLanduseCodes(suitRasterCodesStr,
                           Err.NoSuitabilityRasterCodesSpecified,
                           Err.InvalidSuitabilityRasterCode1)
    self.checkListCount(suitRasterNamesStr,suitRasterCodesStr,"rasters")
    self.checkRasterList(suitRasterNamesStr)
    self.checkFile(claimFileName)
    self.checkFieldName(claimLanduseFieldName,"landuse")
    self.checkFieldName(claimRegionFieldName,"region")
    self.checkFieldName(claimAreaFieldName,"area")
    self.checkFile(claimLookupFileName,optional=True)
    self.landuseTypes.checkLanduseCodes(claimAreaMultiplierLanduseCodesStr,
                           Err.NoClaimAreaMultiplierLanduseCodesSpecified,
                           Err.InvalidClaimAreaMultiplierLanduseCode1,optional=True)
    self.checkListCount(claimAreaMultipliersStr,claimAreaMultiplierLanduseCodesStr,"claim area multipliers")
    self.checkFloatList(claimAreaMultipliersStr,optional=True)
    self.checkRaster(cellAreaKM2RasterName)
    self.checkRaster(semiRandomNoiseRasterName,optional=True)
    self.checkRaster(outRasterName,asOutput=True)

    # Convert code and names to arrays.
    #self.year = int(yearStr)
    landusePriorityCodes = self.splitIntegerList(landusePriorityCodesStr)
    regionFilter = self.splitIntegerList(regionFilterStr)
    suitRasterCodes = self.splitIntegerList(suitRasterCodesStr)
    suitRasterNames = self.splitStringList(suitRasterNamesStr)
    claimAreaMultiplierLanduseCodes = self.splitIntegerList(claimAreaMultiplierLanduseCodesStr)
    claimAreaMultipliers = self.splitFloatList(claimAreaMultipliersStr)

    #-----------------------------------------------------------------------------
    # 2021 - Only 1 region is allowed!!!
    #-----------------------------------------------------------------------------
    if len(regionFilter)!=1:
      Err.raiseGlobioError(Err.UserDefined1,
                           "DiscreteLanduseAllocation: Only 1 regions is allowed, %s given." % len(regionFilter))

    # Align extent.
    extent = RU.alignExtent(extent,cellSize)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.nrCols,self.nrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)
    self.outDir = os.path.dirname(outRasterName)

    # Enable monitor en show memory and disk space usage.
    #MON.showMemDiskUsage(Log,"- ","",self.outDir)

    #-----------------------------------------------------------------------------
    # Set the landuse type suitability raster names.
    #-----------------------------------------------------------------------------

    Log.info("%sSetting landuse suitablity info..." % self.indent)

    # Update landuse types with suitablity codes and rasters.
    self.setLanduseSuitabilityRasters(suitRasterCodes,suitRasterNames)

    #-----------------------------------------------------------------------------
    # Read the landuse claims and set the landuse type claims.
    #-----------------------------------------------------------------------------

    Log.info("%sSetting landuse claims..." % self.indent)

    # Set the landuse claims.
    claimFieldNames = [claimRegionFieldName,claimLanduseFieldName,claimAreaFieldName]
    claimFieldTypes = ["I","I","F"]
    self.setLanduseClaims_V2(claimFileName,claimFieldNames,claimFieldTypes)

    ### DEBUG
    if self.debug:
      Log.dbg("#LanduseTypes:")
      self.landuseTypes.show()

    #-----------------------------------------------------------------------------
    # Recalulate landuse type claims.
    #-----------------------------------------------------------------------------

    # Increase or decrease claim area?
    if self.isValueSet(claimAreaMultipliers):
      Log.info("%sRecalculating landuse claims..." % self.indent)
      self.landuseTypes.recalculateClaims(claimAreaMultiplierLanduseCodes,claimAreaMultipliers)

    #-----------------------------------------------------------------------------
    # Read the not-allocatable areas raster and prepare.
    #-----------------------------------------------------------------------------

    if self.isValueSet(notAllocatableAreasRasterName):
      # Reads the not-allocatable areas raster and resizes to extent and resamples to cellsize.
      notAllocRaster = self.readAndPrepareInRaster_V2(extent,cellSize,
                                                      notAllocatableAreasRasterName,
                                                      "not-allocatable areas",calcSumDiv=False,
                                                      prefix= self.indent)

      ########### FOR TESTING.
      self.writeTmpRaster(notAllocRaster,"tmp_not_alloc.tif","- Writing not-allocatable areas")

      #-----------------------------------------------------------------------------
      # Create allocatable areas mask.
      #-----------------------------------------------------------------------------

      Log.info("%sCreating allocatable areas mask..." % self.indent)

      # Select allocatable areas, so where not-allocatable cells are not 1.
      allocatableMask = (notAllocRaster.r != 1)

      # Check allocatable mask.
      if np.sum(allocatableMask) == 0:
        Log.info("%s  No allocatable areas found." % self.indent)
        exit(0)

      ########### FOR TESTING.
      if GLOB.saveTmpData:
        allocMaskRaster = Raster()
        allocMaskRaster.initRasterLike(notAllocRaster,False,np.uint8)
        allocMaskRaster.r = allocatableMask
        self.writeTmpRaster(allocMaskRaster,"tmp_allocmask.tif","- Writing allocatable mask")
        del allocMaskRaster

      # Free not-allocatable areas raster.
      del notAllocRaster
    else:
      allocatableMask = None

    #-----------------------------------------------------------------------------
    # Read the protected areas raster and prepare.
    #-----------------------------------------------------------------------------

    # Need to use protected areas raster?
    if self.isValueSet(paReduceFactorRasterName):

      # Reads the protected areas raster and resizes to extent and resamples to cellsize.
      # High protection is 0.0, no protection is 1.0.
      paReduceFactorRaster = self.readAndPrepareInRaster_V2(extent,cellSize,
                                                            paReduceFactorRasterName,
                                                            "protected areas reduce factor",
                                                            calcSumDiv=False,
                                                            prefix=self.indent)

      ########### FOR TESTING.
      self.writeTmpRaster(paReduceFactorRaster,"tmp_pa_red_factor.tif","- Writing protected areas")
    else:
      paReduceFactorRaster = None

    #-----------------------------------------------------------------------------
    # Read the regions raster and prepare.
    #-----------------------------------------------------------------------------

    # Reads the regions raster and resizes to extent and resamples to cellsize.
    regionRaster = self.readAndPrepareInRaster_V2(extent,cellSize,regionRasterName,
                                                  "region",calcSumDiv=False,
                                                  prefix=self.indent)
    # Set region list.
    regionList = regionFilter

    #-----------------------------------------------------------------------------
    # Check regions and claims.
    #-----------------------------------------------------------------------------

    # Remove regions with no claim.
    Log.info("%sChecking regions and claims..." % self.indent)
    regionList = self.checkRegionsAndClaims(regionList,landusePriorityCodes,prefix=self.indent)

    #Log.info("%sUsing regions: %s" % (self.indent,regionList))

    ########### FOR TESTING.
    if GLOB.saveTmpData:
      region = regionList[0]
      tmpRegionRaster = Raster()
      tmpRegionRaster.initRasterLike(regionRaster,0)
      tmpMask = (regionRaster.r==region)
      tmpRegionRaster.r[tmpMask] = regionRaster.r[tmpMask]
      self.writeTmpRaster(tmpRegionRaster,"tmp_region_%s.tif" % region,"- Writing region raster")
      del tmpMask
      del tmpRegionRaster

    #-----------------------------------------------------------------------------
    # Read the area raster.
    #-----------------------------------------------------------------------------

    # Read the cell area raster.
    areaRaster = self.readAndPrepareInRaster_V2(extent,cellSize,
                                                cellAreaKM2RasterName,"areas",
                                                calcSumDiv=True,
                                                prefix=self.indent)

    ########### FOR TESTING.
    self.writeTmpRaster(areaRaster,"tmp_areas.tif","- Writing areas")

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
      landuseType = self.landuseTypes.getLanduseTypeByCode(landuseCode)

      # No suitability rastername, then skip.
      if landuseType.suitRasterName == "":
        continue

      # Show progress.
      if self.showProgress:
        Log.info("%sProcessing %s (%s)..." % (self.indent,landuseType.name,landuseType.code))

      # Reads the regions raster and resizes to extent and resamples to cellsize.
      currSuitRaster = self.readAndPrepareInRaster_V2(extent,cellSize,
                                                      landuseType.suitRasterName,
                                                      landuseType.name + " suitability",
                                                      calcSumDiv=False,
                                                      prefix=self.indent+"- ")

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
        Log.info("%s- Adding protected areas..." % self.indent)
        currSuitRaster.r *= paReduceFactorRaster.r

        ########### FOR TESTING.
        self.dbgPrintMinMaxNoData(currSuitRaster,"suitability*pa")
        self.dbgPrintArray("currSuitRaster*pa",currSuitRaster.r)
        self.writeTmpRaster(currSuitRaster,"tmp_suitprot_%s.tif" % landuseCode,
                            "- Writing landuse suitability with pa")

      #-----------------------------------------------------------------------------
      # Add semi-random noise (in the  protected areas too).
      #-----------------------------------------------------------------------------

      # Need to add semi-random noise?
      if self.isValueSet(semiRandomNoiseRasterName):
        # Add noise.
        Log.info("%s- Adding semi-random noise..." % self.indent)
        self.addSemiRandomNoise_NoResample_V2(extent,cellSize,
                                              currSuitRaster,
                                              semiRandomNoiseRasterName,
                                              landuseCode,prefix=self.indent)

        ########### FOR TESTING.
        self.dbgPrintMinMaxNoData(currSuitRaster,"suitability+noise")
        self.dbgPrintArray("currSuitRaster+noise",currSuitRaster.r)
        self.writeTmpRaster(currSuitRaster,"tmp_suitprot_%s.tif" % landuseCode,
                            "- Writing landuse suitability with pa and noise")

      #-----------------------------------------------------------------------------
      # Loop regions.
      #-----------------------------------------------------------------------------
      for region in regionList:

        # Show progress.
        if self.showProgress:
          Log.info("%s- Processing region %s..." % (self.indent,region))

        #-----------------------------------------------------------------------------
        # Check region claim.
        #-----------------------------------------------------------------------------
        if not region in landuseType.claims:
          Log.info("%s    Skipping region '%s'. No region claim available for '%s'!" %
                                  (self.indent,region,landuseType.name))
          continue

        #-----------------------------------------------------------------------------
        # Select the cells which are allocatable for the current landuse type.
        #-----------------------------------------------------------------------------

        #-----------------------------------------------------------------------------
        # Select current region.
        #-----------------------------------------------------------------------------

        # Select the cells in the current region.
        currSuitMask = (regionRaster.r == region)

        # Check regions.
        if np.sum(currSuitMask) == 0:
          Log.info("%s    No region cels found." % self.indent)
          continue

        ########### FOR TESTING.
        self.dbgPrintArray("currSuitMask - region",currSuitMask)

        #-----------------------------------------------------------------------------
        # Select allocatable cells.
        #-----------------------------------------------------------------------------

        if not allocatableMask is None:

          # Refine region mask with allocatable cells.
          currSuitMask = np.logical_and(currSuitMask,allocatableMask)

          # Check allocatable cells.
          if np.sum(currSuitMask) == 0:
            Log.info("%s    No allocatable cells in regio found." % self.indent)
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
          Log.info("%s    No free cells in regio found." % self.indent)
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
        currSuitSortIds = np.argsort(selectedCurrSuitRas,kind=self.sortKind)

        ########### FOR TESTING.
        self.dbgPrintArray("currSuitSortIds",currSuitSortIds)
        self.dbgPrintArray("selectedCurrSuitRas[currSuitSortIds]",selectedCurrSuitRas[currSuitSortIds])
        self.dbgPrintArray("selectedCurrSuitRas[currSuitSortIds[-20:]]",selectedCurrSuitRas[currSuitSortIds[-20:]])

        # Cleanup maskedCurrSuitRas.
        del selectedCurrSuitRas

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

        Log.info("%s   Current claim for region is %s" % (self.indent,currClaim))

        # Get the index of the cell which claim area <= cum area.
        insertIdx = np.searchsorted(cumAreaRas,currClaim,side='right')

        ########### FOR TESTING.
        self.dbgPrintTestInfo1(currClaim,insertIdx,cumAreaRas,currSuitSortIds,selectedAreaRas)

        # Calculate the total area and report whether the claim is fully allocated.
        totAreaRas = np.sum(selectedAreaRas[currSuitSortIds],dtype=cumsumDataType)
        if totAreaRas>=currClaim:
          Log.info("%s   100%% of claim is allocated."  % self.indent)
        else:
          Log.info("%s   Only %s%% of claim is allocated" % (self.indent,round((totAreaRas/currClaim*100),1)))

        # Free landuse cumulative area's.
        del cumAreaRas

        # Free masked area's.
        del selectedAreaRas

        #-----------------------------------------------------------------------------
        # Create masked output array.
        #-----------------------------------------------------------------------------

        # Select output cells.
        selectedOutRas = outRaster.r[currSuitMask]

        ########### FOR TESTING.
        self.dbgPrintArray("selectedOutRas",selectedOutRas)

        # Update output raster with landuse.
        selectedOutRas[currSuitSortIds[:insertIdx]] = landuseType.code

        ########### FOR TESTING.
        self.dbgPrintArray("maskedOutRas code",selectedOutRas)

        # Update output raster.
        outRaster.r[currSuitMask] = selectedOutRas

        # Free sorted ids.
        del currSuitSortIds

        # Free suitability mask.
        del currSuitMask

      # Close and free landuse suitability raster.
      del currSuitRaster

    # Close and free the cell area raster.
    del areaRaster

    # Close and free the protected areas reduce factor raster.
    if not paReduceFactorRaster is None:
      del paReduceFactorRaster

    #-----------------------------------------------------------------------------
    # Save the output raster.
    #-----------------------------------------------------------------------------

    # Save the output raster.
    Log.info("%s- Writing %s..." % (self.indent,outRasterName))
    outRaster.write()

    ########### FOR TESTING.
    self.dbgPrintArray("output",outRaster.r)

    # Cleanup.
    del outRaster

    # Show used memory and disk space.
    #MON.showMemDiskUsage()
