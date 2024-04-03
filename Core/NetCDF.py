# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
#
# Remarks:
#           Only NetCDF files with world extent are supported.
#           Due to the lack of spatial reference info in the files the
#           world extent is used as default and the cellsize can be
#           calculated using the number of columns and rows.
#
# Example:
#           <TODO>
#
# Modified: 9 dec 2020, ES, ARIS B.V.
#           - Version 4.1.0
#-------------------------------------------------------------------------------

import os

import netCDF4 as nc
import numpy as np

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Common.Utils as UT

import GlobioModel.Core.RasterUtils as RU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class NetCDF(object):
  fileName = ""
  varDefs = ""
  dataset = None
  raster = None
  extent = None
  cellSize = None
  nrCols = None
  nrRows = None
  dataType = None
  noDataValue = 0

  #-------------------------------------------------------------------------------
  # Filename = .nc filename.
  def init(self,fileName,extent,varDefs):
    self.fileName = fileName
    self.extent = extent
    self.varDefs = varDefs

    # Check extent. Now only world extent is supported!
    if not RU.isEqualExtent(extent,GLOB.extent_World,GLOB.cellSize_10sec):
      # TODO: Constante van maken.
      Err.raiseGlobioError(Err.UserDefined1,"Only NetCDF files with world extent are supported.")

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
  def close(self):
    if not self.dataset is None:
      del self.dataset
    if not self.raster is None:
      del self.raster

  #-------------------------------------------------------------------------------
  # Gets the indices for fetching the data.
  # The indices are dependent from the needed values per variable.
  #
  # If the minCol etc. are given then these values will be used to create
  # sliced indices for the raster data.
  #
  # varDef is an array with:
  #   [time@TIME=2017, GLANDCOVER_30MIN@RASTER=, NGLNDCOV@STRING=Cropland]
  #
  def getDataIndices(self,varDefs,minCol=None,minRow=None,nrCols=None,nrRows=None):
    indices = []
    for varDef in varDefs:
      varNameType = UT.strBefore(varDef,"=").upper()
      varName = UT.strBefore(varNameType,"@")
      varType = UT.strAfter(varNameType,"@")
      varValue = UT.strAfter(varDef,"=")

      # print("."*10)
      # print(varName)

      if varType == "RASTER":
        if (not minCol is None):
          # Add 2 slices for the 2d raster.
          indices.append(slice(minRow,minRow+nrRows))
          indices.append(slice(minCol,minCol+nrCols))
        else:
          # Add 2 ":" for the 2d raster.
          indices.append(slice(None))         # ":" equivalent
          indices.append(slice(None))         # ":" equivalent
        #Log.dbg("getDataIndices %s" % (indices))
      elif varType == "TIME":
        # Get values.
        values = self.getVariableValues(varName)
        # Convert days to years.
        years = [UT.yearFromDays(v) for v in values]

        # print(varName)
        # print(values)
        # print(years)

        # Get index.
        idx = UT.arrayValueGetIndex(years,int(varValue))

        # Not found?
        if idx < 0:
          Err.raiseGlobioError(Err.UserDefined1,
                               "NetCDF variable value not found: %s" % (varValue))
        indices.append(idx)
      elif varType == "STRING":

        # print("*"*66)
        # print("getDataIndices %s" % (varName))

        # Get string values.
        values = self.getVariableValuesAsStr(varName)

        # print(varName)
        # print(values)

        # Get index.
        idx = UT.arrayValueGetIndex(values,varValue)

        # Not found?
        if idx < 0:
          Err.raiseGlobioError(Err.UserDefined1,
                               "NetCDF variable value not found: %s" % (varValue))
        indices.append(idx)
      else:
        Err.raiseGlobioError(Err.UserDefined1,"Invalid NetCDF variable type specified: %s" % (varName))
    return indices

  #-------------------------------------------------------------------------------
  # Gets the variable name with the @RASTER mark.
  # varDef is an array with:
  #   [time@TIME=2017, GLANDCOVER_30MIN@RASTER=, NGLNDCOV@STRING=Cropland]
  def getDataName(self,varDefs):
    for varDef in varDefs:
      varDefName = UT.strBefore(varDef,"=").upper()
      if varDefName.endswith("@RASTER"):
        return UT.strBefore(varDef,"@")
    return ""

  #-------------------------------------------------------------------------------
  def getDimension(self,dimName: str) -> nc.Dimension:
    # Get dimension names.
    dimensionNames = list(self.dataset.dimensions.keys())
    dimensionNamesUC = [v.upper() for v in dimensionNames]
    dimNameUC = dimName.upper()
    idx = dimensionNamesUC.index(dimNameUC)
    # Not found?
    if idx < 0:
      Err.raiseGlobioError(Err.UserDefined1,"Dimension '%s' not found." % dimName)
    # Return dimension.
    dimName = dimensionNames[idx]
    return self.dataset.dimensions[dimName]

  #-------------------------------------------------------------------------------
  def getDimensionNames(self) -> [str]:
    return list(self.dataset.dimensions.keys())

  #-------------------------------------------------------------------------------
  # Returns the time values as years.
  def getTimeValues(self) -> [any]:
    # Set default variable name "time".
    varName = "time"
    # Get variable.
    var = self.getVariable(varName)
    if var is None:
      Err.raiseGlobioError(Err.UserDefined1,"Variable '%s' not found." % varName)
    timeValues = var[:]
    # Convert to years.
    years = [UT.yearFromDays(v) for v in timeValues]
    return years

  #-------------------------------------------------------------------------------
  # Returns the longitude/latitude numpy datatype.
  # Raises am exception if the longitude/latitude variables are not found.
  def getLonLatDataType(self) -> np.dtype:
    lonName = "longitude"
    latName = "latitude"
    varNames = self.getVariableNames()
    if not lonName in varNames:
      Err.raiseGlobioError(Err.NoNetCDFInfoFoundInFile2, lonName, self.fileName)
    if not latName in varNames:
      Err.raiseGlobioError(Err.NoNetCDFInfoFoundInFile2, latName, self.fileName)
    lonVar = self.getVariable(lonName)
    return lonVar.dtype

  #-------------------------------------------------------------------------------
  # Returns the longitude/latitude dimensions as tuple (nrCols,nrRows).
  # Raises am exception if the longitude/latitude variables are not found.
  def getLonLatDimensions(self) -> (int,int):
    lonName = "longitude"
    latName = "latitude"
    varNames = self.getVariableNames()
    if not lonName in varNames:
      Err.raiseGlobioError(Err.NoNetCDFInfoFoundInFile2, lonName, self.fileName)
    if not latName in varNames:
      Err.raiseGlobioError(Err.NoNetCDFInfoFoundInFile2, latName, self.fileName)
    lonVar = self.getVariable(lonName)
    latVar = self.getVariable(latName)
    return (lonVar.shape[0],latVar.shape[0])

  #-------------------------------------------------------------------------------
  # Returns the longitude/latitude nodata value.
  # Raises am exception if the longitude/latitude variables are not found.
  def getLonLatNoDataValue(self) -> any:
    lonName = "longitude"
    latName = "latitude"
    varNames = self.getVariableNames()
    if not lonName in varNames:
      Err.raiseGlobioError(Err.NoNetCDFInfoFoundInFile2, lonName, self.fileName)
    if not latName in varNames:
      Err.raiseGlobioError(Err.NoNetCDFInfoFoundInFile2, latName, self.fileName)
    lonVar = self.getVariable(lonName)
    # TODO: OK?
    if hasattr(lonVar,"missing_value"):
      return lonVar.missing_value
    else:
      return 9.969209968386869e+36

  #-------------------------------------------------------------------------------
  def getVariable(self,varName: str) -> nc.Variable:
    # Get variable names.
    variableNames = list(self.dataset.variables.keys())

    #print("getVariable %s" % (variableNames))

    variableNamesUC = [v.upper() for v in variableNames]
    varNameUC = varName.upper()

    #print("getVariable")

    idx = variableNamesUC.index(varNameUC)
    # Not found?
    if idx < 0:
      Err.raiseGlobioError(Err.UserDefined1,"Variable '%s' not found." % varName)
    # Get proper variable name.
    varName = variableNames[idx]
    # Return variable.
    return self.dataset.variables[varName]

  #-------------------------------------------------------------------------------
  def getVariableNames(self) -> [str]:
    return list(self.dataset.variables.keys())

  #-------------------------------------------------------------------------------
  # Returns a numpy array.
  def getVariableValues(self,varName: str, noDataValue: any=None) -> [any]:
    # Get variable.
    var = self.getVariable(varName)
    #print("getVariableValues %s" % (var))
    if var is None:
      Err.raiseGlobioError(Err.UserDefined1,"Variable '%s' not found." % varName)
    # Get values.
    values = var[:]
    # Convert masked to simple.
    return RU.maskedToNumpy(values,noDataValue)

  #-------------------------------------------------------------------------------
  # Gets the variable byte values (|S1) and converts these to a string.
  # Removes tailing zeros, i.e. b"0".
  # Returns a standard array.
  def getVariableValuesAsStr(self,varName: str) -> [str]:
    # Get variable.
    var = self.getVariable(varName)

    #print("getVariableValuesAsStr %s" % (var))

    if var is None:
      Err.raiseGlobioError(Err.UserDefined1,"Variable '%s' not found." % varName)
    # Get values.
    values = var[:]
    # Convert masked to simple.
    values = RU.maskedToNumpy(values,0)
    # Check type.
    if values.dtype != "|S1":
      Err.raiseGlobioError(Err.UserDefined1,"No valid type for variable '%s'." % varName)
    # Convert bytes to strings.
    strValues = []
    for value in values:
      strValues.append(UT.numpyToStr(value))
    return strValues

  #-------------------------------------------------------------------------------
  def max(self):
    return np.max(self.raster[self.raster != self.noDataValue])

  #-------------------------------------------------------------------------------
  def min(self):
    return np.min(self.raster[self.raster != self.noDataValue])

  #-------------------------------------------------------------------------------
  def printDimensionInfo(self, dimension: nc.Dimension, prefix: str=""):
    prefix += "  "
    if hasattr(dimension,"name"):
      Log.info("%sName      : %s"%(prefix,dimension.name))
    if hasattr(dimension,"size"):
      Log.info("%sSize      : %s"%(prefix,dimension.size))

  #-------------------------------------------------------------------------------
  def printVariableInfo(self, variable: nc.Variable, prefix: str=""):
    prefix += "  "
    if hasattr(variable,"name"):
      Log.info("%sName      : %s"%(prefix,variable.name))
    if hasattr(variable,"long_name"):
      Log.info("%sLong name : %s"%(prefix,variable.long_name))
    if hasattr(variable,"dtype"):
      Log.info("%sDType     : %s"%(prefix,variable.dtype))
    if hasattr(variable,"shape"):
      Log.info("%sShape     : %s"%(prefix,variable.shape))
    if hasattr(variable,"size"):
      Log.info("%sSize      : %s"%(prefix,variable.size))
    if hasattr(variable,"units"):
      Log.info("%sUnits     : %s"%(prefix,variable.units))
    if hasattr(variable,"ndim"):
      Log.info("%sNDim      : %s"%(prefix,variable.ndim))
    if hasattr(variable,"dimensions"):
      Log.info("%sDimensions: %s"%(prefix,variable.dimensions))
    if hasattr(variable,"mask"):
      Log.info("%sMask      : %s"%(prefix,variable.mask))
    if hasattr(variable,"scale"):
      Log.info("%sScale     : %s"%(prefix,variable.scale))

  #-------------------------------------------------------------------------------
  # Read the dataset and raster as readonly.
  #
  # If the extent is given then this value will overrule the original
  # extent of the raster file.
  #
  # Raises an exception if the specified extent is greater than the original
  # extent of the raster file.
  def read(self,extent=None):

    # Open dataset.
    if self.dataset is None:
      self.readDataset()

    # Read info.
    if self.nrCols is None:
      self.readInfo()

    # Custom extent specified? Check if custom extent is in original extent.
    if not extent is None:
      if  not RU.isExtentInExtent(extent,self.extent):
        # TODO: Constante van maken.
        Err.raiseGlobioError(Err.UserDefined1,
                             "The specified extent does not lie in the original raster extent.")

    # Initialize vars for custom extent.
    minCol = None
    minRow = None
    nrCols = None
    nrRows = None

    # Use custom extent?
    if not extent is None:
      # Align custom extent.
      extent = RU.alignExtent(extent,self.cellSize)
      # A different custom extent then the original?
      if not RU.isEqualExtent(self.extent,extent,self.cellSize):
        # Calculate col/row offset and width/height of custom extent.
        minCol,minRow,nrCols,nrRows = RU.calcColRowWindowFromExtent(extent,
                                                                    self.extent,
                                                                    self.cellSize)
        # Update extent.
        self.extent = extent

    # Get data indices.
    indices = self.getDataIndices(self.varDefs,minCol,minRow,nrCols,nrRows)

    # Get data name.
    varDataName = self.getDataName(self.varDefs)

    # Get the data.
    data = self.getVariableValues(varDataName,self.noDataValue)

    #Log.dbg(varDataName)
    #Log.dbg(data.shape)    # (27, 360, 720, 5)
    #Log.dbg(indices)       # [0, slice(None, None, None), slice(None, None, None), 0]

    # Extract raster data.
    if len(indices) == 1:
      self.raster = data[indices[0]]
    elif len(indices) == 2:
      self.raster = data[indices[0],indices[1]]
    elif len(indices) == 3:
      self.raster = data[indices[0],indices[1],indices[2]]
    elif len(indices) == 4:
      self.raster = data[indices[0],indices[1],indices[2],indices[3]]
    elif len(indices) == 5:
      self.raster = data[indices[0],indices[1],indices[2],indices[3],indices[4]]
    else:
      Err.raiseGlobioError(Err.UserDefined1,"Cannot read NetCDF file. Too many dimensions.")

    #Log.dbg(self.raster.shape)

    # Check raster data.
    if self.raster.ndim != 2:
      Err.raiseGlobioError(Err.UserDefined1,"Cannot read NetCDF file. No raster data.")

    # Set raster info.
    self.nrCols = self.raster.shape[1]
    self.nrRows = self.raster.shape[0]
    self.cellSize = (self.extent[2] - self.extent[0]) / self.nrCols
    self.dataType = self.raster.dtype
    self.noDataValue = RU.getNoDataValue(self.dataType)

    # For chaining.
    return self

  #-------------------------------------------------------------------------------
  # Reads the dataset as readonly.
  # Example:
  #   C:\Data\claims.nc#time=2017|GLANDCOVER_30MIN=<DATA>|GLANDCOVER_30MIN=<DATA>|NGLNDCOV=Crop land
  def readDataset(self):

    # Check if raster exist.
    if not RU.rasterExists(self.fileName):
      Err.raiseGlobioError(Err.RasterNotFound1,self.fileName)

    # Open raster.
    if self.dataset is None:
      self.dataset = nc.Dataset(self.fileName)

  #-------------------------------------------------------------------------------
  # Reads the raster info (extent,cellsize,nrCols,nrRows,dataType,noDataValue).
  # Does not open the dataset/band if not already opened.
  def readInfo(self):

    # Read datset if not already done.
    self.readDataset()

    # Check extent.
    if self.extent is None:
      # TODO: Constante van maken.
      Err.raiseGlobioError(Err.UserDefined1,"No extent specified of NetCDF file.")

    # Get number of columns and rows,
    self.nrCols,self.nrRows = self.getLonLatDimensions()

    # Calculate cellsize.
    self.cellSize = (self.extent[2] - self.extent[0]) / self.nrCols

    # Get datatype and nodata value.
    self.dataType = self.getLonLatDataType()
    self.noDataValue = self.getLonLatNoDataValue()

  #-------------------------------------------------------------------------------
  # Shows the raster info.
  def showInfo(self,prefix=""):
    # Check raster.
    if self.raster is None:
      self.read()
    Log.info("%sCellSize: %s" % (prefix,self.cellSize))
    Log.info("%sExtent: %s" % (prefix,self.extent))
    Log.info("%sNrCols/NrRows: %s %s" % (prefix,self.nrCols,self.nrRows))
    Log.info("%sType: %s" % (prefix,RU.dataTypeNumpyToString(self.dataType)))
    Log.info("%sNoData: %s" % (prefix,self.noDataValue))
    Log.info("%sMin: %s" % (prefix,self.min()))
    Log.info("%sMax: %s" % (prefix,self.max()))

  #-------------------------------------------------------------------------------
  # Shows the basic NetCDF info.
  def showBasicInfo(self):

    # Check dataset.
    if self.dataset is None:
      self.readDataset()

    # FileName
    Log.info("")
    Log.info("="*80)
    Log.info("= FileName: %s" % self.fileName)
    Log.info("="*80)

    # METADATA
    Log.info("")
    Log.info("-"*80)
    Log.info("Metadata:")
    Log.info(self.dataset)

    # DIMENSIONS
    Log.info("")
    Log.info("-"*80)
    dimNames = self.getDimensionNames()
    Log.info("Dimensions: %s" % (dimNames))

    # DIMENSION INFO
    Log.info("")
    Log.info("-"*80)
    for dimName in dimNames:
      Log.info("Dimension: %s" % (dimName))
      dim = self.getDimension(dimName)
      #print(dir(dim))
      self.printDimensionInfo(dim)

    # VARIABLES
    Log.info("")
    Log.info("-"*80)
    varNames = self.getVariableNames()
    Log.info("Variables: %s" % (varNames))

    # VARIABLE INFO
    Log.info("")
    Log.info("-"*80)
    for varName in varNames:
      Log.info("Variable: %s" % (varName))
      var = self.getVariable(varName)
      self.printVariableInfo(var)

    # LANDCOVER VALUES
    varName = "NGLNDCOV"
    if varName in varNames:
      Log.info("")
      Log.info("-"*80)
      Log.info("Variable: %s" % (varName))
      values = self.getVariableValuesAsStr(varName)
      Log.info("%s" % (values))

    # TIME VALUES
    varName = "time"
    if varName in varNames:
      Log.info("")
      Log.info("-"*80)
      Log.info("Variable: %s" % (varName))
      values = self.getTimeValues()
      Log.info("%s" % (values))

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
#
# run Core\NetCDF.py
#
if __name__ == "__main__":

  #GLOB.SHOW_TRACEBACK_ERRORS = True

  #-------------------------------------------------------------------------------
  # Basic NetCDF info.
  def test1():
    try:
      fileName = r"G:\data\imgluh_20201118\GLANDCOVER_30MIN.nc"

      extent = GLOB.extent_World

      pNetCDF = NetCDF()
      pNetCDF.init(fileName,extent,None)
      pNetCDF.read()

      print()
      print("#"*80)
      dimNames = pNetCDF.getDimensionNames()
      print("Dimensions: %s" % (dimNames))

      print()
      print("#"*80)
      varNames = pNetCDF.getVariableNames()
      print("Variables: %s" % (varNames))

      print()
      print("#"*80)
      pNetCDF.showInfo()

      pNetCDF.close()
      del pNetCDF

    except:
      Log.err()

  #-------------------------------------------------------------------------------
  # NOK
  # Time NetCDF info.
  def test2():
    try:
      fileName = r"G:\data\imgluh_20201118\GLANDCOVER_30MIN.nc"

      extent = GLOB.extent_World

      pNetCDF = NetCDF()
      pNetCDF.init(fileName,extent,None)
      pNetCDF.read()

      print()
      print("#"*80)
      varName = "Time"
      print("Variable values of '%s':" % (varName))
      print(pNetCDF.getVariableValues(varName))

      print()
      print("#"*80)
      print("Time values:")
      dates =pNetCDF.getTimeValues()
      print(dates)

      pNetCDF.close()
      del pNetCDF

    except:
      Log.err()

  #-------------------------------------------------------------------------------
  # Rasters and landuse codes.
  def test3():
    try:
      fileName = r"G:\data\imgluh_20201118\GLANDCOVER_30MIN.nc"

      extent = GLOB.extent_World

      pNetCDF = NetCDF()
      pNetCDF.init(fileName,extent,None)
      pNetCDF.read()

      print()
      print("#"*80)
      varNames = pNetCDF.getVariableNames()
      print("Variables: %s" % (varNames))

      print()
      print("#"*80)
      varName = "GLANDCOVER_30MIN"
      print("Variable values of '%s':" % (varName))
      noDataValue = 0
      ras = pNetCDF.getVariableValues(varName,noDataValue)
      print(ras.shape)    # (27, 360, 720, 5)
      ras0 = ras[0,:,:,0]
      print(ras0.shape)   # (360, 720)
      UT.printArray("",ras0[180])

      print()
      print("#"*80)
      varName = "NGLNDCOV"
      print("Variable values of '%s':" % (varName))
      values = pNetCDF.getVariableValues(varName)
      print(values.dtype)
      print(values.shape)    # (27, 360, 720, 5)
      values = pNetCDF.getVariableValuesAsStr(varName)
      print(values)

      # [-- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
      # ...
      # -- -- -- -- -- -- -- -- 0.0 0.0 0.0 -- -- -- -- -- -- -- -- -- -- -- --
      # -- -- -- -- -- -- -- -- 0.1149006336927414 0.15656429529190063
      #  0.14238573610782623 0.016048887744545937 0.04239996522665024 0.0 0.0
      #  0.03971409797668457 0.0 0.0 0.0 0.006588908843696117 0.0 0.0 0.0 0.0 0.0
      #  0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0
      #  0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0

      # print("."*80)
      # #v = ras0[180][0]
      # v = ras0[180]
      # print(v.view(np.ma.MaskedArray))
      # print(v)


      # # v2 = v.astype(float)
      # # v2[v2.mask] = 999
      # # print(v2)
      # # v2.mask = np.ma.nomask
      # # print(v2)
      # # print(v2.view())
      # v3 = np.full(v.shape,999,np.float)
      # #v3 = np.array()
      # v3[~v.mask] = v[~v.mask]
      # print(v3)

      # print("."*80)
      # va = np.ma.asarray(v*10,np.int)
      # print(va)

      # print(int(v))
      # if np.isnan(v):
      #   print("isnan")
      # else:
      #   print("not isnan")

      # print()
      # print("#"*80)
      # print("Time values:")
      # dates =pNetCDF.getTimeValues()
      # print(dates)

    except:
      Log.err()
    finally:
      del pNetCDF

  #-------------------------------------------------------------------------------
  # Rasters and landuse codes.
  def test4():
    try:
      fileName = r"G:\data\imgluh_20201118\GLANDCOVER_30MIN.nc"

      extent = GLOB.extent_World

      pNetCDF = NetCDF()
      pNetCDF.init(fileName,extent,None)
      pNetCDF.readDataset()

      # METADATA
      print(pNetCDF.dataset)

      # DIMENSIONS
      print()
      print("#"*80)
      dimNames = pNetCDF.getDimensionNames()
      print("Dimensions: %s" % (dimNames))

      # DIMENSION INFO
      print()
      print("#"*80)
      for dimName in dimNames:
        print("Dimension: %s" % (dimName))
        dim = pNetCDF.getDimension(dimName)
        #print(dir(dim))
        pNetCDF.printDimensionInfo(dim)

      # VARIABLES
      print()
      print("#"*80)
      varNames = pNetCDF.getVariableNames()
      print("Variables: %s" % (varNames))

      # VARIABLE INFO
      print()
      print("#"*80)
      for varName in varNames:
        print("Variable: %s" % (varName))
        var = pNetCDF.getVariable(varName)
        pNetCDF.printVariableInfo(var)

      # VARIABLE VALUES
      print()
      print("#"*80)
      varName = "time"
      print("Variable: %s" % (varName))
      values = pNetCDF.getVariableValues(varName)
      print("%s" % (values))

      # TIME VALUES
      print()
      print("#"*80)
      varName = "time"
      print("Variable: %s" % (varName))
      values = pNetCDF.getTimeValues()
      print("%s" % (values))

      del pNetCDF
    except:
      Log.err()

  #-------------------------------------------------------------------------------
  # Rasters and landuse codes.
  def testBasicInfo5():
    fileName = r"G:\data\imgluh_20201118\GLANDCOVER_30MIN.nc"

    try:
      extent = GLOB.extent_World

      pNetCDF = NetCDF()
      pNetCDF.init(fileName,extent,None)
      pNetCDF.showBasicInfo()
      del pNetCDF
    except:
      Log.err()

  #-------------------------------------------------------------------------------
  # Rasters and landuse codes.
  def testInfo7():

    # Image data (NetCDF).
    inDir = r"G:\data\imgluh_20201118"
    ncFileName = os.path.join(inDir,"GLANDCOVER_30MIN.nc")
    imgLandcoverNamesNetCDFVarName = "NGLNDCOV"
    imgYearNetCDFVarName = "TIME"
    imgDataNetCDFVarName = "GLANDCOVER_30MIN"

    imgLandcoverName = "Cropland"
    year = 1970

    # Get the full raster/NetCDF name to get the claim data.
    # varDefs = [
    #   "%s=%s" % (imgYearNetCDFVarName,year),
    #   "%s=%s" % (imgDataNetCDFVarName,"<RASTER>"),
    #   "%s=%s" % (imgLandcoverNamesNetCDFVarName,imgLandcoverName),
    # ]
    #   C:\Data\claims.nc#time@TIME=2017|GLANDCOVER_30MIN@RASTER=|NGLNDCOV@STRING=Cropland
    varDefs = [
      "%s%s=%s" % (imgYearNetCDFVarName,"@TIME",year),
      "%s%s=%s" % (imgDataNetCDFVarName,"@RASTER",""),
      "%s%s=%s" % (imgLandcoverNamesNetCDFVarName,"@STRING",imgLandcoverName),
    ]

    print()
    print("Using: %s" % ncFileName)
    print()

    try:
      extent = GLOB.extent_World

      pNetCDF = NetCDF()
      pNetCDF.init(ncFileName,extent,varDefs)

      test = False
      if test:
        pNetCDF.readDataset()

        indices = pNetCDF.getDataIndices(varDefs)
        print(indices)

        data = pNetCDF.getVariableValues("GLANDCOVER_30MIN")
        print(data.shape)
        raster = data[indices[0],indices[1],indices[2],indices[3]]
        print(raster)

        raster = data[indices[0],slice(None),slice(None),indices[3]]
        print(raster)
        v = raster[180]
        print(v)
        print(pNetCDF.noDataValue)

        print()
        print("#"*80)

      pNetCDF.showInfo()

      del pNetCDF
    except:
      Log.err()

  #-------------------------------------------------------------------------------
  # Rasters and landuse codes.
  def testReadInfo1():

    # Image data (NetCDF).
    inDir = r"G:\data\imgluh_20201118"
    ncFileName = os.path.join(inDir,"GLANDCOVER_30MIN.nc")
    imgLandcoverNamesNetCDFVarName = "NGLNDCOV"
    imgYearNetCDFVarName = "TIME"
    imgDataNetCDFVarName = "GLANDCOVER_30MIN"

    imgLandcoverName = "Cropland"
    year = 1970

    varDefs = [
      "%s%s=%s" % (imgYearNetCDFVarName,"@TIME",year),
      "%s%s=%s" % (imgDataNetCDFVarName,"@RASTER",""),
      "%s%s=%s" % (imgLandcoverNamesNetCDFVarName,"@STRING",imgLandcoverName),
    ]

    print()
    print("Using: %s" % ncFileName)
    print()

    try:
      extent = GLOB.extent_World

      pNetCDF = NetCDF()
      pNetCDF.init(ncFileName,extent,varDefs)

      test = False
      if test:
        pNetCDF.readDataset()
        print(pNetCDF.dataset)

        nrCols,nrRows = pNetCDF.getLonLatDimensions()
        print("nrCols/nrRows: %s,%s" % (nrCols,nrRows))

        dataType = pNetCDF.getLonLatDataType()
        print(dataType)
        noData = pNetCDF.getLonLatNoDataValue()
        print(noData)

        var = pNetCDF.getVariable("latitude")
        print(var)
        print(var.ndim)
        print(var.shape)
        print(var.dtype)
        print(RU.getNoDataValue(dataType))
        print(var.mask)

      pNetCDF.readInfo()

      pNetCDF.showInfo()

      del pNetCDF
    except:
      Log.err()

  #-------------------------------------------------------------------------------
  def testReadExtent():

    GLOB.debug = True

    # Image data (NetCDF).
    inDir = r"G:\data\imgluh_20201118"
    ncFileName = os.path.join(inDir,"GLANDCOVER_30MIN.nc")
    imgLandcoverNamesNetCDFVarName = "NGLNDCOV"
    imgYearNetCDFVarName = "TIME"
    imgDataNetCDFVarName = "GLANDCOVER_30MIN"

    imgLandcoverName = "Cropland"
    year = 1970

    varDefs = [
      "%s%s=%s" % (imgYearNetCDFVarName,"@TIME",year),
      "%s%s=%s" % (imgDataNetCDFVarName,"@RASTER",""),
      "%s%s=%s" % (imgLandcoverNamesNetCDFVarName,"@STRING",imgLandcoverName),
      ]

    print()
    print("Using: %s" % ncFileName)
    print()

    try:
      extent = GLOB.extent_World

      pNetCDF = NetCDF()
      pNetCDF.init(ncFileName,extent,varDefs)

      test = False
      if test:
        pNetCDF.readDataset()
        print(pNetCDF.dataset)

        nrCols,nrRows = pNetCDF.getLonLatDimensions()
        print("nrCols/nrRows: %s,%s" % (nrCols,nrRows))

        dataType = pNetCDF.getLonLatDataType()
        print(dataType)
        noData = pNetCDF.getLonLatNoDataValue()
        print(noData)

        var = pNetCDF.getVariable("latitude")
        print(var)
        print(var.ndim)
        print(var.shape)
        print(var.dtype)
        print(RU.getNoDataValue(dataType))
        print(var.mask)

      pNetCDF.read()

      print(pNetCDF.r.shape)

      print("Reading extent...")
      extent = [10.0, 10.0, 50.0, 30.0]
      pNetCDF.read(extent)

      print(pNetCDF.r.shape)

      del pNetCDF
    except:
      Log.err()
  #-------------------------------------------------------------------------------
  #-------------------------------------------------------------------------------
  #
  # run Core\NetCDF.py
  #
  # test1()
  # test2()
  # test3()
  # test4()
  # testBasicInfo5()
  # testInfo6()
  # testInfo7()
  #testReadInfo1()
  testReadExtent()
