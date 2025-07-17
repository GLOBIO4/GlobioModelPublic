# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
#
# Region utilities.
#
# Modified: 14 jan 2021, ES, ARIS B.V.
#           - Version 4.1.1
#-------------------------------------------------------------------------------

#import os
import numpy as np
import scipy.ndimage

# import GlobioModel.Core.Error as Err
# import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log

import GlobioModel.Common.Utils as UT

from GlobioModel.Core.Raster import Raster
# import GlobioModel.Core.RasterUtils as RU

#-------------------------------------------------------------------------------
def calcRegionLanduseAreas(regionRaster: Raster,
                           areaRaster: Raster,
                           landuseRaster: Raster,
                           regionCodes: [int],
                           fieldNames: [str]):

  regionLanduseAreas = []

  # Loop regions.
  for regionCode in regionCodes:

    Log.info("- Processing region %s..." % regionCode)

    # Create region mask.
    regionMask = (regionRaster.r == regionCode)
    # Get landuse types in region.
    luTypes = np.unique(landuseRaster.r[regionMask])
    # Calculate sum of areas per landuse type.
    areaSum = scipy.ndimage.labeled_comprehension(areaRaster.r[regionMask],
                                                  landuseRaster.r[regionMask],
                                                  luTypes,np.sum,np.float64,0)
    # Fill an array with current region.
    tmpRegions = len(areaSum) * [regionCode]
    # Combine region, landuse and areas in an array of region/landuse/area tuples.
    tmpAreaSum = zip(tmpRegions,luTypes,areaSum)
    # Add to list.
    regionLanduseAreas.extend(tmpAreaSum)

  # Cleanup.
  del regionMask
  del luTypes
  del tmpRegions
  del tmpAreaSum

  # Create file content.
  lines = []
  lines.append(";".join(fieldNames))
  for regionLanduseArea in regionLanduseAreas:
    lines.append("{};{};{}".format(*regionLanduseArea))
  del regionLanduseAreas
  return lines
  # # Write to file.
  # Utils.fileWrite(csvFileName,lines)
  # # Free areas and lines.
  # regionLanduseAreas = None
  # lines = None

# TODO: Verplaatsen.
#-------------------------------------------------------------------------------
# Calculates sum of areas per region.
# Uses np.float64 to prevent oveflow.
def writeRegionAreas(regionRaster: Raster,
                     areaRaster: Raster,
                     regionCodes: [int],
                     fieldNames: [str],
                     outFileName: str):

  # Calculate sum of areas per region.
  areaSum = scipy.ndimage.labeled_comprehension(areaRaster.r,regionRaster.r,
                                                regionCodes,np.sum,np.float64,0)
  # Combine regions and areas in an array of region/area tuples.
  regionAreas = zip(regionCodes,areaSum)
  del areaSum
  # Create file content.
  lines = []
  lines.append(";".join(fieldNames))
  for regionArea in regionAreas:
    lines.append("{};{}".format(*regionArea))
  del regionAreas
  UT.fileWrite(outFileName,lines)
# def calcRegionAreas(regionCodes: list,regionRaster: Raster,areaRaster: Raster):
#
#   # Calculate sum of areas per region.
#   areaSum = scipy.ndimage.labeled_comprehension(areaRaster.r,regionRaster.r,
#                                                 regionCodes,np.sum,np.float64,0)
#   # Combine regions and areas in an array of region/area tuples.
#   regionAreas = zip(regionCodes,areaSum)
#   del areaSum
#   # Create file content.
#   lines = []
#   # TO-DO: vars gebruiken.
#   lines.append("region;area_km2")
#   for regionArea in regionAreas:
#     lines.append("{};{}".format(*regionArea))
#   del regionAreas
#   return lines
#   # # Write to file.
#   # Utils.fileWrite(csvFileName,lines)
#   # # Free areas and lines.
#   # regionAreas = None
#   # lines = None

