# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************

#-------------------------------------------------------------------------------
# Modified: 25 apr 2016, ES, ARIS B.V.
#           - InvalidNumberOfCSVLines1 added.
#           - ErrorReadingFile1 added.
#           23 sept 2016, ES, ARIS B.V.
#           - Version 4.0.2
#           - NoIntegerListSpecified added.
#           - InvalidIntegerList1 added.
#           - InvalidLandusePriorityName1 added.
#           - FieldNotFound1,NoFieldSpecified1 etc. added.
#           - NoLandusePriorityCodesSpecified,InvalidLandusePriorityCode1 etc.
#             added.
#           - NoRastersSpecified added.
#           - InvalidNumberOfItemsInList3 etc. added.
#           - InvalidExtentNrOfColsRows etc. added.
#           - InvalidArcGISDataType1 added.
#           - NotImplemented1 added.
#           - InvalidFloatList1 etc. added.
#           - InvalidCompressionMode etc. added.
#           - InvalidInteger1 etc. added.
#           - InvalidLanduseReplaceCode1 added.
#           - InvalidIntegerListOfLists1 added.
#           - NoClaimAreaMultiplierLanduseCodesSpecified etc. added.
#           - RasterFromListNotFound1 etc. added.
#           8 may 2017, ES, ARIS B.V.
#           - Version 4.0.6
#           - CannotSaveInMemoryRaster etc. added.
#           - InvalidFloatListLength1 added.
#           9 may 2017, ES, ARIS B.V.
#           - Version 4.0.9
#           - NoSettlementsFound added.
#           2 dec 2020, ES, ARIS B.V.
#           - Version 4.1.0
#           - NoGlobioCalculationPathsSpecified added.
#           - ReadErrorRasterAlreadyCreated1 added (LUH).
#           - RasterNotSupported1 added (LUH).
#           - RasterNotSupportedForWrite1 added (LUH).
#           - RasterCannotBeInitialize1 added (LUH).
#           - NoVariableSpecified1 added (LUH).
#           - NoFilesSpecified added (LUH).
#           - ResamplingInvalidTypeForSum1 added (LUH).
#           11 jan 2021, ES, ARIS B.V.
#           - Version 4.1.1
#           - ReadErrorRasterDataAlreadyCreated1 added (LUH).
#           - NoNetCDFVariableSpecified1 added (LUH).
#           - NoNetCDFInfoFoundInFile2 added (LUH).
#           - RasterDataAvailable added (LUH).
#-------------------------------------------------------------------------------

from sys import exc_info,stdout
from traceback import format_exception, print_exception

errors = {}

