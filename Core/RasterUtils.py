# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#
# All RaterUtils methods are implemented for using with the GDAL libs. Some
# methods are also implemented using the ArcGIS lib arcpy.
#
# The value GLOB.gisLib specifies which lib will be imported, GDAL or
# ArcGIS, and which mehods can be used.
# 
# Modified: 30 sept 2016, ES, ARIS B.V.
#           - Version 4.0.2
#           - calcCellSizeFromExtentColsRows added.
#           - calcExtentToColsRows changed to calcNrColsRowsFromExtent.
#           - calcXYToColRowExtent changed to calcColRowFromXY.
#           - calcXYToColRowGT removed.
#           - isPointInExtent added.
#           - isExtentInExtent added.
#           - calcColRowFromXY modified, isPointInExtent added.
#           - calcColRowWindowFromExtent added.
#           - calcColRowFromXY modified, abs() added.
#           9 nov 2016, ES, ARIS B.V.
#           - Version 4.0.2
#           - Use of gisLib added.
#           - import order modified.
#           - rasterExtent added.
#           - checkCompressionMode added.
#           - createRasterDataset modified, compressionMode added.
#           - getNoDataValue changed, now using -9999.
#           - RasterInfo.show added.
#           - getNoDataValue modified.
#           - rasterValueToString added.
#           7 dec 2016, ES, ARIS B.V.
#           - Version 4.0.3
#           - calcNrColsRowsFromExtent modified.
#           - alignExtent modified.
#           - getNoDataValue modified, now using -3.0e+38 for np.float32.
#           22 jun 2017, ES, ARIS B.V.
#           - Version 4.0.6
#           - strToGeometryType modified.
#           - geometryTypeToStr added.
#           12 sep 2017, ES, ARIS B.V.
#           - Version 4.0.9
#           - geometryTypeToStr modified, extra point types added.
#           29 oct 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           - RasterInfo modified, compression added.
#           - rasterGetInfo modified, compression added.
#           1 nov 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           - degreeToKM_v1a added, faster?
#           20 nov 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           - import geographiclib added.
#           - degreeToKM_v2 added, more accurate?
#           - degreeToKM2 added.
#           - vectorDelete modified.
#           - dataTypeNumpyIsInt added.
#           - dataTypeNumpyToC added.
#           10 sep 2020, ES, ARIS B.V.
#           - Version 4.0.15
#           - rasterCopy removed.
#           - rasterHasExtentCellSize added.
#           - rasterHasExtentCellSize added.
#           10 dec 2020, ES, ARIS B.V.
#           - Version 4.1.0
#           - maskedToNumpy added.
#           - dataTypeNumpyIsFloat added.
#           - dataTypeNumpyIsMinimalInt16 added.
#           - maskedToNumpy added.
#           - isEqualColsRows added.
#           11 jan 2021, ES, ARIS B.V.
#           - Version 4.1.1
#           - isNetCDFName added.
#           - netCDFExists added.
#           - getNetCDFFileName added.
#           - getNetCDFType added.
#           - getNetCDFArguments added.
#           - rasterExists modified.
#           - rasterDelete modified.
#           - isGdalRasterName added.
#           - rasterGetInfo modified.
#           - writeTmpRaster added.
#           - calcExtentFromColsRows added.
#           - semiRandomNoiseGet added.
#           - semiRandomNoiseSeed added.
#           - cellSizeToCellSizeName added.
#           - alignExtentGrow added.
#-------------------------------------------------------------------------------

import os
import ctypes
import math

import numpy as np

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log

import GlobioModel.Common.Utils as UT

from geographiclib.geodesic import Geodesic

if GLOB.gisLib == GLOB.GIS_LIB_GDAL:
  import osgeo.gdal as gd
  import osgeo.ogr as ogr
  import osgeo.osr as osr
else:
  # 20201118
  #import arcpy.sa
  import GlobioModel.Core._arcpy as arcpy

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
# Used for semi-random noise.
__randomState = np.random.RandomState()

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class RasterInfo(object):
  linePrefix = ""
  #-----------------------------------------------------------------------------
  def __init__(self):
    self.cellSize = None
    self.nrCols = None
    self.nrRows = None
    self.extent = None
    self.noDataValue = None
    self.dataType = None         # Numpy type
    self.compression = None
  #-----------------------------------------------------------------------------
  def __str__(self):
    s = self.linePrefix + "CellSize: %s\n" % self.cellSize
    s += self.linePrefix + "Extent: %s %s %s %s\n" % (self.extent[0],self.extent[1],self.extent[2],self.extent[3])
    s += self.linePrefix + "NrCols/NrRows: %s %s\n" % (self.nrCols,self.nrRows)
    s += self.linePrefix + "NoDataValue: %s\n" % rasterValueToString(self.noDataValue,self.dataType,3)
    s += self.linePrefix + "DataType: %s\n" % dataTypeNumpyToString(self.dataType)
    # 20181029
    if self.compression is None:
      s += self.linePrefix + "Compression: Unknown"
    else:
      s += self.linePrefix + "Compression: %s" % self.compression
    return s
  #-----------------------------------------------------------------------------
  def show(self,caption=None,linePrefix=None):
    if not caption is None:
      print(caption)
      self.linePrefix = "  "
    if not linePrefix is None:
      self.linePrefix = linePrefix
    print(self)
      
#-------------------------------------------------------------------------------
# Align the extent with lower-left as origin (i.e. a multiple of cellsize).
def alignExtent(extent,cellSize):
  precision = 8
  nrCols,nrRows = calcNrColsRowsFromExtent(extent,cellSize)
  
  #Log.dbg("alignExtent - nrCols/nrRows: %s %s" % (nrCols,nrRows))

  minx = round(extent[0] / cellSize,0) * cellSize
  miny = round(extent[1] / cellSize,0) * cellSize
  maxx = minx + nrCols * cellSize
  maxy = miny + nrRows * cellSize

  #Log.dbg("alignExtent - minx/miny: %s %s" % (minx,miny))

  minx = round(minx,precision)
  miny = round(miny,precision)
  maxx = round(maxx,precision)
  maxy = round(maxy,precision)
  return [minx,miny,maxx,maxy]

#-------------------------------------------------------------------------------
# Align the extent with lower-left as origin (i.e. a multiple of cellsize).
# Ensure the original extent is fully within the aligned extent.
def alignExtentGrow(extent,cellSize):
  precision = 8
  nrCols,nrRows = calcNrColsRowsFromExtent(extent,cellSize)

  # Get lower left point.
  minx = UT.trunc(extent[0] / cellSize) * cellSize
  miny = UT.trunc(extent[1] / cellSize) * cellSize
  minx = UT.trunc(minx,precision)
  miny = UT.trunc(miny,precision)

  # Get upper left point.
  maxx = minx + nrCols * cellSize
  maxy = miny + nrRows * cellSize
  maxx = UT.trunc(maxx,precision)
  maxy = UT.trunc(maxy,precision)

  # Check upper left point.
  # TODO: Check for very small cellsize?
  while maxx < extent[2]:
    maxx = UT.trunc(maxx+cellSize,precision)
  while maxy < extent[3]:
    maxy = UT.trunc(maxy+cellSize,precision)

  return [minx,miny,maxx,maxy]

#-------------------------------------------------------------------------------
def asciiGridExists(fileName):
  return os.path.isfile(fileName)

#-------------------------------------------------------------------------------
# Extent is a list of [minx,miny,maxx,maxy].
def calcCellSizeFromExtentColsRows(extent,nrCols,nrRows):
  dx = abs(extent[2] - extent[0])
  dy = abs(extent[3] - extent[1])
  cellSize1 = dx / float(nrCols)
  cellSize2 = dy / float(nrRows)
  if not isEqualCellSize(cellSize1,cellSize2):
    Err.raiseGlobioError(Err.InvalidExtentNrOfColsRows)
  return cellSize1

#-------------------------------------------------------------------------------
def calcExtentFromColsRows(minX,minY,cellSize,col1,row1,col2,row2):
  x1 = minX + col1 * cellSize
  y1 = minY + row1 * cellSize
  x2 = minX + col2 * cellSize + cellSize
  y2 = minY + row2 * cellSize + cellSize
  return [x1,y1,x2,y2]

#-------------------------------------------------------------------------------
def calcExtentFromGT(geotransform,nrCols,nrRows):
  precision = 9
  minx = geotransform[0]
  miny = geotransform[3] + nrRows * geotransform[5]
  maxx = geotransform[0] + nrCols * geotransform[1]
  maxy = geotransform[3]
  minx = round(minx,precision)
  miny = round(miny,precision)
  maxx = round(maxx,precision)
  maxy = round(maxy,precision)
  return [minx,miny,maxx,maxy]

#-------------------------------------------------------------------------------
def calcExtentFromUpperLeftXY(minX,maxY,nrCols,nrRows,cellSize):
  precision = 9
  maxX = minX + nrCols * cellSize
  minY = maxY - nrRows * cellSize
  minX = round(minX,precision)
  minY = round(minY,precision)
  maxX = round(maxX,precision)
  maxY = round(maxY,precision)
  return [minX,minY,maxX,maxY]

# #-------------------------------------------------------------------------------
# def calcExtentFromColsRows(minCol,minRow,nrCols,nrRows,cellSize):
#   precision = 9
#   maxX = minX + nrCols * cellSize
#   minY = maxY - nrRows * cellSize
#   minX = round(minX,precision)
#   minY = round(minY,precision)
#   maxX = round(maxX,precision)
#   maxY = round(maxY,precision)
#   return [minX,minY,maxX,maxY]

#-------------------------------------------------------------------------------
# Extent1 and Extent2 are lists of [minx,miny,maxx,maxy].
# Returns None when no overlap.
def calcExtentOverlap(extent1,extent2):
  if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:
    Err.raiseGlobioError(Err.NotImplemented1,"calcExtentOverlap")
  else:
    # Create ring 1.
    ring1 = ogr.Geometry(ogr.wkbLinearRing)
    ring1.AddPoint(extent1[0], extent1[1])
    ring1.AddPoint(extent1[0], extent1[3])
    ring1.AddPoint(extent1[2], extent1[3])
    ring1.AddPoint(extent1[2], extent1[1])
    ring1.AddPoint(extent1[0], extent1[1])
  
    # Create polygon 1.
    poly1 = ogr.Geometry(ogr.wkbPolygon)
    poly1.AddGeometry(ring1)
  
    # Create ring 2.
    ring2 = ogr.Geometry(ogr.wkbLinearRing)
    ring2.AddPoint(extent2[0], extent2[1])
    ring2.AddPoint(extent2[0], extent2[3])
    ring2.AddPoint(extent2[2], extent2[3])
    ring2.AddPoint(extent2[2], extent2[1])
    ring2.AddPoint(extent2[0], extent2[1])
  
    # Create polygon 2.
    poly2 = ogr.Geometry(ogr.wkbPolygon)
    poly2.AddGeometry(ring2)
  
    extentGeom = poly1.Intersection(poly2)
    if extentGeom.GetGeometryName()=="POLYGON":
      envelope = extentGeom.GetEnvelope()
      return [envelope[0],envelope[2],envelope[1],envelope[3]]
    else:
      return None
  
#-------------------------------------------------------------------------------
# Extent is a list of [minx,miny,maxx,maxy].
def calcNrColsRowsFromExtent(extent,cellSize):
  return (int(round((extent[2]-extent[0]) / cellSize,0)),
          int(round((extent[3]-extent[1]) / cellSize,0)))