#-------------------------------------------------------------------------------
# Calculates sum of areas per region and landcover type.
# Uses np.float64 to prevent oveflow.
def writeRegionLandcoverAreas(regionRaster: Raster,
                              areaRaster: Raster,
                              landcoverRaster: Raster,
                              regionCodes: [int],
                              fieldNames: [str],
                              outFileName: str,
                              prefix: str="",
                              silent: bool=False):
  # Calulate areas.
  regionLandcoverAreas = []
  # Loop regions.
  for regionCode in regionCodes:

    if not silent:
      Log.info("%s- Processing region %s..." % (prefix,regionCode))

    # Create region mask.
    regionMask = (regionRaster.r == regionCode)
    # Get landcover types in region.
    lcTypes = np.unique(landcoverRaster.r[regionMask])
    # Calculate sum of areas per landcover type.
    areaSum = scipy.ndimage.labeled_comprehension(areaRaster.r[regionMask],
                                                  landcoverRaster.r[regionMask],
                                                  lcTypes,np.sum,np.float64,0)
    # Fill an array with current region.
    tmpRegions = len(areaSum) * [regionCode]
    # Combine region, landcover and areas in an array of region/landcover/area tuples.
    tmpAreaSum = zip(tmpRegions,lcTypes,areaSum)
    # Add to list.
    regionLandcoverAreas.extend(tmpAreaSum)
  # Cleanup.
  del regionMask
  del lcTypes
  del tmpRegions
  del tmpAreaSum
  # Create file content.
  lines = []
  lines.append(";".join(fieldNames))
  for regionLandcoverArea in regionLandcoverAreas:
    lines.append("{};{};{}".format(*regionLandcoverArea))
  del regionLandcoverAreas
  UT.fileWrite(outFileName,lines)
# def calcRegionLandcoverAreas(regionCodes: list,regionRaster: Raster,
#                              landcoverRaster: Raster,areaRaster: Raster):
#   # Calulate areas.
#   regionLandcoverAreas = []
#   # Loop regions.
#   for regionCode in regionCodes:
#
#     Log.info("- Processing region %s..." % regionCode)
#
#     # Create region mask.
#     regionMask = (regionRaster.r == regionCode)
#     # Get landcover types in region.
#     lcTypes = np.unique(landcoverRaster.r[regionMask])
#     # Calculate sum of areas per landcover type.
#     areaSum = scipy.ndimage.labeled_comprehension(areaRaster.r[regionMask],
#                                                   landcoverRaster.r[regionMask],
#                                                   lcTypes,np.sum,np.float64,0)
#     # Fill an array with current region.
#     tmpRegions = len(areaSum) * [regionCode]
#     # Combine region, landcover and areas in an array of region/landcover/area tuples.
#     tmpAreaSum = zip(tmpRegions,lcTypes,areaSum)
#     # Add to list.
#     regionLandcoverAreas.extend(tmpAreaSum)
#
#   # Cleanup.
#   del regionMask
#   del lcTypes
#   del tmpRegions
#   del tmpAreaSum
#
#   # Create file content.
#   lines = []
#   # TODO: vars gebruiken.
#   lines.append("region;landcover;area_km2")
#   for regionLandcoverArea in regionLandcoverAreas:
#     lines.append("{};{};{}".format(*regionLandcoverArea))
#   del regionLandcoverAreas
#   return lines
#   # # Write to file.
#   # Utils.fileWrite(csvFileName,lines)
#   # # Free areas and lines.
#   # regionLandcoverAreas = None
#   # lines = None


#-------------------------------------------------------------------------------
# Calculates sum of areas per region and landuse type.
# Uses the unique landuse codes in the landuse raster.
# Uses np.float64 to prevent oveflow.
def writeRegionLanduseAreas(regionRaster: Raster,
                            areaRaster: Raster,
                            landuseRaster: Raster,
                            regionCodes: [int],
                            fieldNames: [str],
                            outFileName: str,
                            prefix: str="",
                            silent: bool=False):

  regionLanduseAreas = []

  # Loop regions.
  for regionCode in regionCodes:

    if not silent:
      Log.info("%s- Processing region %s..." % (prefix,regionCode))

    # Create region mask.
    regionMask = (regionRaster.r == regionCode)
    # Get landuse types in region.
    luTypes = np.unique(landuseRaster.r[regionMask])
    # Calculate sum of areas per landuse type.
    areaSum = scipy.ndimage.labeled_comprehension(areaRaster.r[regionMask],
                                                  landuseRaster.r[regionMask],
                                                  luTypes,np.sum,np.float64,0)
    # Fill an array with current region.
    tmpRegions = len(areaSum) * [regionCode]
    # Combine region, landuse and areas in an array of region/landuse/area tuples.
    tmpAreaSum = zip(tmpRegions,luTypes,areaSum)
    # Add to list.
    regionLanduseAreas.extend(tmpAreaSum)

  # Cleanup.
  del regionMask
  del luTypes
  del tmpRegions
  del tmpAreaSum

  # Create file content.
  lines = []
  lines.append(";".join(fieldNames))
  for regionLanduseArea in regionLanduseAreas:
    lines.append("{};{};{}".format(*regionLanduseArea))
  del regionLanduseAreas
  UT.fileWrite(outFileName,lines)