# Defines the error number constants.
(
  Unknown,
  UserDefined1,
  NotImplemented1,

  InvalidCommand,
  InvalidOption1,

  NoValidGlobioConfiguration,
  NoValidGlobioScript,

  # Directory
  DirectoryNotFound1,
  NoDirectorySpecified,
  DirectoryAlreadyExists1,
  InvalidDirectoryName1,

  # File
  FileNotFound1,
  NoFileSpecified,
  FileAlreadyExists1,
  InvalidFileName1,
  ErrorReadingFile1,
  NoFilesSpecified,

  IncludeFileNotFound1,

  NoCompressionModeSpecified,
  InvalidCompressionMode1,

  # Declaration (script)
  InvalidDeclaration,
  InvalidArgumentDeclaration,
  InvalidArgumentDeclaration1,
  InvalidNumberOfArgumentsInCall,
  NoArgumentInOutTypeSpecified,
  TypeNotFound1,
  NoVariableSpecified1,

  # Constant (script)
  ConstantNotFound1,

  # Variable (script)
  VariableNotFound1,
  VariableAlreadyExists1,
  VariableOrConstantNotFound1,
  InvalidVariableDeclaration,
  InvalidVariableDeclaration1,
  InvalidVariableDeclarationRecursive,
  InvalidVariableAssignment,
  InvalidVariableName1,
  InvalidVariableNameConstant1,
  InvalidVariableNameType1,
  InvalidVariableNameReservedWord1,
  InvalidVariableReferenceType1,
  InvalidConstantReferenceType1,
  VariableIsUsedRecursive1,
  NoValidVariableValue,
  NoValidVariableValue3,
  NoValidVariableConstantType3,
  NoValidVariableValueReference1,
  VariableValueNotSet1,
  VariablesNotAllowedInIncludedScripts,
  VariableTypeNotAllowedConcatenation2,
  VariableTypeCanNotUsedInConcatenation2,
  ConstantTypeCanNotUsedInConcatenation2,

  # Keyword
  NoValidKeywordOrVariable1,
  NoValidKeyword1,
  RelatedKeywordOfKeywordNotFound1,

  # Runcommand
  NoValidRunCommandInRunBlock,
  NoValidRunCommand2,
  
  RunableAlreadyExists1,

  NoRunNameSpecified,
  RunNotFound1,
  NoScenarioNameSpecified,
  ScenarioNotFound1,
  NoModuleNameSpecified,
  ModuleNotFound1,
  ListNotFound1,
  MsgNotFound1,
  
  InvalidListDeclaration,
  
  NoGlobioCalculationNameSpecified,
  NoGlobioCalculationPathsSpecified,
  GlobioCalculationNotFound1,
  GlobioCalculationFileNotFound1,
  GlobioCalculationClassNotFound1,
  InvalidGlobioCalculationClass1,
  GlobioCalculationNoDocumentationFound1,
  GlobioCalculationInvalidDocumentation1,
  GlobioCalculationInvalidDeclaration1,
  GlobioCalculationInvalidDeclarationNoInOut1,
  GlobioCalculationInvalidDeclarationTypeNotFound2,
  
  NoValidLineMissingLeftParenthesis,
  NoValidLineMissingRightParenthesis,
  InvalidArgumentsArgumentMissing,
  InvalidArgumentsArgumentsMissing,

  # Vector
  VectorNotFound1,
  NoVectorSpecified,
  VectorAlreadyExists1,
  InvalidVectorName1,

  # Raster  
  RasterNotFound1,
  NoRasterSpecified,
  RasterAlreadyExists1,
  InvalidRasterName1,
  NoRastersSpecified,
  RasterFromListNotFound1,
  RasterFromListAlreadyExists1,
  CannotReadInMemoryRaster,
  CannotSaveInMemoryRaster,
  ReadErrorRasterDataAlreadyCreated1,
  RasterNotSupported1,
  RasterNotSupportedForWrite1,
  RasterCannotBeInitialized1,
  NoRasterDataAvailable,

  # Table
  TableNotFound1,
  TableAlreadyExists1,

  # Field
  FieldNotFound1,
  NoFieldSpecified1,
  InvalidFieldList2,
  NoFieldsSpecified1,
  InvalidFieldType1,
  NoFieldTypesSpecified1,
  InvalidNumberOfFieldTypes2,

  # Variable (NetCDF)
  NoNetCDFVariableSpecified1,
  NoNetCDFInfoFoundInFile2,

  # Numpy
  InvalidNumpyDataType1,

  # GDAL
  InvalidGDALDataType1,

  # ArcGIS
  InvalidArcGISDataType1,

  # CSV  
  InvalidNumberOfCSVFieldtypes2,
  InvalidNumberOfCSVLines1,
  InvalidCSVFieldtype1,
  InvalidIntegerInCSVFile2,
  InvalidFloatInCSVFile2,

  # Lists.
  InvalidNumberOfItemsInList3,
  InvalidNumberOfItemsInList4,

  # Integer list.
  NoIntegerListSpecified,
  InvalidIntegerList1,
  InvalidIntegerListOfLists1,

  # Float list.
  NoFloatListSpecified,
  InvalidFloatList1,
  InvalidFloatListLength1,

  # Integer, floats, extent, cellsize etc.
  InvalidIntegerValue1,
  InvalidIntegerValueBetween3,
  InvalidFloatValue1,
  InvalidFloatValueBetween3,
  InvalidBooleanValue1,
  InvalidExtentValue1,
  InvalidExtentNrOfColsRows,
  InvalidRasterExtentNotAligned5,
  InvalidCellSizeValue1,
  InvalidGlobioCellSize1,
  InvalidRasterGlobioCellSize2,
  InvalidExtentNotInExtent2,

  # Resampling
  ResamplingRasterContainsNoData1,
  ResamplingInvalidTypeForSum1,

  # GLOBIO_
  InvalidNumberOfArguments2,

  # Landuse names/codes.
  NoLandusePriorityNamesSpecified, 
  InvalidLandusePriorityName1,
  NoLandusePriorityCodesSpecified, 
  InvalidLandusePriorityCode1,
  NoAnthropogenicLanduseCodesSpecified,
  InvalidAnthropogenicLanduseCode1,
  NoNotAllocatableLanduseCodesSpecified,
  InvalidNotAllocatableLanduseCode1,
  NoSuitabilityRasterCodesSpecified, 
  InvalidSuitabilityRasterCode1,
  NoLanduseReplaceWithCodeSpecified, 
  InvalidLanduseReplaceWithCode1,
  NoLanduseUndefinedCodeSpecified, 
  InvalidLanduseUndefinedCode1,
  NoClaimAreaMultiplierLanduseCodesSpecified,
  InvalidClaimAreaMultiplierLanduseCode1,
  NoLanduseReplaceCodesSpecified,
  InvalidLanduseReplaceCodes1,

  # Human encroachment.
  NoSettlementsFound,

  # "Temp" are dummy constants to prevent changing the range all the time.
  Temp

) = range(161)