#-------------------------------------------------------------------------------
# Extent1 and Extent2 are lists of [minx,miny,maxx,maxy].
def calcExtentUnion(extent1,extent2):
  precision = 9
  minX = min(extent1[0],extent2[0])
  minY = min(extent1[1],extent2[1])
  maxX = max(extent1[2],extent2[2])
  maxY = max(extent1[3],extent2[3])
  minX = round(minX,precision)
  minY = round(minY,precision)
  maxX = round(maxX,precision)
  maxY = round(maxY,precision)
  return [minX,minY,maxX,maxY]

#-------------------------------------------------------------------------------
# Extent is a list of [minx,miny,maxx,maxy].
def calcExtentWidthHeight(extent):
  return (extent[2]-extent[0],extent[3]-extent[1])


#-------------------------------------------------------------------------------
# Calculates the col/row from a point within an extent.
# Returns (-1,-1) if the point lies outside the extent.
# Raster col/row origin 0/0 is upper left.
# Raster cell extent bottom left side included; top right excluded. 
# Extent is a list of [minx,miny,maxx,maxy].
def calcColRowFromXY(x,y,extent,cellSize):
  delta = 0.000000000001
  # Check if xy not in extent.
  if not isPointInExtent(x,y,extent,delta):
    return (-1,-1)
  col = UT.trunc((x - extent[0]) / cellSize)
  row = UT.trunc((extent[3] - extent[1]) / cellSize) - 1 -  UT.trunc((y - extent[1]) / cellSize)
  # x is upper bound?
  if abs(extent[2] - x) < delta:
    col -= 1
  # y is upper bound?
  if (extent[3] - y) < delta:
    row += 1
  return (col,row)  

#-------------------------------------------------------------------------------
# Calculates the window (col/row offset and size) from an extent within an extent.
# Returns MinCol, MinRow, NrCols, NrRows.
# Returns (-1,-1,0,0) if the srcExtent lies outside the inExtent.
# The srcExtent espresses the outer extent of the window
# Raster cell extent bottom left side included; top right excluded. 
# Raster col/row origin 0/0 is upper left.
# Extents are lists of [minx,miny,maxx,maxy].
#
# 230
#     1   2   3   4      0,0  1,0  2,0  3,0
# 220
#     5   6   7   8      0,1  1,1  2,1  3,1
# 210
#     9  10  11  12      0,2  1,2  2,2  3,2
# 200
#   1   1   1   1   1  
#   0   1   2   3   4
#   0   0   0   0   0
#
# [[ 1  2  3  4]
#  [ 5  6  7  8]
#  [ 9 10 11 12]]
# [100, 200, 140, 230]
# ---------------------------
# [100, 200, 140, 230] - 0 0 4 3 - 
# [[ 1  2  3  4]
#  [ 5  6  7  8]
#  [ 9 10 11 12]]
# [100, 200, 110, 210] - 0 2 1 1 - 
# [[9]]
# [110, 210, 120, 220] - 1 1 1 1 - 
# [[6]]
# [120, 220, 130, 230] - 2 0 1 1 - 
# [[3]]
# [130, 220, 140, 230] - 3 0 1 1 - 
# [[4]]
# [120, 220, 140, 230] - 2 0 2 1 - 
# [[3 4]]
# [100, 210, 140, 230] - 0 0 4 2 - 
# [[1 2 3 4]
#  [5 6 7 8]]
# [100, 200, 130, 220] - 0 1 3 2 - 
# [[ 5  6  7]
#  [ 9 10 11]]
# [100, 200, 130, 240] - -1 -1 0 0 - 
# []
def calcColRowWindowFromExtent(srcExtent,fullExtent,cellSize):
  delta = 0.000000000001

  # Check if the srcExtent is not in the inExtent.
  if not isExtentInExtent(srcExtent,fullExtent,delta):
    return (-1,-1,0,0)

  # Get origin of srcExtent.
  srcX1 = srcExtent[0]
  srcY1 = srcExtent[1]

  # Get origin of fullExtent.
  inX1 = fullExtent[0]
  inY1 = fullExtent[1]

  # Get number of rows of inExtent.  
  _,inNrRows = calcNrColsRowsFromExtent(fullExtent,cellSize)

  # Get number of rows of srcExtent.  
  nrCols,nrRows = calcNrColsRowsFromExtent(srcExtent,cellSize)

  # Calculate minCol, minRow and maxRow.  
  minCol = UT.trunc(abs(srcX1-inX1) / float(cellSize))
  minRow = UT.trunc(abs(srcY1-inY1) / float(cellSize))
  maxRow = minRow + nrRows

  # Recalculate minRow because of different origin.
  minRow = inNrRows - maxRow

  return (minCol,minRow,nrCols,nrRows)

#-------------------------------------------------------------------------------
# Upper left col/row = 0,0.
# Extent is a list of [minx,miny,maxx,maxy].
# Returns the upper/left cell corner.
def calcUpperLeftXYFromColRow(col,row,extent,cellSize):
  precision = 9
  ulX = extent[0]
  ulY = extent[3]
  x = ulX + col * cellSize
  y = ulY - row * cellSize
  x = round(x,precision)
  y = round(y,precision)
  return (x,y)

#-------------------------------------------------------------------------------
# Use a delta value, because raster cellsizes can be slightly different from the
# default cellsizes.
def cellSizeToCellSizeName(cellSize: float) -> str:
  delta = cellSize / 1000000
  for idx,defCellSize in  enumerate(GLOB.cellSizes):
    if (cellSize>=(defCellSize - delta)) and (cellSize<=(defCellSize + delta)):
      return GLOB.cellSizeNames[idx]
  # Not found.
  Err.raiseGlobioError(Err.UserDefined1,"No valid cellsize specified (cellSizeToCellSizeName).")

#-------------------------------------------------------------------------------
# Posible values from hight to low compression rate: LZW,DEFLATE,PACKBITS
def checkCompressionMode(compressionMode):
  if compressionMode == "":
    Err.raiseGlobioError(Err.NoCompressionModeSpecified)
  compressionModeUpper = compressionMode.upper()
  if (compressionModeUpper != "LZW") and (compressionModeUpper != "DEFLATE") and \
     (compressionModeUpper != "PACKBITS"):
    Err.raiseGlobioError(Err.InvalidCompressionMode1,compressionMode)
    
#-------------------------------------------------------------------------------
# Creates a raster dataset.
# DriverName can be: "MEM" or "GTiff".
# Extent is a list of [minx,miny,maxx,maxy].
def createRasterDataset(driverName,fileName,extent,cellSize,dataType,
                        compressionMode=None):

  if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:
    Err.raiseGlobioError(Err.NotImplemented1,"createRasterDataset")
  else:
    # Set properties.          
    nrCols, nrRows = calcNrColsRowsFromExtent(extent,cellSize)
          
    # Get the driver.
    driver = gd.GetDriverByName(driverName)
  
    #Log.dbg("createRasterDataset - rasterType: %s" % dataType)
  
    # Get raster type.
    rasterType = dataTypeNumpyToGdal(dataType)
    
    #Log.dbg("Numpy rasterType: %s" % str(rasterType))
    
    # Set options.
    if driverName.lower() == "gtiff":
      options = ["BIGTIFF=IF_SAFER"]
    else:
      options = []
 
    # Set compression mode options?   
    if not compressionMode is None:
      checkCompressionMode(compressionMode)
      options.append("COMPRESS="+compressionMode)
        
    # Create raster with 1 band.
    dataset = driver.Create(fileName,nrCols,nrRows,1,rasterType,options=options)

    # Set the transform based on the upper left corner and given pixel dimensions.
    transform = [extent[0], cellSize, 0.0, extent[3], 0.0, -cellSize]
    dataset.SetGeoTransform(transform)
    
    # Set projection (WGS84).
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(GLOB.epsgWGS84)
    dataset.SetProjection(srs.ExportToWkt())

    return dataset    

#-------------------------------------------------------------------------------
# Conversion between ArcGIS types and Numpy types.
def dataTypeArcGISToNumpy(dataType):
  if dataType==0:
    Err.raiseGlobioError(Err.InvalidArcGISDataType1,dataTypeArcGISToString(dataType))
  elif dataType==1:
    Err.raiseGlobioError(Err.InvalidArcGISDataType1,dataTypeArcGISToString(dataType))
  elif dataType==2:
    Err.raiseGlobioError(Err.InvalidArcGISDataType1,dataTypeArcGISToString(dataType))
  elif dataType==3:
    return np.uint8
  elif dataType==4:
    return np.int8
  elif dataType==5:
    return np.uint16
  elif dataType==6:
    return np.int16
  elif dataType==7:
    return np.uint32
  elif dataType==8:
    return np.int32
  elif dataType==9:
    return np.float32
  elif dataType==10:
    return np.float64
  elif dataType==11:
    Err.raiseGlobioError(Err.InvalidArcGISDataType1,dataTypeArcGISToString(dataType))
  elif dataType==12:
    Err.raiseGlobioError(Err.InvalidArcGISDataType1,dataTypeArcGISToString(dataType))
  elif dataType==13:
    Err.raiseGlobioError(Err.InvalidArcGISDataType1,dataTypeArcGISToString(dataType))
  elif dataType==14:
    Err.raiseGlobioError(Err.InvalidArcGISDataType1,dataTypeArcGISToString(dataType))
  else:
    Err.raiseGlobioError(Err.InvalidGDALDataType1,dataTypeArcGISToString(dataType))

#-------------------------------------------------------------------------------
def dataTypeArcGISToString(dataType):
  if dataType==0:
    return "1-bit"
  elif dataType==1:
    return "2-bit"
  elif dataType==2:
    return "4-bit"
  elif dataType==3:
    return "8-bit unsigned integer"
  elif dataType==4:
    return "8-bit signed integer"
  elif dataType==5:
    return "16-bit unsigned integer"
  elif dataType==6:
    return "16-bit signed integer"
  elif dataType==7:
    return "32-bit unsigned integer"
  elif dataType==8:
    return "32-bit signed integer"
  elif dataType==9:
    return "32-bit floating point"
  elif dataType==10:
    return "64-bit double precision"
  elif dataType==11:
    return "8-bit complex"
  elif dataType==12:
    return "16-bit complex"
  elif dataType==13:
    return "32-bit complex"
  elif dataType==14:
    return "64-bit complex"
  else:
    return "unknown"

#-------------------------------------------------------------------------------
# Conversion between GDAL types and Numpy types.
def dataTypeGdalToNumpy(dataType):
  if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:
    Err.raiseGlobioError(Err.NotImplemented1,"dataTypeGdalToNumpy")
  else:
    if dataType==gd.GDT_Byte:
      return np.uint8
      #return np.byte
    elif dataType==gd.GDT_Int16:
      return np.int16
    elif dataType==gd.GDT_Int32:
      return np.int32
    elif dataType==gd.GDT_UInt16:
      return np.uint16
    elif dataType==gd.GDT_UInt32:
      return np.uint32
    elif dataType==gd.GDT_Float32:
      return np.float32
    elif dataType==gd.GDT_Float64:
      return np.float64
    elif dataType==gd.GDT_CInt16:
      Err.raiseGlobioError(Err.InvalidGDALDataType1,dataTypeGdalToString(dataType))
    elif dataType==gd.GDT_CInt32:
      Err.raiseGlobioError(Err.InvalidGDALDataType1,dataTypeGdalToString(dataType))
    elif dataType==gd.GDT_CFloat32:
      Err.raiseGlobioError(Err.InvalidGDALDataType1,dataTypeGdalToString(dataType))
    elif dataType==gd.GDT_CFloat64:
      Err.raiseGlobioError(Err.InvalidGDALDataType1,dataTypeGdalToString(dataType))
    else:
      Err.raiseGlobioError(Err.InvalidGDALDataType1,dataTypeGdalToString(dataType))