#-----------------------------------------------------------------------------
# Creates a list of region codes from the region raster.
def createRegionListFromRegionRaster(regionRaster: Raster,
                                     includeNoDataValue: bool):
  # Get unique values from region raster.
  regionCodes = np.unique(regionRaster.r)
  # No nodata value?
  if not includeNoDataValue:
    # Remove nodata value.
    regionCodes = regionCodes[(regionCodes!=regionRaster.noDataValue)]
  return list(regionCodes)

#-------------------------------------------------------------------------------
# Create a mask of regions.
# regionRaster is a Raster() object.
# regionFilter is a list of integer codes.
def createRegionMask(regionRaster: Raster,regions: [int]):
  # No filter?
  if len(regions)==0:
    # Select all.
    mask = regionRaster.getDataMask()
  else:
    mask = None
    # Select from list.
    for region in regions:
      if mask is None:
        mask = (regionRaster.r == region)
      else:
        mask = np.logical_or(mask,(regionRaster.r == region))
  return mask

#-------------------------------------------------------------------------------
# Set nodata in the region raster for region codes not in the regionFilter and
# for region codes in the regionExcludeFilter.
def filterRegionRaster(regionRaster: Raster,
                       regionFilter: list, regionExcludeFilter: list):

  # Need to filter the regions?
  if len(regionFilter)>0:
    #Log.info("Filtering regions...")
    # Set nodata in region raster outside the regions in regionFilter.
    setRegionRasterFilter(regionRaster,regionFilter)

  # Need to exclude regions?
  if len(regionExcludeFilter)>0:
    #Log.info("Excluding regions...")
    # Set nodata in region raster which should be excluded.
    setRegionRasterExclude(regionRaster,regionExcludeFilter)

#-------------------------------------------------------------------------------
# Set nodata in region raster which should be excluded.
def setRegionRasterExclude(regionRaster: Raster,regionExcludeFilter: list):
  # Need to exclude regions?
  if len(regionExcludeFilter) > 0:
    # Create a mask for unwanted regions.
    regionMask = createRegionMask(regionRaster,regionExcludeFilter)
    # Set unwanted regions to NoData.
    regionRaster.r[regionMask] = regionRaster.noDataValue
    # Free the masked regions.
    del regionMask
  # # Save temp raster?
  # if GLOB.saveTmpData:
  #   tmpName = "tmp_selected_excl_regions.tif"
  #   Log.info("- Writing after excluding regions: "+tmpName)
  #   self.writeTmpRaster(regionRaster,tmpName)

#-------------------------------------------------------------------------------
# Set nodata in region raster outside the regions in regionFilter.
def setRegionRasterFilter(regionRaster: Raster,regionFilter: list):
  # Need to filter the regions?
  if len(regionFilter) > 0:
    # Create a mask for unwanted regions.
    regionMask = createRegionMask(regionRaster,regionFilter)
    # Set unwanted regions to NoData.
    regionRaster.r[~regionMask] = regionRaster.noDataValue     # pylint: disable=invalid-unary-operand-type
    # Free the masked regions.
    del regionMask
  # # Save temp raster?
  # if GLOB.saveTmpData:
  #   tmpName = "tmp_selected_filt_regions.tif"
  #   Log.info("- Writing selected regions: "+tmpName)
  #   RU.writeTmpRaster(regionRaster,tmpName)

