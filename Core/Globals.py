# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
#
# Contains the global variables.
#
# Use:
#   import Globals as GLOB
#
# For example:
#   GLOB.constants
#
# Modified: 25 apr 2016, ES, ARIS B.V.
#           - Version 4.0.1
#           - globioSubSubVersion changed to 1.
#           19 sept 2016, ES, ARIS B.V.
#           - Version 4.0.2.1
#           - globioSubSubVersion changed to 2.
#           - globioBuildVersion added.
#           - import Utils added.
#           - userName="..." changed to Utils.getUserName().
#           - userTempDir="..." changed to Utils.getUserTempDir().
#           - GIS_LIB_GDAL and GIS_LIB_ARCGIS added.
#           - gisLib added.
#           5 dec 2016, ES, ARIS B.V.
#           - Version 4.0.3.1
#           - globioSubSubVersion changed to 3.
#           - globioReleaseDate changed to dec 2016.
#           12 dec 2016, ES, ARIS B.V.
#           - Version 4.0.4.0
#           - globioSubSubVersion changed to 4.
#           - globioBuildVersion changed to 0.
#           14 dec 2016, ES, ARIS B.V.
#           - Version 4.0.5.0
#           - globioSubSubVersion changed to 5.
#           2 feb 2017, ES, ARIS B.V.
#           - Version 4.0.5.0/1.0.1
#           - appSubSubVersion changed to 1.
#           - globioReleaseDate changed to feb 2017.
#           - appReleaseDate changed to feb 2017.
#           5 apr 2017, ES, ARIS B.V.
#           - Version 4.0.6.0
#           23 aug 2017, ES, ARIS B.V.
#           - Version 4.0.7.0
#           - globioReleaseDate changed to aug 2017.
#           - monitorEnabled added.
#           1 sep 2017, ES, ARIS B.V.
#           - Version 4.0.8.0
#           - globioReleaseDate changed to sep 2017.
#           6 sep 2017, ES, ARIS B.V.
#           - Version 4.0.9.0
#           14 sep 2017, ES, ARIS B.V.
#           - Version 4.0.10.0
#           28 sep 2017, ES, ARIS B.V.
#           - Version 4.0.11.0
#           5 dec 2017, ES, ARIS B.V.
#           - Version 4.0.11.0
#           22 oct 2018, ES, ARIS B.V.
#           - Version 4.0.12.0
#           15 apr 2019, ES, ARIS B.V.
#           - Version 4.0.13.0
#           18 sep 2020, ES, ARIS B.V.
#           - Version 4.0.15
#           - createOutDir added.
#           - overwriteOutput added.
#           - numberOfCores added.
#           8 oct 2020, ES, ARIS B.V.
#           - Version 4.0.16
#           18 nov 2020, ES, ARIS B.V.
#           - Version 4.1.0
#           - Code converted to Python3.
#           - Variable calculationPaths added. This contains a list of
#             search paths used for importing calculation modules.
#           11 jan 2021, ES, ARIS B.V.
#           - Version 4.1.1
#           - netCDFImportPath added for specifying the path which is used
#             for importing NetCDF types/classes.
#           - cellSzie* and extent* added.
#           - cellSizes and cellSizeNames added.
#-------------------------------------------------------------------------------

import GlobioModel.Common.Utils as UT

# 20201118
from GlobioModel.Core.Constants import ConstantList
from GlobioModel.Core.ScriptBase import ScriptBaseList
from GlobioModel.Core.Types import TypeList
from GlobioModel.Core.Variables import VariableList

# Version information.
globioVersion = "4.3"
globioSubSubVersion = "1"
globioBuildVersion = "1"
globioReleaseDate = "mar 2024"
appVersion = "1.1"
appSubSubVersion = "0"
appReleaseDate = "feb 2021"

#### REMARK: Setting can be overriden by settings in Variables_Config.py!!!

# Errors.
# When showing errors, also show the location of the error in the python code.
SHOW_TRACEBACK_ERRORS = False
#SHOW_TRACEBACK_ERRORS = True

# Testing.
testing = False              # Used in the Logger.

# Switches.
debug = False                # To show extra debug messages.
#debug = True                 # To show extra debug messages.
saveTmpData = False          # To save temporary data.

# Memory and disk monitor.
# When enabled shows info about memory and disk usage during a run.
monitorEnabled = False

# Create output dir when not already exists.
createOutDir = False

# Overwrite extisting output.
overwriteOutput = False

# Number of cores used during parallelization.
numberOfCores = 0

# Logging.
logging = True
logToFile = True
logfileBaseName = "_globio4.log"
logfileName = ""
logfileHeaderLength = 80

# GIS library constants.
GIS_LIB_GDAL = 0
GIS_LIB_ARCGIS = 1

# GIS library.
gisLib = GIS_LIB_GDAL

# Username en tempdir.
userName = UT.getUserName()
userTempDir = UT.getUserTempDir()

# Search paths for importing calculation modules.
calculationPaths = [
  "GlobioModel.Calculations",
  "GlobioModel.Preprocessing",
  "GlobioModel.Postprocessing",
  "GlobioModel.LanduseHarmonization",
  "GlobioModel.Calculations_REF",
  "GlobioModel.Preprocessing_REF",
]

# Path used to import NetCDF classes/types.
netCDFImportPath = "GlobioModel.NetCDF"

# Directory with config files.
configDir = ""

# Constants, types and variables.
# 20201118
# constants = None
# types = None
# variables = None
constants = ConstantList()
types = TypeList()
variables = VariableList()

# Runs, scenarios and modules.
# 20201118
#runables = None
runables = ScriptBaseList()

# Reserved keywords.
reservedWords = ["INCLUDE",
                 "BEGIN_RUN","END_RUN",
                 "RUN",
                 "BEGIN_SCENARIO","END_SCENARIO",
                 "RUN_SCENARIO",
                 "BEGIN_MODULE","END_MODULE",
                 "RUN_MODULE",
                 "LIST","DO_LIST"]

# Cellsizes.
cellSize_10deg = 10.0
cellSize_1deg = 1.0
cellSize_30min = 30.0 / 60.0
cellSize_5min = 5.0 / 60.0
cellSize_30sec = 1.0 / 60.0 * 30.0 / 60.0
cellSize_10sec = 1.0 / 60.0 * 10.0 / 60.0

cellSizes = [cellSize_10deg,cellSize_1deg,
             cellSize_30min,cellSize_5min,
             cellSize_30sec,cellSize_10sec]
cellSizeNames = ["10deg","1deg","30min","5min", "30sec","10sec"]

# Valid cellsizes.
validCellSizes = "|".join(cellSizeNames)

# Extents.
extent_World = [-180.0,-90.0,180.0,90.0]
extent_Europe = [-25.0,33.0,45.0,72.0]
extent_NL = [3.0,50.0,8.0,54.0]

# EPSG codes.
epsgWGS84 = 4326