#-------------------------------------------------------------------------------
def dataTypeGdalToString(dataType):
  if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:
    Err.raiseGlobioError(Err.NotImplemented1,"dataTypeGdalToString")
  else:
    if dataType==gd.GDT_Byte:
      return "byte"
    elif dataType==gd.GDT_Int16:
      return "int16"
    elif dataType==gd.GDT_Int32:
      return "int32"
    elif dataType==gd.GDT_UInt16:
      return "uint16"
    elif dataType==gd.GDT_UInt32:
      return "uint32"
    elif dataType==gd.GDT_Float32:
      return "float32"
    elif dataType==gd.GDT_Float64:
      return "float64"
    elif dataType==gd.GDT_CInt16:
      return "cint16"
    elif dataType==gd.GDT_CInt32:
      return "cint32"
    elif dataType==gd.GDT_CFloat32:
      return "cfloat32"
    elif dataType==gd.GDT_CFloat64:
      return "cfloat64"
    else:
      return "unknown"

#-------------------------------------------------------------------------------
# Returns if the datatype is a numpy float type.
def dataTypeNumpyIsFloat(dataType: np.dtype) -> bool:
  if (dataType==np.float) or\
     (dataType==np.float16) or\
     (dataType==np.float32) or\
     (dataType==np.float64):
    return True
  else:
    return False

#-------------------------------------------------------------------------------
# Returns if the datatype is minimal a integer16 type.
def dataTypeNumpyIsMinimalInt16(dataType: np.dtype) -> bool:
  if (dataType==np.uint16) or\
     (dataType==np.uint32) or\
     (dataType==np.uint64) or\
     (dataType==np.int16) or\
     (dataType==np.int32) or\
     (dataType==np.int64):
    return True
  else:
    return False

#-------------------------------------------------------------------------------
# Returns if the datatype is a numpy integer type.
def dataTypeNumpyIsInt(dataType):
  if (dataType==np.uint8) or (dataType==np.uint16) or \
     (dataType==np.uint32) or (dataType==np.uint64) or \
     (dataType==np.byte) or \
     (dataType==np.int8) or (dataType==np.int16) or \
     (dataType==np.int32) or (dataType==np.int64):
    return True
  else:
    return False

#-------------------------------------------------------------------------------
# Conversion between Numpy types and C types.
def dataTypeNumpyToC(dataType):
  if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:
    Err.raiseGlobioError(Err.NotImplemented1,"dataTypeNumpyToC")
  else:
    if dataType==np.int8:
      return ctypes.c_char
    elif dataType==np.int16:
      return ctypes.c_short
    elif dataType==np.int32:
      return ctypes.c_int
    elif dataType==np.int64:
      return ctypes.c_long
    elif dataType==np.uint8:
      return ctypes.c_byte
    elif dataType==np.byte:
      return ctypes.c_byte
    elif dataType==np.uint16:
      return ctypes.c_ushort
    elif dataType==np.uint32:
      return ctypes.c_uint
    elif dataType==np.uint64:
      return ctypes.c_ulong
    elif dataType==np.float16:
      Err.raiseGlobioError(Err.InvalidNumpyDataType1,dataTypeNumpyToString(dataType))
    elif dataType==np.float32:
      return ctypes.c_float
    elif dataType==np.float64:
      return ctypes.c_double
    elif dataType==np.complex64:
      Err.raiseGlobioError(Err.InvalidNumpyDataType1,dataTypeNumpyToString(dataType))
    elif dataType==np.complex128:
      Err.raiseGlobioError(Err.InvalidNumpyDataType1,dataTypeNumpyToString(dataType))
    else:
      Err.raiseGlobioError(Err.InvalidNumpyDataType1,dataTypeNumpyToString(dataType))

#-------------------------------------------------------------------------------
# Conversion between Numpy types and GDAL types.
def dataTypeNumpyToGdal(dataType):
  if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:
    Err.raiseGlobioError(Err.NotImplemented1,"dataTypeNumpyToGdal")
  else:
    if dataType==np.int8:
      Err.raiseGlobioError(Err.InvalidNumpyDataType1,dataTypeNumpyToString(dataType))
    elif dataType==np.int16:
      return gd.GDT_Int16
    elif dataType==np.int32:
      return gd.GDT_Int32
    elif dataType==np.int64:
      Err.raiseGlobioError(Err.InvalidNumpyDataType1,dataTypeNumpyToString(dataType))
    elif dataType==np.uint8:
      return gd.GDT_Byte
    elif dataType==np.byte:
      #return gd.GDT_Byte
      Err.raiseGlobioError(Err.InvalidNumpyDataType1,dataTypeNumpyToString(dataType))
    elif dataType==np.uint16:
      return gd.GDT_UInt16
    elif dataType==np.uint32:
      return gd.GDT_UInt32
    elif dataType==np.uint64:
      Err.raiseGlobioError(Err.InvalidNumpyDataType1,dataTypeNumpyToString(dataType))
    elif dataType==np.float16:
      Err.raiseGlobioError(Err.InvalidNumpyDataType1,dataTypeNumpyToString(dataType))
    elif dataType==np.float32:
      return gd.GDT_Float32
    elif dataType==np.float64:
      return gd.GDT_Float64
    elif dataType==np.complex64:
      Err.raiseGlobioError(Err.InvalidNumpyDataType1,dataTypeNumpyToString(dataType))
    elif dataType==np.complex128:
      Err.raiseGlobioError(Err.InvalidNumpyDataType1,dataTypeNumpyToString(dataType))
    else:
      Err.raiseGlobioError(Err.InvalidNumpyDataType1,dataTypeNumpyToString(dataType))

#-------------------------------------------------------------------------------
# Remark: np.int8 == np.byte.
def dataTypeNumpyToString(dataType):
  if dataType==np.int8:
    return "int8/byte"
  elif dataType==np.int16:
    return "int16"
  elif dataType==np.int32:
    return "int32"
  elif dataType==np.int64:
    return "int64"
  elif dataType==np.byte:
    return "int8/byte"
  elif dataType==np.uint8:
    return "uint8"
  elif dataType==np.uint16:
    return "uint16"
  elif dataType==np.uint32:
    return "uint32"
  elif dataType==np.uint64:
    return "uint64"
  elif dataType==np.float16:
    return "float16"
  elif dataType==np.float32:
    return "float32"
  elif dataType==np.float64:
    return "float64"
  elif dataType==np.complex64:
    return "complex64"
  elif dataType==np.complex128:
    return "complex128"
  else:
    return "unknown"

#-------------------------------------------------------------------------------
# Calculates the geodetic distance between 2 point using the geographic library.
def degreeToKM(lon1,lat1,lon2,lat2):
  R = 6371.0 # km
  dLat = toRad(lat2-lat1)
  dLon = toRad(lon2-lon1)
  a1 = math.sin(dLat/2.0) * math.sin(dLat/2.0)
  a2 = math.cos(toRad(lat1)) * math.cos(toRad(lat2)) 
  a3 = math.sin(dLon/2.0) * math.sin(dLon/2.0)
  a = a1 + a2 * a3
  c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0-a)) 
  d = R * c
  return d

#-------------------------------------------------------------------------------
# Calculates the geodetic distance between 2 point using the geographic library.
#
# Accuracy:
# - 2 lines in RD_NEW -> converted with GDAL to WGS84 -> acc. @@@
def degreeToKM_v2(lon1,lat1,lon2,lat2):
  wgs84 = Geodesic.WGS84
  resultM = wgs84.Inverse(lat1,lon1,lat2,lon2)
  if "s12" in resultM:
    return resultM["s12"] / 1000.0
  else:
    return None

#-------------------------------------------------------------------------------
# Calculates the geodetic area of a polygon using the geographic library.
#
# Arguments:
# - coords: list of tuples with (lon,lat) of the exterior of the polygon.
# Accuracy:
# - 1 poly in RD_NEW -> converted with GDAL to WGS84 -> acc. @@@
# Remarks:
# - The input polygon does not need to be closed (last vertices = first vertices).
#  
def degreeToKM2(coords):
  #wgs84 = geodesic.Geodesic.WGS84
  wgs84 = Geodesic.WGS84
  p = wgs84.Polygon()
  for c in coords:
    p.AddPoint(c[1],c[0])
  _,_,area = p.Compute()
  return abs(area / 1000000.0)

#-------------------------------------------------------------------------------
def esriGridExists(gridName):
  if os.path.isdir(gridName):
    hrdFileName = os.path.join(gridName,"hdr.adf")
    if os.path.isfile(hrdFileName):
      return True
    else:
      return False
  else:
    return False

#-------------------------------------------------------------------------------
# Extent is a list of [minx,miny,maxx,maxy].
def extentToStr(extent):
  return "%s %s %s %s" % (extent[0],extent[1],extent[2],extent[3])

#-------------------------------------------------------------------------------
def fgdbDelete(fgdbName):
  pass

#-------------------------------------------------------------------------------
def fgdbExists(fgdbName):
  if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:
    return arcpy.Exists(fgdbName)
  else:
    if os.path.isdir(fgdbName):
      gdbFileName = os.path.join(fgdbName,"gdb")
      if os.path.isfile(gdbFileName):
        return True  
      else:
        return False  
    else:
      return False  

#-------------------------------------------------------------------------------
def fgdbFcExists(vectorName):
  if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:
    return arcpy.Exists(vectorName)
  else:
    driver = ogr.GetDriverByName("FileGDB")
    fgdbName = getFgdbName(vectorName)
    fcName = getFgdbFcName(vectorName).lower()
    try:
      fgdb = driver.Open(fgdbName, 0)
      for idx in range(fgdb.GetLayerCount()):
        if fgdb.GetLayerByIndex(idx).GetName().lower()==fcName:
          return True
      return False
    except:
      return False

#-------------------------------------------------------------------------------
def geometryTypeToStr(geometryType):
  if geometryType == ogr.wkbPoint:
    return "point"
  elif geometryType == ogr.wkbPoint25D:
    return "point25D"
  elif geometryType == ogr.wkbPointM:
    return "pointM"
  elif geometryType == ogr.wkbPointZM:
    return "pointZM"
  elif geometryType == ogr.wkbMultiPoint:
    return "multipoint"
  elif geometryType == ogr.wkbLineString:
    return "linestring"
  elif geometryType == ogr.wkbMultiLineString:
    return "multilinestring"
  elif geometryType == ogr.wkbPolygon:
    return "polygon"
  elif geometryType == ogr.wkbMultiPolygon:
    return "multipolygon"
  else:
    return "unknown"  

#-------------------------------------------------------------------------------
def geoTifExists(fileName):
  return os.path.isfile(fileName)

#-------------------------------------------------------------------------------
def getFgdbName(vectorName):
  idx1 = vectorName.find("\\")
  idx2 = vectorName.find("/")
  if idx1 > idx2:
    c = "\\"
  else:
    c = "/"
  return UT.strBeforeLast(vectorName,c)

#-------------------------------------------------------------------------------
def getFgdbFcName(vectorName):
  idx1 = vectorName.find("\\")
  idx2 = vectorName.find("/")
  if idx1 > idx2:
    c = "\\"
  else:
    c = "/"
  return UT.strAfterLast(vectorName,c)

#-------------------------------------------------------------------------------
# dataType is GDAL datatype.
def getGdalResampleMethod(dataType):
  # Not implemented yet.
  Err.raiseGlobioError(Err.NotImplemented1,"getGdalResampleMethod")