#-------------------------------------------------------------------------------
# Defines the error messages.
def defineErrors():
  
  addError(Unknown,"Unknown error.")
  addError(UserDefined1,"{0}")
  addError(NotImplemented1,"Method '{0}' not implemented.")

  addError(InvalidCommand,"Invalid command.")
  addError(InvalidOption1,"Invalid option '{0}'.")

  addError(NoValidGlobioConfiguration,"Errors found in the GLOBIO configuration. Stopped.")
  addError(NoValidGlobioScript,"Errors found in this GLOBIO script. Stopped.")

  addError(DirectoryNotFound1,"Directory '{0}' not found.")
  addError(NoDirectorySpecified,"No directory specified.")
  addError(DirectoryAlreadyExists1,"Directory '{0}' already exists.")
  addError(InvalidDirectoryName1,"'{0}' is an invalid directory name.")

  addError(FileNotFound1,"File '{0}' not found.")
  addError(NoFileSpecified,"No file specified.")
  addError(FileAlreadyExists1,"File '{0}' already exists.")
  addError(InvalidFileName1,"'{0}' is an invalid file name.")
  addError(ErrorReadingFile1,"Error reading file '{0}'.")
  addError(NoFilesSpecified,"No files specified.")

  addError(IncludeFileNotFound1,"Include file '{0}' not found in userscript directory or config directory.")

  addError(NoCompressionModeSpecified,"No compression mode specified, use LZW, DEFLATE or PACKBITS.")
  addError(InvalidCompressionMode1,"Invalid  compression mode '{0}' specified, use LZW, DEFLATE or PACKBITS.")

  addError(InvalidDeclaration,"Invalid declaration.")

  addError(InvalidArgumentDeclaration,"Invalid argument declaration.")
  addError(InvalidArgumentDeclaration1,"Invalid argument declaration - {0}")
  addError(InvalidNumberOfArgumentsInCall,"Invalid number of arguments in call.")
  addError(NoArgumentInOutTypeSpecified,"No IN or OUT argument type specified.")

  addError(TypeNotFound1,"Type '{0}' not found.")
  addError(NoVariableSpecified1,"No variable specified for '%s'.")

  addError(ConstantNotFound1,"Constant '{0}' not found.")
  
  addError(VariableNotFound1,"Variable '{0}' not found.")
  addError(VariableAlreadyExists1,"Variable '{0}' already exists.")
  addError(VariableOrConstantNotFound1,"Variable or constant '{0}' not found.")
  addError(InvalidVariableDeclaration,"Invalid variable declaration.")
  addError(InvalidVariableDeclaration1,"Invalid variable declaration of variable {0}.")
  addError(InvalidVariableDeclarationRecursive,"Invalid variable declaration. Recursion not allowed.")
  addError(InvalidVariableAssignment,"Invalid variable assignment.")
  addError(InvalidVariableName1,"Invalid variable name '{0}'.")
  addError(InvalidVariableNameConstant1,"Invalid variable name '{0}', a constant with the same name already exists.")
  addError(InvalidVariableNameType1,"Invalid variable name '{0}', a type with the same name already exists.")
  addError(InvalidVariableNameReservedWord1,"Invalid variable name '{0}', {0} is a reserved word.")
  addError(InvalidVariableReferenceType1,"Variable reference '{0}' has an invalid type.")
  addError(InvalidConstantReferenceType1,"Constant reference '{0}' has an invalid type.")
  addError(VariableIsUsedRecursive1,"Recursive use of variable '{0}' is not allowed.")
  addError(NoValidVariableValue,"No valid variable value.")
  addError(NoValidVariableValue3,"'{0}' is no valid value for variable '{1}' of type '{2}'.")
  addError(NoValidVariableConstantType3,"Constant '{0}' has no valid type for variable '{1}' of type '{2}'.")
  addError(NoValidVariableValueReference1,"A variable reference is no valid value for variable '{0}'.")
  addError(VariableValueNotSet1,"Value of variable '{0}' is not set.")
  addError(VariablesNotAllowedInIncludedScripts,"Defining or setting global variables in included scripts is not allowed.")
  addError(VariableTypeNotAllowedConcatenation2,"Variable '{0}' of type {1} can not be set by combining other variables.")
  addError(VariableTypeCanNotUsedInConcatenation2,"Variable '{0}' of type {1} can not be used for combined values.")
  addError(ConstantTypeCanNotUsedInConcatenation2,"Constant '{0}' of type {1} can not be used for combined values.")
    
  addError(NoValidKeyword1,"'{0}' is no valid keyword.")
  addError(RelatedKeywordOfKeywordNotFound1,"Related keyword '{0}' of '{1}' not found.")

  addError(NoValidKeywordOrVariable1,"'{0}' is no valid keyword or variable.")

  addError(NoValidRunCommandInRunBlock,"A RUN command is not valid in a RUN definition.")

  addError(RunableAlreadyExists1,"A run, scenario or module with name '{0}' already exists.")
  addError(NoValidRunCommand2,"'{0}' is no valid run command for '{1}'.")

  addError(NoRunNameSpecified,"No run name specified.")
  addError(RunNotFound1,"Run '{0}' not found.")
  addError(NoScenarioNameSpecified,"No scenario name specified.")
  addError(ScenarioNotFound1,"Scenario '{0}' not found.")
  addError(NoModuleNameSpecified,"No module name specified.")
  addError(ModuleNotFound1,"Module '{0}' not found.")
  addError(ListNotFound1,"List '{0}' not found.")
  addError(MsgNotFound1,"Msg '{0}' not found.")

  addError(InvalidListDeclaration,"Invalid list declaration.")

  addError(NoGlobioCalculationNameSpecified,"No GLOBIO calculation name specified.")
  addError(NoGlobioCalculationPathsSpecified,"There are no GLOBIO calculation paths specified in Globals.py.")
  addError(GlobioCalculationNotFound1,"GLOBIO calculation '{0}' not found.")
  addError(GlobioCalculationFileNotFound1,"GLOBIO calculation file '{0}' not found.")
  addError(GlobioCalculationClassNotFound1,"GLOBIO calculation '{0}' not found.")
  addError(InvalidGlobioCalculationClass1,"Invalid GLOBIO calculation class '{0}'.")
  addError(GlobioCalculationNoDocumentationFound1,"No GLOBIO calculation documentation found for '{0}'.")
  addError(GlobioCalculationInvalidDocumentation1,"Invalid GLOBIO calculation documentation found for '{0}'.")
  addError(GlobioCalculationInvalidDeclaration1,"Invalid GLOBIO calculation argument declaration in module '{0}'.")
  addError(GlobioCalculationInvalidDeclarationNoInOut1,"Invalid GLOBIO calculation argument declaration in module '{0}'. No IN or OUT argument type specified.")
  addError(GlobioCalculationInvalidDeclarationTypeNotFound2,"Invalid GLOBIO calculation argument declaration in module '{0}'. Type '{1}' not found.")

  addError(NoValidLineMissingLeftParenthesis,"Invalid line, missing '('.")
  addError(NoValidLineMissingRightParenthesis,"Invalid line, missing ')'.")
  addError(InvalidArgumentsArgumentMissing,"Invalid arguments, argument missing.")
  addError(InvalidArgumentsArgumentsMissing,"Invalid arguments, arguments missing.")

  # Vector
  addError(VectorNotFound1,"Vector datasource '{0}' not found.")
  addError(NoVectorSpecified,"No vector datasource name specified.")
  addError(VectorAlreadyExists1,"Vector datasource '{0}' already exists.")
  addError(InvalidVectorName1,"'{0}' is an invalid vector datasource name.")

  # Raster
  addError(RasterNotFound1,"Raster '{0}' not found.")
  addError(NoRasterSpecified,"No raster name specified.")
  addError(RasterAlreadyExists1,"Raster '{0}' already exists.")
  addError(InvalidRasterName1,"'{0}' is an invalid raster name.")
  addError(NoRastersSpecified,"No raster names specified.")
  addError(RasterFromListNotFound1,"Raster '{0}' from raster list not found.")
  addError(RasterFromListAlreadyExists1,"Raster '{0}' from raster list already exists.")
  addError(CannotReadInMemoryRaster,"Cannot read an in-memory raster.")
  addError(CannotSaveInMemoryRaster,"Cannot save an in-memory raster.")
  addError(ReadErrorRasterDataAlreadyCreated1,"Read error. Internal raster data of '{0}' already created.")
  addError(RasterNotSupported1,"The specified raster is not supported: {0}")
  addError(RasterNotSupportedForWrite1,"The specified raster cannot be written to disk (readonly type): {0}")
  addError(RasterCannotBeInitialized1,"A raster of name '{0}' cannot be initialized (readonly type).")
  addError(NoRasterDataAvailable,"No raster data available.")

  # Table
  addError(TableNotFound1,"Table '{0}' not found.")
  addError(TableAlreadyExists1,"Table '{0}' already exists.")

  # Field
  addError(FieldNotFound1,"Field '{0}' not found.")
  addError(NoFieldSpecified1,"No field specified for parameter '{0}'.")
  addError(InvalidFieldList2,"Field '{0}' not found.")
  addError(NoFieldsSpecified1,"No fields specified for parameter '{0}'.")
  addError(InvalidFieldType1,"No valid fieldtype '{0}'.")
  addError(NoFieldTypesSpecified1,"No fieldtypes specified for parameter '{0}'.")
  addError(InvalidNumberOfFieldTypes2,"No valid number of fieldtypes specified for parameter '{0}', {1} expected'.")

  # Variable (NetCDF)
  addError(NoNetCDFVariableSpecified1,"No NetCDF variable specified for parameter '{0}'.")
  addError(NoNetCDFInfoFoundInFile2,"No '{0}' info found in NetCDF file: {1}.")

  # Numpy
  addError(InvalidNumpyDataType1, "Invalid Numpy datatype {0}.")

  # GDAL
  addError(InvalidGDALDataType1, "Invalid GDAL datatype {0}.")

  # ArcGIS
  addError(InvalidArcGISDataType1, "Invalid ArcGIS datatype {0}.")
  
  # CSV
  addError(InvalidNumberOfCSVFieldtypes2, "Invalid number of fieldtypes, {0} found while {1} where expected.")
  addError(InvalidNumberOfCSVLines1, "Invalid number of lines found in file {0}.")
  addError(InvalidCSVFieldtype1, "Invalid fieldtype '{0}' for csv files, used I,F or S.")
  addError(InvalidIntegerInCSVFile2, "The value '{0}' is not a valid integer value in csv file {1}.")
  addError(InvalidFloatInCSVFile2, "The value '{0}' is not a valid float value in csv file {1}.")

  # Lists.
  addError(InvalidNumberOfItemsInList3, "Invalid number of items in list '{0}'. {1} found while {2} expected.")
  addError(InvalidNumberOfItemsInList4, "Invalid number of {0} in list '{1}'. {2} found while {3} expected.")

  # Integer list
  addError(NoIntegerListSpecified, "No list of integers specified.")
  addError(InvalidIntegerList1, "The list '{0}' is not a valid list of integers.")
  addError(InvalidIntegerListOfLists1, "The list '{0}' is not a valid list of (list of) integers.")

  # Float list
  addError(NoFloatListSpecified, "No list of floats specified.")
  addError(InvalidFloatList1, "The list '{0}' is not a valid list of floats.")
  addError(InvalidFloatListLength1, "The list '{0}' has not the valid number of floats.")

  # Integer, floats, extent, cellsize etc.
  addError(InvalidIntegerValue1, "The value '{0}' is not a valid integer value.")
  addError(InvalidIntegerValueBetween3, "The value '{0}' is not a valid integer value. The value " + \
                                      "must be between {1} and {2}.")
  addError(InvalidFloatValue1, "The value '{0}' is not a valid floating point value.")
  addError(InvalidFloatValueBetween3, "The value '{0}' is not a valid floating point value. The value " + \
                                      "must be between {1} and {2}.")
  addError(InvalidBooleanValue1, "The value '{0}' is not a valid boolean value.")
  addError(InvalidExtentValue1, "The value '{0}' is not an extent value.")
  addError(InvalidExtentNrOfColsRows, "The extent has an invalid number of columns and rows.")
  addError(InvalidRasterExtentNotAligned5, "The extent ({0},{1},{2},{3}) of raster '{4}' is not aligned at 0,0.")
  addError(InvalidCellSizeValue1, "The value '{0}' is not a valid cellsize value.")
  addError(InvalidGlobioCellSize1, "Cellsize '{0}' is not a valid GLOBIO cellsize.")
  addError(InvalidRasterGlobioCellSize2, "Cellsize '{0}' of raster '{1}' is not a valid GLOBIO cellsize.")
  addError(InvalidExtentNotInExtent2, "INvalid extent, '{0}' not in '{1}'.")

  # Resampling
  addError(ResamplingRasterContainsNoData1, "Raster '{0}' contains cells with nodata which is not allowed for resampling.")
  addError(ResamplingInvalidTypeForSum1, "Raster '{0}' has an invalid datatype for resampling with the 'sum' option.")

  # GLOBIO_
  addError(InvalidNumberOfArguments2, "Invalid number of arguments ({0}) when running {1}.")

  # Land use priority names/codes.  
  addError(NoLandusePriorityNamesSpecified, "No list of land-use priority names specified.")
  addError(InvalidLandusePriorityName1, "Invalid land-use priority name {0}.")
  addError(NoLandusePriorityCodesSpecified, "No list of land-use priority codes specified.")
  addError(InvalidLandusePriorityCode1, "Invalid land-use priority code {0}.")
  addError(NoAnthropogenicLanduseCodesSpecified, "No list of anthropogenic land-use codes specified.")
  addError(InvalidAnthropogenicLanduseCode1, "Invalid anthropogenic land-use code {0}.")
  addError(NoNotAllocatableLanduseCodesSpecified, "No list of not-allocatable land-use codes specified.")
  addError(InvalidNotAllocatableLanduseCode1, "Invalid not-allocatable land-use code {0}.")
  addError(NoSuitabilityRasterCodesSpecified, "No list of suitability raster land-use codes specified.")
  addError(InvalidSuitabilityRasterCode1, "Invalid suitability raster land-use code {0}.")
  addError(NoLanduseReplaceWithCodeSpecified, "No land-use replace code specified.")
  addError(InvalidLanduseReplaceWithCode1, "Invalid land-use replace code {0}.")
  addError(NoLanduseUndefinedCodeSpecified, "No land-use code for 'undefined' specified.")
  addError(InvalidLanduseUndefinedCode1, "Invalid land-use code for 'undefined' {0}.")
  addError(NoClaimAreaMultiplierLanduseCodesSpecified, "list of claim area multiplier land-use codes specified.")
  addError(InvalidClaimAreaMultiplierLanduseCode1, "Invalid claim area multiplier land-use code {0}.")
  addError(NoLanduseReplaceCodesSpecified, "list of land-use codes specified to replacing with land-use replace codes.")
  addError(InvalidLanduseReplaceCodes1, "Invalid land-use codes {0} for replacing with land-use replace code.")

  # Human Encroachment.
  addError(NoSettlementsFound, "No settlements found. Aborting run.")

