# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Remarks:
#           Raster types:
#           - <name>.tif - geotif, read/write.
#           - <none> - in-memory raster, noread/nowrite.
#           - <name>.asc - esri asciigrid, read/nowrite.
#           - <name>.nc - NetCDF, read/nowrite.
#
# Modified: 30 sept 2016, ES, ARIS B.V.
#           - Version 4.0.2
#           - write modified, check on existance of directory added.
#           - min and max modified, now using data mask.
#           - initRasterCellAreas added.
#           2 nov 2016, ES, ARIS B.V.
#           - Version 4.0.2
#           - resample modified, np.full(...,dtype=self.dataType) added because
#             of warning.
#           - initRaster modified, convertValuePythonToDataTypeNumpy added.
#           - initRaster modified, use of np.zeros added.
#           - initRaster modified, use of convertValuePythonToDataTypeNumpy added.
#           - compressionMode added.
#           - write and writeAs modified, compress added.
#           - readInfo modified, check on valid nodata value added.
#           - getValueFromXY added.
#           7 dec 2016, ES, ARIS B.V.
#           - Version 4.0.3
#           - showInfo added.
#           5 feb 2017, ES, ARIS B.V.
#           - Version 4.0.5
#           - resampleGetMeanValueSkipNoData modified, if len(a)>0 added.
#           - resample modified, count = np.sum(self.raster==self.noDataValue).
#           15 mar 2017, ES, ARIS B.V.
#           - Version 4.0.5
#           - resampleGetMeanValueSkipNoData modified, now using np.sum which
#             is faster.
#           8 may 2017, ES, ARIS B.V.
#           - Version 4.0.6
#           - compress added.
#           - __init__ modified, compress added.
#           - write modified, now write(self).
#           - writeAs modified.
#           - initDataset modified.
#           - read modified.
#           - isMemRaster modified.
#           30 oct 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           - flip added.
#           5 nov 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           - calcZonalMean added.
#           - createMaskFromList_AND added.
#           - createMaskFromList_OR added.
#           - showData added.
#           16 nov 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           - readRow added.
#           28 nov 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           - writeRow added.
#           - resampleGetSumValue added.
#           - resample modified, calcSum added.
#           - initRasterEmpty modified, noDataValue=None added.
#           2 dec 2020, ES, ARIS B.V.
#           - Version 4.1.0
#           - resample modified, now using rstep/cstep.
#           10 dec 2020, ES, ARIS B.V.
#           - Version 4.1.0
#           - Support for AsciiGrid (.asc) added (readonly).
#           - resample modified, because of "not calcSum".
#           - resampleGetSumValueSkipNoData added.
#           - resample modified, sumSkipNoData added.
#           8 jan 2021, ES, ARIS B.V.
#           - Version 4.1.0
#           - repeat added.
#           - resample renamed to resample_do_not_use (for ref. testing).
#           - new resample method added:
#             - calcSum renamed to calcSumDiv.
#             - sumSkipNoData renamed to sumDivSkipNoData.
#             - "if calcSumDiv:" error corrected!
#             - upscaling now divides cell values when calcSumDiv is True.
#           11 jan 2021, ES, ARIS B.V.
#           - Version 4.1.1
#           - Support for NetCDF (.nc) added (readonly).
#           - checkIsReadOnly added.
#           - write, writeAs and writeRow modified, checkIsReadOnly added.
#           - writeAs modified, checkIsReadOnly added.
#           - writeAs modified, checkIsReadOnly added.
#           - writeRow modified, because of CannotSaveInMemoryRaster.
#           - read modified, NetCDF added.
#           - readInfo modified, NetCDF added.
#           - read modified, read of custom extent added.
#           - getExtentByValue added.
#           - getDataByExtent added.
#           - replace added.
#           - writeCol added.
#           - writeRow modified.
#-------------------------------------------------------------------------------

import os

import numpy as np
import osgeo.gdal as gd

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Common.Utils as UT