#-------------------------------------------------------------------------------
# Returns the NetCDF filename and arguments as a list.
# A NETCDF datasourceName has the following parts:
#    <path>\<name>.nc#<type>|arg1|arg2|arg3|...
# Return an empty list when not found.
def getNetCDFArguments(datasourceName):
  datasourceName = datasourceName.strip()
  if datasourceName.find("#") < 0:
    return []
  if datasourceName.find("|") < 0:
    return []
  fn = UT.strBefore(datasourceName,"#")
  s = UT.strAfter(datasourceName,"|")
  args = s.split("|")
  args.insert(0,fn)
  return args
# def XgetNetCDFArguments(datasourceName):
#   datasourceName = datasourceName.strip()
#   if datasourceName.find("#") < 0:
#     return []
#   if datasourceName.find("|") < 0:
#     return []
#   s = UT.strAfter(datasourceName,"|")
#   return s.split("|")

#-------------------------------------------------------------------------------
# Returns the .nc filename.
# A NETCDF datasourceName has the following parts:
#    <path>\<name>.nc#<type>|arg1|arg2|arg3|...
# The additional "#" part is not necessary.
def getNetCDFFileName(datasourceName):
  datasourceName = datasourceName.strip()
  if datasourceName.find("#") >= 0:
    return UT.strBefore(datasourceName,"#")
  else:
    return datasourceName

#-------------------------------------------------------------------------------
# Returns the NetCDF type.
# A NETCDF datasourceName has the following formats:
#    <path>\<name>.nc
#    <path>\<name>.nc#<type>
#    <path>\<name>.nc#<type>|arg1|arg2|arg3|...
# Returns an empty string when not found.
def getNetCDFType(datasourceName):
  datasourceName = datasourceName.strip()
  if datasourceName.find("#") < 0:
    return ""
  s = UT.strAfter(datasourceName,"#")
  if s.find("|") < 0:
    return s
  else:
    return UT.strBefore(s,"|")

# #-------------------------------------------------------------------------------
# # Returns the NetCDF type.
# # A NETCDF datasourceName has the following parts:
# #    <path>\<name>.nc#<type>|arg1|arg2|arg3|...
# # Return an empty string when not found.
# def getNetCDFType(datasourceName):
#   datasourceName = datasourceName.strip()
#   if datasourceName.find("#") < 0:
#     return ""
#   if datasourceName.find("|") < 0:
#     return ""
#   s = UT.strAfter(datasourceName,"#")
#   return UT.strBefore(s,"|")

#-------------------------------------------------------------------------------
# dataType is numpy datatype.
def getNoDataValue(dataType):
  if dataType==np.uint8:
    noDataValue = np.iinfo("uint8").max
  elif dataType==np.uint16:
    noDataValue = np.iinfo("uint16").max
  elif dataType==np.uint32:
    noDataValue = np.iinfo("uint32").max
  elif dataType==np.int8:
    noDataValue = np.iinfo("int8").min
  elif dataType==np.int16:
    noDataValue = np.iinfo("int16").min
  elif dataType==np.int32:
    noDataValue = np.iinfo("int32").min
  elif dataType==np.int64:
    noDataValue = np.iinfo("int64").min
  elif dataType==np.float16:
    noDataValue = np.finfo("float16").min
  elif dataType==np.float32:
    # This code gives -3.40282e+38, this values is not accepted by
    # GDAL, -3.4e+38 does!!!
    #noDataValue = np.finfo("float32").min
    # Using -3.4e+38 does not give good results when making a raster mask
    # and selecting on this value like (ras.r == r.noDataValue). 
    # Using -3.0e+38 solves the problem.
    #noDataValue = -3.4e+38
    noDataValue = -3.0e+38
  elif dataType==np.float64:
    noDataValue = np.finfo("float64").min
  elif dataType==np.float:
    noDataValue = np.finfo("float").min
  else:
    noDataValue = -9999.0
  return noDataValue

#-------------------------------------------------------------------------------
def isAsciiGridName(datasourceName):
  return UT.sameText(UT.getFileNameExtension(datasourceName),".asc")

#-------------------------------------------------------------------------------
# Checks if the cellsizes are equal.
def isEqualCellSize(cellSize1,cellSize2):
  return UT.isEqualFloat(cellSize1,cellSize2)

#-------------------------------------------------------------------------------
# Checks if the cols/rows are equal.
def isEqualColsRows(cols1: int, rows1: int,
                    cols2: int, rows2: int) -> bool:
  if (cols1==cols2) and (rows1==rows2):
    return True
  else:
    return False

#-------------------------------------------------------------------------------
# Ext1 and Ext2 are lists of [minx,miny,maxx,maxy].
# Returns True if the difference between the two extents is less then
# a thenth of the cellsize. 
def isEqualExtent(ext1,ext2,cellSize):
  delta = cellSize / 10.0
  if abs(ext1[0]-ext2[0]) >= delta:
    return False
  if abs(ext1[1]-ext2[1]) >= delta:
    return False
  if abs(ext1[2]-ext2[2]) >= delta:
    return False
  if abs(ext1[3]-ext2[3]) >= delta:
    return False
  return True

#-------------------------------------------------------------------------------
# Extent is a list of [minx,miny,maxx,maxy].
def isExtent(extent):
  if not UT.isArray(extent):
    return False
  if len(extent)!=4:
    return False
  for f in extent:
    if not UT.isFloat(f):
      return False
  return True

#-------------------------------------------------------------------------------
# Extent is a list of [minx,miny,maxx,maxy].
def isExtentAligned(extent,cellSize):
  newExtent = alignExtent(extent,cellSize)
  #print "extent,newextent: %s %s" % (extent,newExtent)
  return isEqualExtent(extent,newExtent,cellSize)

#-------------------------------------------------------------------------------
# Returns if the extent is within the fullExtent or touches the border.
# The extents are lists of [minx,miny,maxx,maxy].
def isExtentInExtent(extent,fullExtent,delta=0.000000000001):
  x1 = extent[0]
  y1 = extent[1]
  x2 = extent[2]
  y2 = extent[3]
  return (isPointInExtent(x1,y1,fullExtent,delta) and
          isPointInExtent(x2,y2,fullExtent,delta))

#-------------------------------------------------------------------------------
def isFgdbName(datasourceName):
  return UT.sameText(UT.getFileNameExtension(datasourceName),".gdb")

#-------------------------------------------------------------------------------
def isFgdbFcName(datasourceName):
  fgdbName = getFgdbName(datasourceName)
  if isFgdbName(fgdbName):
    fcName = getFgdbFcName(datasourceName)
    if len(fcName)>0:
      return True
    else:
      return False    
  else:
    return False

#-------------------------------------------------------------------------------
def isGdalRasterName(datasourceName):
  return (isGeoTifName(datasourceName) or isAsciiGridName(datasourceName))

#-------------------------------------------------------------------------------
def isGeoTifName(datasourceName):
  return UT.sameText(UT.getFileNameExtension(datasourceName),".tif")

#-------------------------------------------------------------------------------
# Returns if the datasource name is a valid NetCDF raster name.
# A NETCDF datasourceName has the following formats:
#    <path>\<name>.nc
#    <path>\<name>.nc#<type>
#    <path>\<name>.nc#<type>|arg1|arg2|arg3|...
# The <type> is the NetCDF python class defined in the NetCDF folder.
# @@@At least the <type> and one <arg1> should be specified.
def isNetCDFName(datasourceName):
  datasourceName = datasourceName.strip()

  # 20210114
  # if datasourceName.find("#") < 0:
  #   return False
  # if datasourceName.find("|") < 0:
  #   return False
  # if UT.strAfter(datasourceName,"|") == "":
  #   return False

  # Get the filename.
  fileName = getNetCDFFileName(datasourceName)
  return UT.sameText(UT.getFileNameExtension(fileName),".nc")
# #-------------------------------------------------------------------------------
# # Returns if the datasource name is a valid NetCDF raster name.
# # A NETCDF datasourceName has the following parts:
# #    <path>\<name>.nc#<type>|arg1|arg2|arg3|...
# # The <type> is the NetCDF python class defined in the NetCDF folder.
# # At least the <type> and one <arg1> should be specified.
# def isNetCDFName(datasourceName):
#   datasourceName = datasourceName.strip()
#   if datasourceName.find("#") < 0:
#     return False
#   if datasourceName.find("|") < 0:
#     return False
#   if UT.strAfter(datasourceName,"|") == "":
#     return False
#   # Get the filename.
#   fileName = getNetCDFFileName(datasourceName)
#   return UT.sameText(UT.getFileNameExtension(fileName),".nc")

#-------------------------------------------------------------------------------
# Returns if the point is within the extent or lies on the border.
# Extent is a list of [minx,miny,maxx,maxy].
def isPointInExtent(x,y,extent,delta=0.000000000001):
  # Increase extent with delta.
  minX = extent[0] - delta
  minY = extent[1] - delta
  maxX = extent[2] + delta
  maxY = extent[3] + delta
  # Check point.
  return (x>=minX) and (x<=maxX) and (y>=minY) and (y<=maxY)
  
#-------------------------------------------------------------------------------
def isShapeFileName(datasourceName):
  return UT.sameText(UT.getFileNameExtension(datasourceName),".shp")

#-------------------------------------------------------------------------------
def listDrivers():
  if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:
    Err.raiseGlobioError(Err.NotImplemented1,"listDrivers")
  else:
    cnt = ogr.GetDriverCount()
    formatsList = []
    for i in range(cnt):
      driver = ogr.GetDriver(i)
      driverName = driver.GetName()
      if not driverName in formatsList:
        formatsList.append(driverName)
    cnt = gd.GetDriverCount()
    formatsList.sort()
    for drv in formatsList:
      print(drv)

#-------------------------------------------------------------------------------
# Converts a masked array to a simple numpy array.
def maskedToNumpy(maskedArray,noDataValue=None):

  # Is masked?
  if not hasattr(maskedArray,"mask"):
    # No conversion needed.
    return maskedArray

  # Get nodata value.
  if noDataValue is None:
    noDataValue = getNoDataValue(maskedArray.dtype)

  # Create new array.
  npArray = np.full(maskedArray.shape,noDataValue,maskedArray.dtype)

  # Copy non-masked values and retrun.
  npArray[~maskedArray.mask] = maskedArray[~maskedArray.mask]
  return npArray

#-------------------------------------------------------------------------------
# Returns if the NetCDF filename exists.
# A NETCDF datasourceName has the following formats:
#    <path>\<name>.nc
#    <path>\<name>.nc#<type>
#    <path>\<name>.nc#<type>|arg1|arg2|arg3|...
def netCDFExists(datasourceName):
  # Do we have a bare .nc filename?
  if datasourceName.lower().endswith(".nc"):
    return os.path.isfile(datasourceName)
  # Check if valid filename.
  if not isNetCDFName(datasourceName):
    return False
  # Get the .nc filename and check.
  fileName = getNetCDFFileName(datasourceName)
  if not os.path.isfile(fileName):
    return False
  # Get the NetCDF type.
  netCDFType = getNetCDFType(datasourceName)
  # Do we have no NetCDF type?
  if netCDFType == "":
    return False
  # Get the class instance.
  pInstance = UT.createClassInstance(GLOB.netCDFImportPath,netCDFType)
  #print("netCDFExists %s" % (pInstance,))
  # TODO: Check the (number of) arguments???
  if pInstance is None:
    return False
  else:
    return True