#-------------------------------------------------------------------------------
def addError(errorNr,msg):
  errors[errorNr] = msg

#-------------------------------------------------------------------------------
def errorNrToStr(errorNr):
  return errors[errorNr]

#-------------------------------------------------------------------------------
def getErrorMsg():
  _, exc_value,_ = exc_info()
  if type(exc_value) is list:
    msg =  "".join(exc_value)
  else:
    msg = str(exc_value)
  return msg

#-------------------------------------------------------------------------------
# Returns a list with messages.
def getErrorMsgWithTraceBack():
  result = []  
  exc_type, exc_value, exc_traceback = exc_info()
  msgs = format_exception(exc_type, exc_value, exc_traceback)
  for msg in msgs:
    result.append(strBeforeLast(msg,"\n"))
  return result

#-------------------------------------------------------------------------------
def getRaisedErrorMsg():
  _,exc_value,_ = exc_info()
  return str(exc_value)

#-------------------------------------------------------------------------------
def raiseGlobioError(errorNr,*args):
  msgFormat = errors[errorNr]
  if len(args)==0:
    errorMsg = msgFormat
  elif len(args)==1:
    errorMsg = msgFormat.format(args[0])
  elif len(args)==2:
    errorMsg = msgFormat.format(args[0],args[1])
  elif len(args)==3:
    errorMsg = msgFormat.format(args[0],args[1],args[2])
  elif len(args)==4:
    errorMsg = msgFormat.format(args[0],args[1],args[2],args[3])
  elif len(args)==5:
    errorMsg = msgFormat.format(args[0],args[1],args[2],args[3],args[4])
  #raise GlobioError("Error: " + errorMsg)
  raise GlobioError(errorMsg)