import GlobioModel.Core.CellArea as CellArea
import GlobioModel.Core.RasterUtils as RU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Raster(object):
  fileName = ""
  dataset = None
  band = None
  raster = None
  memmap = None
  extent = None
  cellSize = None
  nrCols = None
  nrRows = None
  nrBands = None
  dataType = None
  noDataValue = 0
  compress = True
  # Posible values from hight to low compression rate: LZW,DEFLATE,PACKBITS
  compressionMode = "LZW"

  #### New properties, also modify copyInfo!!!!!!!!!!!!
  
  #-------------------------------------------------------------------------------
  # Creates a in-memory raster when no fileName is specified. To save an in-memory
  # raster use writeAs().
  def __init__(self,fileName=None,compress=True):
    self.fileName = fileName
    self.dataset = None
    self.band = None
    self.raster = None
    self.memmap = None
    self.extent = None
    self.cellSize = None
    self.nrCols = None
    self.nrRows = None
    self.nrBands = None
    self.dataType = None
    self.noDataValue = 0
    self.compress = compress

  #-------------------------------------------------------------------------------
  def __del__(self):
    self.close()

  #-------------------------------------------------------------------------------
  # Shortcut to self.raster.
  @property
  def r(self):
    return self.raster
    
  #-------------------------------------------------------------------------------
  # Shortcut to self.raster.
  @r.setter
  def r(self,raster):
    self.raster = raster

  #-------------------------------------------------------------------------------
  # Checks readonly raster types. Throws an exception if so.
  def checkIsReadOnly(self,fileName):
    if (RU.isAsciiGridName(fileName)) or (RU.isNetCDFName(fileName)):
      Err.raiseGlobioError(Err.RasterNotSupportedForWrite1,fileName)

  #-------------------------------------------------------------------------------
  def close(self):
    if not self.band is None:
      self.band = None
    if not self.dataset is None:
      gd.Dataset.__swig_destroy__(self.dataset)
      self.dataset = None
    if not self.raster is None:
      self.raster = None
    if not self.memmap is None:
      self.memmap = None

  #-------------------------------------------------------------------------------
  # Converts the raster data to a new datatype and/or nodata value.
  # DataType is numpy data type.
  def convert(self,dataType=None,noDataValue=None):
    # Check arguments.
    if dataType is None:
      dataType = self.dataType
    if noDataValue is None:
      noDataValue = self.noDataValue
    # Create output raster.      
    outRaster = Raster()
    outRaster.initRaster(self.extent,self.cellSize,dataType,noDataValue)
    # Copy raster data.
    outRaster.raster = self.raster.astype(dataType)
    # Different nodatvalue.
    if noDataValue != self.noDataValue:
      # Create nodata mask.
      mask = (self.raster == self.noDataValue)
      # Update nodata.
      outRaster.raster[mask] = noDataValue
    return outRaster

  #-------------------------------------------------------------------------------
  # Conversion between Numpy types and GDAL types.
  def convertValuePythonToDataTypeNumpy(self,pythonValue,numpyDataType):
    if numpyDataType==np.int8:
      Err.raiseGlobioError(Err.InvalidNumpyDataType1,RU.dataTypeNumpyToString(numpyDataType))
    elif numpyDataType==np.int16:
      return int(pythonValue)
    elif numpyDataType==np.int32:
      return int(pythonValue)
    elif numpyDataType==np.int64:
      Err.raiseGlobioError(Err.InvalidNumpyDataType1,RU.dataTypeNumpyToString(numpyDataType))
    elif numpyDataType==np.uint8:
      return int(pythonValue)
    elif numpyDataType==np.byte:
      Err.raiseGlobioError(Err.InvalidNumpyDataType1,RU.dataTypeNumpyToString(numpyDataType))
    elif numpyDataType==np.uint16:
      return int(pythonValue)
    elif numpyDataType==np.uint32:
      return int(pythonValue)
    elif numpyDataType==np.uint64:
      Err.raiseGlobioError(Err.InvalidNumpyDataType1,RU.dataTypeNumpyToString(numpyDataType))
    elif numpyDataType==np.float16:
      Err.raiseGlobioError(Err.InvalidNumpyDataType1,RU.dataTypeNumpyToString(numpyDataType))
    elif numpyDataType==np.float32:
      return float(pythonValue)
    elif numpyDataType==np.float64:
      return float(pythonValue)
    elif numpyDataType==np.complex64:
      Err.raiseGlobioError(Err.InvalidNumpyDataType1,RU.dataTypeNumpyToString(numpyDataType))
    elif numpyDataType==np.complex128:
      Err.raiseGlobioError(Err.InvalidNumpyDataType1,RU.dataTypeNumpyToString(numpyDataType))
    else:
      Err.raiseGlobioError(Err.InvalidNumpyDataType1,RU.dataTypeNumpyToString(numpyDataType))

  #-------------------------------------------------------------------------------
  def copyInfo(self,fromRaster):
    self.extent = fromRaster.extent
    self.cellSize = fromRaster.cellSize
    self.nrCols = fromRaster.nrCols
    self.nrRows = fromRaster.nrRows
    self.dataType = fromRaster.dataType 
    self.noDataValue = fromRaster.noDataValue
    self.compressionMode = fromRaster.compressionMode

  #-------------------------------------------------------------------------------
  # Creates a mask from a list of values, i.e. [4,5].
  # The mask is refined for all subsequent values of the list.
  def createMaskFromList_AND(self,values):
    mask = None
    for value in values:
      if mask is None:
        # Create mask.
        mask = (self.raster == value)
      else:
        # Refine mask.
        mask = np.logical_and(mask,self.raster == value)
    return mask

  #-------------------------------------------------------------------------------
  # Creates a mask from a list of values, i.e. [4,5].
  # The mask is extended for all subsequent values of the list.
  def createMaskFromList_OR(self,values):
    mask = None
    for value in values:
      if mask is None:
        # Create mask.
        mask = (self.raster == value)
      else:
        # Extent mask.
        mask = np.logical_or(mask,self.raster == value)
    return mask

  #-------------------------------------------------------------------------------
  # Fills raster with a value.
  def fill(self,value,mask=None):
    if mask is None:
      self.raster = value
    else:
      self.raster[mask] = value

  #-------------------------------------------------------------------------------
  # Flips the row order of the raster data (to correct the grid origin).
  #
  # DOES NOT WORK IN NUMPY- Only in >=1.12, now 1.8.
  # np.flip(inData,1)
  #
  def flip(self):
    # Create a temporary raster. 
    tmpRaster = np.full_like(self.raster,0.0)
    # Set max index for reverse counting.
    maxIndex = self.nrRows - 1
    # Copy rows and save in reversed order.
    for i in range(self.nrRows):
      tmpRaster[maxIndex-i][:] = self.raster[i][:]
    # Update raster.
    self.raster = tmpRaster

  #-------------------------------------------------------------------------------
  # Returns specified data/region of the raster data
  def getDataByExtent(self,extent):

    # Empty raster?
    if self.raster is None:
      Err.raiseGlobioError(Err.NoRasterDataAvailable)

    minCol,minRow,nrCols,nrRows = RU.calcColRowWindowFromExtent(extent,
                                                                self.extent,
                                                                self.cellSize)
    return self.raster[minRow:minRow+nrRows,minCol:minCol+nrCols]

  #-------------------------------------------------------------------------------
  # Returns a mask for cells with data (i.e. no nodata).
  def getDataMask(self):
    return self.raster != self.noDataValue

  #-------------------------------------------------------------------------------
  # Returns the extent of the data/region of the specified value.
  # Return None if not found.
  #-------------------------------------------------------------------------------
  def getExtentByValue(self,value):

    # Empty raster?
    if self.raster is None:
      Err.raiseGlobioError(Err.NoRasterDataAvailable)

    minRow = UT.maxInt()
    minCol = UT.maxInt()
    maxRow = -1
    maxCol = -1

    useWhere = True
    if useWhere:
      # Get rows/cols coordinates.
      rowscols = np.where(self.raster==value)
      if len(rowscols[0])>0:
        # Get min/max coordinates.
        minRow = rowscols[0].min()
        maxRow = rowscols[0].max()
        minCol = rowscols[1].min()
        maxCol = rowscols[1].max()
    else:
      for r in range(self.nrRows):
        for c in range(self.nrCols):
          if self.raster[r,c] == value:
            minRow = min(minRow,r)
            minCol = min(minCol,c)
            maxRow = max(maxRow,r)
            maxCol = max(maxCol,c)
            #continue

    if (maxCol==-1) or (maxRow==-1):
      return None

    #print("min/max col/row: %s %s %s %s" % (minCol,minRow,maxCol,maxRow))
    minX,minY = RU.calcUpperLeftXYFromColRow(minCol,maxRow,self.extent,self.cellSize)
    minY = minY - self.cellSize
    #print("min xy: %s %s" % (minX,minY))
    maxX,maxY = RU.calcUpperLeftXYFromColRow(maxCol,minRow,self.extent,self.cellSize)
    maxX = maxX + self.cellSize
    #print("max xy: %s %s" % (maxX,maxY))
    #print("nr col/row: %s %s" % (maxCol-minCol,maxRow-minRow))
    return [minX,minY,maxX,maxY]

  #-------------------------------------------------------------------------------
  # Returns a mask for cells with no nodata.
  def getNoDataMask(self):
    return self.raster == self.noDataValue

  #-------------------------------------------------------------------------------
  # Returns the value from a x/y point.
  # Returns NoData if x/y is outside the raster or empty raster.
  def getValueFromXY(self,x,y):
    # Empty raster?
    if self.raster is None:
      Log.dbg("Raster.getValueFromXY - Empty raster.")
      return self.noDataValue
    # Point not in raster?
    if not RU.isPointInExtent(x,y,self.extent):
      Log.dbg("Raster.getValueFromXY - Point not in extent.")
      return self.noDataValue
    col,row = RU.calcColRowFromXY(x,y,self.extent,self.cellSize)
    return self.raster[row,col]

  #-------------------------------------------------------------------------------
  # Creates a TIFF, ASC, NetCDF or MEM dataset. No raster memory will be allocated.
  # ASC and NetCDF datasets are ReadOnly.
  def initDataset(self,extent,cellSize,dataType,noDataValue):

    # Set properties.          
    self.extent = extent
    self.cellSize = cellSize
    self.dataType = dataType
    self.noDataValue = noDataValue
    self.nrCols, self.nrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)

    #Log.dbg("Raster.initDataset - extent: %s" % (self.extent))
    #Log.dbg("Raster.initDataset - cellSize: %s" % (self.cellSize))
    #Log.dbg("Raster.initDataset - cols/rows: %s %s" % (self.nrCols,self.nrRows))

    # Check raster name.
    if (self.fileName is None) or (len(self.fileName)==0):    
      driverName = "MEM"
      self.fileName = ""
      compressionMode = None
    elif RU.isGeoTifName(self.fileName):
      driverName = "GTiff"
      if self.compress:
        compressionMode = self.compressionMode
      else:
        compressionMode = None
    elif RU.isAsciiGridName(self.fileName):
      driverName = "AAIGrid"
      compressionMode = None
    else:
      driverName = ""
      compressionMode = None
      Err.raiseGlobioError(Err.RasterNotSupported1,self.fileName)

    # Create dataset. No raster memory will be allocated.
    self.dataset = RU.createRasterDataset(driverName,self.fileName,extent,cellSize,
                                          dataType,compressionMode)

    # Set band.  
    self.band = self.dataset.GetRasterBand(1)

    # Set nodata value.
    self.band.SetNoDataValue(noDataValue)

  #-------------------------------------------------------------------------------
  # Init raster for write.
  # DataType is numpy datatype.
  def initRaster(self,extent,cellSize,dataType,noDataValue,value=None):

    # Check raster name.
    if (not self.fileName is None) and (len(self.fileName)>0):
      # AsciiGrid raster?
      if RU.isAsciiGridName(self.fileName):
        # Ascii grid is readonly and cannot be created.
        Err.raiseGlobioError(Err.RasterCannotBeInitialized1,self.fileName)

    # Check value.
    if value is None:
      value = noDataValue
      
    # Init dataset.
    self.initDataset(extent,cellSize,dataType,noDataValue)   

    # Fill raster.
    self.raster = np.zeros((self.nrRows,self.nrCols),dtype=self.dataType)
    self.raster += self.convertValuePythonToDataTypeNumpy(value,self.dataType)

  #-------------------------------------------------------------------------------
  # DataType is numpy datatype.
  def initRasterMB(self,extent,cellSize,dataType,noDataValue,value=None,nrBands=1):

    # Check raster name.
    if (not self.fileName is None) and (len(self.fileName)>0):
      # AsciiGrid raster?
      if RU.isAsciiGridName(self.fileName):
        # Ascii grid is readonly and cannot be created.
        Err.raiseGlobioError(Err.RasterCannotBeInitialized1,self.fileName)

    # Check value.
    if value is None:
      value = noDataValue
      
    # Init dataset.
    # 20201130
    #self.initDataset(extent,cellSize,dataType,noDataValue,nrBands)   
    self.initDataset(extent,cellSize,dataType,noDataValue)

    # Fill raster.
    self.raster = np.zeros((self.nrRows,self.nrCols),dtype=self.dataType)
    self.raster += self.convertValuePythonToDataTypeNumpy(value,self.dataType)

  #-------------------------------------------------------------------------------
  # Initialises a float32 raster and fills with the WGS84 cellarea. 
  def initRasterCellAreas(self,extent,cellSize):

    # Check raster name.
    if (not self.fileName is None) and (len(self.fileName)>0):
      # AsciiGrid raster?
      if RU.isAsciiGridName(self.fileName):
        # Ascii grid is readonly and cannot be created.
        Err.raiseGlobioError(Err.RasterCannotBeInitialized1,self.fileName)

    # Init dataset.
    self.initDataset(extent,cellSize,np.float32,0.0)

    # Calculate cellarea.
    self.raster = CellArea.createCellAreaRaster(extent,cellSize)

  #-------------------------------------------------------------------------------
  # DataType is numpy datatype.
  def initRasterEmpty(self,extent,cellSize,dataType,noDataValue=None):

    # Check raster name.
    if (not self.fileName is None) and (len(self.fileName)>0):
      # AsciiGrid raster?
      if RU.isAsciiGridName(self.fileName):
        # Ascii grid is readonly and cannot be created.
        Err.raiseGlobioError(Err.RasterCannotBeInitialized1,self.fileName)

    # Check noDataValue.
    if noDataValue is None:
      noDataValue = RU.getNoDataValue(dataType)

    # Init dataset.
    self.initDataset(extent,cellSize,dataType,noDataValue)   
  
    # Set empty raster.
    self.raster = None
  
  #-------------------------------------------------------------------------------
  def initRasterLike(self,fromRaster,value=None,dataType=None):
    if dataType is None:
      dataType = fromRaster.dataType
    self.initRaster(fromRaster.extent,fromRaster.cellSize,
                    dataType,fromRaster.noDataValue,value)
  
  #-------------------------------------------------------------------------------
  def isMemRaster(self):
    if (self.fileName is None) or (len(self.fileName)==0):    
      return (self.dataset.GetDriver().ShortName=="MEM")
    else:
      return False

  #-------------------------------------------------------------------------------
  def max(self):
    return np.max(self.raster[self.getDataMask()])

  #-------------------------------------------------------------------------------
  def min(self):
    return np.min(self.raster[self.getDataMask()])
  
  #-------------------------------------------------------------------------------
  # Read a raster file as readonly. Use WriteAs to save to a new raster file.
  #
  # If the extent is given then this value will overrule the original
  # extent of the raster file.
  #
  # Raises an exception if the specified extent is greater than the original
  # extent of the raster file.
  def read(self,extent=None):

    # Check if in-memory raster.
    if self.isMemRaster():
      Err.raiseGlobioError(Err.CannotReadInMemoryRaster)

    # Set raster name.
    fileName = self.fileName

    # Check if raster exist.
    if not RU.rasterExists(fileName):
      Err.raiseGlobioError(Err.RasterNotFound1,fileName)

    # 20210111
    # Check if we already have a raster data. We do not allow to
    # internaly "overwrite" existing raster data.
    if not self.raster is None:
      Err.raiseGlobioError(Err.ReadErrorRasterDataAlreadyCreated1,fileName)

    # Check the raster type.
    if RU.isGdalRasterName(fileName):
      # GDAL RASTER

      # Open raster.
      if self.dataset is None:
        self.dataset = gd.Open(self.fileName,gd.GA_ReadOnly)

      # Read first band.
      if self.band is None:
        self.band = self.dataset.GetRasterBand(1)

      # Reads the raster info (extent,cellsize,nrCols,nrRows,dataType,noDataValue)
      # of the already opened dataset and band.
      self.readInfo()

      # Custom extent specified? Check if custom extent is in original extent.
      if not extent is None:
        if  not RU.isExtentInExtent(extent,self.extent):
          # TODO: Constante van maken.
          Err.raiseGlobioError(Err.UserDefined1,
                               "The specified extent does not lie in the original raster extent.")

      # 20210111
      # Custom extent specified?
      if not extent is None:
        # Align custom extent.
        extent = RU.alignExtent(extent,self.cellSize)
        # A different custom extent then the original?
        if not RU.isEqualExtent(self.extent,extent,self.cellSize):
          # Custom extent different from raster extent.

          # Calculate col/row offset and width/height of custom extent.
          minCol,minRow,nrCols,nrRows = RU.calcColRowWindowFromExtent(extent,
                                                                      self.extent,
                                                                      self.cellSize)
          # Read extent of raster: xoff, yoff, xcount, ycount
          self.raster = self.band.ReadAsArray(minCol,minRow,nrCols,nrRows)

          # Update extent, nrCols and nrRows.
          self.extent = extent
          self.nrCols = nrCols
          self.nrRows = nrRows
        else:
          # Custom extent same as raster extent, read full raster extent.
          self.raster = self.band.ReadAsArray()
      else:
        # No custom extent specified, read full raster extent.
        self.raster = self.band.ReadAsArray()
    else:
      # NETCDF RASTER

      #Log.dbg("Raster.read - NETCDF")

      # Get the NetCDF type/classname.
      netCDFType = RU.getNetCDFType(fileName)

      # Get the NetCDF arguments.
      netCDFArgs = RU.getNetCDFArguments(fileName)

      # Create the NetCDF class instance.
      netCDF = UT.createClassInstance(GLOB.netCDFImportPath,netCDFType)

      # Init the NetCDF file.
      netCDF.init(*netCDFArgs)

      # Reads the raster info (extent,cellsize,nrCols,nrRows,dataType,noDataValue).
      netCDF.readInfo()

      # Set raster properties.
      self.extent = netCDF.extent
      self.cellSize = netCDF.cellSize
      self.dataType = netCDF.dataType
      self.noDataValue = netCDF.noDataValue
      self.nrCols = netCDF.nrCols
      self.nrRows = netCDF.nrRows

      # Custom extent specified?
      if not extent is None:

        #Log.dbg("Raster.read - extent: %s" % (extent,))

        # Custom extent specified, read raster extent and set raster.
        netCDF.read(extent)
        self.raster = netCDF.raster
        # Update extent, nrCols and nrRows.
        self.extent = netCDF.extent
        self.nrCols = netCDF.nrCols
        self.nrRows = netCDF.nrRows
        del netCDF
      else:
        # No custom extent specified, read full raster extent and set raster.
        netCDF.read()
        self.raster = netCDF.raster
        del netCDF

    # For chaining.
    return self

  #-------------------------------------------------------------------------------
  # Reads the raster info (extent,cellsize,nrCols,nrRows,dataType,noDataValue).
  # Opens the dataset/band if not already opened.
  # Does not reads the raster if not already read.
  def readInfo(self):
    # Check the raster type.
    if RU.isGdalRasterName(self.fileName):
      # GDAL RASTER
      # Open raster.
      if self.dataset is None:
        self.dataset = gd.Open(self.fileName,gd.GA_ReadOnly)
      # Read first band.
      if self.band is None:
        self.band = self.dataset.GetRasterBand(1)
      # Get cellsize.
      self.cellSize = self.dataset.GetGeoTransform()[1]
      # Get nrCols/nrRows.
      self.nrCols = self.dataset.RasterXSize
      self.nrRows = self.dataset.RasterYSize
      # Get extent.
      self.extent = RU.calcExtentFromGT(self.dataset.GetGeoTransform(),
                                        self.nrCols,self.nrRows)
      # Get numpy data.
      self.dataType = RU.dataTypeGdalToNumpy(self.band.DataType)
      # Get nodata value.
      self.noDataValue = self.band.GetNoDataValue()
      # Check nodata value. Sometimes no nodata value is specified.
      if self.noDataValue is None:
        # Set default nodata value according to datatype.
        self.noDataValue = RU.getNoDataValue(self.dataType)
        # Show warning message.
        Log.info("Warning: No nodata value specified in raster '%s'. " \
                 "Using default value %s." % (self.fileName,self.noDataValue))
    else:
      # NETCDF RASTER

      # Get the NetCDF type/classname.
      netCDFType = RU.getNetCDFType(self.fileName)

      # Get the NetCDF arguments.
      netCDFArgs = RU.getNetCDFArguments(self.fileName)

      # Create the NetCDF class instance.
      netCDF = UT.createClassInstance(GLOB.netCDFImportPath,netCDFType)

      # Init the NetCDF file.
      netCDF.init(*netCDFArgs)

      # Reads the raster info (extent,cellsize,nrCols,nrRows,dataType,noDataValue).
      netCDF.readInfo()

  #-------------------------------------------------------------------------------
  # Reads 1 row and returns the column values as a 1d array.
  # Read as readonly.
  # Caution: The .raster property is not used and remains unchanged.
  def readRow(self,rowNr):

    # Check if in-memory raster.
    if self.isMemRaster():
      Err.raiseGlobioError(Err.CannotReadInMemoryRaster)

    # Check if NetCDF raster.
    if RU.isNetCDFName(self.fileName):
      Err.raiseGlobioError(Err.UserDefined1,"NetCDF raster type not supported (readRow).")

    # Set raster name.
    fileName = self.fileName

    # Check if raster exist.
    if not RU.rasterExists(fileName):
      Err.raiseGlobioError(Err.RasterNotFound1,fileName)
    
    # Open raster.
    if self.dataset is None:
      self.dataset = gd.Open(self.fileName,gd.GA_ReadOnly)

    # Read first band.
    if self.band is None:
      self.band = self.dataset.GetRasterBand(1)

    # Read raster info.
    self.readInfo()

    # Read raster row: xoff, yoff, xcount, ycount
    rowData = self.band.ReadAsArray(0,rowNr,self.nrCols,1)
      
    # Return the column values as an 1d array.
    return rowData[0]

  #-------------------------------------------------------------------------------
  # Copies the raster data 'count' times in x and y direction.
  # The cellsize is divided by 'count'.
  # The nrCols/nrRowns is multiplied by 'count'.
  def repeat(self,count):
    count = int(count)
    if count <= 1:
      count = 1
    self.cellSize = self.cellSize / count
    self.nrCols = self.nrCols * count
    self.nrRows = self.nrRows * count
    self.r = np.tile(self.r,(count,count))

  #-------------------------------------------------------------------------------
  # Replaces data with the data of the replaceRaster.
  # The cellsize of the replaceRaster must equal to the rasters cellsize.
  # The extent of the replaceRaster must fully lie within the rasters extent.
  # The dataType and noDataValue of the replaceRaster must equal to the
  # rasters dataType and noDataValue.
  def replace(self,replaceRaster):

    # Check cellsize.
    if not RU.isEqualCellSize(replaceRaster.cellSize,self.cellSize):
      # TODO
      Err.raiseGlobioError(Err.UserDefined1,"Invalid cellsize of replace raster.")

    # Check extent.
    if not RU.isExtentInExtent(replaceRaster.extent,self.extent):
      # TODO
      Err.raiseGlobioError(Err.UserDefined1,"Invalid extent of replace raster.")

    # Check datatype.
    if replaceRaster.dataType != self.dataType:
      # TODO
      Err.raiseGlobioError(Err.UserDefined1,"Invalid datatype of replace raster.")

    # # Check nodata value.
    # if replaceRaster.noDataValue != self.noDataValue:
    #   # TODO
    #   Err.raiseGlobioError(Err.UserDefined1,"Invalid nodata value of replace raster.")

    #-------------------------------------------------------------------------------
    # Get replace postion.
    #-------------------------------------------------------------------------------

    # Get the position of the replace data within the current raster.
    minCol,minRow,nrCols,nrRows = RU.calcColRowWindowFromExtent(replaceRaster.extent,
                                                                self.extent,self.cellSize)

    #-------------------------------------------------------------------------------
    # Make nodata value "transparent".
    #-------------------------------------------------------------------------------

    # Create "stamp" raster data of current raster.
    stampRas = self.raster[minRow:minRow+nrRows,minCol:minCol+nrCols]

    # Create data mask of replace raster.
    replaceMask = replaceRaster.getDataMask()

    # Stamp replace raster data.
    stampRas[replaceMask] = replaceRaster.raster[replaceMask]

    # Replace current data with replace data.
    self.raster[minRow:minRow+nrRows,minCol:minCol+nrCols] = stampRas

  #-------------------------------------------------------------------------------
  # Returns the value from the array with the highest occurence.
  def resampleGetMajorityValue(self,arr,nodata=None):
    bc = np.bincount(arr.flatten())
    ii = np.nonzero(bc)[0]
    idx = np.argmax(bc[ii],axis=None)
    return ii[idx]
  
  #-------------------------------------------------------------------------------
  # Returns the mean value from the array.
  # Be aware that the array should not contain nodata values!!!
  def resampleGetMeanValue(self,arr,nodata=None):
    return np.mean(arr)

  #-------------------------------------------------------------------------------
  # Returns the mean value from the array.
  # Cells with the nodata value are not used calculating the mean.
  def resampleGetMeanValueSkipNoData(self,arr,nodata):
    m = (arr!=nodata)
    if np.sum(m)>0:
      return np.mean(arr[m])
    else:
      return nodata

  #-------------------------------------------------------------------------------
  # Returns the sum value from the array.
  # Be aware that the array should not contain nodata values!!!
  def resampleGetSumValue(self,arr,nodata=None):
    return np.sum(arr)

  #-------------------------------------------------------------------------------
  # Returns the sum value from the array.
  # Cells with the nodata value are not used calculating the sum.
  def resampleGetSumValueSkipNoData(self,arr,nodata):
    m = (arr!=nodata)
    if np.sum(m)>0:
      return np.sum(arr[m])
    else:
      return nodata

  #-------------------------------------------------------------------------------
  # Downsampling:
  #   For integer rasters the majority is calculated. When equal counts the
  #   minimum value is used.
  #   For float rasters the mean is calculated. NoDataValues are skipped
  #   when floatSkipNoData is True.
  #   When calcSumDiv is True the sum is calculated. NoDataValues are
  #   skipped when sumDivSkipNoData is True.
  # Upsampling:
  #   For integer and float rasters the original value is copied.
  #   When calcSumDiv is True the the original value is divided by
  #   the scalefactor. NoDataValues are never divided.
  #
  # Flags:
  #   If 'floatSkipNoData' is True float rasters cells with nodata are not
  #   used to compute the mean.
  #   If 'floatSkipNoData' is False all float rasters cells are used to
  #   compute the mean. To ensure correct results a check is done to see
  #   if there are noDataValues. If so, an exception is raised.
  #   'floatSkipNoData' is not used for integer grids.
  #
  #   If 'sumDivSkipNoData' is True rasters cells with nodata are not used
  #   to compute the sum.
  #   If 'sumDivSkipNoData' is False all rasters cells are used to compute
  #   the sum. To ensure correct results a check is done to see if
  #   there are noDataValues. If so, an exception is raised.
  #   'sumDivSkipNoData' is not used when 'calcSum' is False.
  #
  # Returns a Raster.
  def resample(self,toCellSize,noDataValue=None,
               floatSkipNoData=True,
               calcSumDiv=False,sumDivSkipNoData=True):

    if noDataValue is None:
      noDataValue = self.noDataValue

    # Create memory raster.
    outRaster = Raster()

    # Same cellsize?
    if UT.isEqualFloat(toCellSize,self.cellSize):
      # Init raster.
      outRaster.initRasterLike(self,noDataValue)
      # Copy original raster.
      outRaster.raster = self.raster
      # Not the same noDataValue?
      if noDataValue != self.noDataValue:
        # Replace nodata.
        mask = (self.raster == self.noDataValue)
        outRaster.raster[mask] = noDataValue
      return outRaster

    #Log.dbg(str(raster))

    # Downsampling?
    if toCellSize > self.cellSize:
      # Downsample.

      # Check for calcSumDiv flag and type. Floats cannot be
      # downsampled with the majority filter.
      if not calcSumDiv:
        # Float type?
        if RU.dataTypeNumpyIsFloat(self.dataType):
          # Skip NoData values?
          if floatSkipNoData:
            downSampleFunc = self.resampleGetMeanValueSkipNoData
          else:
            # Check for nodata values. Floating point rasters with nodata values
            # can not be resampled.
            # Count the nr of nodata values.
            count = np.sum(self.raster==self.noDataValue)
            if count > 0:
              Err.raiseGlobioError(Err.ResamplingRasterContainsNoData1,self.fileName)
            downSampleFunc = self.resampleGetMeanValue
        else:
          downSampleFunc = self.resampleGetMajorityValue
      else:
        # Float type?
        if RU.dataTypeNumpyIsFloat(self.dataType):
          # Skip NoData values?
          if sumDivSkipNoData:
            downSampleFunc = self.resampleGetSumValueSkipNoData
          else:
            # Check for nodata values. Rasters with nodata values can not be resampled.
            # Count the nr of nodata values.
            count = np.sum(self.raster==self.noDataValue)
            if count > 0:
              Err.raiseGlobioError(Err.ResamplingRasterContainsNoData1,self.fileName)
            downSampleFunc = self.resampleGetSumValue
        else:
          # Integer type. Check for minimal int16 type (because of posible overflow for sum).
          # In any other cases an overflow can always occur!!!
          if not RU.dataTypeNumpyIsMinimalInt16(self.dataType):
            Err.raiseGlobioError(Err.ResamplingInvalidTypeForSum1,self.fileName)
          # SkipNoData values?
          if sumDivSkipNoData:
            downSampleFunc = self.resampleGetSumValueSkipNoData
          else:
            # Check for nodata values. Rasters with nodata values can not be resampled.
            # Count the nr of nodata values.
            count = np.sum(self.raster==self.noDataValue)
            if count > 0:
              Err.raiseGlobioError(Err.ResamplingRasterContainsNoData1,self.fileName)
            downSampleFunc = self.resampleGetSumValue

      # Calculate new number of cols/rows.
      newNrCols,newNrRows = RU.calcNrColsRowsFromExtent(self.extent,toCellSize)

      #Log.dbg("Cols,Rows: %s %s" % (self.nrCols,self.nrRows))
      #Log.dbg("New Cols,Rows: %s %s" % (newNrCols,newNrRows))

      # Calculate step factor.
      step = UT.trunc(self.nrCols / newNrCols)
      step1 = UT.trunc(self.nrRows / newNrRows)
      if step1 < step:
        Log.dbg("Replacing with new step...")
        step = step1

      #Log.dbg("Downsampling with factor %s..." % step)

      # Calculate total number of cols/rows for original raster.
      truncNrCols = newNrCols * step
      truncNrRows = newNrRows * step

      #Log.dbg("Trunc Cols,Rows: %s %s" % (truncNrCols,truncNrRows))

      # Different from raster number of cols/rows?
      if (self.nrCols!=truncNrCols) or (self.nrRows!=truncNrRows):
        Log.dbg("New raster will be truncated...")
        # Recalculate extent.
        newExtent = RU.calcExtentFromUpperLeftXY(self.extent[0],self.extent[3],
                                                 newNrCols,newNrRows,toCellSize)
        Log.dbg("New Extent: %s" % (newExtent))
      else:
        newExtent = self.extent

      #Log.dbg("Extent: %s" % (self.extent))
      #Log.dbg("New Extent: %s" % (newExtent))

      # Init raster with nodata.
      outRaster.initRaster(newExtent,toCellSize,self.dataType,noDataValue)

      #Log.dbg("OutRaster New Cols,Rows: %s %s" % (outRaster.nrCols,outRaster.nrRows))

      # Loop raster blocks.
      for r in np.arange(0,truncNrRows,step):
        for c in np.arange(0,truncNrCols,step):
          # Get value.
          #outRaster.raster[r/step,c/step] = downSampleFunc(self.raster[r:r+step,c:c+step],noDataValue)
          rstep = UT.trunc(r/step)
          cstep = UT.trunc(c/step)
          outRaster.raster[rstep,cstep] = downSampleFunc(self.raster[r:r+step,c:c+step],noDataValue)
    else:
      # Upsample.

      # Calculate new number of cols/rows.
      newNrCols,newNrRows = RU.calcNrColsRowsFromExtent(self.extent,toCellSize)

      #Log.dbg("Cols,Rows: %s %s" % (self.nrCols,self.nrRows))
      #Log.dbg("New Cols,Rows: %s %s" % (newNrCols,newNrRows))

      # Calculate step factor.
      step = UT.trunc(newNrCols / self.nrCols)
      step1 = UT.trunc(newNrRows / self.nrRows)
      if step1 < step:
        Log.dbg("Replacing with new step...")
        step = step1

      #Log.dbg("Upsampling with factor %s..." % step)
      #Log.dbg("Upsampling with factor %s..." % step)
      #Log.dbg(calcSumDiv)

      # Check for calcSum flag.
      if calcSumDiv:
        divider = step * step
        Log.info("- Upsampling divider: %s" % divider)
      else:
        divider = 1

      # Init raster with nodata.
      outRaster.initRaster(self.extent,toCellSize,self.dataType,noDataValue)

      for r in np.arange(0,self.nrRows):
        for c in np.arange(0,self.nrCols):
          r1 = r*step
          c1 = c*step
          value = self.raster[r,c]
          if value != self.noDataValue:
            value /= divider
          outRaster.raster[r1:r1+step,c1:c1+step] = np.full((step,step),value,
                                                            dtype=self.dataType)

    # Show resampled raster.
    #Log.dbg(str(pResult.outRaster))

    # Return the result.
    return outRaster

  #-------------------------------------------------------------------------------
  #
  # ### DO NOT USE THIS METHOD - ONLY FOR REFERENCE TESTING USE !!!!!!!!
  #
  # Downsampling:
  #   For integer rasters the majority is calculated. When equal counts the
  #   minimum value is used.
  #   For float rasters the mean is calculated. NoDataValues are skipped
  #   when floatSkipNoData is True.
  #   When calcSumDiv is True the sum is calculated. NoDataValues are
  #   skipped when sumDivSkipNoData is True.
  # Upsampling:
  #   For integer and float rasters the original value is copied.
  #   When calcSumDiv is True the the original value is divided by
  #   the scalefactor. NoDataValues are never divided.
  #
  # Flags:
  #   If 'floatSkipNoData' is True float rasters cells with nodata are not
  #   used to compute the mean.
  #   If 'floatSkipNoData' is False all float rasters cells are used to
  #   compute the mean. To ensure correct results a check is done to see
  #   if there are noDataValues. If so, an exception is raised.
  #   'floatSkipNoData' is not used for integer grids.
  #
  #   If 'sumSkipNoData' is True rasters cells with nodata are not used
  #   to compute the sum.
  #   If 'sumSkipNoData' is False all rasters cells are used to compute
  #   the sum. To ensure correct results a check is done to see if
  #   there are noDataValues. If so, an exception is raised.
  #   'sumSkipNoData' is not used when 'calcSum' is False.
  #
  # Returns a Raster.
  # 20210108
  # Versie met "if calcSum:" en de divider.
  def resample_do_not_use(self,toCellSize,noDataValue=None,
                          floatSkipNoData=True,
                          calcSumDiv=False,sumDivSkipNoData=True):

    if noDataValue is None:
      noDataValue = self.noDataValue

    # Create memory raster.
    outRaster = Raster()

    # Same cellsize?
    if UT.isEqualFloat(toCellSize,self.cellSize):
      # Init raster.
      outRaster.initRasterLike(self,noDataValue)
      # Copy original raster.
      outRaster.raster = self.raster
      # Not the same noDataValue?
      if noDataValue != self.noDataValue:
        # Replace nodata.
        mask = (self.raster == self.noDataValue)
        outRaster.raster[mask] = noDataValue
      return outRaster

    #Log.dbg(str(raster))

    # Downsample?
    if toCellSize > self.cellSize:

      # Check for calcSum flag and type. Floats cannot be
      # downsampled with the majority filter.
      # 20201211
      if calcSumDiv:
      #if not calcSumDiv:
        # Float type?
        # 20201211
        # if (self.dataType==np.float16) or (self.dataType==np.float32) or\
        #     (self.dataType==np.float64):
        if RU.dataTypeNumpyIsFloat(self.dataType):
          # SkipNoData values?
          if floatSkipNoData:
            downSampleFunc = self.resampleGetMeanValueSkipNoData
          else:
            # Check for nodata values. Floating point rasters with nodata values
            # can not be resampled.
            # Count the nr of nodata values.
            count = np.sum(self.raster==self.noDataValue)
            if count > 0:
              Err.raiseGlobioError(Err.ResamplingRasterContainsNoData1,self.fileName)
            downSampleFunc = self.resampleGetMeanValue
        else:
          downSampleFunc = self.resampleGetMajorityValue
      else:
        # 20201211
        # Float type?
        if RU.dataTypeNumpyIsFloat(self.dataType):
          # Skip NoData values?
          if sumDivSkipNoData:
            downSampleFunc = self.resampleGetSumValueSkipNoData
          else:
            # Check for nodata values. Rasters with nodata values can not be resampled.
            # Count the nr of nodata values.
            count = np.sum(self.raster==self.noDataValue)
            if count > 0:
              Err.raiseGlobioError(Err.ResamplingRasterContainsNoData1,self.fileName)
            downSampleFunc = self.resampleGetSumValue
        else:
          # Integer type. Check for minimal int16 type (because of posible overflow for sum).
          # In any other cases an overflow can always occur!!!
          if not RU.dataTypeNumpyIsMinimalInt16(self.dataType):
            Err.raiseGlobioError(Err.ResamplingInvalidTypeForSum1,self.fileName)
          # Skip NoData values?
          if sumDivSkipNoData:
            downSampleFunc = self.resampleGetSumValueSkipNoData
          else:
            # Check for nodata values. Rasters with nodata values can not be resampled.
            # Count the nr of nodata values.
            count = np.sum(self.raster==self.noDataValue)
            if count > 0:
              Err.raiseGlobioError(Err.ResamplingRasterContainsNoData1,self.fileName)
            downSampleFunc = self.resampleGetSumValue

      # Calculate new number of cols/rows.
      newNrCols,newNrRows = RU.calcNrColsRowsFromExtent(self.extent,toCellSize)

      #Log.dbg("Cols,Rows: %s %s" % (self.nrCols,self.nrRows))
      #Log.dbg("New Cols,Rows: %s %s" % (newNrCols,newNrRows))

      # Calculate step factor.
      step = UT.trunc(self.nrCols / newNrCols)
      step1 = UT.trunc(self.nrRows / newNrRows)
      if step1 < step:
        Log.dbg("Replacing with new step...")
        step = step1

      #Log.dbg("Downsampling with factor %s..." % step)

      # Calculate total number of cols/rows for original raster.
      truncNrCols = newNrCols * step
      truncNrRows = newNrRows * step

      #Log.dbg("Trunc Cols,Rows: %s %s" % (truncNrCols,truncNrRows))

      # Different from raster number of cols/rows?
      if (self.nrCols!=truncNrCols) or (self.nrRows!=truncNrRows):
        Log.dbg("New raster will be truncated...")
        # Recalculate extent.
        newExtent = RU.calcExtentFromUpperLeftXY(self.extent[0],self.extent[3],
                                                 newNrCols,newNrRows,toCellSize)
        Log.dbg("New Extent: %s" % (newExtent))
      else:
        newExtent = self.extent

      #Log.dbg("Extent: %s" % (self.extent))
      #Log.dbg("New Extent: %s" % (newExtent))

      # Init raster with nodata.
      outRaster.initRaster(newExtent,toCellSize,self.dataType,noDataValue)

      #Log.dbg("OutRaster New Cols,Rows: %s %s" % (outRaster.nrCols,outRaster.nrRows))

      # Loop raster blocks.
      for r in np.arange(0,truncNrRows,step):
        for c in np.arange(0,truncNrCols,step):
          # Get value.
          # 20201202
          #outRaster.raster[r/step,c/step] = downSampleFunc(self.raster[r:r+step,c:c+step],noDataValue)
          rstep = UT.trunc(r/step)
          cstep = UT.trunc(c/step)
          outRaster.raster[rstep,cstep] = downSampleFunc(self.raster[r:r+step,c:c+step],noDataValue)
    else:
      # Upsampling.

      # Calculate new number of cols/rows.
      newNrCols,newNrRows = RU.calcNrColsRowsFromExtent(self.extent,toCellSize)

      #Log.dbg("Cols,Rows: %s %s" % (self.nrCols,self.nrRows))
      #Log.dbg("New Cols,Rows: %s %s" % (newNrCols,newNrRows))

      # Calculate step factor.
      step = UT.trunc(newNrCols / self.nrCols)
      step1 = UT.trunc(newNrRows / self.nrRows)
      if step1 < step:
        Log.dbg("Replacing with new step...")
        step = step1

      #Log.dbg("Upsampling with factor %s..." % step)
      print("Upsampling with factor %s..." % step)
      print(calcSumDiv)

      # Check for calcSum flag.
      if calcSumDiv:
        divider = step * step
      else:
        divider = 1

      print("Upsampling divider %s..." % divider)

      # Init raster with nodata.
      outRaster.initRaster(self.extent,toCellSize,self.dataType,noDataValue)

      for r in np.arange(0,self.nrRows):
        for c in np.arange(0,self.nrCols):
          r1 = r*step
          c1 = c*step
          value = self.raster[r,c]
          if value != self.noDataValue:
            value /= divider
          outRaster.raster[r1:r1+step,c1:c1+step] = np.full((step,step),value,
                                                            dtype=self.dataType)

    # Show resampled raster.
    #Log.dbg(str(pResult.outRaster))

    # Return the result.
    return outRaster

  #-------------------------------------------------------------------------------
  # Resizes the input raster to the new extent.
  # If parts of the raster lies outside the new extent the raster will be clipped. 
  def resize(self,toExtent,noDataValue=None):
  
    if noDataValue is None:
      noDataValue = self.noDataValue

    # Align extent.
    toExtent = RU.alignExtent(toExtent,self.cellSize)
    
    # Create memory raster.
    outRaster = Raster()

    # Same extent?
    if RU.isEqualExtent(self.extent,toExtent,self.cellSize):
      #Log.dbg("- Equal extent, copying original raster...")
      # Init raster.
      outRaster.initRasterLike(self,noDataValue)
      # Copy original raster.
      outRaster.raster = self.raster
      # Not the same noDataValue?
      if noDataValue != self.noDataValue:
        # Replace nodata.
        mask = self.raster == self.noDataValue 
        outRaster.raster[mask] = noDataValue 
      return outRaster

    # Calculate newnumber of cols/rows.
    newNrCols, newNrRows = RU.calcNrColsRowsFromExtent(toExtent,self.cellSize)

    #Log.dbg("New NrCols/NrRows: %s %s" % (newNrCols,newNrRows))

    # Init empty raster.
    outRaster.initRasterEmpty(toExtent,self.cellSize,self.dataType,noDataValue) 

    # Create new raster with nodata.
    outRaster.raster = np.full((newNrRows,newNrCols),noDataValue,dtype=self.dataType)

    # Calculate overlap extent.
    overlapExtent = RU.calcExtentOverlap(self.extent,toExtent)
    
    #Log.dbg("Overlap extent: %s" % overlapExtent)

    # Check overlap extent.
    if overlapExtent is None:
      # No overlap found, return nodata raster.
      #Log.dbg("- No overlap found.")
      return outRaster

    # Get number of cols/rows in overlap.
    overlapNrCols, overlapNrRows = RU.calcNrColsRowsFromExtent(overlapExtent,self.cellSize)

    #Log.dbg("Overlap NrCols/NrRows: %s %s" % (overlapNrCols,overlapNrRows))

    # Calculate upper left col/row of overlap extent in raster.
    minC1,minR1 = RU.calcColRowFromXY(overlapExtent[0],overlapExtent[3]-self.cellSize,
                                      self.extent,self.cellSize) 

    #Log.dbg("Org rows/cols: %s,%s %s,%s" % (minR1,minC1,minR1+overlapNrRows,minC1+overlapNrCols))

    # Calculate upper left col/row of overlap extent in new raster.
    minC2,minR2 = RU.calcColRowFromXY(overlapExtent[0],overlapExtent[3]-self.cellSize,
                                      toExtent,self.cellSize) 
  
    #Log.dbg("Org rows/cols: %s,%s %s,%s" % (minR2,minC2,minR2+overlapNrRows,minC2+overlapNrCols))
    #Log.dbg("[%s:%s,%s:%s] [%s:%s,%s:%s]" % (minR2,minR2+overlapNrRows,minC2,minC2+overlapNrCols,
    #                                         minR1,minR1+overlapNrRows,minC1,minC1+overlapNrCols))

    # Copy the data in overlap extent to the new rasters. 
    outRaster.raster[minR2:minR2+overlapNrRows,minC2:minC2+overlapNrCols] = self.raster[minR1:minR1+overlapNrRows,minC1:minC1+overlapNrCols]

    # Return result.
    return outRaster     

  #-------------------------------------------------------------------------------
  # Shows the raster data.  
  # precision = number of decimals for floats.
  # showNoDataValues = when True, raw nodata value will be shown, else they will
  # be printed as "-".
  def showData(self,caption,precision=1,showNoDataValues=False):
    if (not caption is None) and (caption != ""):
      Log.info(caption + ":")
    for r in range(self.nrRows):
      s = ""
      for c in range(self.nrCols):
        value = self.raster[r,c]
        if showNoDataValues:
          # Show nodata values.
          s += UT.formatValue(value,precision)
        else:
          # Show nodata values as "-".
          if value == self.noDataValue:
            # Left padded "-" to total length of 7.
            s += "{:^7s}".format("-")
            #s += 6*" " +"-"
          else:
            s += UT.formatValue(value,precision)
      Log.info(s)

  #-------------------------------------------------------------------------------
  def showInfo(self,prefix=""):
    Log.info("%sCellSize: %s" % (prefix,self.cellSize))
    Log.info("%sExtent: %s" % (prefix,self.extent))
    Log.info("%sNrCols/NrRows: %s %s" % (prefix,self.nrCols,self.nrRows))
    Log.info("%sType: %s" % (prefix,RU.dataTypeNumpyToString(self.dataType)))
    Log.info("%sNoData: %s" % (prefix,self.noDataValue))
    Log.info("%sMin: %s" % (prefix,self.min()))
    Log.info("%sMax: %s" % (prefix,self.max()))

  #-------------------------------------------------------------------------------
  # Writes a raster.
  # The raster should not already exist.
  def write(self):

    # Check if in-memory raster.
    if self.isMemRaster():
      Err.raiseGlobioError(Err.CannotSaveInMemoryRaster)

    # Set raster name.
    fileName = self.fileName

    # Check raster name.
    if (fileName is None) or (len(fileName)==0):    
      Err.raiseGlobioError(Err.NoRasterSpecified)

    # Check readonly raster types.
    self.checkIsReadOnly(self.fileName)

    # Check directory of raster name.
    dirName = os.path.dirname(fileName)
    if not os.path.isdir(dirName):    
      Err.raiseGlobioError(Err.DirectoryNotFound1,dirName)

    # Write data.
    self.dataset.GetRasterBand(1).WriteArray(self.raster)
    self.dataset.GetRasterBand(1).FlushCache()

  #-------------------------------------------------------------------------------
  # Writes a currently opened raster to a new file.
  # Just reading and writing with .write() does not work.
  # Replaces the original fileName and dataset with the new one.
  def writeAs(self,newFileName,compress=True):

    # Check raster name.
    if (newFileName is None) or (len(newFileName)==0):    
      Err.raiseGlobioError(Err.NoRasterSpecified)

    # Check readonly raster types.
    self.checkIsReadOnly(newFileName)

    # Set compress.
    self.compress = compress

    #Log.dbg("Writing data...")    

    # Save as tiff.
    driverName = "GTiff"
    
    # Compress?
    if self.compress:
      compressionMode = self.compressionMode
    else:
      compressionMode = None
      
    # Create dataset.
    newDataset = RU.createRasterDataset(driverName,newFileName,
                                        self.extent,self.cellSize,self.dataType,
                                        compressionMode)
    # Get new band.  
    newBand = newDataset.GetRasterBand(1)
    
    # Set nodata value.
    newBand.SetNoDataValue(self.noDataValue)
    
    # Write data.
    newDataset.GetRasterBand(1).WriteArray(self.raster)
    newDataset.GetRasterBand(1).FlushCache()

    # Cleanup existing band and dataset.
    self.band = None
    if not self.dataset is None:
      gd.Dataset.__swig_destroy__(self.dataset)
      self.dataset = None
    
    # Update with new band, dataset and filename.  
    self.band = newBand
    self.dataset = newDataset
    self.fileName = newFileName

  #-------------------------------------------------------------------------------
  # Writes 1 column. Data should be a 2d array.
  # Caution: The .raster property is not used and remains unchanged.
  # Remark: If possible use writeRow() which is much FASTER!!!
  def writeCol(self,colNr,data):

    # Check if in-memory raster.
    if self.isMemRaster():
      Err.raiseGlobioError(Err.CannotSaveInMemoryRaster)

    # Check readonly raster types.
    self.checkIsReadOnly(self.fileName)

    # Check dataset.
    if self.dataset is None:
      Err.raiseGlobioError(Err.UserDefined1,"Raster not initialize for writing...")
    
    # Write raster row: data, xoff, yoff.
    self.dataset.GetRasterBand(1).WriteArray(data,colNr,0)
    self.dataset.GetRasterBand(1).FlushCache()

  #-------------------------------------------------------------------------------
  # Writes 1 row. Data should be a 2d array.
  # Caution: The .raster property is not used and remains unchanged.
  def writeRow(self,rowNr,data):

    # Check if in-memory raster.
    if self.isMemRaster():
      Err.raiseGlobioError(Err.CannotSaveInMemoryRaster)

    # Check readonly raster types.
    self.checkIsReadOnly(self.fileName)

    # Check dataset.
    if self.dataset is None:
      Err.raiseGlobioError(Err.UserDefined1,"Raster not initialize for writing...")

    # Write raster row: data, xoff, yoff.
    self.dataset.GetRasterBand(1).WriteArray(data,0,rowNr)
    self.dataset.GetRasterBand(1).FlushCache()

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  
  #-------------------------------------------------------------------------------
  def testRasterResize1():
    try:
      arr = np.array([[ 0,  0,  1,  1,  2,  5,  3,  3],
                      [ 2,  0,  1,  4,  4,  2,  3,  3],
                      [ 9,  9,  1,  1,  2,  9,  8,  9],
                      [ 8,  8,  1,  4,  4,  8,  9,  8],
                      [ 7,  7,  1,  1,  2,  5,  3,  3],
                      [ 6,  6,  1,  4,  4,  2,  3,  3]])
      #arr = np.arange(6*8).reshape(6,8)
      print(arr)
      extent = [100,200,108,206]
      newExtent = [100,200,102,204]
      cellSize = 1
      d = cellSize / 2
      noDataValue = 255
      print("cellsize: %s" % cellSize)
      print("extent: %s" % extent)
      print("new extent: %s" % newExtent)
      c,r = RU.calcColRowFromXY(newExtent[0], newExtent[1], extent, cellSize)
      print("xy: %s,%s -> %s,%s -> arr[%s,%s] = %s" % (newExtent[0], newExtent[1],c,r,r,c,arr[r,c]))
      #print "ll value: " % (r,c,arr[r,c])
      c,r = RU.calcColRowFromXY(newExtent[2]-d, newExtent[3]-d, extent, cellSize)
      print("xy: %s,%s -> %s,%s -> arr[%s,%s] = %s" % (newExtent[2], newExtent[3],c,r,r,c,arr[r,c]))
      #print "xy: %s,%s -> %s,%s" % (newExtent[2], newExtent[3],c,r)
      #print "ur value: arr[%s,%s] = %s" % (r,c,arr[r,c])
      
      ras = Raster()
      ras.initRasterEmpty(extent,cellSize,np.uint8,noDataValue)
      ras.r = arr
      ras2 = ras.resize(newExtent)
      print(ras2.r)
      
      extent = [100,200,108,206]
      newExtent = [105,202,110,204]
      cellSize = 1
      ras = Raster()
      ras.initRasterEmpty(extent,cellSize,np.uint8,noDataValue)
      ras.r = arr
      ras2 = ras.resize(newExtent)
      print(ras2.r)

      extent = [100,200,108,206]
      newExtent = [98,198,110,208]
      cellSize = 1
      ras = Raster()
      ras.initRasterEmpty(extent,cellSize,np.uint8,noDataValue)
      ras.r = arr
      ras2 = ras.resize(newExtent)
      print(ras2.r)

      extent = [100,200,108,206]
      newExtent = [98,198,99,199]
      cellSize = 1
      ras = Raster()
      ras.initRasterEmpty(extent,cellSize,np.uint8,noDataValue)
      ras.r = arr
      ras2 = ras.resize(newExtent)
      print(ras2.r)
      
    except:
      Err.showError()  
    
  #-------------------------------------------------------------------------------
  def testRasterResize2():
    try:
      arr = np.array([[ 0,  1,  2,  3],
                      [ 4,  5,  6,  7]])
      extent = [100,600,500,800]
      newExtent = [300,700,500,800]
      cellSize = 100
      noDataValue = 255
      print("cellsize: %s" % cellSize)
      print("extent: %s" % extent)
      print("new extent: %s" % newExtent)
      c,r = RU.calcColRowFromXY(newExtent[0], newExtent[1], extent, cellSize)
      print("xy: %s,%s -> %s,%s" % (newExtent[0], newExtent[1],c,r))
      print("ll value: arr[%s,%s] = %s" % (r,c,arr[r,c]))
      c,r = RU.calcColRowFromXY(newExtent[2], newExtent[3], extent, cellSize)
      print("xy: %s,%s -> %s,%s" % (newExtent[2], newExtent[3],c,r))
      print("ur value: arr[%s,%s] = %s" % (r,c,arr[r,c]))
      
      ras = Raster()
      ras.initRasterEmpty(extent,cellSize,np.uint8,noDataValue)
      ras.r = arr
      ras2 = ras.resize(newExtent)
      print(ras2.r)

    except:
      Err.showError()  

  #-------------------------------------------------------------------------------
  def testRasterResizeAndMerge1():
    try:
      extents = []
      
      extent = [-180.0,-56.0,-26.0,84.0]
      extents.append(extent)

      extent = [-26.0,-56.0,180.0,84.0]
      extents.append(extent)

      outDir = r""
      inRasName = os.path.join(outDir,"esa_copy_30sec.tif")
      
      inRas = Raster(inRasName)
      inRas.read()
  
      # Split    
      for i in range(len(extents)):
        extent = extents[i]

        newName = os.path.join(outDir,"esa_resize%s.tif"%i)
        if RU.rasterExists(newName):
          RU.rasterDelete(newName)
        print("resizing..."        )
        newRas = inRas.resize(extent)
        print("writing...")
        # 20170509        
        #newRas.write(newName)
        newRas.writeAs(newName)

      # Merge.
      print("merging...")
      
      # Merge extenst
      mergeExtent = extents[0]
      for i in range(len(extents)):
        extent = extents[i]
        mergeExtent = RU.calcExtentUnion(mergeExtent,extent)

      # Create output.
      outName = os.path.join(outDir,"esa_merge.tif")
      outRas = Raster(outName)
      outRas.initRaster(mergeExtent,inRas.cellSize,inRas.dataType,inRas.noDataValue)
      
      # Merge rasters.
      for i in range(len(extents)):
        rasName = os.path.join(outDir,"esa_resize%s.tif"%i)
        ras = Raster(rasName)
        ras.read()
        newRas = ras.resize(mergeExtent)
        # Merge.
        mask = (newRas.r != newRas.noDataValue)
        outRas.r[mask] = newRas.r[mask]
        newRas.close()
        newRas = None
         
      print("writing..."        )
      outRas.write()
      outRas.close()
      outRas = None

      print("Ready")
    except:
      Err.showError()  
      
  #-------------------------------------------------------------------------------
  def testRasterReadWrite():
    try:

      inDir = r""
      fn = os.path.join(inDir,"esa_copy_30sec.tif")
      fn2 = os.path.join(inDir,"test2.tif")

      print("reading..."        )
      ras = Raster(fn).read()

      ras.r += 100 

      if RU.rasterExists(fn2):
        RU.rasterDelete(fn2)
        
      print("writing..."        )
      ras.writeAs(fn2)

      ras.close()
      ras = None
      
      print("Ready")
    except:
      Err.showError()        
      
  #-------------------------------------------------------------------------------
  def testRasterWrite():
    pass

  #-------------------------------------------------------------------------------
  def testRasterWriteReadMem():
    pass  

  #-------------------------------------------------------------------------------
  def testRasterReadRow():
    pass
    # 20201118
    pass
    # 20201118

  #-------------------------------------------------------------------------------
  def testAsciiGridRaster():

    inFileName = "GREG_30min.asc"

    try:
      print("Reading raster: %s" % inFileName)
      pRaster = Raster(inFileName)
      pRaster.read()
      pRaster.showInfo()
      pRaster.close()
      del pRaster
    except:
      Err.showError()

    print()
    outFileName = "test.asc"
    try:

      nrCols = 6
      nrRows = 4
      extent = [0.0,0.0,60.0,40.0]
      cellSize = 10.0

      zoneRas = np.array([
        0,  0,  0,  0, 0, 25,
        0, 26, 26, 26, 0, 25,
        0,  0, 26, 26, 0, 25,
        0,  0,  0,  0, 0, 25
      ]).reshape(nrRows,nrCols)

      print(RU.isAsciiGridName(outFileName))

      print("Writing raster: %s" % outFileName)
      pRaster = Raster(outFileName)
      pRaster.initRasterEmpty(extent,cellSize,np.uint8)
      pRaster.r = zoneRas
      pRaster.write()
      pRaster.close()
      del pRaster
    except:
      Err.showError()

  #-------------------------------------------------------------------------------
  # ========================================
  # Majority
  # [[20 20 20 20 20 10]
  #  [20 10 10 10 10 10]
  # [99 20 99 99 99 99]
  # [20 20 20 20 20 99]]
  # Size: 6
  # [[20 10 10]
  #  [20 20 99]]
  # resample: 0.000 sec
  # ========================================
  # Sum + skip
  # [[20 20 20 20 20 10]
  #  [20 10 10 10 10 10]
  # [99 20 99 99 99 99]
  # [20 20 20 20 20 99]]
  # Size: 6
  # [[70 60 50]
  #  [60 40 20]]
  # resample: 0.000 sec
  # ========================================
  # Sum + no skip
  # [[20 20 20 20 20 10]
  #  [20 10 10 10 10 10]
  # [99 20 99 99 99 99]
  # [20 20 20 20 20 99]]
  # Size: 6
  # [[ 70  60  50]
  #  [159 238 317]]
  # resample: 0.000 sec
  # ========================================
  # Upsc - Majority
  # [[20 20 20 20 20 10]
  #  [20 10 10 10 10 10]
  # [99 20 99 99 99 99]
  # [20 20 20 20 20 99]]
  # Size: 96
  # [[20 20 20 20 20 20 20 20 20 20 10 10]
  #  [20 20 20 20 20 20 20 20 20 20 10 10]
  # [20 20 10 10 10 10 10 10 10 10 10 10]
  # [20 20 10 10 10 10 10 10 10 10 10 10]
  # [99 99 20 20 99 99 99 99 99 99 99 99]
  # [99 99 20 20 99 99 99 99 99 99 99 99]
  # [20 20 20 20 20 20 20 20 20 20 99 99]
  # [20 20 20 20 20 20 20 20 20 20 99 99]]
  # resample: 0.000 sec
  # ========================================
  # Upsc - Sum + skip
  # [[20 20 20 20 20 10]
  #  [20 10 10 10 10 10]
  # [99 20 99 99 99 99]
  # [20 20 20 20 20 99]]
  # Size: 96
  # [[ 5  5  5  5  5  5  5  5  5  5  2  2]
  #  [ 5  5  5  5  5  5  5  5  5  5  2  2]
  # [ 5  5  2  2  2  2  2  2  2  2  2  2]
  # [ 5  5  2  2  2  2  2  2  2  2  2  2]
  # [99 99  5  5 99 99 99 99 99 99 99 99]
  # [99 99  5  5 99 99 99 99 99 99 99 99]
  # [ 5  5  5  5  5  5  5  5  5  5 99 99]
  # [ 5  5  5  5  5  5  5  5  5  5 99 99]]
  # resample: 0.000 sec
  # ========================================
  # Upsc - Sum + no skip
  # [[20 20 20 20 20 10]
  #  [20 10 10 10 10 10]
  # [99 20 99 99 99 99]
  # [20 20 20 20 20 99]]
  # Size: 96
  # [[ 5  5  5  5  5  5  5  5  5  5  2  2]
  #  [ 5  5  5  5  5  5  5  5  5  5  2  2]
  # [ 5  5  2  2  2  2  2  2  2  2  2  2]
  # [ 5  5  2  2  2  2  2  2  2  2  2  2]
  # [24 24  5  5 24 24 24 24 24 24 24 24]
  # [24 24  5  5 24 24 24 24 24 24 24 24]
  # [ 5  5  5  5  5  5  5  5  5  5 24 24]
  # [ 5  5  5  5  5  5  5  5  5  5 24 24]]
  # resample: 0.000 sec
  #-----------------------------------------------------------------------------
  # Using Raster.resample.
  def testRasterResample():
    from GlobioModel.Common.Timer import Timer
    import GlobioModel.ArisPythonTest.TestData as TD

    tim = Timer()

    td = TD.TestData()

    tileFactor = 1
    #tileFactor = 2
    #tileFactor = 100
    #tileFactor = 500
    print("tileFactor: %s" % (tileFactor,))

    def createTestRaster(tileFactor):
      ras = td.createRasterLanduseNatureNoData_v1()
      raster = td.rasterFromRas(ras)
      print(raster.r)
      raster.repeat(tileFactor)
      if tileFactor == 2:
        print(raster.r)
      return raster

    # Majority.
    print("="*40)
    print("Majority")
    raster = createTestRaster(tileFactor)
    tim.start()
    newRaster = raster.resample(raster.cellSize * 2)
    tim.stop()
    print("Size: %s" % newRaster.r.size)
    print(newRaster.r)
    tim.show("resample: ")

    # Sum + skip.
    print("="*40)
    print("Sum + skip")
    raster = createTestRaster(tileFactor)
    tim.start()
    newRaster = raster.resample(raster.cellSize * 2,calcSumDiv=True,sumDivSkipNoData=True)
    tim.stop()
    print("Size: %s" % newRaster.r.size)
    print(newRaster.r)
    tim.show("resample: ")

    # Sum + no skip.
    print("="*40)
    print("Sum + no skip")
    raster = createTestRaster(tileFactor)
    tim.start()
    raster.noDataValue = -1
    newRaster = raster.resample(raster.cellSize * 2,calcSumDiv=True,sumDivSkipNoData=False)
    tim.stop()
    print("Size: %s" % newRaster.r.size)
    print(newRaster.r)
    tim.show("resample: ")

    # Upsc - Majority.
    print("="*40)
    print("Upsc - Majority")
    raster = createTestRaster(tileFactor)
    tim.start()
    newRaster = raster.resample(raster.cellSize / 2)
    tim.stop()
    print("Size: %s" % newRaster.r.size)
    print(newRaster.r)
    tim.show("resample: ")

    # Upsc - Sum + skip.
    print("="*40)
    print("Upsc - Sum + skip")
    raster = createTestRaster(tileFactor)
    tim.start()
    newRaster = raster.resample(raster.cellSize / 2,calcSumDiv=True,sumDivSkipNoData=True)
    tim.stop()
    print("Size: %s" % newRaster.r.size)
    print(newRaster.r)
    tim.show("resample: ")

    # Upsc - Sum + no skip.
    print("="*40)
    print("Upsc - Sum + no skip")
    raster = createTestRaster(tileFactor)
    raster.noDataValue = -1
    tim.start()
    newRaster = raster.resample(raster.cellSize / 2,calcSumDiv=True,sumDivSkipNoData=False)
    tim.stop()
    print("Size: %s" % newRaster.r.size)
    print(newRaster.r)
    tim.show("resample: ")

  #-------------------------------------------------------------------------------
  def testNetCDFRasterRead():

    inRasterName = "GLANDCOVER_30MIN.nc"
    inRasterName += "#ImageLandCoverNetCDF"
    inRasterName += "|1970|Cropland"

    try:
      print("Reading raster: %s" % inRasterName)

      print("- FileName: %s" % RU.getNetCDFFileName(inRasterName))
      print("- Type: %s" % RU.getNetCDFType(inRasterName))
      print("- Args: %s" % (RU.getNetCDFArguments(inRasterName),))

      print("- IsNetCDFName: %s" % RU.isNetCDFName(inRasterName))
      print("- RasterExists: %s" % RU.rasterExists(inRasterName))

      pRaster = Raster(inRasterName)
      print("Reading...")
      pRaster.read()
      print("Showing info...")
      pRaster.showInfo()
      print(pRaster.r.shape)
      del pRaster
    except:
      Err.showErrorWithTraceback()

  #-------------------------------------------------------------------------------
  def testRasterReadExtent():

    GLOB.debug = True

    ncRasterName = "GLANDCOVER_30MIN.nc"
    ncRasterName += "#ImageLandCoverNetCDF"
    ncRasterName += "|1970|Cropland"

    inRasterName = ncRasterName

    outDir = r""
    outRasterName = os.path.join(outDir,"glandcover_30min.tif")

    extRasterName1 = os.path.join(outDir,"extent_nc_30min.tif")
    extRasterName2 = os.path.join(outDir,"extent_tif_30min.tif")

    # Remove output.
    RU.rasterDelete(outRasterName)
    RU.rasterDelete(extRasterName1)
    RU.rasterDelete(extRasterName2)

    try:
      print("")
      print("Reading raster: %s" % inRasterName)
      inRaster = Raster(inRasterName)
      inRaster.read()
      inRaster.showInfo()

      print("Writing raster: %s" % outRasterName)
      outRaster = Raster()
      outRaster.initRasterLike(inRaster)
      outRaster.r = inRaster.r
      outRaster.writeAs(outRasterName)

      # Cleanup.
      del inRaster
      del outRaster

      print("")
      extent = [10.0, 10.0, 50.0, 30.0]
      print("Extent: %s" % extent)
      print("")

      # Read extent NC.
      print("")
      print("Reading raster: %s" % inRasterName)
      inRaster = Raster(inRasterName)
      inRaster.read(extent)
      inRaster.showInfo()

      print("Writing raster: %s" % extRasterName1)
      outRaster = Raster()
      outRaster.initRasterLike(inRaster)
      outRaster.r = inRaster.r
      outRaster.showInfo()
      outRaster.writeAs(extRasterName1)

      # Cleanup.
      del inRaster
      del outRaster

      # Read extent TIF.
      print("")
      print("Reading raster: %s" % outRasterName)
      inRaster = Raster(outRasterName)
      inRaster.read(extent)
      inRaster.showInfo()

      print("Writing raster: %s" % extRasterName2)
      outRaster = Raster()
      outRaster.initRasterLike(inRaster)
      outRaster.r = inRaster.r
      outRaster.showInfo()
      outRaster.writeAs(extRasterName2)

      # Cleanup.
      del inRaster
      del outRaster

      # Info.
      print("")
      print("Info")
      print("")
      pInfo = RU.rasterGetInfo(ncRasterName)
      pInfo.show(ncRasterName)
      pInfo = RU.rasterGetInfo(extRasterName1)
      pInfo.show(extRasterName1)
      pInfo = RU.rasterGetInfo(extRasterName2)
      pInfo.show(extRasterName2)

      # Compare.
      from GlobioModel.Calculations.GLOBIO_CompareRasters import GLOBIO_CompareRasters
      pCalc = GLOBIO_CompareRasters()
      pCalc.run(extRasterName1,extRasterName2)
      del pCalc

    except:
      Err.showErrorWithTraceback()

  #-------------------------------------------------------------------------------
  def testGetExtentByValue():

    GLOB.debug = True

    nrCols = 6
    nrRows = 4
    extent = [0.0,0.0,60.0,40.0]
    cellSize = 10.0
    noDataValue = 0

    ras = np.array([
      20, 20, 20, 20, 20, 12,
      20, 11, 11, 11, 12, 12,
      20, 20, 20, 11, 11, 14,
      20, 20, 13, 13, 14, 14
    ]).reshape(nrRows,nrCols)

    print(ras)

    raster = Raster()
    raster.initRasterEmpty(extent,cellSize,np.int32,noDataValue)
    raster.r = ras

    value = 11
    print(extent)
    print(value)
    ext = raster.getExtentByValue(value)
    print(ext)

    ras2 = raster.getDataByExtent(ext)
    print(ras2)

    # print("From: %s,%s " % (col1,row1))
    # print("To: %s,%s " % (col2,row2))
    #
    # # [[20 20 20 20 20 12]
    # #  [20 11 11 11 12 12]
    # #  [20 20 20 11 11 14]
    # #  [20 20 13 13 14 14]]
    # # From: 1,1
    # # To: 4,2
    #
    # region = raster.r[row1:row2+1,col1:col2+1]
    # print(region)
    #
    # row1 = 0
    # col1 = 0
    # row2 = 3
    # col2 = 3
    # print()
    # print(ras)
    # print("From: %s,%s " % (col1,row1))
    # print("To: %s,%s " % (col2,row2))
    # region = raster.r[row1:row2+1,col1:col2+1]
    # print(region)
    #
    # row1 = 2
    # col1 = 2
    # row2 = 2
    # col2 = 4
    # print()
    # print(ras)
    # print("From: %s,%s " % (col1,row1))
    # print("To: %s,%s " % (col2,row2))
    # region = raster.r[row1:row2+1,col1:col2+1]
    # #region = raster.r[row1:row2,col1:col2+1]
    # print(region)
    #
    # # region = raster.getRegionByColsRows(col1,row1,col2,row2)
    # # print(region)

  #-------------------------------------------------------------------------------
  def testReplace():

    GLOB.debug = True

    nrCols = 6
    nrRows = 4
    extent = [0.0,0.0,60.0,40.0]
    cellSize = 10.0
    noDataValue = 99

    ras = np.array([
      20, 20, 20, 20, 20, 10,
      20, 10, 10, 10, 10, 10,
      99, 20, 99, 99, 99, 99,
      20, 20, 20, 20, 20, 99
    ]).reshape(nrRows,nrCols)

    print("Main raster:")
    print(ras)

    raster = Raster()
    raster.initRasterEmpty(extent,cellSize,np.int32,noDataValue)
    raster.r = ras

    extent2 = [0.0,0.0,30.0,20.0]
    subRas = np.array([
      1,  2,  3,
      11, 12, 13,
    ]).reshape(2,3)
    print("Sub raster:")
    print(subRas)

    subRaster = Raster()
    noDataValue = 13
    subRaster.initRasterEmpty(extent2,cellSize,np.int32,noDataValue)
    subRaster.r = subRas

    raster.replace(subRaster)
    print("Result raster:")
    print(raster.r)

  #-------------------------------------------------------------------------------
  def testGetExtentByValue_Region12():

    GLOB.debug = True
    from GlobioModel.Core.CalculationBase import  CalculationBase

    rasterName = "GREG_30min.asc"
    region = 12

    extent = [-25.0, 33.0, 45.0, 72.0]
    cellSize = 0.5

    pInfo = RU.rasterGetInfo(rasterName)
    pInfo.show()
    pCalc = CalculationBase()
    raster = pCalc.readAndPrepareInRaster_V2(extent,cellSize,rasterName,
                                             "region",
                                             calcSumDiv=False)

    savRasterName = "tmp.tif"
    if not RU.rasterExists(savRasterName):
      RU.rasterDelete(savRasterName)
      savRaster = Raster(savRasterName)
      savRaster.initRasterLike(raster)
      savRaster.r = raster.r
      print("Writing %s..." % savRasterName)
      savRaster.write()
      del savRaster

    def getExtentByValue(raster,value):
      #print("getExtentByValue")
      #print("(%s,%s)" % (raster.nrRows,raster.nrCols))
      # minX = raster.extent[0]
      # minY = raster.extent[1]
      # print(RU.calcExtentFromColsRows(minX,minY,raster.cellSize,
      #                                 0,0,raster.nrCols,raster.nrRows))
      # Get rows/cols coordinates.
      rowscols = np.where(raster.raster==value)
      # Get min/max coordinates.
      row1 = rowscols[0].min()
      row2 = rowscols[0].max()
      col1 = rowscols[1].min()
      col2 = rowscols[1].max()

      # col1 = rowscols[0].min()
      # col2 = rowscols[0].max()
      # row1 = rowscols[1].min()
      # row2 = rowscols[1].max()

      # print("(%s,%s)" % (row2-row1,col2-col1))
      # Get extent.
      minX = raster.extent[0]
      minY = raster.extent[1]
      # print("row")
      # print(raster.raster[row2+1])
      # print(raster.raster[row2+2])
      return RU.calcExtentFromColsRows(minX,minY,raster.cellSize,col1,row1,col2,row2)