# #-------------------------------------------------------------------------------
# # Returns if the NetCDF filename exists.
# # A NETCDF RasterName has the following parts:
# #    <path>\<name>.nc#<type>|arg1|arg2|arg3|...
# def netCDFExists(datasourceName):
#   # Check if valid filename.
#   if not isNetCDFName(datasourceName):
#     return False
#   # Get the .nc file and check.
#   fileName = getNetCDFFileName(datasourceName)
#   if not os.path.isfile(fileName):
#     return False
#   # Get the NetCDF type.
#   netCDFType = getNetCDFType(datasourceName)
#   # Get the NetCDF arguments.
#   #netCDFArgs = getNetCDFArguments(datasourceName)
#   # Get the class instance.
#   pInstance = UT.createClassInstance(GLOB.netCDFImportPath,netCDFType)
#   #print("netCDFExists %s" % (pInstance,))
#   # TODO: Check the (number of) arguments???
#   if pInstance is None:
#     return False
#   else:
#     return True

#-------------------------------------------------------------------------------
def rasterCellSize(rasterName):
  if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:
    propResult = arcpy.GetRasterProperties_management(rasterName,"CELLSIZEX")
    cellSize = UT.asFloat(propResult.getOutput(0))
    propResult = None
    return cellSize
  else:
    # Open raster.
    dataset = gd.Open(rasterName,gd.GA_ReadOnly)
    # Get cellsize.  
    cellSize = dataset.GetGeoTransform()[1]
    dataset = None
    return cellSize

#-------------------------------------------------------------------------------
# # Creates an unsigned integer raster with random values between 0 and 255.
# def rasterCopy(path,name,cellSize,extent):
#   if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:
#     Err.raiseGlobioError(Err.NotImplemented1,"rasterCopy")
#   else:
#     fullName = os.path.join(path,name)
#     rasterDelete(fullName)
#     # Create a floating point raster.
#     raster = arcpy.sa.CreateRandomRaster(123, cellSize, extent)
#     # Convert to an integer raster with values between 0 and 255.
#     intRaster = arcpy.sa.Int(raster * 255)
#     intRaster.save(fullName)
#     intRaster = None

#-------------------------------------------------------------------------------
# Source: PyGeoprocessing.
def rasterCreateFromExtent(rasterFileName,extent,cellSize,dataType,nodata):
  # """Create a blank raster based on a vector file extent.
  # Args:
  #     xRes: the x size of a pixel in the output dataset must be a
  #         positive value
  #     yRes: the y size of a pixel in the output dataset must be a
  #         positive value
  #     format: gdal GDT pixel type
  #     nodata: the output nodata value
  #     rasterFile (string): URI to file location for raster
  #     extent: extent of output raster
  #
  # Returns:
  #     raster: blank raster whose bounds fit within `shp`s bounding box
  #         and features are equivalent to the passed in data
  # """
  if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:
    Err.raiseGlobioError(Err.NotImplemented1,"rasterCreateFromExtent")
  else:
    width = UT.trunc(math.ceil(abs(extent[1] - extent[0]) / cellSize))
    height = UT.trunc(math.ceil(abs(extent[3] - extent[2]) / cellSize))
  
    Log.dbg("Cols,rows: %s %s" % (width,height))
  
    # Get the driver.
    driver = gd.GetDriverByName('GTiff')
  
    # 1 means only create 1 band
    dataset = driver.Create(rasterFileName,width,height,1,
                            dataType,options=['BIGTIFF=IF_SAFER'])
    dataset.GetRasterBand(1).SetNoDataValue(nodata)
  
    # Set the transform based on the upper left corner and given pixel dimensions.
    rasterTransform = [extent[0], cellSize, 0.0, extent[3], 0.0, -cellSize]
    dataset.SetGeoTransform(rasterTransform)
  
    # Use the same projection on the raster as the shapefile.
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    dataset.SetProjection(srs.ExportToWkt())
  
    # Initialize everything to nodata
    dataset.GetRasterBand(1).Fill(nodata)
    dataset.GetRasterBand(1).FlushCache()
  
    return dataset

#-------------------------------------------------------------------------------
# Creates an unsigned integer raster with random values between 0 and 255.
def rasterCreateRandom(path,name,cellSize,extent):
  if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:
    fullName = os.path.join(path,name)
    rasterDelete(fullName)
    # Create a floating point raster.
    raster = arcpy.sa.CreateRandomRaster(123, cellSize, extent)
    # Convert to an integer raster with values between 0 and 255.
    intRaster = arcpy.sa.Int(raster * 255)
    intRaster.save(fullName)
    intRaster = None
  else:
    Err.raiseGlobioError(Err.NotImplemented1,"rasterCreateRandom")

#-------------------------------------------------------------------------------
def rasterDelete(rasterName):
  if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:
    if rasterExists(rasterName):
      arcpy.Delete_management(rasterName)
  else:
    if asciiGridExists(rasterName) or geoTifExists(rasterName):
      # Remove raster file.
      os.remove(rasterName)
      # Remove additional esri files.
      ext = UT.getFileNameExtension(rasterName)
      fileName = rasterName.replace(ext,ext+".ovr")
      if os.path.isfile(fileName):
        os.remove(fileName)
      fileName = rasterName.replace(ext,ext+".aux.xml")
      if os.path.isfile(fileName):
        os.remove(fileName)
      fileName = rasterName.replace(ext,ext+".vat.cpg")
      if os.path.isfile(fileName):
        os.remove(fileName)
      fileName = rasterName.replace(ext,ext+".vat.dbf")
      if os.path.isfile(fileName):
        os.remove(fileName)
    elif netCDFExists(rasterName):
      fileName = getNetCDFFileName(rasterName)
      # Remove .nc file.
      if os.path.isfile(fileName):
        os.remove(fileName)

#-------------------------------------------------------------------------------
def rasterDatasetCellSize(rasterDataset):
  if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:
    Err.raiseGlobioError(Err.NotImplemented1,"rasterDatasetCellSize")
  else:
    return rasterDataset.GetGeoTransform()[1]

#-------------------------------------------------------------------------------
def rasterExists(rasterName):
  if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:
    return arcpy.Exists(rasterName)
  else:
    if esriGridExists(rasterName) or asciiGridExists(rasterName) or \
       geoTifExists(rasterName) or netCDFExists(rasterName):
      return True
    else:
      return False

#-------------------------------------------------------------------------------
def rasterExtent(rasterName):
  pInfo = rasterGetInfo(rasterName)
  return pInfo.extent

#-------------------------------------------------------------------------------
def rasterNrBands(rasterName):
  pInfo = rasterGetInfo(rasterName)
  return pInfo.extent

#-------------------------------------------------------------------------------
# Converts a value to a string according to his numpy datatype.
# So integers without a decimal point.
def rasterValueToString(value,dataType,precision=1):
  if value is None:
    return "-"
  if (dataType==np.int8) or (dataType==np.int16) or (dataType==np.int32) or \
     (dataType==np.int64) or (dataType==np.byte) or (dataType==np.uint8) or \
     (dataType==np.uint16) or (dataType==np.uint32) or (dataType==np.uint64):
    return UT.intToStr(value,False)
  elif (dataType==np.float16) or (dataType==np.float32) or (dataType==np.float64):
    if value < -1e+10:
      return UT.floatToStrE(value,1,False)
    else:
      return UT.floatToStr(value,precision,False)
  else:
    return "%s" % value

#-------------------------------------------------------------------------------
# Returns object with: cellSize,nrCols,nrRows,extent,noDataValue. 
def rasterGetInfo(rasterName):
  if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:

    # Create info object.
    pInfo = RasterInfo()
    
    # Get cellsize.
    propResult = arcpy.GetRasterProperties_management(rasterName,"CELLSIZEX")
    pInfo.cellSize = UT.asFloat(propResult.getOutput(0))
    
    # Get nrCols/nrRows/nrBands.
    propResult = arcpy.GetRasterProperties_management(rasterName,"COLUMNCOUNT")
    pInfo.nrCols = int(propResult.getOutput(0))
    propResult = arcpy.GetRasterProperties_management(rasterName,"ROWCOUNT")
    pInfo.nrRows = int(propResult.getOutput(0))
    #propResult = arcpy.GetRasterProperties_management(rasterName,"BANDCOUNT")
    #pInfo.nrBands = int(propResult.getOutput(0))
   
    # Get extent.
    propResult = arcpy.GetRasterProperties_management(rasterName,"LEFT")
    minX = UT.asFloat(propResult.getOutput(0))
    propResult = arcpy.GetRasterProperties_management(rasterName,"BOTTOM")
    minY = UT.asFloat(propResult.getOutput(0))
    propResult = arcpy.GetRasterProperties_management(rasterName,"RIGHT")
    maxX = UT.asFloat(propResult.getOutput(0))
    propResult = arcpy.GetRasterProperties_management(rasterName,"TOP")
    maxY = UT.asFloat(propResult.getOutput(0))
    pInfo.extent = [minX,minY,maxX,maxY]
  
    # Get nodata value.
    rasterBandName = os.path.join(rasterName,"Band_1")
    rasDesc=arcpy.Describe(rasterBandName)
    pInfo.noDataValue = rasDesc.noDataValue
    # 20201118
    #pInfo.noDataValue = rasDesc.height
    propResult = arcpy.GetRasterProperties_management(rasterName,"VALUETYPE")
    dataType = int(propResult.getOutput(0))
    pInfo.dataType = dataTypeArcGISToNumpy(dataType)
    
    return pInfo
  
  else:
    # Create info object.
    pInfo = RasterInfo()

    if isGdalRasterName(rasterName):
      # Open raster.
      dataset = gd.Open(rasterName,gd.GA_ReadOnly)
      # Read first band.
      band = dataset.GetRasterBand(1)
      # Get cellsize.
      pInfo.cellSize = dataset.GetGeoTransform()[1]
      # Get nrCols/nrRows/nrBands.
      pInfo.nrCols = dataset.RasterXSize
      pInfo.nrRows = dataset.RasterYSize
      #pInfo.nrBands = dataset.RasterCount
      # Get extent.
      pInfo.extent = calcExtentFromGT(dataset.GetGeoTransform(),pInfo.nrCols,pInfo.nrRows)
      # Get nodata value.
      pInfo.noDataValue = band.GetNoDataValue()
      # Get nodata value.
      gdalDataType = band.DataType
      pInfo.dataType = dataTypeGdalToNumpy(gdalDataType)

      # Get metadata.
      meta = dataset.GetMetadata("IMAGE_STRUCTURE")
      if not meta is None:
        # Get compression type.
        compression = meta.get("COMPRESSION",None)
        if compression is None:
          pInfo.compression = "None"
        else:
          pInfo.compression = compression

      # Close and clean up dataset
      del band
      gd.Dataset.__swig_destroy__(dataset)
      del dataset

    else:

      # Get the NetCDF type/classname.
      netCDFType = getNetCDFType(rasterName)

      # Get the NetCDF arguments.
      netCDFArgs = getNetCDFArguments(rasterName)

      # Create the NetCDF class instance.
      netCDF = UT.createClassInstance(GLOB.netCDFImportPath,netCDFType)

      # Init the NetCDF file.
      netCDF.init(*netCDFArgs)

      # Reads the raster info (extent,cellsize,nrCols,nrRows,dataType,noDataValue).
      netCDF.readInfo()

      # Get the info.
      pInfo.cellSize = netCDF.cellSize
      pInfo.nrCols = netCDF.nrCols
      pInfo.nrRows = netCDF.nrRows
      pInfo.extent = netCDF.extent[:]
      pInfo.noDataValue = netCDF.noDataValue
      pInfo.dataType = netCDF.dataType
      pInfo.compression = None

      # Cleanup.
      del netCDF

    return pInfo

