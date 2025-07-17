# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 25 apr 2016, ES, ARIS B.V.
#           - Version 4.0.1
#           - readValueFromLookup added.
#           23 sept 2016, ES, ARIS B.V.
#           - Version 4.0.2
#           - checkRaster modified, option optional added.
#           - checkIntegerList added.
#           - checkFile added.
#           - checkLookup, modified because of checkFile.
#           - checkFieldName, checkFieldNames, checkFieldTypes, added.
#           - checkRasterList added.
#           - splitIntegerList added.
#           - splitStringList added.
#           - checkFile modified, option optional added.
#           - readAndPrepareInRaster modified, option prefix added.
#           - getGlobioFullVersion added.
#           - showStartMsg modified.
#           - checkListCount added.
#           - checkFloatList added.
#           - splitFloatList added.
#           - checkInteger added.
#           - enableLogToFile added.
#           7 dec 2016, ES, ARIS B.V.
#           - Version 4.0.3
#           - readAndPrepareInRaster modified.
#           - rasterInfo added.
#           - prepareStandAloneRun modified, variables added.
#           - fileNameSetVersion added.
#           15 dec 2016, ES, ARIS B.V.
#           - Version 4.0.5
#           - writeTmpRaster modified, now with copy of raster.
#           19 jan 2017, ES, ARIS B.V.
#           - Version 4.0.5
#           - checkFile and checkRaster modified.
#           - isValueSet added.
#           22 jun 2017, ES, ARIS B.V.
#           - Version 4.0.6
#           - msgMemoryUsage modified.
#           - reclassUniqueValues modified, now using defaultValue.
#           - reclassUniqueValuesTwoKeys modified, now using defaultValue.
#           13 sep 2017, ES, ARIS B.V.
#           - Version 4.0.9
#           - __del__() added.
#           8 nov 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           - showElapsedTime added.
#           - debugPrint and dbgPrint() added.
#           - showHeaderMsg added.
#           - initProgress added.
#           - showProgress added.
#           - showProgress modified, now using print.
#           - calcWeightedMSA added.
#           10 sep 2020, ES, ARIS B.V.
#           - Version 4.0.15
#           - resizeResampleRaster added.
#           - copyRaster added.
#           - checkDirectory, checkFile, checkRaster, checkVector modified
#             because of overwriteOutput and createOutDir.
#           9 oct 2020, ES, ARIS B.V.
#           - Version 4.0.16.
#           - checkVector modified, argument "optional" added.
#           3 dec 2020, ES, ARIS B.V.
#           - Version 4.1.0.
#           - __init__ modified, len(GLOB.constants) == 0 added.
#           11 dec 2020, ES, ARIS B.V.
#           - Version 4.1.0.
#           - checkVariableName added.
#           - checkFileList added.
#           11 jan 2021, ES, ARIS B.V.
#           - Version 4.1.1
#           - readAndPrepareInRaster_V2 added, uses read(extent) to read a raster.
#           - checkCellSize added.
#           - checkInteger modified.
#           - checkDirectory modified, optional added.
#           - checkRasterOrTemplate added.
#           - getRegionExtents added.
#           - None replaced with del.
# TODO:     20210114
#           - Use of RasterUtils.writeTmpRaster().
#-------------------------------------------------------------------------------

import sys
import os

import numpy as np

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

from GlobioModel.Common.Timer import Timer
import GlobioModel.Common.Utils as UT

from GlobioModel.Core.Lookup import Lookup

if GLOB.gisLib == GLOB.GIS_LIB_GDAL:
  from GlobioModel.Core.Raster import Raster

import GlobioModel.Core.RasterUtils as RU
import GlobioModel.Core.RegionUtils as RGU

# WEL NODIG IVM FOUTMELDING IN VARIABLES!!!!!!!!!!!!!
#import GlobioModel.Core.AppUtils

from GlobioModel.Core.Constants import ConstantList
from GlobioModel.Core.Types import TypeList
from GlobioModel.Core.Variables import VariableList
 
