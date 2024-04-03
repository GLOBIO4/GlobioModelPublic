# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
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
#-------------------------------------------------------------------------------

import GlobioModel.Common.Utils as Utils

# Version information.
globioVersion = "4.0"
globioSubSubVersion = "10"
globioBuildVersion = "0"
globioReleaseDate = "sep 2017"
appVersion = "1.0"
appSubSubVersion = "1"
appReleaseDate = "mar 2017"

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
userName = Utils.getUserName()
userTempDir = Utils.getUserTempDir()

# Model settings.
validCellSizes = ""

# Directory with config files.
configDir = ""

# Constants, types and variables.
constants = None
types = None
variables = None

# Runs, scenarios and modules.
runables = None

# Reserved keywords.
reservedWords = ["INCLUDE",
                 "BEGIN_RUN","END_RUN",
                 "RUN",
                 "BEGIN_SCENARIO","END_SCENARIO",
                 "RUN_SCENARIO",
                 "BEGIN_MODULE","END_MODULE",
                 "RUN_MODULE",
                 "LIST","DO_LIST"]

# EPSG codes.
epsgWGS84 = 4326