#-------------------------------------------------------------------------------
def rasterHasExtentCellSize(rasterName,extent,cellSize):
  # Get raster info.
  pInfo = rasterGetInfo(rasterName)
  # Extent not equal.
  if not isEqualCellSize(pInfo.extent,extent):
    return False
  # Cellsize not equal.
  if not isEqualCellSize(pInfo.cellSize,cellSize):
    return False
  return True

#-------------------------------------------------------------------------------
# Generate 2d semi-random data with values between 0.0 and 1.0.
def semiRandomNoiseGet(nrCols: int,nrRows: int):
  #global __randomState
  return __randomState.random((nrRows,nrCols))

#-------------------------------------------------------------------------------
# Reseed semi-random noise generator.
def semiRandomNoiseSeed(seed: int):
  global __randomState
  __randomState = np.random.RandomState(seed)

#-------------------------------------------------------------------------------
def shapeFileExists(vectorName):
  if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:
    return arcpy.Exists(vectorName)
  else:
    if os.path.isfile(vectorName):
      ext = UT.getFileNameExtension(vectorName)
      fileName = vectorName.replace(ext,".dbf")
      if not os.path.isfile(fileName):
        return False
      fileName = vectorName.replace(ext,".shx")
      if not os.path.isfile(fileName):
        return False
      return True
    else:
      return False

#-------------------------------------------------------------------------------
def shapeFileDelete(vectorName):
  if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:
    if shapeFileExists(vectorName):
      arcpy.Delete_management(vectorName)
  else:
    driver = ogr.GetDriverByName("ESRI Shapefile")
    driver.DeleteDataSource(vectorName)

#-------------------------------------------------------------------------------
def strToGeometryType(s):
  s = s.lower()
  if s == "point":
    return ogr.wkbPoint
  elif s == "multipoint":
    return ogr.wkbMultiPoint
  elif s == "linestring":
    return ogr.wkbLineString
  elif s == "multilinestring":
    return ogr.wkbMultiLineString
  elif s == "polygon":
    return ogr.wkbPolygon
  elif s == "multipolygon":
    return ogr.wkbMultiPolygon
  else:
    return None  

#-------------------------------------------------------------------------------
def toRad(degree):
  return degree * 3.14 / 180.0

#-------------------------------------------------------------------------------
def vectorExists(vectorName):
  if shapeFileExists(vectorName) or fgdbFcExists(vectorName):
    return True
  else:
    return False

#-------------------------------------------------------------------------------
def vectorDelete(vectorName):
  if isShapeFileName(vectorName) and shapeFileExists(vectorName):
    shapeFileDelete(vectorName)

#-------------------------------------------------------------------------------
# Writes the raster(data) to a tempory raster file.
# Raster is a Raster or an np.array.
# If a Raster, a copy is made and written.
def writeTmpRaster(raster,outDir,tmpFileName,
                   extent=None,cellSize=None,infoCaption=""):
  from GlobioModel.Core.Raster import Raster
  if not GLOB.saveTmpData:
    return
  if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:
    Err.raiseGlobioError(Err.NotImplemented1,"writeTmpRaster")

  # Show info message?
  if infoCaption != "":
    Log.info("%s: %s" % (infoCaption,tmpFileName))
  # Set filename.
  if os.path.dirname(tmpFileName)=="":
    if outDir is None:
      Log.info("Warning: writing tmp raster, no outdir specified.")
      return
    tmpFileName = os.path.join(outDir,tmpFileName)
  # Check filename.
  if rasterExists(tmpFileName):
    rasterDelete(tmpFileName)
  # Is Raster object?
  if isinstance(raster,Raster):
    # It's a Raster.
    # Make a copy (because of potential locking problems).
    tmpRaster = Raster(tmpFileName)
    tmpRaster.initRasterLike(raster)
    tmpRaster.raster = raster.raster
  else:
    # It's a np.array.
    if extent is None:
      Log.info("Warning: writing tmp raster, no extent specified.")
      return
    if cellSize is None:
      Log.info("Warning: writing tmp raster, no cellSize specified.")
      return
    noDataValue = getNoDataValue(raster.dtype)
    tmpRaster = Raster(tmpFileName)
    tmpRaster.initRasterEmpty(extent,cellSize,raster.dtype,noDataValue)
    tmpRaster.raster = raster
  # Write raster.
  tmpRaster.write()
  del tmpRaster

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":

  #-----------------------------------------------------------------------------
  def msgExt(extent):
    print(extentToStr(extent))
  
  #-----------------------------------------------------------------------------
  def testAlignExtent():
    
    extent = [24.4,33.9,28.3,37.1]
    
    msgExt(alignExtent(extent,1))
    msgExt(alignExtent(extent,0.5))
    msgExt(alignExtent(extent,0.2))

    # LET OP:
    #print alignExtent(extent,0.2)
    #GEEFT: [24.400000000000002, 33.800000000000004, 28.200000000000003, 37.00000000000001]

    cellSize = 50
    extent = [120,210,301,402]
    print("-------------")
    msgExt(extent)
    print("%s -> %s" % (extent,alignExtent(extent,cellSize)))
    msgExt(extent)

    extent = [120,210,300,400]
    print("%s -> %s" % (extent,alignExtent(extent,cellSize)))

    extent = [100,200,300,400]
    print("%s -> %s" % (extent,alignExtent(extent,cellSize)))

  #-----------------------------------------------------------------------------
  def testCalcExtentWidthHeight():
    extent = [-180,-90,180,90]
    print(calcExtentWidthHeight(extent))

  #-----------------------------------------------------------------------------
  def testCalcExtentOverlap():
    extent1 = [0,0,10,10]
    
    extent2 = [2,2,8,8]
    print(calcExtentOverlap(extent1,extent2))

    extent2 = [8,8,12,12]
    print(calcExtentOverlap(extent1,extent2))

    extent2 = [10,10,12,12]
    print(calcExtentOverlap(extent1,extent2))

    extent2 = [11,11,12,12]
    print(calcExtentOverlap(extent1,extent2))

  #-------------------------------------------------------------------------------
  # (0, 0)
  # (0, 7)
  # (9, 0)
  # (9, 9)
  # [[ 0  1  2  3  4  5  6  7]
  #  [ 8  9 10 11 12 13 14 15]
  #  [16 17 18 19 20 21 22 23]
  #  [24 25 26 27 28 29 30 31]
  #  [32 33 34 35 36 37 38 39]
  #  [40 41 42 43 44 45 46 47]]
  # 0 0 - 0
  # 5 7 - 47
  # [100, 200, 108, 206]
  # 100 200 - 0 5 - 40
  # 100 206 - 0 0 - 0
  # 108 200 - 7 5 - 47
  # 108 206 - 7 0 - 7
  # ----------------
  # 100 201 - 0 4 - 32
  # 101 200 - 1 5 - 41
  # 101 201 - 1 4 - 33
  # 101.5 201.5 - 1 4 - 33
  # 101.99 201.99 - 1 4 - 33
  # 102 202 - 2 3 - 26
  # 108 206 - 7 0 - 7
  # 109 207 - -1 -1 - Not valid.
  def testCalcColRowFromXY():
    extent = [0,0,100,100]
    cellSize = 10
    x = 0
    y = 100
    print(calcColRowFromXY(x,y,extent,cellSize))

    x = 0
    y = 20
    print(calcColRowFromXY(x,y,extent,cellSize))

    x = 100
    y = 100
    print(calcColRowFromXY(x,y,extent,cellSize))

    x = 100
    y = 0
    print(calcColRowFromXY(x,y,extent,cellSize))

#     arr = np.array([[ 0,  0,  1,  1,  2,  5,  3,  3],
#                     [ 2,  0,  1,  4,  4,  2,  3,  3],
#                     [ 0,  0,  1,  1,  2,  5,  3,  3],
#                     [ 2,  0,  1,  4,  4,  2,  3,  3],
#                     [ 0,  5,  1,  1,  2,  5,  3,  3],
#                     [ 5,  5,  1,  4,  4,  2,  3,  3]])
    arr = np.arange(6*8).reshape(6,8)
    extent = [100,200,108,206]
    cellSize = 1
    print(arr)
    r = 0
    c = 0
    print("%s %s - %s" % (r,c,arr[r,c]))
    r = 5
    c = 7
    print("%s %s - %s" % (r,c,arr[r,c]))
    print(extent)
    x = 100
    y = 200
    c,r = calcColRowFromXY(x,y,extent,cellSize)
    print("%s %s - %s %s - %s" % (x,y,c,r,arr[r,c]))
    x = 100
    y = 206
    c,r = calcColRowFromXY(x,y,extent,cellSize)
    print("%s %s - %s %s - %s" % (x,y,c,r,arr[r,c]))
    x = 108
    y = 200
    c,r = calcColRowFromXY(x,y,extent,cellSize)
    print("%s %s - %s %s - %s" % (x,y,c,r,arr[r,c]))
    x = 108
    y = 206
    c,r = calcColRowFromXY(x,y,extent,cellSize)
    print("%s %s - %s %s - %s" % (x,y,c,r,arr[r,c]))

    # 20161021
    print("----------------")
    x = 100
    y = 201
    c,r = calcColRowFromXY(x,y,extent,cellSize)
    print("%s %s - %s %s - %s" % (x,y,c,r,arr[r,c]))
    x = 101
    y = 200
    c,r = calcColRowFromXY(x,y,extent,cellSize)
    print("%s %s - %s %s - %s" % (x,y,c,r,arr[r,c]))
    x = 101
    y = 201
    c,r = calcColRowFromXY(x,y,extent,cellSize)
    print("%s %s - %s %s - %s" % (x,y,c,r,arr[r,c]))
    x = 101.5
    y = 201.5
    c,r = calcColRowFromXY(x,y,extent,cellSize)
    print("%s %s - %s %s - %s" % (x,y,c,r,arr[r,c]))
    x = 101.99
    y = 201.99
    c,r = calcColRowFromXY(x,y,extent,cellSize)
    print("%s %s - %s %s - %s" % (x,y,c,r,arr[r,c]))
    x = 102
    y = 202
    c,r = calcColRowFromXY(x,y,extent,cellSize)
    print("%s %s - %s %s - %s" % (x,y,c,r,arr[r,c]))
    x = 108
    y = 206
    c,r = calcColRowFromXY(x,y,extent,cellSize)
    print("%s %s - %s %s - %s" % (x,y,c,r,arr[r,c]))
    x = 109
    y = 207
    c,r = calcColRowFromXY(x,y,extent,cellSize)
    if (c<0) or (r<0):
      print("%s %s - %s %s - Not valid." % (x,y,c,r))
    else:
      print("%s %s - %s %s - %s" % (x,y,c,r,arr[r,c]))

    print("----------------")
    extent = [0.0,0.0,10.0,10.0]
    cellSize = 10.0
    # lr    
    x = extent[0]
    y = extent[1]
    print(calcColRowFromXY(x,y,extent,cellSize))
    # ALL (0,0)
    # ur    
    x = extent[0]
    y = extent[3]
    print(calcColRowFromXY(x,y,extent,cellSize))
    # ul
    x = extent[2]
    y = extent[3]
    print(calcColRowFromXY(x,y,extent,cellSize))
    # ll
    x = extent[2]
    y = extent[1]
    print(calcColRowFromXY(x,y,extent,cellSize))
    
  #-------------------------------------------------------------------------------
  # (8, 6)
  # (8, 6)
  # (122, 1)
  # (122, 2)
  def testNrCalcColsRowsFromExtent():
    cellSize = 1
    extent = [100,200,108,206]
    print(calcNrColsRowsFromExtent(extent,cellSize))

    cellSize = 1
    extent = [100.5,200.5,108.5,206.5]
    print(calcNrColsRowsFromExtent(extent,cellSize))

    cellSize = 0.2
    extent = [100,100.0,124.4,100.399999]
    print(calcNrColsRowsFromExtent(extent,cellSize))

    cellSize = 0.2
    extent = [100,100.0,124.4,100.4]
    print(calcNrColsRowsFromExtent(extent,cellSize))

  #-------------------------------------------------------------------------------
  def testCalcExtentFromUpperLeftXY():
    extent = [-180,-90,180,90]
    print(extent)
    print(calcExtentFromUpperLeftXY(-180,90,6,3,30))

  #-------------------------------------------------------------------------------
  # Methode wordt gebruikt in Raster.resample.
  def testTruncExtent():
    extent = [-180.0044642857, -56.01339243789997, 179.99495771429997, 89.99361556210002]

    fromCellSize = 0.008929
    toCellSize = 0.5

    print("From cellsize: %s" % fromCellSize)
    print("To cellsize: %s" % toCellSize)

    # Calculate step factor.  
    step = UT.trunc(toCellSize / fromCellSize)

    Log.dbg("Downsampling with factor %s..." % step)

    nrCols,nrRows = calcNrColsRowsFromExtent(extent,fromCellSize)
    
    # Calculate new number of cols/rows.
    newNrCols = nrCols / step
    newNrRows = nrRows / step

    newNrCols2,newNrRows2 = calcNrColsRowsFromExtent(extent,toCellSize)
    
    Log.dbg("Cols,Rows: %s %s" % (nrCols,nrRows))
    Log.dbg("New Cols,Rows: %s %s" % (newNrCols,newNrRows))
    Log.dbg("New Cols2,Rows2: %s %s" % (newNrCols2,newNrRows2))

    # Calculate number of cols/rows with original cellsize.
    truncNrCols = newNrCols * step
    truncNrRows = newNrRows * step

    Log.dbg("Trunc Cols,Rows: %s %s" % (truncNrCols,truncNrRows))
    
    # Different from raster number of cols/rows?
    if (nrCols!=truncNrCols) or (nrRows!=truncNrRows):
      Log.dbg("New raster will be truncated...")
      # Recalculate extent.
      newExtent = calcExtentFromUpperLeftXY(extent[0],extent[3],
                                            newNrCols,newNrRows,toCellSize)
    else:
      newExtent = extent

    calcExtent = calcExtentFromUpperLeftXY(extent[0],extent[3],nrCols,nrRows,fromCellSize)

    Log.dbg("Calc Extent: %s" % calcExtent)

    Log.dbg("Extent: %s" % (extent))
    Log.dbg("New Extent: %s" % (newExtent))

    Log.dbg("Calc Extent W/H: %s %s" % calcExtentWidthHeight(calcExtent))
    Log.dbg("Extent W/H: %s %s" % calcExtentWidthHeight(extent))
    Log.dbg("New Extent W/H: %s %s" % calcExtentWidthHeight(newExtent))

  #-------------------------------------------------------------------------------
  # Extent: [-180, -90, 180, 90]
  # Cellsize: 0.00833333333333
  # 30sec c/r: 43200 21600
  # 30sec newExtent: [-180, -90.0, 180.0, 90]
  def testCellSizeExtent():
    # Calculate cellsize.
