# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 31 aug 2017, ES, ARIS B.V.
#           - Version 4.0.7.0
#           - monitorEnabled added.
#           18 sep 2020, ES, ARIS B.V.
#           - Version 4.0.15
#           - CreateOutDir added.
#           - OverwriteOutput added.
#           - NumberOfCores added.
#-------------------------------------------------------------------------------

import GlobioModel.Core.Globals as GLOB
from GlobioModel.Core.ScriptLines import ScriptLine

#-------------------------------------------------------------------------------
def defineVariables(variableList):

  # Use dummy scriptline.
  scriptLine = ScriptLine("-",0,"Variables_Config")

  # Switches.
  variableList.addGlobalVar("ShowTracebackErrors","","BOOLEAN",str(GLOB.SHOW_TRACEBACK_ERRORS),scriptLine,"SHOW_TRACEBACK_ERRORS")
  variableList.addGlobalVar("Debug","","BOOLEAN",str(GLOB.debug),scriptLine,"debug")
  variableList.addGlobalVar("LogToFile","","BOOLEAN",str(GLOB.logToFile),scriptLine,"logToFile")
  variableList.addGlobalVar("SaveTmpData","","BOOLEAN",str(GLOB.saveTmpData),scriptLine,"saveTmpData")
  variableList.addGlobalVar("MonitorEnabled","","BOOLEAN",str(GLOB.monitorEnabled),scriptLine,"monitorEnabled")
  variableList.addGlobalVar("CreateOutDir","","BOOLEAN",str(GLOB.createOutDir),scriptLine,"createOutDir")
  variableList.addGlobalVar("OverwriteOutput","","BOOLEAN",str(GLOB.overwriteOutput),scriptLine,"overwriteOutput")
  variableList.addGlobalVar("NumberOfCores","","INTEGER",str(GLOB.numberOfCores),scriptLine,"numberOfCores")