from GlobioModel.Config.Constants_Config import defineConstants
from GlobioModel.Config.Types_Config import defineTypes
from GlobioModel.Config.Variables_Config import defineVariables

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class CalculationBase(object):
  name = ""
  timer = None
  
  # For writing to temporary rasters.
  extent = None
  cellSize = None
  outDir = None

  # For memory usage.
  startMemUsed = -1
  maxMemUsed = -1

  # Progress.
  progCount = 0
  progPrevPerc = None
  progTotalCount = 0

  # Debug print flags.
  debugPrint = False
  debugPrintArray = False
  debugPrintMinMaxNoData = False

  # Debug printArray defaults.
  debugPrintArrayMaxLen = 20
  debugPrintArrayPrecision = 1

  #-------------------------------------------------------------------------------
  def __init__(self):
    self.name = self.__class__.__name__
    self.timer = Timer()
    # A standalone run?
    # 20201203
    # if GLOB.constants is None:
    if (GLOB.constants is None) or (len(GLOB.constants) == 0):
      # Define errors, constants, types etc.
      self.prepareStandAloneRun()

  #-------------------------------------------------------------------------------
  def __del__(self):
    # Cleanup the monitor when allocated.
    MON.cleanup()

  #-------------------------------------------------------------------------------
  # Returns the weighted MSA raster.
  def calcWeightedMSA(self,extent,cellSize,
                      msaRasterNames,msaRasterDescriptions,
                      fracRasterNames,fracRasterDescriptions):

    # Create MSA raster.
    # Initialize with 0.0.
    noDataValue = -999.0
    outRaster = Raster()
    outRaster.initRaster(extent,cellSize,np.float32,noDataValue,0.0)

    # Create raster for total fraction.
    # Initialize with 0.0.
    noDataValue = -999.0
    totFracRaster = Raster()
    totFracRaster.initRaster(extent,cellSize,np.float32,noDataValue,0.0)

    #-----------------------------------------------------------------------------
    # Calculate weighted sum of MSA.
    #-----------------------------------------------------------------------------
    
    for i in range(len(msaRasterNames)):
      msaRasterName = msaRasterNames[i]
      msaRasterDescription = msaRasterDescriptions[i]
      fracRasterName = fracRasterNames[i]
      fracRasterDescription = fracRasterDescriptions[i]

      #-----------------------------------------------------------------------------
      # Read the MSA raster and prepare.
      #-----------------------------------------------------------------------------
    
      # Reads the raster and resizes to extent and resamples to cellsize.
      msaRaster = self.readAndPrepareInRaster(extent,cellSize,msaRasterName,msaRasterDescription+" msa")

      #-----------------------------------------------------------------------------
      # Read the fraction raster and prepare.
      #-----------------------------------------------------------------------------
    
      # Reads the raster and resizes to extent and resamples to cellsize.
      fracRaster = self.readAndPrepareInRaster(extent,cellSize,fracRasterName,fracRasterDescription+" fractions")

      #-----------------------------------------------------------------------------
      # Create masks.
      #-----------------------------------------------------------------------------

      # Get data mask.
      dataMask = msaRaster.getDataMask()

      # Get fraction mask.
      fracMask = (fracRaster.r > 0.0)

      # Combine masks.
      dataMask = np.logical_and(fracMask,dataMask)
      
      #-----------------------------------------------------------------------------
      # Calculate weighted sum of MSA.
      #-----------------------------------------------------------------------------

      # Calculate msa.      
      outRaster.r[dataMask] += msaRaster.r[dataMask] * fracRaster.r[dataMask]

      #-----------------------------------------------------------------------------
      # Calculate sum of fractions.
      #-----------------------------------------------------------------------------
  
      # Add fraction to total.
      totFracRaster.r[dataMask] += fracRaster.r[dataMask]
        
      # Clear masks.
      del fracMask
      del dataMask

      # Close and free the fraction and msa raster.
      del fracRaster
      del msaRaster

    #-----------------------------------------------------------------------------
    # Calculate final MSA, i.e. weighte MSA / total of fractions.
    #-----------------------------------------------------------------------------

    # Select fractions > 0.0.
    dataMask = (totFracRaster.r > 0.0)

    # Calculate MSA.
    outRaster.r[dataMask] /= totFracRaster.r[dataMask]

    # Set nodata.
    outRaster.r[~dataMask] = outRaster.noDataValue

    # Cleanup.
    del dataMask
    del totFracRaster

    return outRaster

  #-------------------------------------------------------------------------------
  def checkCellSize(self,cellSize,rasterName=None):
    if not UT.isFloat(cellSize):
      Err.raiseGlobioError(Err.InvalidCellSizeValue1,cellSize)
    # Get valid globio cellsizes.
    validCellSizesStr = GLOB.constants["ValidCellSizes"].value
    validCellSizes = validCellSizesStr.split("|")
    # Is valid globio cellsize?
    for vcs in validCellSizes:
      # Get const value.
      validCellSize = GLOB.constants[vcs].value
      if UT.isEqualFloat(cellSize,validCellSize):
        return
    if rasterName is None:
      Err.raiseGlobioError(Err.InvalidGlobioCellSize1,cellSize)
    else:
      Err.raiseGlobioError(Err.InvalidRasterGlobioCellSize2,cellSize,rasterName)

  #-------------------------------------------------------------------------------
  def checkBoolean(self,value):
    if not UT.isBoolean(value):
      Err.raiseGlobioError(Err.InvalidBooleanValue1,value)
  
  #-------------------------------------------------------------------------------
  def checkDirectory(self,dirName,asOutput=False,optional=False):
    if (optional) and (not self.isValueSet(dirName)):
      # No checks needed.
      return
    if not self.isValueSet(dirName):
      Err.raiseGlobioError(Err.NoDirectorySpecified)
    if asOutput:
      if os.path.isdir(dirName):
        # Need to create output directory?
        if GLOB.createOutDir:
          # Create full ouput path.
          os.makedirs(dirName)
        else:
         Err.raiseGlobioError(Err.DirectoryAlreadyExists1,dirName)
    else:
      if not os.path.isdir(dirName):
        Err.raiseGlobioError(Err.DirectoryNotFound1,dirName)

  #-------------------------------------------------------------------------------
  def checkExtent(self,extent):
    if not RU.isExtent(extent):
      Err.raiseGlobioError(Err.InvalidExtentValue1,extent)

  #-------------------------------------------------------------------------------
  # Only checks if not empty.
  def checkFieldName(self,name,paramName):
    if name == "":
      Err.raiseGlobioError(Err.NoFieldSpecified1,paramName)

  #-------------------------------------------------------------------------------
  # Only checks if not empty.
  def checkFieldNames(self,nameList,paramName):
    if nameList == "":
      Err.raiseGlobioError(Err.NoFieldsSpecified1,paramName)

  #-------------------------------------------------------------------------------
  def checkFieldTypes(self,typeList,fieldCount,paramName):
    if typeList == "":
      Err.raiseGlobioError(Err.NoFieldTypesSpecified1,paramName)
    validTypes = ["I","F","S"]
    tokens = typeList.split("|")
    if len(tokens)!=fieldCount:    
      Err.raiseGlobioError(Err.InvalidNumberOfFieldTypes2,paramName,fieldCount)
    for token in tokens:
      if not token in validTypes:
        Err.raiseGlobioError(Err.InvalidFieldType1,token)
  
  #-------------------------------------------------------------------------------
  def checkFile(self,fileName,asOutput=False,optional=False):
    if (optional) and (not self.isValueSet(fileName)):
      # No checks needed.
      return
    if not self.isValueSet(fileName):
        Err.raiseGlobioError(Err.NoFileSpecified)
    if asOutput:
      # Do not overwrite output?
      if not GLOB.overwriteOutput:
        # Ouput should not exist.
        if os.path.isfile(fileName):
          Err.raiseGlobioError(Err.FileAlreadyExists1,fileName)
      outDir = os.path.dirname(fileName)    
      # Does the output directory not exist.
      if not os.path.isdir(outDir):
        # Need to create output directory?
        if GLOB.createOutDir:
          # Create full ouput path.
          os.makedirs(outDir)
        else:
          Err.raiseGlobioError(Err.DirectoryNotFound1,outDir)
    else:
      if not RU.rasterExists(fileName):
        Err.raiseGlobioError(Err.FileNotFound1,fileName)

  #-------------------------------------------------------------------------------
  # Checks if the list is of format file1|file2|file3 and contains
  # valid filenames.
  # optional: the filenames are valid when it is an empty string ("") or NONE.
  def checkFileList(self,fileNameList,asOutput=False,optional=False):
    if (optional) and (not self.isValueSet(fileNameList)):
      return
    if not self.isValueSet(fileNameList):
      Err.raiseGlobioError(Err.NoFilesSpecified)
    fileNames = fileNameList.split("|")
    for fileName in fileNames:
      if self.isValueSet(fileName):
        self.checkFile(fileName,asOutput)

  #-------------------------------------------------------------------------------
  def checkFloat(self,value,minValue,maxValue):
    if not UT.isFloat(value):
      Err.raiseGlobioError(Err.InvalidFloatValue1,value)
    if (value<minValue) or (value>maxValue):
      Err.raiseGlobioError(Err.InvalidFloatValueBetween3,value,minValue,maxValue)
  
  #-------------------------------------------------------------------------------
  # Checks if the list is of format float1|float2|float3.
  # needCnt: if >0 then the list needs the specified number of floats. 
  # optional: the list is valid when it is an empty string ("") or None. 
  def checkFloatList(self,floatList,needCnt=0,optional=False):
    
    if (optional) and (not self.isValueSet(floatList)):
      # No checks needed.
      return

    if not self.isValueSet(floatList):
      Err.raiseGlobioError(Err.NoFloatListSpecified)
    
    tokens = floatList.split("|")
    for token in tokens:
      if not UT.isFloat(token):
        Err.raiseGlobioError(Err.InvalidFloatList1,floatList)

    if needCnt>0:
      if (len(tokens)!=needCnt):
        Err.raiseGlobioError(Err.InvalidFloatListLength1,floatList)
        
  #-------------------------------------------------------------------------------
  def checkInteger(self,value,minValue,maxValue):
    if not UT.isInteger(value):
      Err.raiseGlobioError(Err.InvalidIntegerValue1,value)
    # 20210115
    value = int(value)
    if (value<minValue) or (value>maxValue):
      Err.raiseGlobioError(Err.InvalidIntegerValueBetween3,value,minValue,maxValue)
  
  #-------------------------------------------------------------------------------
  # Checks if the list is of format int1|int2|int3.
  # optional: the list is valid when it is an empty string ("") or None. 
  def checkIntegerList(self,intList,optional=False):
    
    if (optional) and (not self.isValueSet(intList)):
      # No checks needed.
      return

    if not self.isValueSet(intList):
      Err.raiseGlobioError(Err.NoIntegerListSpecified)
    
    tokens = intList.split("|")
    for token in tokens:
      if not UT.isInteger(token):
        Err.raiseGlobioError(Err.InvalidIntegerList1,intList)

  #-------------------------------------------------------------------------------
  # Checks if the list is of format int1+int2|int3|int4+int5 or int1|int2|int3.
  # optional: the list is valid when it is an empty string ("") or None. 
  def checkIntegerListOfLists(self,intListOfLists,optional=False):
    
    if (optional) and (not self.isValueSet(intListOfLists)):
      # No checks needed.
      return

    if not self.isValueSet(intListOfLists):
      Err.raiseGlobioError(Err.NoIntegerListSpecified)

    # Get lists of integers.
    intLists = intListOfLists.split("|")
    
    # Check lists.
    for intList in intLists:
      # Split using "+".
      tokens = intList.split("+")
      for token in tokens:
        if not UT.isInteger(token):
          Err.raiseGlobioError(Err.InvalidIntegerListOfLists1,intListOfLists)

  #-------------------------------------------------------------------------------
  # Checks if the list of format str1|str2|str3 has the same number of items
  # as the reference list of the same format.
  # itemName: items in the list; used for error message; if not specified
  #           "items" is used. 
  def checkListCount(self,strList,strReferenceList,itemName=""):
    if (strList=="") and (strReferenceList==""):
      # No checks needed.
      return
    items = self.splitStringList(strList)
    itemCount = len(items)
    references = self.splitStringList(strReferenceList)
    refCount = len(references)
    if itemCount != refCount:
      if itemName == "":
        Err.raiseGlobioError(Err.InvalidNumberOfItemsInList3,strList,itemCount,refCount)
      else:
        Err.raiseGlobioError(Err.InvalidNumberOfItemsInList4,itemName,strList,itemCount,refCount)

  #-------------------------------------------------------------------------------
  def checkLookup(self,fileName,asOutput=False):
    self.checkFile(fileName,asOutput)

  #-------------------------------------------------------------------------------
  # optional: the raster name is valid when it is an empty string ("") or None. 
  def checkRaster(self,rasterName,asOutput=False,optional=False,
                  checkCellSize=True):

    if (optional) and (not self.isValueSet(rasterName)):
      # No checks needed.
      return

    if not self.isValueSet(rasterName):
      Err.raiseGlobioError(Err.NoRasterSpecified)
      
    if asOutput:
      # Do not overwrite output?
      if not GLOB.overwriteOutput:
        # Ouput should not exist.
        if RU.rasterExists(rasterName):
          Err.raiseGlobioError(Err.RasterAlreadyExists1,rasterName)
      outDir = os.path.dirname(rasterName)    
      # Does the output directory not exist.
      if not os.path.isdir(outDir):
        # Need to create output directory?
        if GLOB.createOutDir:
          # Create full ouput path.
          os.makedirs(outDir)
        else:
          Err.raiseGlobioError(Err.DirectoryNotFound1,outDir)
    else:
      if not RU.rasterExists(rasterName):
        Err.raiseGlobioError(Err.RasterNotFound1,rasterName)
      if checkCellSize:
        # Get raster info.
        pInfo = RU.rasterGetInfo(rasterName)
        # Check cellsize.
        self.checkCellSize(pInfo.cellSize,os.path.basename(rasterName))
        # Check extent.
        if not RU.isExtentAligned(pInfo.extent,pInfo.cellSize):
          Err.raiseGlobioError(Err.InvalidRasterExtentNotAligned5,
                               pInfo.extent[0],pInfo.extent[1],pInfo.extent[2],pInfo.extent[3],
                               os.path.basename(rasterName))

  #-------------------------------------------------------------------------------
  # Checks if the list is of format raster1|raster2|raster3 and contains
  # valid raster names.
  # optional: the rasters are valid when it is an empty string ("") or NONE. 
  def checkRasterList(self,rasterNameList,asOutput=False,optional=False):
    if (optional) and (not self.isValueSet(rasterNameList)):
      return
    if not self.isValueSet(rasterNameList):
      Err.raiseGlobioError(Err.NoRastersSpecified)
    rasterNames = rasterNameList.split("|")
    for rasterName in rasterNames:
      #JM: change for ScenSuit rasterlist, that could contain NONE value
      #self.checkRaster(rasterName,asOutput)
      self.checkRaster(rasterName,asOutput,optional=True)

  #-------------------------------------------------------------------------------
  # Checks a raster name which can be a normal raster name or a template name.
  # A template name is formatted as:
  #   <path>\<rastername template>#<var1 value1>|<var1 value2>#<var2 value1>|<var2 value2>|...
  # The template shoud contain {} tokens which will be replaced by the variable values
  # specified after the template.
  # Example:
  #   C:\Data\img_claims_{}_{}.tif#2015|2020#1|2|3|4
  # optional: the raster name is valid when it is an empty string ("") or None.
  def checkRasterOrTemplate(self,rasterName,asOutput=False,optional=False,
                            checkCellSize=True):
    # Is it a template?
    if rasterName.find("{}")>=0:
      # TODO: Extra checks?
      # Check values list.
      if rasterName.find("#")<0:
        Err.raiseGlobioError(Err.UserDefined1,
                "No valid raster name template, o value list specified: %s" % rasterName)
      # Get raster names.
      templateName = UT.strBefore(rasterName,"#")
      templateData = UT.strAfter(rasterName,"#")
      templateValues = UT.strSplit(templateData,"#")
      # Get all posible raster names.
      templRasterNames = UT.resolveTemplate(templateName,templateValues)
      # Check all raster names.
      for templRasterName in templRasterNames:
        self.checkRaster(templRasterName,asOutput,optional,checkCellSize)
    else:
      # Ordinary raster name.
      self.checkRaster(rasterName,asOutput,optional,checkCellSize)

  #-------------------------------------------------------------------------------
  #
  def getImageClaimsRasterName(self,claimRasterName,year,landuseCode):
    if claimRasterName.find("#")<0:
      rasterName = claimRasterName
    else:
      rasterName = UT.strBefore(claimRasterName,"#")
    rasterName = rasterName % (year,landuseCode)
    return rasterName

  #-------------------------------------------------------------------------------
  # Only checks if not empty.
  def checkVariableName(self,name,paramName):
    if name == "":
      Err.raiseGlobioError(Err.NoVariableSpecified1,paramName)

  #-------------------------------------------------------------------------------
  # optional: the vector name is valid when it is an empty string ("") or None. 
  def checkVector(self,vectorName,asOutput=False,optional=False):

    if (optional) and (not self.isValueSet(vectorName)):
      # No checks needed.
      return

    if not self.isValueSet(vectorName):
      Err.raiseGlobioError(Err.NoVectorSpecified)
    
    if asOutput:
      # Do not overwrite output?
      if not GLOB.overwriteOutput:
        # Ouput should not exist.
        if RU.vectorExists(vectorName):
          Err.raiseGlobioError(Err.VectorAlreadyExists1,vectorName)
      outDir = os.path.dirname(vectorName)    
      # Does the output directory not exist.
      if not os.path.isdir(outDir):
        # Need to create output directory?
        if GLOB.createOutDir:
          # Create full ouput path.
          os.makedirs(outDir)
        else:
          Err.raiseGlobioError(Err.DirectoryNotFound1,outDir)
    else:
      if not RU.vectorExists(vectorName):
        Err.raiseGlobioError(Err.VectorNotFound1,vectorName)

  #-------------------------------------------------------------------------------
  # Copies the input raster to a new raster.
  # Raises an error when the output raster already exists!
  def copyRaster(self,inRasterName,outRasterName):
    
    # Check if output raster already exists.
    if RU.rasterExists(outRasterName):
      Err.raiseGlobioError(Err.RasterAlreadyExists1,outRasterName)
      
    # Read input raster.
    inRaster = Raster(inRasterName)
    inRaster.read()
  
    # Create output raster.
    outRaster = Raster(outRasterName)
    outRaster.initRasterLike(inRaster)

    # Copy data.
    outRaster.r = inRaster.r[:]

    # Cleanup.
    del inRaster
    del outRaster

  #-------------------------------------------------------------------------------
  # Show debug message.
  def dbgPrint(self,s,indent="  "):
    if not self.debugPrint:
      return
    print("%s# %s" % (indent,s))

  #-------------------------------------------------------------------------------
  # Prints an array from start.
  def dbgPrintArray(self,name,data):
    if not self.debugPrintArray:
      return
    if len(data) > self.debugPrintArrayMaxLen:
      data = data[:self.debugPrintArrayMaxLen]
    UT.printArray(name,data,self.debugPrintArrayPrecision)

  #-------------------------------------------------------------------------------
  # Prints an array end.
  def dbgPrintArrayAtIndex(self,name,data,index):
    if not self.debugPrintArray:
      return
    if len(data) > (2*self.debugPrintArrayMaxLen):
      data = data[index-self.debugPrintArrayMaxLen:index+self.debugPrintArrayMaxLen]
    UT.printArray(name,data,self.debugPrintArrayPrecision)

  #-------------------------------------------------------------------------------
  # Prints an array at index with n elements beforen and after.
  def dbgPrintArrayEnd(self,name,data):
    if not self.debugPrintArray:
      return
    if len(data) > self.debugPrintArrayMaxLen:
      data = data[-1*self.debugPrintArrayMaxLen:]
    UT.printArray(name,data,self.debugPrintArrayPrecision)

  #-------------------------------------------------------------------------------
  # Print the raster min, max and nodata value of a Raster() object.
  def dbgPrintMinMaxNoData(self,raster,name):
    if not self.debugPrintMinMaxNoData:
      return
    Log.info("- %s min: %s " % (name,raster.min()))
    Log.info("- %s max: %s" % (name,raster.max()))
    Log.info("- %s nodata: %s " % (name,raster.noDataValue))

  #-------------------------------------------------------------------------------
  def doc(self):
    s = self.run.__doc__
    if s is None:
      return ""
    lines1 = s.split("\n")
    lines1 = lines1[1:-1]
    lines2 = []
    for line in lines1:
      lines2.append(line.strip())
    return "\n".join(lines2)

  #-------------------------------------------------------------------------------
  # Enable logging to a file.
  def enableLogToFile(self,outDir):
    # Get the base logfile name.
    baseFileName = Log.getBaseLogFileName()
    # Does the directory exist?
    if os.path.isdir(outDir):
      # Log file in output dir.
      GLOB.logfileName = os.path.join(outDir,baseFileName)
      # Flush the log startup buffer because of pending messages.
      Log.flushStartupBufferToFile()

  #-------------------------------------------------------------------------------
  # Set <name>.<ext> to <name>_v<version>.<ext> or <name> to <name>_v<version>. 
  def fileNameSetVersion(self,fileName,version):
    # Has extension?
    if fileName.find("") >= 0:
      fileName = fileName.replace(".","_v"+str(version)+".")
    else:
      fileName = fileName + "_v"+str(version)
    return fileName

  #-------------------------------------------------------------------------------
  def getGLOBIOFullVersion(self):
    return GLOB.globioVersion+"."+GLOB.globioSubSubVersion+"."+GLOB.globioBuildVersion

  #-------------------------------------------------------------------------------
  def getMinimalCellSize(self,rasterNames):
    minCellSize = sys.float_info.max
    for rasterName in rasterNames: 
      cellSize = RU.rasterCellSize(rasterName)
      minCellSize = min(minCellSize,cellSize)
    return minCellSize

  #-------------------------------------------------------------------------------
  # Returns a default rastername based on the specified cellsize.
  def getCellAreaRasterName(self,cellAreaDir: str,cellSize: float,version: int=2):
    cellSizeName = RU.cellSizeToCellSizeName(cellSize)
    rasterName = "cellarea_km2_v%s_%s.tif" % (version,cellSizeName)
    rasterName = os.path.join(cellAreaDir,rasterName)
    return rasterName

  #-------------------------------------------------------------------------------
  # Returns a dict with per region code the regions extent, using .
  def getRegionExtents(self,regionRasterName: str,extent: [any],cellSize: float,
                       regionFilter: [int],regionExcludeFilter: [int],
                       prefix="",silent=False) -> dict:

    # Read the region raster and resizes to extent and resamples to cellsize.
    regionRaster = self.readAndPrepareInRaster_V2(extent,cellSize,
                                                  regionRasterName,"regions",
                                                  calcSumDiv=False,
                                                  prefix=prefix,silent=silent)
    if not silent:
      Log.info("Filtering regions...")

    # Filter the regions, i.e. set to noData.
    RGU.filterRegionRaster(regionRaster,regionFilter,regionExcludeFilter)

    if not silent:
      Log.info("Getting region codes...")

    # Create a list of unique regions from the region raster.
    regionCodes = RGU.createRegionListFromRegionRaster(regionRaster,
                                                       includeNoDataValue=False)

    # Create a dict with region code(as key) and extents.
    regionDict = dict()
    for regionCode in regionCodes:
      regionExtent = regionRaster.getExtentByValue(regionCode)

      regionDict[regionCode] = regionExtent

    # Cleanup.
    del regionRaster

    return regionDict

  #-------------------------------------------------------------------------------
  def initProgress(self,totalCount):
    self.progCount = 1
    self.progPrevPerc = None
    self.progTotalCount = totalCount

  #-------------------------------------------------------------------------------
  # Returns if the value string is set, i.e. not is "" and not is None or "NONE".
  def isValueSet(self,value):
    # None?
    if (value is None):
      return False
    # A list?
    if type(value) is list:
      if len(value) == 0:
        return False
      else:
        return True
    # A string?
    # 20201118
    #if isinstance(value,basestring):
    if UT.isString(value):
      if (value=="") or (value.upper()=="NONE"):
        return False
      else:
        return True
    # Other.
    return True

  #-------------------------------------------------------------------------------
  def newTimer(self):
    return Timer()

  #-------------------------------------------------------------------------------
  # Show start or maximum memory usage info.
  def msgMemoryUsage(self,indent="  ",prefix=""):
    # First time?
    if self.startMemUsed < 0:
      # Get currently used memory.
      memUsed = UT.memPhysicalUsed()
      # Set start memory to currently used memory.
      self.startMemUsed = memUsed
      # Show memory data.
      memTotalStr = UT.bytesToStr(UT.memPhysicalTotal())
      memUsedStr = UT.bytesToStr(UT.memPhysicalUsed())
      memAvailStr = UT.bytesToStr(UT.memPhysicalAvailable())
      Log.info("%s%sMemory total/inuse/available: %s   %s   %s" % (indent,prefix,memTotalStr,memUsedStr,memAvailStr))
    else:
      # Save memory used.
      self.saveMemoryUsage()
      # Convert memory used to string with proper units.
      maxMemUsedStr = UT.bytesToStr(self.maxMemUsed)
      # Show memory used.
      Log.info("%s%sMemory used: %s" % (indent,prefix,maxMemUsedStr))

  #-------------------------------------------------------------------------------
  # Must be run if the calculation is not run from Globio4.py. 
  def prepareStandAloneRun(self):
    
    Log.LOG_TRACEBACK_ERRORS = True
    
    # Define errors.
    Err.defineErrors()

    # Create the global lists for types, constants and variables.
    GLOB.types = TypeList()
    GLOB.constants = ConstantList()
    GLOB.variables = VariableList()
     
    # Set the global constants and types.
    defineTypes(GLOB.types)
    defineConstants(GLOB.constants)

    # Define the buildin variables and set the default value.
    defineVariables(GLOB.variables)
    
  #-------------------------------------------------------------------------------
  def rasterInfo(self,inRasterName,prefix=""):

    if not RU.rasterExists(inRasterName):
      Err.raiseGlobioError(Err.RasterNotFound1,inRasterName)
    
    # Read raster and show info.
    inRaster = Raster(inRasterName)
    inRaster.read()
    inRaster.showInfo(prefix)

    # Close and free the output.
    del inRaster

  #-------------------------------------------------------------------------------
  def readAndPrepareInRaster(self,extent,cellSize,
                             inRasterName,inRasterDisplayName,
                             prefix="",silent=False):
    if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:
      Err.raiseGlobioError(Err.NotImplemented1,"readAndPrepareInRaster")
    else:
      # Read the raster.
      if not silent:
        Log.info("%sReading %s raster..." % (prefix,inRasterDisplayName))
      inRaster = Raster(inRasterName).read()
   
      # Show datatype.
      #Log.dbg("readAndPrepareInRaster - DataType: %s" % RU.dataTypeNumpyToString(inRaster.dataType))

      # Calculate indent.
      indent = " " * len(prefix)

      # Resize raster to extent.
      if not RU.isEqualExtent(inRaster.extent,extent,cellSize):
        if not silent:
          Log.info("%sResizing %s raster..." % (prefix,inRasterDisplayName))
          Log.info("%s- Orginal extent: %s" % (indent,RU.extentToStr(inRaster.extent)))
          Log.info("%s- New extent: %s" % (indent,RU.extentToStr(extent)))
        inRaster = inRaster.resize(extent)
      else:
        # Set (aligned) extent.
        inRaster.extent = extent
        
      # Resample raster to cellsize.
      if not RU.isEqualCellSize(inRaster.cellSize,cellSize):
        if not silent:
          Log.info("%sResampling %s raster..." % (prefix,inRasterDisplayName))
          Log.info("%s- Orginal cellsize: %s" % (indent,inRaster.cellSize))
          Log.info("%s- New cellsize: %s" % (indent,cellSize))
        inRaster = inRaster.resample(cellSize)
   
      # Return the prepared raster.
      return inRaster

  #-------------------------------------------------------------------------------
  # Uses read(extent) to read the raster.
  #
  # Downsampling:
  #   For integer rasters the majority is calculated. When equal counts the
  #   minimum value is used.
  #   For float rasters the mean is calculated.
  #   When calcSumDiv is True the sum is calculated. NoDataValues are never summed.
  # Upsampling:
  #   For integer and float rasters the original value is copied.
  #   When calcSumDiv is True the the original value is divided by
  #   the scalefactor. NoDataValues are never divided.
  #
  def readAndPrepareInRaster_V2(self,extent,cellSize,
                                inRasterName,inRasterDisplayName,
                                calcSumDiv,
                                prefix="",silent=False):
    if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:
      Err.raiseGlobioError(Err.NotImplemented1,"readAndPrepareInRaster")

    # Read the raster.
    if not silent:
      Log.info("%sReading %s raster..." % (prefix,inRasterDisplayName))
    inRaster = Raster(inRasterName)
    inRaster.read(extent)

    # Resample raster to cellsize.
    if not RU.isEqualCellSize(inRaster.cellSize,cellSize):
      if not silent:
        indent = " " * len(prefix)
        Log.info("%sResampling %s raster..." % (prefix,inRasterDisplayName))
        Log.info("%s- Orginal cellsize: %s" % (indent,inRaster.cellSize))
        Log.info("%s- New cellsize: %s" % (indent,cellSize))
      inRaster = inRaster.resample(cellSize,calcSumDiv=calcSumDiv)

    # Return the prepared raster.
    return inRaster

  #-------------------------------------------------------------------------------
  # Reads 1 value from a lookup file with 1 column.
  def readValueFromLookup(self,lookupFileName,lookupFieldTypes):
    # Create lookup.
    lut = Lookup()
    # Load file.
    lut.loadCSV(lookupFileName,lookupFieldTypes)
    # Get value.
    value = lut[1]
    # Free lookup.    
    del lut
    # Return value.
    return value
  
  #-------------------------------------------------------------------------------
  # The key value are class upperbounds and can be integers or floats.
  # The lookup value can be integers or floats.
  # Example:
  # MAXAREA;MSA
  # 1;0,350
  # 10;0,450
  # 100;0,650
  # 1000;0,900
  # 10000;0,980
  # 999999999;1,000
  def reclassClasses(self,inRaster,lowerBound,
                     lookupFileName,lookupFieldTypes,
                     dataType,noDataValue=None):
    if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:
      Err.raiseGlobioError(Err.NotImplemented1,"reclassClasses")
    else:
      # Check nodata. 
      if noDataValue is None:
        noDataValue = RU.getNoDataValue(dataType)
  
      # Read lookup dict.
      Log.info("Reading lookup...")
      pLookup = Lookup()
      pLookup.loadCSV(lookupFileName,lookupFieldTypes)
  
      # Create output raster.      
      outRaster = Raster()
      outRaster.initRaster(inRaster.extent,inRaster.cellSize,dataType,noDataValue)
   
      # Do lookup.
      cnt = 0
      prevKey = None
      for key in pLookup:
        # Create mask.
        if cnt==0:
          # Set prevkey.
          prevKey = lowerBound
          cnt = 1
  
        Log.dbg("Interval: %s - %s => %s" % (prevKey,key,pLookup[key]))
        outRaster.r[(inRaster.r > prevKey) & (inRaster.r<= key)] = pLookup[key]
        prevKey = key
        
      return outRaster

  #-------------------------------------------------------------------------------
  def reclassUniqueValues(self,inRaster,lookupFileName,lookupFieldTypes,
                          dataType,noDataValue=None):
    if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:
      Err.raiseGlobioError(Err.NotImplemented1,"reclassUniqueValues")
    else:
      # Check nodata. 
      if noDataValue is None:
        noDataValue = RU.getNoDataValue(dataType)
  
      # Read lookup dict.
      Log.info("Reading lookup...")
      pLookup = Lookup()
      pLookup.loadCSV(lookupFileName,lookupFieldTypes)
  
      # Get default value (*;<value>).
      defaultValue = pLookup.defaultValue
      
      # Create output raster.      
      outRaster = Raster()
      outRaster.initRaster(self.extent,self.cellSize,dataType,
                           noDataValue,defaultValue)
   
      # Reclass.
      Log.info("Reclassing...")
      for key in pLookup:
        # Create mask.
        mask = (inRaster.r==key)
        # Set output value using mask.
        outRaster.raster[mask] = pLookup[key]
  
      return outRaster

  #-------------------------------------------------------------------------------
  # The key is a combined key of the inRaster1 and inRaster2.
  # The seperate keys are contatenated by a "_".  
  # The seperate keys values must be a integer.
  # The order of the inRaster1 en inRaster2 is important!!!
  # The lookup value can be integers or floats.
  def reclassUniqueValuesTwoKeys(self,inRaster1,inRaster2,
                                 lookupFileName,lookupFieldTypes,
                                 lookupMainFieldName,
                                 dataType,noDataValue=None):
    if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:
      Err.raiseGlobioError(Err.NotImplemented1,"reclassUniqueValuesTwoKeys")
    else:
      # Check nodata. 
      if noDataValue is None:
        noDataValue = RU.getNoDataValue(dataType)
  
      # Read lookup dict.
      Log.info("Reading lookup...")
      pLookup = Lookup()
      pLookup.loadPivotCSV(lookupFileName,lookupMainFieldName,lookupFieldTypes)

      # Get default value (*;<value>).
      defaultValue = pLookup.defaultValue

      # Create output raster.      
      outRaster = Raster()
      outRaster.initRaster(self.extent,self.cellSize,dataType,
                           noDataValue,defaultValue)
   
      # Reclass.
      Log.info("Reclassing...")
      for key in pLookup:
        # Split key.
        keys = key.split("_")
        key1 = int(keys[0])
        key2 = int(keys[1])
        # Create mask.
        mask = (inRaster1.r==key1) & (inRaster2.r==key2)
        # Set output value using mask.
        outRaster.r[mask] = pLookup[key]
  
      return outRaster
  
  #-------------------------------------------------------------------------------
  # Resizes and/or resamples a raster and writes the result to a new raster.
  # Raises an error when the new raster already exists!
  def resizeResampleRaster(self,extent,cellSize,
                           inRasterName,outRasterName,
                           prefix="",silent=False):
    if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:
      Err.raiseGlobioError(Err.NotImplemented1,"resizeResampleRaster")
    else:

      # Check if output raster already exists.
      if RU.rasterExists(outRasterName):
        Err.raiseGlobioError(Err.RasterAlreadyExists1,outRasterName)

      # Read the input raster.
      if not silent:
        Log.info("%sReading %s raster..." % (prefix,os.path.basename(inRasterName)))
      inRaster = Raster(inRasterName).read()

      # Show datatype.
      #Log.dbg("rasterResizeResample - DataType: %s" % RU.dataTypeNumpyToString(inRaster.dataType))

      # Calculate indent.
      indent = " " * len(prefix)

      # Resize raster to extent.
      if not RU.isEqualExtent(inRaster.extent,extent,cellSize):
        if not silent:
          Log.info("%sResizing %s raster..." % (prefix,os.path.basename(inRasterName)))
          Log.info("%s- Orginal extent: %s" % (indent,RU.extentToStr(inRaster.extent)))
          Log.info("%s- New extent: %s" % (indent,RU.extentToStr(extent)))
        inRaster = inRaster.resize(extent)
      else:
        # Set (aligned) extent.
        inRaster.extent = extent

      # Resample raster to cellsize.
      if not RU.isEqualCellSize(inRaster.cellSize,cellSize):
        if not silent:
          Log.info("%sResampling %s raster..." % (prefix,os.path.basename(inRasterName)))
          Log.info("%s- Orginal cellsize: %s" % (indent,inRaster.cellSize))
          Log.info("%s- New cellsize: %s" % (indent,cellSize))
        inRaster = inRaster.resample(cellSize)

      # Write new raster.
      if not silent:
        Log.info("Writing %s..." % os.path.basename(outRasterName))
      inRaster.writeAs(outRasterName)

      # Cleanup.
      del inRaster

  #-------------------------------------------------------------------------------
  def run(self,*args):
    pass

  #-------------------------------------------------------------------------------
  # Supports 1D lists and 1D and 2D numpy arrays.
  def saveArrayToCSV(self,fileName,ary):
    # Create file content.
    lines = []
    if isinstance(ary,list):
      for i in range(len(ary)):
        lines.append("{}".format(ary[i]))
    elif UT.isNumpyArray(ary):
      ary = ary.ravel()
      for i in range(len(ary)):
        lines.append("{}".format(ary[i]))
    else:
      raise Exception("saveArrayToCSV - Invalid array type.")
    # File exists?
    if os.path.isfile(fileName):
      os.remove(fileName)
    # Directory not exists?.
    if not os.path.isdir(os.path.dirname(fileName)):
      os.makedirs(os.path.dirname(fileName))
    # Write to file.
    UT.fileWrite(fileName,lines)

  #-------------------------------------------------------------------------------
  # Show memory info.
  def saveMemoryUsage(self):
    # Get currently used memory.
    memUsed = UT.memPhysicalUsed()
    # First time?
    if self.startMemUsed < 0:
      # Set start memory to currently used memory.
      self.startMemUsed = memUsed
      # Set max. memory used.
      self.maxMemUsed = 0
    else:
      # Calculate real memory used.
      memUsed = memUsed - self.startMemUsed
      # Update max memory used.
      if memUsed > self.maxMemUsed:
        self.maxMemUsed = memUsed

  #-------------------------------------------------------------------------------
  def showElapsedTime(self,caption=None,timer=None,restart=False):
    if timer is None:
      timer = self.timer
    if timer is None:
      return
    if caption is None:
      caption = "Time elapsed: "
    Log.info(caption+timer.elapsedStr())
    if restart:
      timer.start()

  #-------------------------------------------------------------------------------
  def showEndMsg(self):
    Log.headerLine("-")
    # Is er een timer?
    if self.timer is not None:
      Log.info("- Execution time: "+self.timer.elapsedStr())
      Log.headerLine("-")
    Log.info("")

  #-------------------------------------------------------------------------------
  def showHeaderMsg(self):
    Log.headerLine("=")
    Log.info("# Execution start: "+UT.dateTimeToStr())
    Log.headerLine("=")

  #-------------------------------------------------------------------------------
  def showProgress(self):
    perc = UT.trunc(self.progCount / float(self.progTotalCount) * 100)
    self.progCount += 1
    # 20201118
    #if perc <> self.progPrevPerc:
    if perc != self.progPrevPerc:
      # Do not add the progress to the logfile.
      #Log.info("".join(["Progress ",str(perc),"%..."]))
      print("".join(["Progress ",str(perc),"%..."]))
      self.progPrevPerc = perc

  #-------------------------------------------------------------------------------
  def showStartMsg(self,args):
    Log.info("")
    Log.headerLine("-")
    if GLOB.debug:
      # Show module name and full GLOBIO version.
      Log.info(UT.strConcatAlignRight(
                          "- Running "+self.__class__.__name__,
                          self.getGLOBIOFullVersion(),
                          GLOB.logfileHeaderLength))
    else:
      # Just show module name.
      Log.info("- Running "+self.__class__.__name__)
    Log.headerLine("-")
    # Show the arguments.
    if len(args)>0:
      Log.info("Arguments:")
      for arg in args:
        Log.info("  "+str(arg))
    else:
      Log.info("Arguments: -")
    Log.info("Starting run...")
    # Start the timer.
    self.timer.start()

  #-------------------------------------------------------------------------------
  def showTimer(self,timer):
    Log.info("Time elapsed: "+timer.elapsedStr())

  #-------------------------------------------------------------------------------
  # Converts a list of format float1|float2|float3 to an array of floats.
  def splitFloatList(self,floatList):
    if not self.isValueSet(floatList):
      return []
    return [float(i) for i in floatList.split("|")]
  
  #-------------------------------------------------------------------------------
  # Converts a list of format int1|int2|int3 to an array of integers.
  def splitIntegerList(self,intList):
    if not self.isValueSet(intList):
      return []
    return [int(i) for i in intList.split("|")]

  #-------------------------------------------------------------------------------
  # Converts a list of format int1+int2|int3|int4+int5 to an array of array of integers.
  def splitIntegerListOfLists(self,intListOfLists):
    result = []
    if not self.isValueSet(intListOfLists):
      return result
    intLists = intListOfLists.split("|")
    for intList in intLists:
      result.append([int(i) for i in intList.split("+")])
    return result

  #-------------------------------------------------------------------------------
  # Converts a list of format s1|s2|s3 to an array of strings.
  def splitStringList(self,strList):
    if not self.isValueSet(strList):
      return []
    return strList.split("|")

  #-------------------------------------------------------------------------------
  # Raster is a Raster or an np.array.
  def writeTmpRaster(self,raster,tmpFileName,infoCaption=""):
    if not GLOB.saveTmpData:
      return
    if GLOB.gisLib == GLOB.GIS_LIB_ARCGIS:
      Err.raiseGlobioError(Err.NotImplemented1,"writeTmpRaster")
    else:
      # Show info message?
      if infoCaption != "":
        Log.info("%s: %s" % (infoCaption,tmpFileName))
      # Set filename.
      if os.path.dirname(tmpFileName)=="":
        if self.outDir is None:
          Log.info("Warning: writing tmp raster, no outdir specified.")
          return
        tmpFileName = os.path.join(self.outDir,tmpFileName)
      # Check filename.
      if RU.rasterExists(tmpFileName):
        RU.rasterDelete(tmpFileName)
      # Is Raster object?
      if isinstance(raster,Raster):
        # It's a Raster.
        # Make a copy (because of potential locking problems).
        ras = Raster(tmpFileName)
        ras.initRasterLike(raster)
        ras.raster = raster.raster
      else:
        # It's a np.array.
        noDataValue = RU.getNoDataValue(raster.dtype)
        ras = Raster(tmpFileName)
        ras.initRasterEmpty(self.extent,self.cellSize,raster.dtype,noDataValue)
        ras.raster = raster
      # Write raster.
      ras.write()
      del ras

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  print("ok"  )