#     cellSize_1deg = 1.0
#     cellSize_30min = 30.0 / 60.0
#     cellSize_5min = 5.0 / 60.0
    cellSize_30sec = 1.0 / 60.0 * 30.0 / 60.0
#     cellSize_10sec = 1.0 / 60.0 * 10.0 / 60.0
  
    # Extent in degrees.
    extent = [-180,-90,180,90]
    print("Extent: %s" % (extent))

    cellSize = cellSize_30sec    
    print("Cellsize: %s" % (cellSize))
    
    c,r = calcNrColsRowsFromExtent(extent,cellSize)
    print("30sec c/r: %s %s" % (c,r))

    newExtent = calcExtentFromUpperLeftXY(extent[0],extent[3], c,r,cellSize)
    print("30sec newExtent: %s" % (newExtent))

  #-----------------------------------------------------------------------------
  def testIsEqualExtent():
    ext1 = [-180.0, -90.0, 180.0, 90.0]
    ext2 = [-180.0, -90.0, 180.0, 90.0]
    cellSize = 1.0
    print(isEqualExtent(ext1,ext2,cellSize))
    
    ext1 = [-180.0, -90.0, 180.0, 90.0]
    ext2 = [-180.1, -90.1, 180.1, 90.1]
    cellSize = 1.0
    print(isEqualExtent(ext1,ext2,cellSize))

    ext1 = [-180.0, -90.0, 180.0, 90.0]
    ext2 = [-180.1, -90.1, 180.1, 90.1]
    cellSize = 1.1
    print(isEqualExtent(ext1,ext2,cellSize))

    ext1 = [-180.0, -90.0, 180.0, 90.0]
    ext2 = [-180.1, -90.1, 180.1, 90.1]
    cellSize = 0.9
    print(isEqualExtent(ext1,ext2,cellSize))

  #-----------------------------------------------------------------------------
  def testIsExtentAligned():

    extent = [24.4,33.9,28.3,37.1]
    print(isExtentAligned(extent,1))      # False
    print(isExtentAligned(extent,0.5))    # False
    print(isExtentAligned(extent,0.2))    # False

    extent = [24.4,33.8,28.2,37.0]
    print(isExtentAligned(extent,1))      # False
    print(isExtentAligned(extent,0.5))    # False
    print(isExtentAligned(extent,0.2))    # True

    print("----")
    
    # TRUE
    extent = [24.0,33.0,28.0,37.0]
    print(isExtentAligned(extent,1))

    # FALSE
    extent = [24.1,33.1,28.1,37.1]
    print(isExtentAligned(extent,1))

    # TRUE
    extent = [24.4,33.9,28.3,37.1]
    cellSize = 1
    newExtent = alignExtent(extent,cellSize)
    print(isExtentAligned(newExtent,cellSize))

    # TRUE
    extent = [24.4,33.9,28.3,37.1]
    cellSize = 0.3333
    newExtent = alignExtent(extent,cellSize)
    print(isExtentAligned(newExtent,cellSize))

    # TRUE
    extent = [24.4,33.9,28.3,37.1]
    cellSize = 0.33333333333
    newExtent = alignExtent(extent,cellSize)
    print(isExtentAligned(newExtent,cellSize))

  #-------------------------------------------------------------------------------
  # [[ 1  2  3  4  5]
  #  [ 6  7  8  9 10]
  #  [11 12 13 14 15]
  #  [16 17 18 19 20]]
  # [100, 200, 105, 204]
  # 100 200 - 0 3 - 16
  # 100 204 - 0 0 - 1
  # 105 200 - 4 3 - 20
  # 105 204 - 4 0 - 5
  # 101 201 - 1 2 - 12
  # 103 202 - 3 1 - 9
  # 104 203 - 4 0 - 5
  # 105 204 - 4 0 - 5
  # 106 205 - -1 -1 - 20
  def testIsExtentInExtent():
    nrCols = 5
    nrRows = 4
    arr = np.array([
        1,  2,  3,  4,  5,
        6,  7,  8,  9, 10,
       11, 12, 13, 14, 15,
       16, 17, 18, 19, 20,
    ]).reshape(nrRows,nrCols)
    extent = [100,200,105,204]
    cellSize = 1
    print(arr)
    print(extent)
    x = 100
    y = 200
    c,r = calcColRowFromXY(x,y,extent,cellSize)
    print("%s %s - %s %s - %s" % (x,y,c,r,arr[r,c]))
    x = 100
    y = 204
    c,r = calcColRowFromXY(x,y,extent,cellSize)
    print("%s %s - %s %s - %s" % (x,y,c,r,arr[r,c]))
    x = 105
    y = 200
    c,r = calcColRowFromXY(x,y,extent,cellSize)
    print("%s %s - %s %s - %s" % (x,y,c,r,arr[r,c]))
    x = 105
    y = 204
    c,r = calcColRowFromXY(x,y,extent,cellSize)
    print("%s %s - %s %s - %s" % (x,y,c,r,arr[r,c]))
    x = 101
    y = 201
    c,r = calcColRowFromXY(x,y,extent,cellSize)
    print("%s %s - %s %s - %s" % (x,y,c,r,arr[r,c]))
    x = 103
    y = 202
    c,r = calcColRowFromXY(x,y,extent,cellSize)
    print("%s %s - %s %s - %s" % (x,y,c,r,arr[r,c]))
    x = 104
    y = 203
    c,r = calcColRowFromXY(x,y,extent,cellSize)
    print("%s %s - %s %s - %s" % (x,y,r,c,arr[r,c]))
    x = 105
    y = 204
    c,r = calcColRowFromXY(x,y,extent,cellSize)
    print("%s %s - %s %s - %s" % (x,y,r,c,arr[r,c]))
    x = 106
    y = 205
    c,r = calcColRowFromXY(x,y,extent,cellSize)
    print("%s %s - %s %s - %s" % (x,y,c,r,arr[r,c]))

  #-------------------------------------------------------------------------------
  def testCalcColRowWindowFromExtent_v1():
    nrCols = 5
    nrRows = 4
    arr = np.array([
        1,  2,  3,  4,  5,
        6,  7,  8,  9, 10,
       11, 12, 13, 14, 15,
       16, 17, 18, 19, 20,
    ]).reshape(nrRows,nrCols)
    ex2 = [100,200,105,204]
    cellSize = 1
    print(arr)
    print(ex2)
    print(arr[1,1])
    print(arr[1:3,1:3])
    print("---------------------------")
    ex1 = [100,200,105,204]
    c,r,nc,nr = calcColRowWindowFromExtent(ex1,ex2,cellSize)
    print("%s - %s %s %s %s - \n%s" % (ex1,c,r,nc,nr,arr[r:r+nr,c:c+nc]))

    ex1 = [100,200,101,201]
    c,r,nc,nr = calcColRowWindowFromExtent(ex1,ex2,cellSize)
    print("%s - %s %s %s %s - \n%s" % (ex1,c,r,nc,nr,arr[r:r+nr,c:c+nc]))

    ex1 = [101,201,102,202]
    c,r,nc,nr = calcColRowWindowFromExtent(ex1,ex2,cellSize)
    print("%s - %s %s %s %s - \n%s" % (ex1,c,r,nc,nr,arr[r:r+nr,c:c+nc]))

    ex1 = [101,201,101,201]
    c,r,nc,nr = calcColRowWindowFromExtent(ex1,ex2,cellSize)
    print("%s - %s %s %s %s - \n%s" % (ex1,c,r,nc,nr,arr[r:r+nr,c:c+nc]))

    ex1 = [101,201,103,203]
    c,r,nc,nr = calcColRowWindowFromExtent(ex1,ex2,cellSize)
    print("%s - %s %s %s %s - \n%s" % (ex1,c,r,nc,nr,arr[r:r+nr,c:c+nc]))

    ex1 = [102,202,103,203]
    c,r,nc,nr = calcColRowWindowFromExtent(ex1,ex2,cellSize)
    print("%s - %s %s %s %s - \n%s" % (ex1,c,r,nc,nr,arr[r:r+nr,c:c+nc]))

    ex1 = [103,203,104,204]
    c,r,nc,nr = calcColRowWindowFromExtent(ex1,ex2,cellSize)
    print("%s - %s %s %s %s - \n%s" % (ex1,c,r,nc,nr,arr[r:r+nr,c:c+nc]))

    ex1 = [103,203,105,204]
    c,r,nc,nr = calcColRowWindowFromExtent(ex1,ex2,cellSize)
    print("%s - %s %s %s %s - \n%s" % (ex1,c,r,nc,nr,arr[r:r+nr,c:c+nc]))

