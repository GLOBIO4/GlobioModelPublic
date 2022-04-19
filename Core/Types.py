# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 19 jan 2017, ES, ARIS B.V.
#           - Version 4.0.5
#           - Type.isOptionalValue added.
#           - Dir,File,Raster,Vector methods checkExists and checkNotExists
#             modified.
#           - RasterList added.
#           11 sep 2017, ES, ARIS B.V.
#           - Version 4.0.9
#           - Dir,File,Raster,Vector methods modified for resolving ~ paths.
#           21 sep 2020, ES, ARIS B.V.
#           - Version 4.0.15
#           - Raster.checkNotExists modified, GLOB.overwriteOutput added.
#           - Dir.checkNotExists modified, GLOB.overwriteOutput added.
#           - File.checkNotExists modified, GLOB.overwriteOutput added.
#           - Vector.checkNotExists modified, GLOB.overwriteOutput added.
#           30 nov 2020, ES, ARIS B.V.
#           - Version 4.1.0
#           - import of GlobioModel.Core.RasterUtils moved down because of 
#             circular references.
#-------------------------------------------------------------------------------

import os

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Common.Utils as UT

# 20201130 Because of circular references.
#import GlobioModel.Core.RasterUtils as RU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Type(object):
  name = ""                      # The name.
  description = ""

  #-------------------------------------------------------------------------------
  def __init__(self):
    self.name = self.__class__.__name__.upper()    # classname.
    self.description = ""

  #-------------------------------------------------------------------------------
  # Returns if this type can be assigned to the given toType.
  def canAssignTo(self,toType):
    if toType.name==self.name:
      return True
    elif toType.name=="OBJ":
      return True
    else:
      return False

  #-------------------------------------------------------------------------------
  # Returns if this type can assigned by concatenation. 
  def canAssignedByConcat(self):
    return False

  #-------------------------------------------------------------------------------
  # Returns if this can be used in a concatenation. 
  def canUsedInConcat(self):
    return False

  #-------------------------------------------------------------------------------
  # Raises an exception if the value (dir,file,...) not exists.
  def checkExists(self,strValue,scriptLine):
    pass

  #-------------------------------------------------------------------------------
  # Raises an exception if the value (dir,file,...) already exists.
  def checkNotExists(self,strValue,scriptLine):
    pass

  #-------------------------------------------------------------------------------
  # Checks if the value is valid for this type.
  # For DIR,FILE,... only checks for valid names. Not
  # if a directory or file exists. 
  def checkStrValue(self,strValue,varName,scriptLine):
    # Is it a constant?
    if self.isConstant(strValue):
      # Get the constant.
      pConstant = GLOB.constants[strValue]
      # Check the type of the constant.
      if not pConstant.type.canAssignTo(self):
        Err.raiseSyntaxError(Err.NoValidVariableConstantType3,scriptLine,
                             strValue,varName,self.name)
    else:
      # Check the strValue.
      self._checkStrValue(strValue,varName,scriptLine)

  #-------------------------------------------------------------------------------
  # The exception causes that in checkStrValue and isValidValue only True 
  # returns if the strValue a valid constant is.
  def _checkStrValue(self,strValue,varName,scriptLine):
    Err.raiseSyntaxError(Err.NoValidVariableValue3,scriptLine,
                         strValue,varName,self.name)
  
  #-------------------------------------------------------------------------------
  def isConstant(self,strValue):
    if GLOB.constants.exists(strValue):
      return True
    else:
      return False

  #-------------------------------------------------------------------------------
  # Return if the value is the keyword for an optional value/argument.
  def isOptionalValue(self,strValue):
    if str(strValue).upper()=="NONE":
      return True
    else:
      return False

  #-------------------------------------------------------------------------------
  # Returns if strValue is a constant.
  def isValidConstant(self,strValue):
    if self.isConstant(strValue):
      try:
        self.checkStrValue(strValue,"",None)
        return True
      except:
        return False
    else:
      return False

  #-------------------------------------------------------------------------------
  # Returns True if it's a valid constant.
  def isValidValue(self,strValue):
    try:
      self.checkStrValue(strValue,"",None)
      return True
    except:
      return False

  #-------------------------------------------------------------------------------
  # Returns the value of the constant.
  # Returns None if not found.
  def parseConstant(self,strValue):
    if self.isConstant(strValue):
      return GLOB.constants[strValue].value
    else:
      return None

  #-------------------------------------------------------------------------------
  # Returns the value of strValue.
  # Returns the strValue if not found.
  def parseStrValue(self,strValue):
    #Log.dbg("Types.parseStrValue - "+str(strValue))
    if (strValue is None) or (strValue=="None"):
      return None
    elif self.isConstant(strValue):
      return self.parseConstant(strValue)
    else:
      return self._parseStrValue(strValue)

  #-------------------------------------------------------------------------------
  # Returns the strValue terug.
  def _parseStrValue(self,strValue):
    return strValue

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Obj(Type):
  #-------------------------------------------------------------------------------
  def __init__(self):
    super(Obj,self).__init__()
    self.description = ""
  #-------------------------------------------------------------------------------
  def _checkStrValue(self,strValue,varName,scriptLine):
    # Always OK.
    pass
  #-------------------------------------------------------------------------------
  # Returns if this type can assigned by concatenation. 
  def canAssignedByConcat(self):
    return True

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Boolean(Type):
  #-------------------------------------------------------------------------------
  def __init__(self):
    super(Boolean,self).__init__()
    self.description = ""
  #-------------------------------------------------------------------------------
  def _parseStrValue(self,strValue):
    return self.parseConstant(strValue)

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class CellSize(Type):
  #----------------C--------------------------------------------------------------
  def __init__(self):
    super(CellSize,self).__init__()
    self.description = ""
  #-------------------------------------------------------------------------------
  def _checkStrValue(self,strValue,varName,scriptLine):
    if not UT.isFloat(strValue):
      Err.raiseSyntaxError(Err.NoValidVariableValue3,scriptLine,strValue,varName,self.name)
  #-------------------------------------------------------------------------------
  def _parseStrValue(self,strValue):
    return float(strValue)

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Extent(Type):
  #-------------------------------------------------------------------------------
  def __init__(self):
    super(Extent,self).__init__()
    self.description = ""
  #-------------------------------------------------------------------------------
  def _checkStrValue(self,strValue,varName,scriptLine):
    # minx,miny,maxx,maxy
    tokens = strValue.split(",")
    # 20201118
    #if len(tokens) <> 4:
    if len(tokens) != 4:
      Err.raiseSyntaxError(Err.NoValidVariableValue3,scriptLine,strValue,varName,self.name)
    else:
      for token in tokens:
        if not UT.isFloat(token):
          Err.raiseSyntaxError(Err.NoValidVariableValue3,scriptLine,strValue,varName,self.name)
  #-------------------------------------------------------------------------------
  def _parseStrValue(self,strValue):
    # minx,miny,maxx,maxy
    tokens = strValue.split(",")
    extent = []
    for token in tokens:
      extent.append(float(token))
    return extent

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Float(Type):
  #-------------------------------------------------------------------------------
  def __init__(self):
    super(Float,self).__init__()
    self.description = ""
  #-------------------------------------------------------------------------------
  def _checkStrValue(self,strValue,varName,scriptLine):
    if not UT.isFloat(strValue):
      Err.raiseSyntaxError(Err.NoValidVariableValue3,scriptLine,strValue,varName,self.name)
  #-------------------------------------------------------------------------------
  def _parseStrValue(self,strValue):
    return float(strValue)

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Integer(Type):
  #----------------C--------------------------------------------------------------
  def __init__(self):
    super(Integer,self).__init__()
    self.description = ""
  #-------------------------------------------------------------------------------
  def _checkStrValue(self,strValue,varName,scriptLine):
    if not UT.isInteger(strValue):
      Err.raiseSyntaxError(Err.NoValidVariableValue3,scriptLine,strValue,varName,self.name)
  #-------------------------------------------------------------------------------
  def _parseStrValue(self,strValue):
    return int(strValue)
  #-------------------------------------------------------------------------------
  # Returns if this can be used in a concatenation. 
  def canUsedInConcat(self):
    return True
    
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class String(Type):
  #----------------C--------------------------------------------------------------
  def __init__(self):
    super(String,self).__init__()
    self.description = ""
  #-------------------------------------------------------------------------------
  def _checkStrValue(self,strValue,varName,scriptLine):
    # Always ok.
    pass
  #-------------------------------------------------------------------------------
  # Returns if this type can assigned by concatenation. 
  def canAssignedByConcat(self):
    return True
  #-------------------------------------------------------------------------------
  # Returns if this can be used in a concatenation. 
  def canUsedInConcat(self):
    return True

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Dir(Type):
  #-------------------------------------------------------------------------------
  def __init__(self):
    super(Dir,self).__init__()
    self.description = ""
  #-------------------------------------------------------------------------------
  def _checkStrValue(self,strValue,varName,scriptLine):
    if not UT.isValidDirName(strValue):
      Err.raiseSyntaxError(Err.InvalidDirectoryName1,scriptLine,strValue)
  #-------------------------------------------------------------------------------
  def _parseStrValue(self,strValue):
    # Resolve ~ paths.
    return os.path.expanduser(strValue)
  #-------------------------------------------------------------------------------
  # Returns if this type can assigned by concatenation. 
  def canAssignedByConcat(self):
    return True
  #-------------------------------------------------------------------------------
  # Returns if this can be used in a concatenation. 
  def canUsedInConcat(self):
    return True
  #-------------------------------------------------------------------------------
  # Raises an exception if the dir not exists.
  def checkExists(self,strValue,scriptLine):
    # Keyword for optional dir?
    if self.isOptionalValue(strValue):
      return
    # Resolve ~ paths.
    tmpValue = self._parseStrValue(strValue)
    if not os.path.isdir(tmpValue):
      Err.raiseSyntaxError(Err.DirectoryNotFound1,scriptLine,strValue)
  #-------------------------------------------------------------------------------
  # Raises an exception if the dir already exists.
  def checkNotExists(self,strValue,scriptLine):
    # Keyword for optional dir?
    if self.isOptionalValue(strValue):
      return
    # Resolve ~ paths.
    tmpValue = self._parseStrValue(strValue)
    if os.path.isdir(tmpValue):
      # Do not overwrite output?
      if not GLOB.overwriteOutput:
        Err.raiseSyntaxError(Err.DirectoryAlreadyExists1,scriptLine,strValue)
        # 20210125 HELPT NIET
        # May exist but must be (almost) empty.
        #if not UT.dirIsEmptyButLog(strValue):
        #  Err.raiseSyntaxError(Err.DirectoryAlreadyExists1,scriptLine,strValue)

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class File(Type):
  #------------------------------------------------------------------------------
  def __init__(self):
    super(File,self).__init__()
    self.description = ""
  #-------------------------------------------------------------------------------
  def _checkStrValue(self,strValue,varName,scriptLine):
    if not UT.isValidFileName(strValue):
      Err.raiseSyntaxError(Err.InvalidFileName1,scriptLine,strValue)
  #-------------------------------------------------------------------------------
  def _parseStrValue(self,strValue):
    # Resolve ~ paths.
    return os.path.expanduser(strValue)
  #-------------------------------------------------------------------------------
  # Returns if this type can assigned by concatenation. 
  def canAssignedByConcat(self):
    return True
  #-------------------------------------------------------------------------------
  # Returns if this can be used in a concatenation. 
  def canUsedInConcat(self):
    return True
  #-------------------------------------------------------------------------------
  # Raises an exception if the file not exists.
  def checkExists(self,strValue,scriptLine):
    # Keyword for optional file?
    if self.isOptionalValue(strValue):
      return
    # Resolve ~ paths.
    tmpValue = self._parseStrValue(strValue)
    if not os.path.isfile(tmpValue):
      Err.raiseSyntaxError(Err.FileNotFound1,scriptLine,strValue)
  #-------------------------------------------------------------------------------
  # Raises an exception if the file already exists.
  def checkNotExists(self,strValue,scriptLine):
    # Keyword for optional file?
    if self.isOptionalValue(strValue):
      return
    # Resolve ~ paths.
    tmpValue = self._parseStrValue(strValue)
    if os.path.isfile(tmpValue):
      # Do not overwrite output?
      if not GLOB.overwriteOutput:
        Err.raiseSyntaxError(Err.FileAlreadyExists1,scriptLine,strValue)

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Raster(Type):
  
  #-------------------------------------------------------------------------------
  def __init__(self):
    super(Raster,self).__init__()
    self.description = ""
  #-------------------------------------------------------------------------------
  def _checkStrValue(self,strValue,varName,scriptLine):

    # 20201130 Because of circular references.
    import GlobioModel.Core.RasterUtils as RU

    if (RU.isGeoTifName(strValue)) or (RU.isAsciiGridName(strValue)):
      if not UT.isValidFileName(strValue):
        Err.raiseSyntaxError(Err.InvalidRasterName1,scriptLine,strValue)
    else:
      if not UT.isValidDirName(strValue):
        Err.raiseSyntaxError(Err.InvalidRasterName1,scriptLine,strValue)
  #-------------------------------------------------------------------------------
  def _parseStrValue(self,strValue):
    # Resolve ~ paths.
    return os.path.expanduser(strValue)
  #-------------------------------------------------------------------------------
  # Returns if this type can assigned by concatenation. 
  def canAssignedByConcat(self):
    return True
  #-------------------------------------------------------------------------------
  # Returns if this can be used in a concatenation. 
  def canUsedInConcat(self):
    return True
  #-------------------------------------------------------------------------------
  # Raises an exception if the raster not exists.
  def checkExists(self,strValue,scriptLine):

    # 20201130 Because of circular references.
    import GlobioModel.Core.RasterUtils as RU

    # Keyword for optional raster?
    if self.isOptionalValue(strValue):
      return
    # Resolve ~ paths.
    tmpValue = self._parseStrValue(strValue)
    if not RU.rasterExists(tmpValue):
      Err.raiseSyntaxError(Err.RasterNotFound1,scriptLine,strValue)
  #-------------------------------------------------------------------------------
  # Raises an exception if the raster already exists.
  def checkNotExists(self,strValue,scriptLine):

    # 20201130 Because of circular references.
    import GlobioModel.Core.RasterUtils as RU

    # Keyword for optional raster?
    if self.isOptionalValue(strValue):
      return
    # Resolve ~ paths.
    tmpValue = self._parseStrValue(strValue)
    if RU.rasterExists(tmpValue):
      # Do not overwrite output?
      if not GLOB.overwriteOutput:
        Err.raiseSyntaxError(Err.RasterAlreadyExists1,scriptLine,strValue)

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
# A list of rasters with format raster1|raster2|raster3.
class RasterList(Type):
  #-------------------------------------------------------------------------------
  def __init__(self):
    super(RasterList,self).__init__()
    self.description = ""
  #-------------------------------------------------------------------------------
  def _checkStrValue(self,strValue,varName,scriptLine):
    # Create dummy raster type.
    dummyRasterType = Raster()
    # Get raster names.
    rasterNames = strValue.split("|")
    # Check all rasters.
    for rasterName in rasterNames:
      # Check raster.
      dummyRasterType._checkStrValue(rasterName,varName,scriptLine)
  #-------------------------------------------------------------------------------
  # Returns if this type can assigned by concatenation. 
  def canAssignedByConcat(self):
    return True
  #-------------------------------------------------------------------------------
  # Returns if this can be used in a concatenation. 
  def canUsedInConcat(self):
    return True
  #-------------------------------------------------------------------------------
  # Raises an exception if the rasters not exists.
  def checkExists(self,strValue,scriptLine):
    # Create dummy raster type.
    dummyRasterType = Raster()
    # Get raster names.
    rasterNames = strValue.split("|")
    # Check all rasters.
    for rasterName in rasterNames:
      try:
        # Check raster.
        dummyRasterType.checkExists(rasterName,scriptLine)
      except:
        Err.raiseSyntaxError(Err.RasterFromListNotFound1,scriptLine,rasterName)
        
  #-------------------------------------------------------------------------------
  # Raises an exception if the rasters already exists.
  def checkNotExists(self,strValue,scriptLine):
    # Create dummy raster type.
    dummyRasterType = Raster()
    # Get raster names.
    rasterNames = strValue.split("|")
    # Check all rasters.
    for rasterName in rasterNames:
      try:
        # Check raster.
        dummyRasterType.checkNotExists(rasterName,scriptLine)
      except:
        Err.raiseSyntaxError(Err.RasterFromListAlreadyExists1,scriptLine,rasterName)

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Vector(Type):
  #-------------------------------------------------------------------------------
  def __init__(self):
    super(Vector,self).__init__()
    self.description = ""
  #-------------------------------------------------------------------------------
  def _checkStrValue(self,strValue,varName,scriptLine):

    # 20201130 Because of circular references.
    import GlobioModel.Core.RasterUtils as RU

    if RU.isShapeFileName(strValue):
      if not UT.isValidFileName(strValue):
        Err.raiseSyntaxError(Err.InvalidVectorName1,scriptLine,strValue)
    else:
      if RU.isFgdbFcName(strValue):
        fgdbName = RU.getFgdbName(strValue)
        if not UT.isValidDirName(fgdbName):
          Err.raiseSyntaxError(Err.InvalidVectorName1,scriptLine,strValue)
  #-------------------------------------------------------------------------------
  def _parseStrValue(self,strValue):
    # Resolve ~ paths.
    return os.path.expanduser(strValue)
  #-------------------------------------------------------------------------------
  # Returns if this type can assigned by concatenation. 
  def canAssignedByConcat(self):
    return True
  #-------------------------------------------------------------------------------
  # Returns if this can be used in a concatenation. 
  def canUsedInConcat(self):
    return True
  #-------------------------------------------------------------------------------
  # Raises an exception if the vector not exists.
  def checkExists(self,strValue,scriptLine):

    # 20201130 Because of circular references.
    import GlobioModel.Core.RasterUtils as RU

    # Keyword for optional vector?
    if self.isOptionalValue(strValue):
      return
    # Resolve ~ paths.
    tmpValue = self._parseStrValue(strValue)
    if not RU.vectorExists(tmpValue):
      Err.raiseSyntaxError(Err.VectorNotFound1,scriptLine,strValue)
  #-------------------------------------------------------------------------------
  # Raises an exception if the vector already exists.
  def checkNotExists(self,strValue,scriptLine):

    # 20201130 Because of circular references.
    import GlobioModel.Core.RasterUtils as RU

    # Keyword for optional vector?
    if self.isOptionalValue(strValue):
      return
    # Resolve ~ paths.
    tmpValue = self._parseStrValue(strValue)
    if RU.vectorExists(tmpValue):
      # Do not overwrite output?
      if not GLOB.overwriteOutput:
        Err.raiseSyntaxError(Err.VectorAlreadyExists1,scriptLine,strValue)

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class TypeList(dict):

  #-------------------------------------------------------------------------------
  # Override because of uppercase keys/names.
  def __getitem__(self,name):
    return super(TypeList,self).__getitem__(name.upper())

  #-------------------------------------------------------------------------------
  # Override because of uppercase "name in types".
  def __contains__(self, key):
    return super(TypeList,self).__contains__(key.upper())

  #-------------------------------------------------------------------------------
  def add(self,ptype):
    self[ptype.name.upper()] = ptype

  #-------------------------------------------------------------------------------
  def exists(self,name):
    return name in self

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  pass
  # import Globio4TestRun
  # Globio4TestRun.globio4TestRun()