#-------------------------------------------------------------------------------
# scriptLine mag ook None zijn.
def raiseSyntaxError(errorNr,scriptLine,*args):
  msgFormat = errors[errorNr]
  if len(args)==0:
    errorMsg = msgFormat
  elif len(args)==1:
    errorMsg = msgFormat.format(args[0])
  elif len(args)==2:
    errorMsg = msgFormat.format(args[0],args[1])
  elif len(args)==3:
    errorMsg = msgFormat.format(args[0],args[1],args[2])
  elif len(args)==4:
    errorMsg = msgFormat.format(args[0],args[1],args[2],args[3])
  elif len(args)==5:
    errorMsg = msgFormat.format(args[0],args[1],args[2],args[3],args[4])
  if scriptLine is None:
    msg = "Error: {0}".format(errorMsg)
  else:
    msg = "Error: {0} - {1}:{2}".format(errorMsg,scriptLine.scriptName,scriptLine.lineNr)
  raise SyntaxError(msg)

#-------------------------------------------------------------------------------
# Raises a syntax error with the current error as addition.
def raiseExtentedSyntaxError(errorNr,scriptLine):
  # Haal de huidige error. 
  _, exc_value,_ = exc_info()
  # Strip the error.
  oldMsg = strAfter(str(exc_value),"Error: ")
  oldMsg = strBeforeLast(oldMsg," - ")
  # Get the new message.
  msgFormat = errors[errorNr]
  # Add the old one.
  errorMsg = msgFormat.format(oldMsg)
  if scriptLine is None:
    msg = "Error: {0}".format(errorMsg)
  else:
    msg = "Error: {0} - {1}:{2}".format(errorMsg,scriptLine.scriptName,scriptLine.lineNr)
  raise SyntaxError(msg)