#     ex1 = [100,200,104,203]
#     c,r,nc,nr = calcColRowWindowFromExtent(ex1,ex2,cellSize)
#     print "%s - %s %s %s %s - \n%s" % (ex1,c,r,nc,nr,arr[r:r+nr,c:r+nc])

  #-------------------------------------------------------------------------------
  def testCalcColRowWindowFromExtent():
    nrCols = 4
    nrRows = 3
    arr = np.array([
        1,  2,  3,  4,
        5,  6,  7,  8,
        9, 10, 11, 12
    ]).reshape(nrRows,nrCols)
    ex2 = [100,200,140,230]
    cellSize = 10
    print(arr)
    print(ex2)
    #print arr[1,1]
    #print arr[1:3,1:3]
    
    print("---------------------------")
    # full
    ex1 = [100,200,140,230]
    c,r,nc,nr = calcColRowWindowFromExtent(ex1,ex2,cellSize)
    print("%s - %s %s %s %s - \n%s" % (ex1,c,r,nc,nr,arr[r:r+nr,c:c+nc]))

    # 9
    ex1 = [100,200,110,210]
    c,r,nc,nr = calcColRowWindowFromExtent(ex1,ex2,cellSize)
    print("%s - %s %s %s %s - \n%s" % (ex1,c,r,nc,nr,arr[r:r+nr,c:c+nc]))

    # 6
    ex1 = [110,210,120,220]
    c,r,nc,nr = calcColRowWindowFromExtent(ex1,ex2,cellSize)
    print("%s - %s %s %s %s - \n%s" % (ex1,c,r,nc,nr,arr[r:r+nr,c:c+nc]))

    # 3
    ex1 = [120,220,130,230]
    c,r,nc,nr = calcColRowWindowFromExtent(ex1,ex2,cellSize)
    print("%s - %s %s %s %s - \n%s" % (ex1,c,r,nc,nr,arr[r:r+nr,c:c+nc]))

    # 4
    ex1 = [130,220,140,230]
    c,r,nc,nr = calcColRowWindowFromExtent(ex1,ex2,cellSize)
    print("%s - %s %s %s %s - \n%s" % (ex1,c,r,nc,nr,arr[r:r+nr,c:c+nc]))

    # 3,4
    ex1 = [120,220,140,230]
    c,r,nc,nr = calcColRowWindowFromExtent(ex1,ex2,cellSize)
    print("%s - %s %s %s %s - \n%s" % (ex1,c,r,nc,nr,arr[r:r+nr,c:c+nc]))

    # 1,2,3,4
    # 5,6,7,8
    ex1 = [100,210,140,230]
    c,r,nc,nr = calcColRowWindowFromExtent(ex1,ex2,cellSize)
    print("%s - %s %s %s %s - \n%s" % (ex1,c,r,nc,nr,arr[r:r+nr,c:c+nc]))

    # 5,6,7
    # 9,10,11
    ex1 = [100,200,130,220]
    c,r,nc,nr = calcColRowWindowFromExtent(ex1,ex2,cellSize)
    print("%s - %s %s %s %s - \n%s" % (ex1,c,r,nc,nr,arr[r:r+nr,c:c+nc]))

    # [] -1,-1,0,0
    ex1 = [100,200,130,240]
    c,r,nc,nr = calcColRowWindowFromExtent(ex1,ex2,cellSize)
    print("%s - %s %s %s %s - \n%s" % (ex1,c,r,nc,nr,arr[r:r+nr,c:c+nc]))

  #-------------------------------------------------------------------------------
  def testRasterValueToString():
    i = 123456
    print(rasterValueToString(i,np.uint16))

    f = 123456.123456
    print(rasterValueToString(f,np.float32))
    print(rasterValueToString(f,np.float32,10))

  #-------------------------------------------------------------------------------
  def testCreateRasterDataset():
      
    extent = [0.0,0.0,60.0,40.0]
    cellSize = 10.0
      
    driverName = "GTiff"

    outDir = r""
    
    if not os.path.isdir(outDir):
      os.makedirs(outDir)
    
    for dataType in [np.int16,np.int32,np.uint8,np.uint16,np.uint32,np.float32,np.float64]:

      try:
              
        noDataValue = getNoDataValue(dataType)
        
        print(dataType)
        print(noDataValue)
      
        fileName = "tmp_%s" % dataTypeNumpyToString(dataType)
        fileName = os.path.join(outDir,fileName)
        
        rasterDelete(fileName)
        
        dataset = createRasterDataset(driverName,fileName,extent,cellSize,dataType)
        band = dataset.GetRasterBand(1)
    
        band.SetNoDataValue(noDataValue)
      except:
        print("Errror")

  #-----------------------------------------------------------------------------
  def testAlignExtent_20161207():
    
    cellSize = 0.0083333333333
    extent = [-180.000000339, -89.999999999, 179.999999659, 90.0]

    #print (extent[2] - extent[0]) / cellSize
        
    # NrCols/NrRows: 43200 21600
    
    msgExt(alignExtent(extent,cellSize))
    print(calcNrColsRowsFromExtent(extent,cellSize))

    exit(0)
        
    #-179.999999999 -89.991666666 179.991666666 90.008333333
    # (43199, 21600)

    minx = UT.trunc(extent[0] / cellSize) * cellSize
    miny = UT.trunc(extent[1] / cellSize) * cellSize
      
    Log.dbg(" minx/miny: %s %s" % (minx,miny))

    minx = round(extent[0] / cellSize,0) * cellSize
    miny = round(extent[1] / cellSize,0) * cellSize

    Log.dbg("alignExtent - minx/miny: %s %s" % (minx,miny))

    print(cellSize * 43200)
    print(round(0.4))
    print(round(0.45))
    print(round(0.5))
    print(round(0.6))
      
  #-----------------------------------------------------------------------------
  def testDegreeToKM_20181112():
    
    # https://stackoverflow.com/questions/13026675/calculating-distance-between-two-points-latitude-longitude
    # 538404.100197555 meter
    lon1 = 0
    lat1 = 51.5
    lon2 = -3
    lat2 = 56
    dist = degreeToKM_v2(lon1,lat1,lon2,lat2)
    print(dist)    # RasterUtils.py
         
  #-----------------------------------------------------------------------------
  def testDegreeToKM_v2_20181120():
    lon1 = 0
    lat1 = 51.5
    lon2 = -3
    lat2 = 56
    dist = degreeToKM_v2(lon1,lat1,lon2,lat2)
    print(dist)    # RasterUtils.py

  #-----------------------------------------------------------------------------
  # [ 1  2  3 -1  5]
  # 2.0
  # [ 1  2  3 -1  5]
  # 2.0
  # ........................................
  # [ 1  2  3 -1  5]
  # 2.0
  # [1 2 3 -- 5]
  # 2.75
  # [1 2 3 0 5]
  # 2.2
  # ........................................
  # [ 1.  2.  3. -1.  5.]
  # 2.0
  # [1.0 2.0 3.0 -- 5.0]
  # 2.75
  # [1. 2. 3. 0. 5.]
  # 2.2
  def testMaskedToNumpy():

    x = np.array([1, 2, 3, -1, 5])
    print(x)
    print(np.mean(x))
    #unmx = maskedToNumpy(x,0)
    # print(unmx)
    # print(np.mean(unmx))
    print(x)
    print(np.mean(x))

    print("."*40)
    x = np.array([1, 2, 3, -1, 5])
    mx = np.ma.masked_array(x, mask=[0, 0, 0, 1, 0])
    print(x)
    print(np.mean(x))
    print(mx)
    print(np.mean(mx))
    unmx = maskedToNumpy(mx,0)
    print(unmx)
    print(np.mean(unmx))

    print("."*40)
    x = np.array([1.0, 2.0, 3.0, -1.0, 5.0])
    mx = np.ma.masked_array(x, mask=[0, 0, 0, 1, 0])
    print(x)
    print(np.mean(x))
    print(mx)
    print(np.mean(mx))
    unmx = maskedToNumpy(mx,0.0)
    print(unmx)
    print(np.mean(unmx))

  #-------------------------------------------------------------------------------
  def testAlignGridGrow():
    extent = [24.4,33.9,28.3,37.1]

    def msgCellSizeExt(cs,ex):
      print("%s %s -> %s" % (cs,ex,alignExtentGrow(extent,cellSize)))

    cellSize = 1
    msgCellSizeExt(cellSize,extent)
    cellSize = 0.5
    msgCellSizeExt(cellSize,extent)
    cellSize = 0.2
    msgCellSizeExt(cellSize,extent)

    # LET OP:
    #print alignExtent(extent,0.2)
    #GEEFT: [24.400000000000002, 33.800000000000004, 28.200000000000003, 37.00000000000001]

    cellSize = 50
    extent = [120,210,301,402]
    print("-------------")
    msgExt(extent)
    #print("%s -> %s" % (extent,alignExtentGrow(extent,cellSize)))
    msgCellSizeExt(cellSize,extent)
    msgExt(extent)

    extent = [120,210,300,400]
    #print("%s -> %s" % (extent,alignExtentGrow(extent,cellSize)))
    msgCellSizeExt(cellSize,extent)

    extent = [100,200,300,400]
    #print("%s -> %s" % (extent,alignExtentGrow(extent,cellSize)))
    msgCellSizeExt(cellSize,extent)

  # cellSize = 0.0083333333333
    # extent = [-180.000000339, -89.999999999, 179.999999659, 90.0]
    #
    # #print (extent[2] - extent[0]) / cellSize
    #
    # # NrCols/NrRows: 43200 21600
    #
    # msgExt(alignExtent(extent,cellSize))
    # print(calcNrColsRowsFromExtent(extent,cellSize))
    #
    # exit(0)
    #
    # #-179.999999999 -89.991666666 179.991666666 90.008333333
    # # (43199, 21600)
    #
    # minx = UT.trunc(extent[0] / cellSize) * cellSize
    # miny = UT.trunc(extent[1] / cellSize) * cellSize
    #
    # Log.dbg(" minx/miny: %s %s" % (minx,miny))
    #
    # minx = round(extent[0] / cellSize,0) * cellSize
    # miny = round(extent[1] / cellSize,0) * cellSize
    #
    # Log.dbg("alignExtent - minx/miny: %s %s" % (minx,miny))
    #
    # print(cellSize * 43200)
    # print(round(0.4))
    # print(round(0.45))
    # print(round(0.5))
    # print(round(0.6))

  #-------------------------------------------------------------------------------
  #
  # run Core\RasterUtils.py
  #
  #testCalcNrColsRowsFromExtent()
  #testAlignExtent()
  #testCalcExtentWidthHeight()
  #testCalcColRowFromXY()
  #testCalcExtentOverlap()
  #testCalcExtentFromUpperLeftXY()
  #testTruncExtent()
  #testCellSizeExtent()
  #testIsEqualExtent()
  #testCalcColRowFromXY()
  #testIsExtentInExtent()
  #testCalcColRowWindowFromExtent()
  
  #testIsExtentAligned()    # NOK!!!

  #testRasterValueToString()
  #testCreateRasterDataset()

  #testAlignExtent_20161207()
  #testDegreeToKM_20181112()
  #testDegreeToKM_v2_20181120()
  #testMaskedToNumpy()
  testAlignGridGrow()