# Org extent: [-25.0, 33.0, 45.0, 72.0]
# (140, 78)
# 0.5
# Region: 12
# Calc extent: [12.5, 45.0, 34.5, 70.5]

    print("Org extent: %s" % (extent,))
    print(RU.calcNrColsRowsFromExtent(extent,cellSize))
    print(cellSize)
    print("Region: %s" % region)
    #ext = raster.getExtentByValue(region)
    ext = getExtentByValue(raster,region)
    print("Calc extent: %s" % (ext,))

    print("#"*40)
    minX = 0
    minY = 10
    cellSize = 1
    ext = RU.calcExtentFromColsRows(minX,minY,raster.cellSize,0,0,4,4)
    print("Calc extent: %s" % (ext,))

    test2 = True
    if test2:
      return
    print("#"*40)

    def getExtentByValue2(raster,value):
      print("getExtentByValue2")
      row1 = 9999
      col1 = 9999
      row2 = -1
      col2 = -1
      for r in range(raster.nrRows):
        for c in range(raster.nrCols):
          if raster.r[r,c] == value:
            row1 = min(row1,r)
            col1 = min(col1,c)
            row2 = max(row2,r)
            col2 = max(col2,c)
            #continue
      print("col/row: %s,%s,%s,%s" % (col1,row1,col2,row2))
      print("nr col/row: %s,%s" % (col2-col1,row2-row1))
      # Get extent.
      minX = raster.extent[0]
      minY = raster.extent[1]
      # print("row")
      # print(raster.raster[row2+1])
      # print(raster.raster[row2+2])
      return RU.calcExtentFromColsRows(minX,minY,raster.cellSize,col1,row1,col2,row2)
    ext = getExtentByValue2(raster,region)
    print(ext)

    subRasterName = "tmp.tif"
    RU.rasterDelete(subRasterName)
    subRas = raster.getDataByExtent(ext)
    print(subRas)
    print(subRas.shape)
    subRaster = Raster(subRasterName)
    subRaster.initRasterEmpty(ext,cellSize,raster.dataType,0)
    subRaster.r = subRas
    print("Writing %s..." % subRasterName)
    subRaster.write()
    del subRaster

  #-------------------------------------------------------------------------------
  def testGetExtentByValue_Region12b():

    GLOB.debug = True
    from GlobioModel.Core.CalculationBase import  CalculationBase

    rasterName = "GREG_30min.asc"
    region = 12

    #extent = [-25.0, 33.0, 45.0, 72.0]
    #cellSize = 0.5

    pInfo = RU.rasterGetInfo(rasterName)
    pInfo.show()
    raster = Raster(rasterName)
    raster.read()

    nc,nr = RU.calcNrColsRowsFromExtent(raster.extent,raster.cellSize)
    print("nr col/row: %s,%s" % (nc,nr))
    okExtent = [12,39,29,60]
    okExtent = [12,34,35,60]  # incl cyprus
    print("ok extent %s: " % (okExtent,))
    nc,nr = RU.calcNrColsRowsFromExtent(okExtent,raster.cellSize)
    print("nr col/row: %s %s" % (nc,nr))
    c,r = RU.calcColRowFromXY(okExtent[0],okExtent[1],raster.extent,raster.cellSize)
    #print("min xy col/row: %s %s" % (c,r))
    c2,r2 = RU.calcColRowFromXY(okExtent[2],okExtent[3],raster.extent,raster.cellSize)
    #print("max xy col/row: %s %s" % (c2,r2))
    print("col/row: %s %s %s %s" % (c,r,c2,r2))

    print("#"*40)

  #-------------------------------------------------------------------------------
  def testGetExtentByValue_Region12c():

    GLOB.debug = True
    from GlobioModel.Core.CalculationBase import  CalculationBase

    rasterName = "GREG_30min.asc"
    region = 12

    print("#"*40)
    pInfo = RU.rasterGetInfo(rasterName)
    pInfo.show()
    raster = Raster(rasterName)
    raster.read()

    print("#"*40)
    nc,nr = RU.calcNrColsRowsFromExtent(raster.extent,raster.cellSize)
    print("nr col/row: %s,%s" % (nc,nr))
    okExtent = [12,39,29,60]
    okExtent = [12,34,35,60]  # incl cyprus
    print("ok extent %s: " % (okExtent,))
    nc,nr = RU.calcNrColsRowsFromExtent(okExtent,raster.cellSize)
    print("nr col/row: %s %s" % (nc,nr))
    c,r = RU.calcColRowFromXY(okExtent[0],okExtent[1],raster.extent,raster.cellSize)
    #print("min xy col/row: %s %s" % (c,r))
    c2,r2 = RU.calcColRowFromXY(okExtent[2],okExtent[3],raster.extent,raster.cellSize)
    #print("max xy col/row: %s %s" % (c2,r2))
    print("col/row: %s %s %s %s" % (c,r,c2,r2))

    print("#"*40)
    ext = raster.getExtentByValue(region)
    if not ext is None:
      print(ext)
      subRasterName = "tmp.tif"
      RU.rasterDelete(subRasterName)
      subRas = raster.getDataByExtent(ext)
      subRaster = Raster(subRasterName)
      subRaster.initRasterEmpty(ext,raster.cellSize,raster.dataType,0)
      subRaster.r = subRas
      print("Writing %s..." % subRasterName)
      subRaster.write()
      del subRaster


    print("#"*40)
    newRasterName = "GREG_30min.tif"
    if not RU.rasterExists(newRasterName):
      #RU.rasterDelete(newRasterName)
      newRaster = Raster(newRasterName)
      newRaster.initRasterEmpty(raster.extent,raster.cellSize,raster.dataType,0)
      newRaster.r = raster.r
      print("Writing %s..." % newRasterName)
      newRaster.write()
      del newRaster

    print("#"*40)
    pInfo = RU.rasterGetInfo(newRasterName)
    pInfo.show()
    raster = Raster(newRasterName)
    raster.read()

    print("#"*40)
    ext = raster.getExtentByValue(region)
    if not ext is None:
      print(ext)
      subRasterName = r"tmp.tif"
      if not RU.rasterExists(subRasterName):
        #RU.rasterDelete(subRasterName)
        subRas = raster.getDataByExtent(ext)
        subRaster = Raster(subRasterName)
        subRaster.initRasterEmpty(ext,raster.cellSize,raster.dataType,0)
        subRaster.r = subRas
        print("Writing %s..." % subRasterName)
        subRaster.write()
        del subRaster

#-------------------------------------------------------------------------------
  #
  # run Core\Raster.py
  #
  #testRasterResize1()
  #testRasterResize2()
  #testRasterResizeAndMerge1()
  #testRasterReadWrite()
  #testRasterWrite()
  #testRasterWriteReadMem()
  #testRasterReadRow()
  #testAsciiGridRaster()
  #testRasterResample()
  #testNetCDFRasterRead()
  #testRasterReadExtent()
  #testGetExtentByValue()
  #testReplace()
  #testGetExtentByValue_Region12()
  #testGetExtentByValue_Region12b()
  testGetExtentByValue_Region12c()