#-------------------------------------------------------------------------------
def showError():
  _, exc_value,_ = exc_info()
  print(exc_value)

#-------------------------------------------------------------------------------
# Show the error with line info about the location in the Python code.
def showErrorWithTraceback():
  exc_type, exc_value, exc_traceback = exc_info()
  print_exception(exc_type, exc_value, exc_traceback,file=stdout)
#                            limit=4, file=sys.stdout)

#-------------------------------------------------------------------------------
# Returns the part of the string behind the first occurrance of the given string.
# Returns an empty string if not found.
# Case-insensitive.
def strAfter(s,after):
  index = s.lower().find(after.lower())
  if index < 0:
    return ""
  else:
    return s[(index+len(after)):]

#-------------------------------------------------------------------------------
# Returns the part of the string before the first occurrance of the given string.
# Returns an empty string if not found.
# Case-insensitive.
def strBeforeLast(s,before):
  index = s.lower().rfind(before.lower())
  if index < 0:
    return ""
  else:
    return s[:index]

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class ScriptError(Exception):
  pass

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GlobioError(Exception):
  pass

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
defineErrors()

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  pass
  # import GlobioModel.Core.Error as Err
  #
  # try:
  #   Err.raiseSyntaxError(Err.FileNotFound1, None, "sdasdasd.dat")
  # except:
  #   Err.showErrorWithTraceback()
  #   print("======================================")
  #   exc_type, exc_value, exc_traceback = exc_info()
  #   print("======================================")
  #   msgs = format_exception(exc_type, exc_value, exc_traceback)
  #   print(len(msgs))
  #   for msg in msgs:
  #     print(strBeforeLast(msg,"\n"))
    
