# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
# ******************************************************************************

#-------------------------------------------------------------------------------
# Modified: -
#-------------------------------------------------------------------------------

import os
import glob

import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Common.Utils as UT

import GlobioModel.Core.AppUtils as AU

#-------------------------------------------------------------------------------
def docListConstants(indent=""):
  Log.info(indent+"Constants:")
  indent += "  "
  for constName in GLOB.constants:
    pConst = GLOB.constants[constName]
    Log.info(indent + pConst.type.name + " " + pConst.name + " = " + str(pConst.value))

#-------------------------------------------------------------------------------
def docListGlobalVariables(indent=""):
  Log.info(indent+"Global variables:")
  indent += "  "
  for varFullName in GLOB.variables:
    if varFullName.startswith("SCENARIO_BUILDIN."):
      continue
    pVar = GLOB.variables[varFullName]
    if pVar.isArgument:
      continue
    docListVariable(pVar,indent)

#-------------------------------------------------------------------------------
def docListCalculations(indent=""):
  fileDir = os.path.dirname(__file__)
  calcDir = os.path.join(fileDir,"..","Calculations")
  calcDir = os.path.abspath(calcDir)
  calcFilesFilter = os.path.join(calcDir,"GLOBIO_*.py")  
  calcFiles = glob.glob(calcFilesFilter)
  calcFiles.sort()  
  Log.info(indent+"Calculations:")
  indent += "  "
  for fileName in calcFiles:
    # Get the name.
    name = os.path.basename(fileName)
    name = UT.strBeforeLast(name,".")
    # Show name.
    Log.info(indent + name)
    # Show arguments.
    try:
      # Get the calculation class.
      ClassObj = AU.getGlobioCalculationClassByName(name)
      # Create an instantie.
      pCalc = ClassObj()
      # Get the run documentation.
      doc = pCalc.doc()
      if doc != "":
        indent2 = indent + "  "
        Log.info(indent2 + "Arguments:")
        indent2 = indent2 + "  "
        docLines = UT.strSplit(doc,"\n")
        for line in docLines:
          Log.info(indent2 + line)
    except:
      pass

#-------------------------------------------------------------------------------
def docListVariable(variable,indent=""):
  strValue =  variable.strValue
  parsedValue =  variable.updateParsedValue(variable.parent,variable.scriptLine)
  if strValue is None:
    Log.info(indent + variable.type.name + " " + variable.name + " = None")
  else:
    if strValue == str(parsedValue):
      Log.info(indent + variable.type.name + " " + variable.name + " = " + str(parsedValue))
    else:
      s = UT.strConcatAlignRight(indent + variable.type.name + " " + variable.name + " = " + str(parsedValue),
                                    "  (" + strValue + ")",80)
      Log.info(s)
  if variable.description!="":
    Log.info(indent + "  " + variable.description)
