# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Calculates rasters with harmonized landuse for different years.
#
# Modified: -
#-------------------------------------------------------------------------------

import os
import numpy as np
import scipy.ndimage

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

from GlobioModel.Core.Arguments import Arguments
from GlobioModel.Core.CalculationBase import CalculationBase
from GlobioModel.Core.CSVFile import CSVFile
from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU
import GlobioModel.Core.RegionUtils as RGU

import GlobioModel.Common.Utils as UT

from GlobioModel.LanduseAllocation.LanduseTypes import LanduseTypes

from GlobioModel.LanduseHarmonization.GLOBIO_CalcDiscreteLanduseAllocation_V2 import GLOBIO_CalcDiscreteLanduseAllocation_V2

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_CalcLanduseHarmonization(CalculationBase):
  """
  Calculates rasters with harmonized landuse for different years.
  """

  # Cell area version.
  cellAreaVersion = 2

  claimRegionFieldName = "region"
  claimLanduseFieldName = "landuse"
  claimAreaFieldName = "area_km2"
  claimLandcoverFieldName = "landcover"
  claimFieldNames = [claimRegionFieldName,claimLanduseFieldName,claimAreaFieldName]
  claimFieldTypes = ["I","I","F"]

  claimLookupFileName = None
  claimAreaMultiplierLanduseCodesStr = ""
  claimAreaMultipliersStr = ""

  # List of landuse types (codes/names).
  landuseTypes = LanduseTypes()

  #-------------------------------------------------------------------------------
  def __init__(self):

    # Call parent __init__()
    super(GLOBIO_CalcLanduseHarmonization,self).__init__()

    self.debugPrintArray = False

  #-------------------------------------------------------------------------------
  # Calculates the harmonized claims.
  # Returns a list of region;landuse;claim.
  #
  # TODO: LETOP: Ref. claim niet gevonden, dan 0!!!
  def calcHarmonizedClaims(self,refClaims,imgClaims,imgPrevClaims):

    if refClaims.index is None:
      refClaims.createIndex()
    if imgPrevClaims.index is None:
      imgPrevClaims.createIndex()

    # Process claims year.
    keys = []
    lines = []
    for row in imgClaims.rows:
      # Get row values.
      region_lu = row.getKeyValues()
      imgArea = row.getValue()
      # Get ref. claim.
      refArea = refClaims.getValue(*region_lu)
      # Ref. claim found?
      if not refArea is None:
        imgPrevArea = imgPrevClaims.getValue(*region_lu)
        if imgPrevArea is None:
          imgPrevArea = 0.0
        # Calculate and append.
        harmArea = refArea + (imgArea - imgPrevArea)
        keys.append(region_lu)
        line = "%s;%s;%s" % (region_lu[0],region_lu[1],harmArea)
        lines.append(line)

    # Process claims previous year.
    for row in imgPrevClaims.rows:
      # Get key.
      region_lu = row.getKeyValues()
      imgPrevArea = row.getValue()
      # Already processed?
      if region_lu in keys:
        continue
      # Get ref. claim.
      refArea = refClaims.getValue(*region_lu)
      # Ref. claim found?
      if not refArea is None:
        imgArea = 0.0
        # Calculate and append.
        harmArea = refArea + (imgArea - imgPrevArea)
        lines.append("%s;%s;%s" % (region_lu[0],region_lu[1],harmArea))

    return lines

  #-------------------------------------------------------------------------------
  # Convertes IMAGE claim rasters with fractions to claims per region
  # per GLOBIO landuse type.
  # Returns a list of region;landuse;claim.
  def calcImageClaims(self,extent,cellSize,year,
                           regions,regionRasterName,
                           globioLandusePriorityCodes,
                           globioLanduseCodes,
                           globioLanduseNames,
                           imgClaimsRasterName,
                           imgLanduseNames,
                           cellAreaRasterName,
                           prefix=""):

    # TODO: Let op, leest de hele region raster. Per region inlezen?

    # Read the region raster and resizes to extent and resamples to cellsize.
    regionRaster = self.readAndPrepareInRaster_V2(extent,cellSize,
                                                  regionRasterName,"regions",
                                                  calcSumDiv=False,
                                                  prefix=prefix)

    # Read the cell area raster.
    areaRaster = self.readAndPrepareInRaster_V2(extent,cellSize,
                                                cellAreaRasterName,"areas",
                                                calcSumDiv=True,
                                                prefix=prefix)

    # Create a list for the claims.
    regionLanduseClaims = []

    # Loop the landuse code which need to be allocated.
    for globioLandusePriorityCode in globioLandusePriorityCodes:

      # Get the according code index.
      idx = globioLanduseCodes.index(globioLandusePriorityCode)

      # Get the globio landuse code/name and image landuse name.
      globioLanduseCode = globioLanduseCodes[idx]
      globioLanduseName = globioLanduseNames[idx]
      imgLanduseName = imgLanduseNames[idx]

      Log.info(prefix+"Calculating landuse claims: glo:%s / img:%s" %
                                 (globioLanduseName,imgLanduseName))

      #print(imgClaimsRasterName)
      #print(RU.isNetCDFName)

      # Do we have a NETCDF raster name?
      if RU.isNetCDFName(imgClaimsRasterName):
        # Create the full NetCDF raster name.
        fullImgClaimsRasterName = imgClaimsRasterName
        fullImgClaimsRasterName += "|%s|%s" % (year,imgLanduseName)
      else:
        # We have a template TIF raster name.
        if imgClaimsRasterName.find("#") >= 0:
          imgClaimsRasterName = UT.strBefore(imgClaimsRasterName,"#")
        fullImgClaimsRasterName = imgClaimsRasterName.format(year,globioLanduseCode)

      # Read the claim raster and resizes to extent and resamples to cellsize.
      # The data should ALWAYS have a global coverage!!!
      imgClaimRaster = self.readAndPrepareInRaster_V2(extent,cellSize,
                                                      fullImgClaimsRasterName,
                                                      "IMAGE claims",
                                                      calcSumDiv=True,
                                                      silent=True,
                                                      prefix="    - ")

      #---------------------------------------------------------------------------
      # Calculate the IMAGE landuse claims in km2.
      #   claims = img_claims * area
      #---------------------------------------------------------------------------

      # Get the cells with data.
      mask = imgClaimRaster.getDataMask()

      # Calculate the claim in km2 for cells with data.
      imgClaimRaster.r[mask] *= areaRaster.r[mask]

      # Cleanup.
      del mask

      #---------------------------------------------------------------------------
      # Collect landcover claims (km2) per region.
      #---------------------------------------------------------------------------

      # Calculate sum of claims (km2) per region.
      claimSum = scipy.ndimage.labeled_comprehension(imgClaimRaster.r,
                                                     regionRaster.r,
                                                     regions,
                                                     np.sum,np.float64,0)

      self.dbgPrintArray("claimSum",claimSum)

      # Make equal length.
      landuseCodes = len(regions) * [globioLanduseCode]

      # Combine regions and claims in an array of region/claim tuples and add.
      regLanduseClaims = list(zip(regions,landuseCodes,claimSum))
      regionLanduseClaims.extend(regLanduseClaims)
      #Log.dbg("    %s" % (regLanduseClaims,))

      # Cleanup.
      del imgClaimRaster

    # Cleanup.
    del regionRaster
    del areaRaster

    # Convert tuples to lines of region;landuse;area_km2.
    lines = [";".join(self.claimFieldNames)]
    for regionLanduseClaim in regionLanduseClaims:
      lines.append("{};{};{}".format(*regionLanduseClaim))

    return lines

  #-------------------------------------------------------------------------------
  # Creates a file with harmonized claims.
  # TODO: LETOP: Ref. claim niet gevonden, dan 0!!!
  def createHarmonizedClaimsFile(self,refClaims,
                                 imgClaimsFileName,imgPrevClaimsFileName,
                                 harmonizedClaimsFileName):

    # Read the image claims.
    imgClaims = CSVFile()
    imgClaims.read(imgClaimsFileName,self.claimFieldNames,self.claimFieldTypes)

    # Read the image claims of previous year.
    imgPrevClaims = CSVFile()
    imgPrevClaims.read(imgPrevClaimsFileName,self.claimFieldNames,self.claimFieldTypes)

    # Calculate harmonized claims.
    harmonizedClaims = self.calcHarmonizedClaims(refClaims,
                                                 imgClaims,
                                                 imgPrevClaims)
    # Insert header.
    harmonizedClaims.insert(0,";".join(self.claimFieldNames))
    # Write to disk.
    UT.fileWrite(harmonizedClaimsFileName,harmonizedClaims)

  #-------------------------------------------------------------------------------
  def getAllocatedLanduseRasterName(self,year):
    rasterName = "alloc_landuse_%s.tif" % year
    rasterName = os.path.join(self.outDir,rasterName)
    return rasterName

  #-------------------------------------------------------------------------------
  def getAllocatedLanduseRegionRasterName(self,year,region):
    rasterName = "alloc_landuse_%s_%s.tif" % (year,region)
    rasterName = os.path.join(self.outDir,rasterName)
    return rasterName

  #-------------------------------------------------------------------------------
  def getAllocatedRegionLanduseAreasFileName(self,year):
    fileName = "alloc_regions_landuse_areas_%s.csv" % year
    fileName = os.path.join(self.outDir,fileName)
    return fileName

  #-------------------------------------------------------------------------------
  def getHarmonizedClaimsFileName(self,year):
    fileName = "harmonized_claims_%s.csv" % year
    fileName = os.path.join(self.outDir,fileName)
    return fileName

  #-------------------------------------------------------------------------------
  def getImageClaimsFileName(self,year):
    fileName = "image_claims_%s.csv" % year
    fileName = os.path.join(self.outDir,fileName)
    return fileName

  #-------------------------------------------------------------------------------
  def getRegionAreasFileName(self):
    fileName = "regions_areas.csv"
    fileName = os.path.join(self.outDir,fileName)
    return fileName

  #-------------------------------------------------------------------------------
  def getRegionLandcoverAreasFileName(self):
    fileName = "regions_landcover_areas.csv"
    fileName = os.path.join(self.outDir,fileName)
    return fileName

  #-------------------------------------------------------------------------------
  def getRegionLanduseAreasFileName(self):
    fileName = "regions_landuse_areas.csv"
    fileName = os.path.join(self.outDir,fileName)
    return fileName

  #-------------------------------------------------------------------------------
  def getTotalSuitabilityRasterName(self,region: int):
    rasterName = "total_suitability_%s.tif" % region
    rasterName = os.path.join(self.outDir,rasterName)
    return rasterName

  #-------------------------------------------------------------------------------
  # Resolve not-allocated areas, fill current landuse areas with replace code.
  def resolveLanduseNotAllocatedAreas(self,regionMask: [bool],
                                      landuseRaster: Raster,
                                      landuseReplaceCodes: [int],
                                      landuseReplaceWithCode: [int],
                                      outRaster: Raster):
    # Loop landuse types.
    for landuseCode in landuseReplaceCodes:
      # Select current landuse areas which are not allocated.
      notAllocatedMask = regionMask & \
                         ((landuseRaster.r==landuseCode) &
                         (outRaster.r == outRaster.noDataValue))
      # Fill output with landuse replace code.
      outRaster.r[notAllocatedMask] = landuseReplaceWithCode
    del notAllocatedMask

  #-------------------------------------------------------------------------------
  # Resolve not-allocated areas, fill areas with landcover.
  def resolveLandcoverNotAllocatedAreas(self,landcoverRaster: Raster,
                                        outRaster: Raster):
    # Select areas which are not allocated.
    notAllocatedMask = (outRaster.r == outRaster.noDataValue)
    # Fill output with landcover.
    outRaster.r[notAllocatedMask] = landcoverRaster.r[notAllocatedMask]

  #-------------------------------------------------------------------------------
  # Resolve undefined areas, i.e. not-overlapping areas of regions and
  # not-allocatable areas.
  # regionMask: mask of valid/actual regions.
  def resolveUndefinedAreas(self,regionMask: [bool],
                            landuseUndefinedCode: int,
                            outRaster: Raster):
    # Fill areas outside regions with the undefined code.
    outRaster.r[~regionMask] = landuseUndefinedCode

  #-------------------------------------------------------------------------------
  # Calculates and writes region allocated landuse areas for a year.
  def writeRegionAllocLanduseAreas(self,regionRaster: Raster,
                                   cellAreaRaster: Raster,
                                   allocLanduseRaster: Raster,
                                   regions: [int],
                                   outFileName: str,prefix: str="  "):
    fieldNames = [self.claimRegionFieldName,
                  self.claimLanduseFieldName,self.claimAreaFieldName]
    RGU.writeRegionLanduseAreas(regionRaster,cellAreaRaster,
                                allocLanduseRaster,regions,
                                fieldNames,outFileName,prefix=prefix)

  #-------------------------------------------------------------------------------
  # Calculates and writes region areas.
  def writeRegionAreas(self,regionRaster: Raster,
                       cellAreaRaster: Raster,
                       regions: [int]):
    # Set areas filename and check.
    areasFileName = self.getRegionAreasFileName()
    self.checkFile(areasFileName,asOutput=True)
    # Calculate and write areas.
    fieldNames = [self.claimRegionFieldName,self.claimAreaFieldName]
    RGU.writeRegionAreas(regionRaster,cellAreaRaster,
                         regions,fieldNames,areasFileName)

  #-------------------------------------------------------------------------------
  # Calculates and writes region landcover areas.
  def writeRegionLandcoverAreas(self,regionRaster: Raster,
                                cellAreaRaster: Raster,
                                landcoverRaster: Raster,
                                regions: [int],
                                prefix: str="  "):
    # Set areas filename and check.
    areasFileName = self.getRegionLandcoverAreasFileName()
    self.checkFile(areasFileName,asOutput=True)
    # Calculate and write areas.
    fieldNames = [self.claimRegionFieldName,self.claimLandcoverFieldName,
                  self.claimAreaFieldName]
    RGU.writeRegionLandcoverAreas(regionRaster,cellAreaRaster,
                                  landcoverRaster,
                                  regions,fieldNames,areasFileName,
                                  prefix=prefix)

  #-------------------------------------------------------------------------------
  # Calculates and writes region landuse areas.
  def writeRegionLanduseAreas(self,regionRaster: Raster,
                              cellAreaRaster: Raster,
                              landuseRaster: Raster,
                              regions: [int],
                              prefix: str="  "):
    # Set areas filename and check.
    areasFileName = self.getRegionLanduseAreasFileName()
    self.checkFile(areasFileName,asOutput=True)
    # Calculate and write areas.
    fieldNames = [self.claimRegionFieldName,self.claimLanduseFieldName,
                  self.claimAreaFieldName]
    RGU.writeRegionLanduseAreas(regionRaster,cellAreaRaster,
                                  landuseRaster,
                                  regions,fieldNames,areasFileName,
                                  prefix=prefix)

  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN STRING Years
    IN RASTER Regions
    IN STRING RegionFilter
    IN STRING RegionExcludeFilter
    IN RASTER Landcover
    IN RASTER Landuse
    IN STRING LanduseCodes
    IN STRING LanduseNames
    IN STRING LandusePriorityCodes
    IN STRING LanduseReplaceCodes
    IN STRING LanduseReplaceWithCode
    IN STRING LanduseUndefinedCode
    IN FILE ReferenceClaims
    IN RASTER ImageClaims
    IN STRING ImageLanduseNames
    IN RASTER NotAllocatableAreas
    IN RASTER PAReduceFactor
    IN STRING SuitRasterCodes
    IN RASTERLIST SuitRasterNames
    IN RASTER CellAreasKM2
    IN RASTER SemiRandomNoise
    IN BOOLEAN CalculateRegionAreas
    IN BOOLEAN CalculateRegionLandcoverAreas
    IN BOOLEAN CalculateRegionLanduseAreas
    IN BOOLEAN CalculateRegionAllocatedLanduseAreas
    OUT DIR AllocatedLanduse
    """

    self.run_v6(*args)

  #-------------------------------------------------------------------------------
  # v2 : Aanroep van resolveLandcoverNotAllocatedAreas toegevoegd.
  #      Aanroep van resolveLanduseNotAllocatedAreas toegevoegd.
  #      Aanroep van resolveUndefinedAreas toegevoegd.
  # v3 : CalculateRegionAreas etc. toegevoegd.
  # v4 : Met calculateRegionAllocLanduseAreas etc.
  # v5 : Met area/noise rastername.
  # v6 : Met Arguments.
  #
  # Opmerkingen:
  # - De Image claims zijn fracties per jaar per landuse type.
  # - Deze per type per cel omzetten naar een opp.
  # - Dan per type regio de opp sommeren.
  def run_v6(self,*args):

    self.showStartMsg(args)

    # Create argument checker.
    pArgs = Arguments(args)

    # Get arguments.

    extent = pArgs.next()
    cellSize = pArgs.next()
    yearsStr = pArgs.next()

    regionRasterName = pArgs.next()
    regionFilterStr = pArgs.next()
    regionExcludeFilterStr = pArgs.next()

    landcoverRasterName = pArgs.next()
    landuseRasterName = pArgs.next()

    globioLanduseCodesStr = pArgs.next()
    globioLanduseNamesStr = pArgs.next()
    globioLandusePriorityCodesStr = pArgs.next()
    globioLanduseReplaceCodesStr = pArgs.next()
    globioLanduseReplaceWithCodeStr = pArgs.next()
    globioLanduseUndefinedCodeStr = pArgs.next()

    refClaimsFileName = pArgs.next()
    imgClaimsRasterName = pArgs.next()
    imgLanduseNamesStr = pArgs.next()

    notAllocatableAreasRasterName = pArgs.next()
    paReduceFactorRasterName = pArgs.next()
    suitRasterCodesStr = pArgs.next()
    suitRasterNamesStr = pArgs.next()

    cellAreaKM2RasterName = pArgs.next()
    semiRandomNoiseRasterName = pArgs.next()

    calculateRegionAreasStr = pArgs.next()
    calculateRegionLandcoverAreasStr = pArgs.next()
    calculateRegionLanduseAreasStr = pArgs.next()
    calculateRegionAllocLanduseAreasStr = pArgs.next()

    outDir = pArgs.next()

    # Check number of arguments.
    pArgs.check(self.name)

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkIntegerList(yearsStr)
    # TODO: Check yearsStr minimale lengte is 2.

    self.checkRaster(regionRasterName)
    self.checkIntegerList(regionFilterStr,optional=True)
    self.checkIntegerList(regionExcludeFilterStr,optional=True)

    self.checkRaster(landcoverRasterName,optional=True)
    self.checkRaster(landuseRasterName,optional=True)

    self.checkIntegerList(globioLanduseCodesStr)
    self.checkListCount(globioLanduseNamesStr,globioLanduseCodesStr,"GLOBIO landuse names")

    # Set landuse types and check.
    self.landuseTypes.init(globioLanduseCodesStr,globioLanduseNamesStr)
    self.landuseTypes.checkLanduseCodes(globioLandusePriorityCodesStr,
                           Err.NoLandusePriorityCodesSpecified,
                           Err.InvalidLandusePriorityCode1)
    self.landuseTypes.checkLanduseCodes(globioLanduseReplaceCodesStr,
                           Err.NoLanduseReplaceCodesSpecified,
                           Err.InvalidLanduseReplaceCodes1)
    self.landuseTypes.checkLanduseCodes(globioLanduseReplaceWithCodeStr,
                           Err.NoLanduseReplaceWithCodeSpecified,
                           Err.InvalidLanduseReplaceWithCode1)
    self.landuseTypes.checkLanduseCodes(globioLanduseUndefinedCodeStr,
                           Err.NoLanduseUndefinedCodeSpecified,
                           Err.InvalidLanduseUndefinedCode1)

    self.checkLookup(refClaimsFileName)

    self.checkRasterOrTemplate(imgClaimsRasterName,checkCellSize=False)   # because of incomplete filename.
    self.checkListCount(imgLanduseNamesStr,globioLanduseNamesStr,"IMAGE landuse names")

    # Get and check if not-allocatable area raster set.
    self.checkRaster(notAllocatableAreasRasterName,optional=True)
    if self.isValueSet(notAllocatableAreasRasterName):
      Err.raiseGlobioError(Err.UserDefined1,"A not-allocatable area raster cannot be used.")

    # Get and check if PA reduce factor raster set.
    self.checkRaster(paReduceFactorRasterName,optional=True)
    if self.isValueSet(paReduceFactorRasterName):
      Err.raiseGlobioError(Err.UserDefined1,"A protected area (PA) reduce factor raster cannot be used.")

    self.landuseTypes.checkLanduseCodes(suitRasterCodesStr,
                           Err.NoSuitabilityRasterCodesSpecified,
                           Err.InvalidSuitabilityRasterCode1)
    self.checkListCount(suitRasterNamesStr,suitRasterCodesStr,"rasters")
    self.checkRasterList(suitRasterNamesStr)

    self.checkRaster(cellAreaKM2RasterName)
    self.checkRaster(semiRandomNoiseRasterName)

    self.checkBoolean(calculateRegionAreasStr)
    self.checkBoolean(calculateRegionLandcoverAreasStr)
    self.checkBoolean(calculateRegionLanduseAreasStr)

    # TODO: aanpassen?
    #self.checkDirectory(outDir,asOutput=True)
    if not os.path.isdir(outDir):
      os.makedirs(outDir)

    # Convert codes and names to arrays.
    years = self.splitIntegerList(yearsStr)
    # Check years.
    if len(years)<2:
      Err.raiseGlobioError(Err.UserDefined1,"Invalid number of years, at least 2 years needed.")
    regionFilter = self.splitIntegerList(regionFilterStr)
    regionExcludeFilter = self.splitIntegerList(regionExcludeFilterStr)
    globioLanduseCodes = self.splitIntegerList(globioLanduseCodesStr)
    globioLandusePriorityCodes = self.splitIntegerList(globioLandusePriorityCodesStr)
    globioLanduseNames = self.splitStringList(globioLanduseNamesStr)
    globioLanduseReplaceCodes = self.splitIntegerList(globioLanduseReplaceCodesStr)
    globioLanduseReplaceWithCode = int(globioLanduseReplaceWithCodeStr)
    globioLanduseUndefinedCode = int(globioLanduseUndefinedCodeStr)

    imgLanduseNames = self.splitStringList(imgLanduseNamesStr)

    calculateRegionAreas = calculateRegionAreasStr
    calculateRegionLandcoverAreas = calculateRegionLandcoverAreasStr
    calculateRegionLanduseAreas = calculateRegionLanduseAreasStr
    calculateRegionAllocLanduseAreas = calculateRegionAllocLanduseAreasStr

    # Align extent.
    extent = RU.alignExtent(extent,cellSize)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.outDir = outDir

    # Enable monitor en show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    #-----------------------------------------------------------------------------
    # Read the region raster and get the region codes and extents.
    #-----------------------------------------------------------------------------

    # Get the region extents.
    regionExtents = self.getRegionExtents(regionRasterName,extent,cellSize,
                                          regionFilter,regionExcludeFilter)

    # Get the wanted region codes.
    regions = list(regionExtents.keys())

    # Check regions.
    if len(regions) == 0:
      Err.raiseGlobioError(Err.UserDefined1,"No regions to process. Aborting.")

    Log.info("- Nr. of regions found: %s" % len(regions))
    Log.info("- Using region: %s" %  UT.arrayToStr(regions,","))

    #-----------------------------------------------------------------------------
    # Create total suitability and save per region.
    # All years use the same suitablity.
    #-----------------------------------------------------------------------------

    #@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    #@@@@@@@@@ WORDT NOG NIET GEBRUIKT!!!!!!!!!!!!!!!!!!!!
    #@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

    calcSuitability = False
    if calcSuitability:
      pass
      # Log.info("Creating total suitability per region...")
      #
      # # Loop regions.
      # for region in regions:
      #
      #   Log.info("- Processing region %s..." % region)
      #
      #   # Get region extent.
      #   regionExtent = self.getRegionExtent(region)
      #
      #   # Get total suitability raster name.
      #   totSuitRasterName = self.getTotalSuitabilityRasterName(region)
      #
      #   # Create total suitability raster.
      #   totSuitRaster = self.createTotalSuitabilityRaster(regionExtent,cellSize)
      #
      #   # Writing raster.
      #   totSuitRaster.writeAs(totSuitRasterName)
      #
      #   # Cleanup.
      #   del totSuitRaster

    #-----------------------------------------------------------------------------
    # Create IMAGE claims per year.
    # Calculate:
    #   IMG_CLAIM = FRACTION * CELL_AREA
    # All files include region;landuse;area_km2.
    #-----------------------------------------------------------------------------

    calcImageClaims = True
    if calcImageClaims:

      Log.info("Converting IMAGE claims...")

      # Loop years.
      for year in years:

        Log.info("- Processing %s..." % year)

        # Calculates the IMAGE claims for each year.
        # Returns a list with of region;landuse;area_km2.
        regionLanduseClaims = self.calcImageClaims(extent,cellSize,year,
                                                   regions,regionRasterName,
                                                   globioLandusePriorityCodes,
                                                   globioLanduseCodes,
                                                   globioLanduseNames,
                                                   imgClaimsRasterName,
                                                   imgLanduseNames,
                                                   cellAreaKM2RasterName,
                                                   prefix="    ")

        # Get IMAGE claims filename and write to disk.
        imgClaimsFileName = self.getImageClaimsFileName(year)
        UT.fileWrite(imgClaimsFileName,regionLanduseClaims)

        # Cleanup.
        del regionLanduseClaims

    ##############################################################################
    # Create allocate landuse per year per region.
    ##############################################################################

    Log.info("Allocating landuse claims...")

    #-----------------------------------------------------------------------------
    # Read reference claims for 2015.
    #-----------------------------------------------------------------------------

    Log.info("- Reading reference claims for 2015...")

    # Read reference csv file and create index on region,lanuse.
    refClaims = CSVFile()
    refClaims.read(refClaimsFileName,self.claimFieldNames,self.claimFieldTypes)
    refClaims.createIndex()

    #-----------------------------------------------------------------------------
    # Set years.
    #-----------------------------------------------------------------------------

    # First year is 2015, allocYears is the remaining.
    firstYear = years[0]
    allocYears = years[1:]
    del years

    # Loop years.
    for i,year in enumerate(allocYears):

      Log.info("- Processing %s..." % year)

      # Set previous year.
      if i == 0:
        previousYear = firstYear
      else:
        previousYear = allocYears[i-1]

      #-----------------------------------------------------------------------------
      # Create harmonized claims per year.
      # Calculate:
      #   HARM_CLAIM = REF_CLAIM + (IMG_CLAIM_Y - IMG_CLAIM_Y-1)
      # All files include region;landuse;area_km2.
      #-----------------------------------------------------------------------------

      Log.info("    Calculating harmonized claims...")

      # Get the fil names.
      imgClaimsFileName = self.getImageClaimsFileName(year)
      imgPrevClaimsFileName = self.getImageClaimsFileName(previousYear)
      harmonizedClaimsFileName = self.getHarmonizedClaimsFileName(year)

      # Create the harmonized claims file
      self.createHarmonizedClaimsFile(refClaims,
                                      imgClaimsFileName,
                                      imgPrevClaimsFileName,
                                      harmonizedClaimsFileName)

      # Loop regions.
      for region in regions:

        #Log.info("- Allocating landuse for region %s..." % region)
        Log.info("")
        Log.info("    Allocating landuse for region %s..." % region)

        # Set region info.
        allocRegionExtent = regionExtents[region]
        allocRegionFilterStr = str(region)
        allocRegionExcludeFilterStr = ""

        # Get allocated landuse raster name.
        allocYearRegionRasterName = self.getAllocatedLanduseRegionRasterName(year,region)

        # Run landuse allocation module.
        pAlloc = GLOBIO_CalcDiscreteLanduseAllocation_V2()
        pAlloc.run_v25(allocRegionExtent,cellSize,
                       globioLanduseCodesStr,globioLanduseNamesStr,
                       globioLandusePriorityCodesStr,
                       landcoverRasterName,
                       regionRasterName,
                       allocRegionFilterStr,
                       allocRegionExcludeFilterStr,
                       landuseRasterName,
                       globioLanduseReplaceCodesStr,
                       globioLanduseReplaceWithCodeStr,
                       globioLanduseUndefinedCodeStr,
                       notAllocatableAreasRasterName,
                       paReduceFactorRasterName,
                       suitRasterCodesStr,suitRasterNamesStr,
                       harmonizedClaimsFileName,
                       self.claimLanduseFieldName,
                       self.claimRegionFieldName,
                       self.claimAreaFieldName,
                       self.claimLookupFileName,
                       self.claimAreaMultiplierLanduseCodesStr,
                       self.claimAreaMultipliersStr,
                       cellAreaKM2RasterName,
                       semiRandomNoiseRasterName,
                       allocYearRegionRasterName)

    #-----------------------------------------------------------------------------
    # Merge allocated landuse per year.
    #-----------------------------------------------------------------------------

    Log.info("Merging allocated landuse rasters...")

    # Loop years.
    for year in allocYears:

      Log.info("- Processing %s..." % year)

      # Get allocated landuse raster name.
      allocLanduseRasterName = self.getAllocatedLanduseRasterName(year)

      # Create full extent allocated landuse raster and initialize.
      noDataValue = 0
      allocLanduseRaster = Raster(allocLanduseRasterName)
      allocLanduseRaster.initRaster(extent,cellSize,np.uint8,noDataValue)

      #-----------------------------------------------------------------------------
      # Merge allocated landuse of regions.
      #-----------------------------------------------------------------------------

      # Merge allocated landuse of regions.
      for region in regions:

        # Get allocated landuse region raster name.
        allocLanduseRegionRasterName = self.getAllocatedLanduseRegionRasterName(year,
                                                                                region)

        # Read allocated landuse region raster.
        allocLanduseRegionRaster = Raster(allocLanduseRegionRasterName)
        allocLanduseRegionRaster.read()

        self.dbgPrintArray("    AllocRegion: ",allocLanduseRegionRaster.r)

        # Update full raster with region data.
        allocLanduseRaster.replace(allocLanduseRegionRaster)

        # Cleanup.
        del allocLanduseRegionRaster

      #-----------------------------------------------------------------------------
      # Resolve undefined areas, i.e. not-overlapping areas of regions (@@@and
      # not-allocatable areas). TODO: not-allocatable areas???
      #-----------------------------------------------------------------------------

      Log.info("    Resolving undefined areas...")

      # Read the region raster and resizes to extent and resamples to cellsize.
      regionRaster = self.readAndPrepareInRaster_V2(extent,cellSize,
                                                    regionRasterName,"regions",
                                                    calcSumDiv=False,
                                                    prefix="      ")

      # Get actual regions mask.
      actualRegionMask = RGU.createRegionMask(regionRaster,regions)

      # Resolve undefined areas, fill with LanduseUndefinedCode.
      self.resolveUndefinedAreas(actualRegionMask,
                                 globioLanduseUndefinedCode,
                                 allocLanduseRaster)

      #-----------------------------------------------------------------------------
      # Resolve not-allocated areas, fill current landuse areas with replace code.
      # Bv. "1|2|3|4" -> "5"  dus vrijgevallen landuse wordt "secondary vegetation".
      #-----------------------------------------------------------------------------
      if self.isValueSet(landuseRasterName):

        Log.info("    Resolving not-allocated areas, using replace code...")

        # Read the landuse raster and resizes to extent and resamples to cellsize.
        landuseRaster = self.readAndPrepareInRaster_V2(extent,cellSize,
                                                       landuseRasterName,"landuse",
                                                       calcSumDiv=False,
                                                       prefix="      ")
        # Resolve not-allocated areas with landuse. Replace landuse codes.
        self.resolveLanduseNotAllocatedAreas(actualRegionMask,
                                             landuseRaster,
                                             globioLanduseReplaceCodes,
                                             globioLanduseReplaceWithCode,
                                             allocLanduseRaster)
        del landuseRaster

      #-----------------------------------------------------------------------------
      # Resolve remaining not-allocated areas, fill with with landcover.
      #-----------------------------------------------------------------------------
      if self.isValueSet(landcoverRasterName):

        Log.info("    Resolving not-allocated areas, filling with landcover...")

        # Read the landcover raster and resizes to extent and resamples to cellsize.
        landcoverRaster = self.readAndPrepareInRaster_V2(extent,cellSize,
                                                         landcoverRasterName,"landcover",
                                                         calcSumDiv=False,
                                                         prefix="      ")

        # Resolve remaining not-allocated areas with landcover.
        self.resolveLandcoverNotAllocatedAreas(landcoverRaster,
                                               allocLanduseRaster)
        del landcoverRaster

      #-----------------------------------------------------------------------------
      # Calculate region allocated landuse areas (optional).
      #-----------------------------------------------------------------------------
      if calculateRegionAllocLanduseAreas:

        Log.info("    Calculating region/landuse areas...")

        # Read the region raster and resizes to extent and resamples to cellsize.
        cellAreaRaster = self.readAndPrepareInRaster_V2(extent,cellSize,
                                                        cellAreaKM2RasterName,"cellarea",
                                                        calcSumDiv=True,
                                                        prefix="      ")

        # Calculate and write the region allocated landuse areas.
        allocAreasFileName = self.getAllocatedRegionLanduseAreasFileName(year)
        self.checkFile(allocAreasFileName,asOutput=True)
        self.writeRegionAllocLanduseAreas(regionRaster,cellAreaRaster,
                                          allocLanduseRaster,regions,
                                          allocAreasFileName,prefix="      ")
        del cellAreaRaster

      # Cleanup.
      del regionRaster

      #-----------------------------------------------------------------------------
      # Write allocated landuse.
      #-----------------------------------------------------------------------------

      Log.info("    Writing allocated landuse...")
      Log.info("    - Writing %s..." % allocLanduseRasterName)

      # Write full extent allocated landuse raster.
      allocLanduseRaster.write()

      self.dbgPrintArray("    Alloc: ",allocLanduseRaster.r)

      # Cleanup.
      del allocLanduseRaster

    #-----------------------------------------------------------------------------
    # Calculate regions, landcover, landuse areas (optional).
    #-----------------------------------------------------------------------------

    # Calculate regions or landcover or landuse areas?
    if calculateRegionAreas or \
       (calculateRegionLandcoverAreas and self.isValueSet(landcoverRasterName)) or \
       (calculateRegionLanduseAreas and self.isValueSet(landuseRasterName)):

      Log.info("Reading rasters...")

      # Read the region raster and resizes to extent and resamples to cellsize.
      regionRaster = self.readAndPrepareInRaster_V2(extent,cellSize,
                                                    regionRasterName,"regions",
                                                    calcSumDiv=False,
                                                    prefix="  ")
      # Filter the regions, i.e. set to noData.
      RGU.filterRegionRaster(regionRaster,regionFilter,regionExcludeFilter)

      # Read the cellarea raster and resizes to extent and resamples to cellsize.
      cellAreaRaster = self.readAndPrepareInRaster_V2(extent,cellSize,
                                                      cellAreaKM2RasterName,"cellarea",
                                                      calcSumDiv=True,
                                                      prefix="  ")
      # Calculate region areas?
      if calculateRegionAreas:

        Log.info("Calculating region areas...")

        self.writeRegionAreas(regionRaster,cellAreaRaster,regions)

      # Calculate region/landcover areas?
      if calculateRegionLandcoverAreas and self.isValueSet(landcoverRasterName):

        Log.info("Calculating region/landcover areas...")

        # Read the landcover raster and resizes to extent and resamples to cellsize.
        landcoverRaster = self.readAndPrepareInRaster_V2(extent,cellSize,
                                                      landcoverRasterName,"landcover",
                                                      calcSumDiv=False,
                                                      prefix="  ")
        self.writeRegionLandcoverAreas(regionRaster,cellAreaRaster,
                                       landcoverRaster,regions,prefix="  ")

      # Calculate region/landuse areas?
      if calculateRegionLanduseAreas and self.isValueSet(landuseRasterName):

        Log.info("Calculating region/landuse areas...")

        # Read the landuse raster and resizes to extent and resamples to cellsize.
        landuseRaster = self.readAndPrepareInRaster_V2(extent,cellSize,
                                                         landuseRasterName,"landuse",
                                                         calcSumDiv=False,
                                                         prefix="  ")
        self.writeRegionLanduseAreas(regionRaster,cellAreaRaster,
                                     landuseRaster,regions,prefix="  ")

    # Show used memory and disk space.
    MON.showMemDiskUsage()

    self.showEndMsg()
