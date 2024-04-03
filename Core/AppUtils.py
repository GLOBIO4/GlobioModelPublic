# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 19 jan 2017, ES, ARIS B.V.
#           - Version 4.0.5
#           - runGlobioCalculation modified, now using pCalc.run(*args).
#           2 dec 2020, ES, ARIS B.V.
#           - Version 4.1.0
#           - importGlobioCalculationFile added.
#           - checkGlobioCalculationName modified.
#           - getGlobioCalculationClassByName modified.
#           - checkGlobioCalculationName modified, try except added.
#-------------------------------------------------------------------------------

from copy import deepcopy
from importlib import import_module

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Common.Utils as Utils

from GlobioModel.Core.Variables import Variable,VariableList

#-------------------------------------------------------------------------------
# Check the arguments on () and empty arguments.
def checkArgumentsAsStrings(scriptLine):
  
  args = []
  
  # No ()?    
  if (scriptLine.line.find("(")<0) and (scriptLine.line.find(")")<0):
    return args

  # A ( but no )?
  if (scriptLine.line.find("(")>=0) and (scriptLine.line.find(")")<0):
    Err.raiseSyntaxError(Err.NoValidLineMissingRightParenthesis,scriptLine)

  # No ( but )?
  if (scriptLine.line.find("(")<0) and (scriptLine.line.find(")")>=0):
    Err.raiseSyntaxError(Err.NoValidLineMissingLeftParenthesis,scriptLine)
  
  # Get the part between ().  
  argsStr = Utils.strAfter(scriptLine.line,"(")
  argsStr = Utils.strBefore(argsStr,")")
  
  # Split into parts.
  args = Utils.strSplit(argsStr,",")
  
  print(args)
  
  # Check on empty arguments.
  cnt = 0
  for arg in args:
    if len(arg) == 0:
      cnt += 1
  if cnt == 1:    
      Err.raiseSyntaxError(Err.InvalidArgumentsArgumentMissing,scriptLine)
  if cnt > 1:    
      Err.raiseSyntaxError(Err.InvalidArgumentsArgumentsMissing,scriptLine)

#-------------------------------------------------------------------------------
# Check the declaration.
# If parentScript not is None then variables will be checkd if defined.
# Example: INTEGER Test1
def checkDeclaration(scriptLine,parentScript):

  #Log.dbg("checkDeclaration - " + scriptLine.line)
  
  # Is there a "="?
  if scriptLine.line.find("=") >= 0:
    Err.raiseSyntaxError(Err.InvalidDeclaration,scriptLine)

  # Split the line.
  tokens = Utils.strSplit(scriptLine.line," ")

  #Log.dbg("checkDeclaration "+str(tokens))
  
  # Just 1 token?
  if len(tokens) < 2:
    # Is there a valid type?
    if isType(tokens[0]):
      Err.raiseSyntaxError(Err.NoVariableSpecified,scriptLine)
    else:
      Err.raiseSyntaxError(Err.TypeNotFound1,scriptLine,tokens[0])
  elif len(tokens) > 2:
    # More than 2 tokens?
    Err.raiseSyntaxError(Err.InvalidDeclaration,scriptLine)
  else:
    # 2 tokens.
    typeName = tokens[0]
    varName = tokens[1]
    # Check the variable name.
    checkVariableName(varName,scriptLine)    
    if parentScript is not None:
      varFullName = getVariableFullName(varName, parentScript)
      checkTypeVariableName(typeName,varFullName,scriptLine)       

#-------------------------------------------------------------------------------
# Check if agrument declaration starts with IN or OUT.
def checkArgumentInOut(scriptLine):
  # Split the line.
  tokens = Utils.strSplit(scriptLine.line," ")
  # No tokens?
  if len(tokens) < 1:
    Err.raiseSyntaxError(Err.InvalidDeclaration,scriptLine)
  # No IN or OUT?
  if (tokens[0].upper()!="IN") and (tokens[0].upper()!="OUT"):
    Err.raiseSyntaxError(Err.NoArgumentInOutTypeSpecified,scriptLine)
    
#-------------------------------------------------------------------------------
# Check the argument declaration.
# Is the same as checkDeclaration() but gives an extended error.
# Checks no private variables. Check on duplicate names
# is done for var declarations in the block.
# Examples:
#   IN INTEGER Test1
#   OUT FILE Test1
def checkArgumentDeclaration(scriptLine):
  try:
    # Get arguments.
    strArgs = getArgumentsAsStrings(scriptLine)
    
    #Log.dbg("checkArgumentDeclaration "+str(strArgs))
    
    # Loop through arguments.
    for strArg in strArgs:
      # Create e temporary scriptline.
      tmpScriptLine = deepcopy(scriptLine)
      tmpScriptLine.line = strArg
      # Check if there is an IN or OUT.
      checkArgumentInOut(tmpScriptLine)
      # Remove IN and OUT.
      tmpScriptLine.line = Utils.strAfter(tmpScriptLine.line," ")
      # Check the declaration.      
      checkDeclaration(tmpScriptLine,None)       
  except:
    msg = Err.getRaisedErrorMsg()
    declMsg = Err.errorNrToStr(Err.InvalidDeclaration)
    # Is there an InvalidDeclaration error?
    if msg.find(declMsg) >=0:
      # Replace the whole errormessage.
      Err.raiseSyntaxError(Err.InvalidArgumentDeclaration,scriptLine)
    else:
      # Add the old message.
      Err.raiseExtentedSyntaxError(Err.InvalidArgumentDeclaration1,scriptLine)

#-------------------------------------------------------------------------------
# Checks if 's a valid GLOBIO calculation declaration/call.
# So if the <name>.py exists, a class is defined, and the
# class contains the necessary methods.
# Does not checks the arguments. 
def checkGlobioCalculationName(scriptLine):

  # Set the class and import name.
  className = getGlobioCalculationName(scriptLine)

  # Import the GLOBIO calculation file based on the classname. 
  pImport = importGlobioCalculationFile(className,scriptLine)

  # 20201202
  # # Get the class,
  # ClassObj = getattr(pImport,className)
  # if ClassObj is None:
  #   Err.raiseSyntaxError(Err.GlobioCalculationClassNotFound1,scriptLine,className)

  # Get the class.
  try:
    ClassObj = getattr(pImport,className)
  except:
    Err.raiseSyntaxError(Err.GlobioCalculationClassNotFound1,scriptLine,className)
  if ClassObj is None:
    Err.raiseSyntaxError(Err.GlobioCalculationClassNotFound1,scriptLine,className)

  try:
    # Create a class instance.
    pCalc = ClassObj()
    # Because of elipse syntax warning.
    pCalc = pCalc
  except:
    Err.raiseSyntaxError(Err.GlobioCalculationClassNotFound1,scriptLine,className)

  # Check the class methods.
  pProp = getattr(ClassObj,"doc")
  if pProp is None:
    Err.raiseSyntaxError(Err.InvalidGlobioCalculationClass1,scriptLine,className)
  pProp = getattr(ClassObj,"run")
  if pProp is None:
    Err.raiseSyntaxError(Err.InvalidGlobioCalculationClass1,scriptLine,className)
# 20201202
# def checkGlobioCalculationName(scriptLine):
#
#   # Set the class and import name.
#   className = getGlobioCalculationName(scriptLine)
#   importName = className
#
#   try:
#     # Import the GLOBIO code. 
#     pImport = import_module(importName)
#   except:
#     Err.raiseSyntaxError(Err.GlobioCalculationFileNotFound1,scriptLine,importName+".py")
#
#   # Get the class,
#   ClassObj = getattr(pImport,className)
#   if ClassObj is None:
#     Err.raiseSyntaxError(Err.GlobioCalculationClassNotFound1,scriptLine,className)
#
#   try:
#     # Create a class instance.
#     pCalc = ClassObj()
#     # Because of elipse syntax warning.
#     pCalc = pCalc
#   except:
#     Err.raiseSyntaxError(Err.GlobioCalculationClassNotFound1,scriptLine,className)
#
#   # Check the class methods.
#   pProp = getattr(ClassObj,"doc")
#   if pProp is None:
#     Err.raiseSyntaxError(Err.InvalidGlobioCalculationClass1,scriptLine,className)
#   pProp = getattr(ClassObj,"run")
#   if pProp is None:
#     Err.raiseSyntaxError(Err.InvalidGlobioCalculationClass1,scriptLine,className)

#-------------------------------------------------------------------------------
# Check if it's a valid globio calculation declaration.
# So if the argument declarations in the documentation are valid. 
# Does not check the actual arguments. 
def checkGlobioCalculationArgumentsFromDeclaration(scriptLine):
  # Get the class name.
  className = getGlobioCalculationName(scriptLine)
  # Get the class.
  ClassObj = getGlobioCalculationClass(scriptLine)
  # Create an instantie.
  pCalc = ClassObj()
  # Get the run documentation.
  doc = pCalc.doc()
  # No run documentation, so no arguments?
  if len(doc)==0:
    return
    
  # Check the run documentation.
  lines = Utils.strSplit(doc,"\n")
  for line in lines:
    # Create a temporary scriptline.
    tmpScriptLine = deepcopy(scriptLine)
    tmpScriptLine.line = line
    tmpScriptLine.lineNr = 0
    tmpScriptLine.scriptName = ""
    
    try:
      # Check if there is a IN or OUT.
      checkArgumentInOut(tmpScriptLine)
    except:
      Err.raiseSyntaxError(Err.GlobioCalculationInvalidDeclarationNoInOut1,None,className)
    
    # Remove the IN and OUT.
    tmpScriptLine.line = Utils.strAfter(tmpScriptLine.line," ")
    
    try:
      # Check the declaration.
      checkDeclaration(tmpScriptLine,None)       
    except:
      Err.raiseSyntaxError(Err.GlobioCalculationInvalidDeclaration1,None,className)
    
    # Check the type.
    typeName = getKeyword(tmpScriptLine)
    if not isType(typeName):
      Err.raiseSyntaxError(Err.GlobioCalculationInvalidDeclarationTypeNotFound2,None,className,typeName)

#-------------------------------------------------------------------------------
# Checks the list declaration.
# If the parentScript is not None, the there is also a check if the variable
# already is defined.
# Example: LIST INTEGER Test1 = var1|var2
def checkListDeclaration(scriptLine,parentScript):

  #Log.dbg("checkListDeclaration")
  
  # Is there no "="?
  if scriptLine.line.find("=") < 0:
    Err.raiseSyntaxError(Err.InvalidListDeclaration,scriptLine)

  # Add spaces around the "=".
  line = scriptLine.line.replace("="," = ")

  # Split the line.
  tokens = Utils.strSplit(line," ")

  #Log.dbg("checkListDeclaration "+str(tokens))
  
  # There must be at least 5 tokens.
  if len(tokens) < 5:
    Err.raiseSyntaxError(Err.InvalidListDeclaration,scriptLine)

  # 4-th token a "="?
  if tokens[3] != "=":
    Err.raiseSyntaxError(Err.InvalidListDeclaration,scriptLine)

  # Get the type and the var name.
  typeName = tokens[1]
  varName = tokens[2]
  
  # Get the fullname.
  varFullName = getVariableFullName(varName, parentScript)
  
  # Check the type and the fullName.
  checkTypeVariableName(typeName,varFullName,scriptLine)       

#-------------------------------------------------------------------------------
# Checks if a BEGIN_RUN and RUN etc. line contains a name too.
def checkRunableName(scriptLine):
  # No space?
  if scriptLine.line.find(" ")<0:
    # Get the keyword.
    keyword = getKeyword(scriptLine)
    # Show the correct error message.
    if keyword == "BEGIN_RUN":
      Err.raiseSyntaxError(Err.NoRunNameSpecified,scriptLine)
    elif keyword == "RUN":
      Err.raiseSyntaxError(Err.NoRunNameSpecified,scriptLine)
    elif keyword == "BEGIN_SCENARIO":
      Err.raiseSyntaxError(Err.NoScenarioNameSpecified,scriptLine)
    elif keyword == "RUN_SCENARIO":
      Err.raiseSyntaxError(Err.NoScenarioNameSpecified,scriptLine)
    elif keyword == "BEGIN_MODULE":
      Err.raiseSyntaxError(Err.NoModuleNameSpecified,scriptLine)
    elif keyword == "RUN_MODULE":
      Err.raiseSyntaxError(Err.NoModuleNameSpecified,scriptLine)

#-------------------------------------------------------------------------------
# Checks if the type and variable name are valid.
#
# Is a typeName is given than it is a declaration and the variable
# must not been declared already as global or private variable.
#
# Is typeName is None than it is an assignment and the variable
# must already been declared as global or private variable.
#
# Examples:
#   INTEGER Test1
#   Test1
def checkTypeVariableName(typeName,varFullName,scriptLine):

  # Check if the variable already exists or doesn't exists.
  if typeName is None:

    #----------------------------------------------------      
    # An assignment.
    #----------------------------------------------------      

    # The variable must already exist.
    if not GLOB.variables.exists(varFullName):
      varName = getVariableNameFromFullName(varFullName)
      Err.raiseSyntaxError(Err.VariableNotFound1,scriptLine,varName)
  else:
    #Log.dbg("VariableList.checkVariableName - None")

    #----------------------------------------------------      
    # A declaration.
    #----------------------------------------------------      

    # Check the type.
    if not isType(typeName):
      Err.raiseSyntaxError(Err.TypeNotFound1,scriptLine,typeName)

    # The variable may not already exist.
    if GLOB.variables.exists(varFullName):
      varName = getVariableNameFromFullName(varFullName)
      Err.raiseSyntaxError(Err.VariableAlreadyExists1,scriptLine,varName)

#-------------------------------------------------------------------------------
# Checks if the variable name is valid.
def checkVariableName(varName,scriptLine):

  # Check if the variable name is "=".
  if varName == "=":
    Err.raiseSyntaxError(Err.InvalidVariableName1,scriptLine,varName)

  # Check if the variable name starts with a "$".
  if varName[0] == "$":
    Err.raiseSyntaxError(Err.InvalidVariableName1,scriptLine,varName)

  # Check if the variable name contains a ".".
  if varName.find(".")>=0:
    Err.raiseSyntaxError(Err.InvalidVariableName1,scriptLine,varName)

  # Check if the variable name is a constant, type or reserved keyword.
  if GLOB.constants.exists(varName):
    Err.raiseSyntaxError(Err.InvalidVariableNameConstant1,scriptLine,varName)

  if isReservedWord(varName):
    Err.raiseSyntaxError(Err.InvalidVariableNameReservedWord1,scriptLine,varName)

#-------------------------------------------------------------------------------
# Copy the simulateIsCreated flag from the reference variables
# to the argument variables.
def copyReferenceVariablesSimulateIsCreated(referenceVariables,variableFullNames):
  index = 0
  for varFullName in variableFullNames:
    # Get the correspnding refvar.
    pRefVar = referenceVariables[index]
    # Not None?
    if not pRefVar is None:
      # Get the variable.
      pVar = GLOB.variables[varFullName]
      # Update the simulateIsCreated flag.
      pVar.simulateIsCreated = pRefVar.simulateIsCreated
    index += 1

#-------------------------------------------------------------------------------
# Returns a list with arguments. So all blocks between "(" and ")" and
# separated by semicolons.
# Returns a list of strings.
# Can also return an empty list.
# Check the arguments first with checkArguments.
#
# Processes:
#   BEGIN_SCENARIO Scenario_new(IN INFEAT LandUseCov,OUT INTEGER Year)
# And:
#    RUN_SCENARIO Scenario_new($LandUseCov,$Year)
#
# Example return values:
#   $LandUseCov
#   30min
#   123
def getArgumentsAsStrings(scriptLineOrString):
  args = []
  
  # A string?
  # 20201118
  #if isinstance(scriptLineOrString,basestring):
  if Utils.isString(scriptLineOrString):
    line = scriptLineOrString
  else:
    line = scriptLineOrString.line
  
  # No brackets?    
  if (line.find("(")<0) and (line.find(")")<0):
    return args

  # Get the part between the brackets.  
  argsStr = Utils.strAfter(line,"(")
  argsStr = Utils.strBefore(argsStr,")")
  
  # Split in parts.
  args = Utils.strSplit(argsStr,",")

  # Trim args.
  for i in range(len(args)):
    args[i] = args[i].strip()
  
  return args

#-------------------------------------------------------------------------------
# Returns the arguments of a declaration.
# Returns a list with created variables.
def createArgumentVariablesFromDeclaration(scriptLine,parentScript):
  args = VariableList()
  
  # Get the arguments.
  strArgs = getArgumentsAsStrings(scriptLine)
  
  # Loop through the arguments.
  for strArg in strArgs:
    
    # Create a temporary scriptline.
    tmpScriptLine = deepcopy(scriptLine)
    tmpScriptLine.line = strArg
    
    # Get the argument type (IN or OUT).
    argType = Utils.strBefore(tmpScriptLine.line," ")

    # Remove the IN and OUT.
    tmpScriptLine.line = Utils.strAfter(tmpScriptLine.line," ")
    
    # Get the type and var.
    typeName,varName = getDeclarationTypeAndVariableName(tmpScriptLine)
    
    # Create a variable.
    pVar = Variable(varName,"",typeName,parentScript,scriptLine)

    # Mark that it is an argument variable.
    pVar.isArgument = True

    # Set the argument type.
    if argType.upper()=="IN":
      pVar.isInput = True
    else:
      pVar.isInput = False

    # Add the variable.
    args.add(pVar)
  return args  

#-------------------------------------------------------------------------------
# Gets the arguments of a list (actualy the list variable).
# LIST STRING FILE = A|B|C 
def getArgumentsFromList(scriptLine,parentScript):
  args = VariableList()
  # Return the part behind the space.
  command = Utils.strAfter(scriptLine.line," ").strip()
  # Create a temporary scriptline.
  tmpScriptLine = deepcopy(scriptLine)
  tmpScriptLine.line = command
  # Get the type and var.
  typeName,varName = getDeclarationTypeAndVariableName(tmpScriptLine)
  # Create a variable.
  pVar = Variable(varName,"",typeName,parentScript,scriptLine)
  # Add the variable.
  args.add(pVar)
  return args  

#-------------------------------------------------------------------------------
# Returns a varName of an assignment.
# First check with isAssginment
# Example:
#   Test2 = 123
#   Test3=456
def getAssignmentVariableName(scriptLine):
  # Get the name.
  return Utils.strBefore(scriptLine.line,"=").strip()

#-------------------------------------------------------------------------------
# Get the value in the assignment.
# Example:
#   INTEGER Test1
#   INTEGER Test2 = 123
#   INTEGER Test3=456
def getAssignmentValue(scriptLine):
    # Get the value.
    return Utils.strAfter(scriptLine.line,"=").strip()

#-------------------------------------------------------------------------------
# Returns a tuple with typeName and varName.
# TypeName is None there is no type.
# First check with checkDeclaration.
# So:
#   typeName,varName = self.getDeclarationTypeAndVariableName(...)
# Example:
#   INTEGER Test1
#   INTEGER Test2 = 123
#   INTEGER Test3=456
def getDeclarationTypeAndVariableName(scriptLineOrString):
  # A string?
  # 20201118
  #if isinstance(scriptLineOrString,basestring):
  if Utils.isString(scriptLineOrString):
    line = scriptLineOrString
  else:
    line = scriptLineOrString.line
  # Add spaces around the "=".
  line = line.replace("="," = ")
  # Split the line in parts.
  tokens = Utils.strSplit(line," ")
  # There is a type.
  typeName = tokens[0]
  varName = tokens[1]
  return (typeName,varName)  

#-------------------------------------------------------------------------------
# Returns a VariableList.
def createGlobioCalculationArgumentVariablesFromDeclaration(scriptLine,parentScript):

  args = VariableList()

  # Get the class.
  ClassObj = getGlobioCalculationClass(scriptLine)
  # Create a instance.
  pCalc = ClassObj()
  # Get the run documentation.
  doc = pCalc.doc()
  # No run documentation, so no arguments?
  if len(doc)==0:
    pass
  else:
    # Split the run documentation in lines.
    lines = Utils.strSplit(doc,"\n")
    # Loop through the lines.
    for line in lines:
      # Create a temporary scriptline.
      tmpScriptLine = deepcopy(scriptLine)
      tmpScriptLine.line = line
      tmpScriptLine.lineNr = 0
      tmpScriptLine.scriptName = ""

      # Get the argument type (IN or OUT).
      argType = Utils.strBefore(tmpScriptLine.line," ")

      # Remove the IN and OUT.
      tmpScriptLine.line = Utils.strAfter(tmpScriptLine.line," ")
    
      # Get the type and var.
      typeName,varName = getDeclarationTypeAndVariableName(tmpScriptLine)

      # Create a variable.
      pVar = Variable(varName,"",typeName,parentScript,scriptLine)

      # Set the variable is an argument.
      pVar.isArgument = True
  
      # Set the argument type.
      if argType.upper()=="IN":
        pVar.isInput = True
      else:
        pVar.isInput = False
      
      # Add the variable.
      args.add(pVar)
  return args  

#-------------------------------------------------------------------------------
# Returns the GlobioCalculation name.
# So the part before the "(".
def getGlobioCalculationName(scriptLine):
  # Check if there is no "(".
  if scriptLine.line.find("(")<0:
    # Use the whole command.
    name = scriptLine.line
  else:
    # Return the part before the "(".
    name = Utils.strBefore(scriptLine.line,"(").strip()
  return name

#-------------------------------------------------------------------------------
# Returns the GlobioCalculation class.
# First check with checkGlobioCalculationCall if it is a valid class.
def getGlobioCalculationClass(scriptLine):
  # Get the class name.
  className = getGlobioCalculationName(scriptLine)
  # Get the class.
  return getGlobioCalculationClassByName(className)

#-------------------------------------------------------------------------------
# Returns the GlobioCalculation class.
# First check with checkGlobioCalculationCall if it is a valid class.
def getGlobioCalculationClassByName(name):

  # Import the GLOBIO calcuation module. 
  pImport = importGlobioCalculationFile(name,"")

  # Get the class,
  ClassObj = getattr(pImport,name)

  return ClassObj
# 20201202
# def getGlobioCalculationClassByName(name):
#
#   # Set import name.
#   importName = name
#  
#   # Import the GLOBIO code. 
#   pImport = import_module(importName)
#
#   # Get the class,
#   ClassObj = getattr(pImport,name)
#
#   return ClassObj
 
#-------------------------------------------------------------------------------
# Returns the keyword in capitals.
def getKeyword(scriptLine):
  # Check if there is a space.
  if scriptLine.line.find(" ")<0:
    # Return the whole line.
    return scriptLine.line.upper()
  else:
    # Return the part before the space.
    return Utils.strBefore(scriptLine.line," ").strip().upper()
 
#-------------------------------------------------------------------------------
# Returns the name (is variable) of the list declaration in capitals.
def getListName(scriptLine):
  # Return the part behind the 1st space.
  command = Utils.strAfter(scriptLine.line," ").strip()
  # Return the part behind the 2nd space.
  command = Utils.strAfter(command," ").strip()
  # Return the part before the =.
  name = Utils.strBefore(command,"=").strip().upper()
  return name

#-------------------------------------------------------------------------------
# Returns the fullname of the list. So the parent script name included.
def getListFullName(listName,parentScript):
  # Use the same method as before variables.
  return getVariableFullName(listName,parentScript)

#-------------------------------------------------------------------------------
# Returns a tuple with typeName and varName.
# So:
#   typeName,varName = self.getListTypeAndVariableName(...)
# Example:
#   LIST INTEGER Test1
#   LIST INTEGER Test2 = 123
#   LIST INTEGER Test3=456
def getListTypeAndVariableName(scriptLine):
  # Add spaces around the =.
  line = scriptLine.line.replace("="," = ")
  # Split the line in parts.
  tokens = Utils.strSplit(line," ")
  # Get the type and the var.
  typeName = tokens[1]
  varName = tokens[2]
  return (typeName,varName)  

#-------------------------------------------------------------------------------
# Returns a tupel with (refName,searchName) with the first
# reference name and the search name.
# Returns from "aaa$X;bbb": ("X","$X;") 
# Returns (None,None) if np reference is found.
def getReferenceNameSearchName(strValue):
  if not hasReference(strValue):
    return (None,None)
  else:
    # Get the reference name.
    refName = Utils.strAfter(strValue,"$")
    # Is there a ";"?
    if refName.find(";")>=0:
      # Change the reference name.
      refName = Utils.strBefore(refName,";")
      # Set the full name.
      searchName = "$"+refName + ";"
    else:
      # Set the full name.
      searchName = "$"+refName
    return (refName,searchName)

#-------------------------------------------------------------------------------
# Returns a list with reference variables which are referenced in the values.
# If a value doesn't contain reference variables a None is returned.
# No reference variables used in concatenations will be returned.
def getReferenceVariablesFromValues(values,parentScript):
  refVars = []

  #Log.dbg("AU.getReferenceVariablesFromValues - %s" % values)

  # Loop through the values.  
  for value in values:
    # Get the reference name and search name.
    refName,searchName = getReferenceNameSearchName(value)
    
    #Log.dbg("AU.getReferenceVariablesFromValues - %s" % value)
    #Log.dbg("AU.getReferenceVariablesFromValues - %s" % refName)
    #Log.dbg("AU.getReferenceVariablesFromValues - %s" % searchName)

    # Is there a reference variable?
    if not refName is None:
      #Log.dbg("AU.getReferenceVariablesFromValues - 111111111111111")
      # Is the value just a variable name.
      if value.replace(searchName,"")=="":
        # Get variable.
        pVar = getVariable(refName,parentScript)
        refVars.append(pVar)
      else:
        refVars.append(None)
    else:
      refVars.append(None)
  return refVars
     
#-------------------------------------------------------------------------------
# Returns from a BEGIN_RUN, RUN etc. line the name in capitals.
def getRunableName(scriptLine):
  # Return the part behind the space.
  command = Utils.strAfter(scriptLine.line," ").strip()
  # Check if there us no (.
  if command.find("(")<0:
    # Use the whole command.
    name = command.upper()
  else:
    # Return the part before the (.
    name = Utils.strBefore(command,"(").strip().upper()
  return name

#-------------------------------------------------------------------------------
# Get the variable.
def getVariable(varName,parentScript):

  # Get the full PRIVATE name.
  varFullName = getVariableFullName(varName,parentScript)

  # Not found and the parentscript is a List?
  if not GLOB.variables.exists(varFullName) and parentScript.isList():
    # Loop while no list.
    while True:
      # Set the list parent as parentcsript.
      parentScript = parentScript.parent
      # No list?
      if not parentScript.isList():
        break
    # Get the full PRIVATE name.
    varFullName = getVariableFullName(varName,parentScript)

  # Not found?
  if not GLOB.variables.exists(varFullName):
    # Get the full GLOBAL name.
    varFullName = getVariableFullName(varName,None)

  # Does the variable exist?
  if GLOB.variables.exists(varFullName):
    pVar = GLOB.variables[varFullName]
  else:
    pVar = None
  return pVar

#-------------------------------------------------------------------------------
# Returns the fullname of the variable. So parent script name included.
def getVariableFullName(varName,parentScript):
  if parentScript is None:
    return getVariableGlobalName(varName)
  elif parentScript.isGlobalScript():
    return getVariableGlobalName(varName)
  else:
    return parentScript.name+"."+varName

#-------------------------------------------------------------------------------
def getVariableNameFromFullName(varFullName):
  return Utils.strAfter(varFullName,".")

#-------------------------------------------------------------------------------
def getVariableGlobalName(varName):
  return "GLOBAL."+varName

#-------------------------------------------------------------------------------
# Returns if the strValue contains a reference (so has a $).
def hasReference(strValue):
  # A reference to other variables?
  if strValue.find("$")>=0:
    return True
  else:
    return False
 
#-------------------------------------------------------------------------------
# Imports a calculation file based on the classname.
# Returns the imported module.
def importGlobioCalculationFile(className,scriptLine):
  # Check global calculation paths.
  if len(GLOB.calculationPaths) == 0:
    Err.raiseGlobioError(Err.NoGlobioCalculationPathsSpecified)
  # Loop calculation paths.
  pImport = None
  for path in GLOB.calculationPaths:
    try:
      # Construct import name.
      importName = path.strip(".") + "." + className
      # Import the GLOBIO code. 
      pImport = import_module(importName)
      break
    except:
      #print(importName)
      pass
  # Calculation file not found.
  if pImport is None:  
      Err.raiseSyntaxError(Err.GlobioCalculationFileNotFound1,scriptLine,className+".py")
  return pImport

#-------------------------------------------------------------------------------
# Returns True if a variable is being set So if there are minimal 3
# tokens and the second token is a "=".
# There is no check on the validity of the variable name.
# Example:
#   Test1 = 123
#   Test1=123
def isAssignment(scriptLine):
  # Add spaces around the =.
  line = scriptLine.line.replace("="," = ")
  tokens = Utils.strSplit(line," ")
  if len(tokens)>=3:
    if tokens[1]=="=":
      return True
    else:
      return False
  else:
    return False
  
#-------------------------------------------------------------------------------
# Returns True there is a variable declaration. So if there are 2
# tokens and the first token is a type.
# There is no check on the validity of the variable name.
# Example:
#   INTEGER Test1
def isDeclaration(scriptLine):
  # Is there a "="?
  if scriptLine.line.find("=") >= 0:
    return False
  # Split the line.
  tokens = Utils.strSplit(scriptLine.line," ")
  # 2 tokens?
  if len(tokens)==2:
    if isType(tokens[0]):
      return True
    else:
      return False
  else:
    return False

#-------------------------------------------------------------------------------
# Returns True if there is a variable declaration or an assignment. So
# if there are at least 4 tokens and the 3rd token is a "=".
# There is no check on the validity of the variable name.
# Example:
#   INTEGER Test1 = 123
#   INTEGER Test1=123
#   INTEGER Test1=aaa bbb ccc ddd
#   Test1 = 123
#   Test1=123
#   Test1 = aaa bbb ccc ddd
def isDeclarationOrAssignment(scriptLine):
  # Add spaces around the =.
  line = scriptLine.line.replace("="," = ")
  # Split the line.
  tokens = Utils.strSplit(line," ")
  if len(tokens)<3:
    # < 3. 
    return False
  elif len(tokens)==3:
    # 3. 
    if tokens[1]=="=":
      return True
    else:
      return False
  else:
    # 4 or more. 
    if tokens[1]=="=":
      return True
    elif tokens[2]=="=":
      if isType(tokens[0]):
        return True
      else:
        return False
    else:
      return False

#-------------------------------------------------------------------------------
# Returns True if there is a variable declaration and an assignment. So
# if there are at least 4 tokens and the 3rd token is a "=".
# There is no check on the validity of the variable name.
# Example:
#   INTEGER Test1 = 123
#   INTEGER Test1=123
#   INTEGER Test1=aaa bbb ccc ddd
def isDeclarationAndAssignment(scriptLineOrString):
  # A string?
  # 20201118
  #if isinstance(scriptLineOrString,basestring):
  if Utils.isString(scriptLineOrString):
    line = scriptLineOrString
  else:
    line = scriptLineOrString.line
  # Add spaces around the =.
  line = line.replace("="," = ")
  # Split the line.
  tokens = Utils.strSplit(line," ")
  if len(tokens)<4:
    # < 4. 
    return False
  else:
    # 4 or more. 
    if tokens[2]=="=":
      if isType(tokens[0]):
        return True
      else:
        return False
    else:
      return False
  
#-------------------------------------------------------------------------------
# Returns True if there is a Globio calculation call. So if the 
# line begins with GLOBIO_
def isGlobioCalculationCall(scriptLine):
  if scriptLine.line.startswith("GLOBIO_"):
    return True
  else:
    return False

#-------------------------------------------------------------------------------
def isInclude(scriptLine):
  keyword = getKeyword(scriptLine)
  if keyword == "INCLUDE":
    return True
  else:
    return False

#-------------------------------------------------------------------------------
def isList(scriptLine):
  keyword = getKeyword(scriptLine)
  if keyword == "LIST":
    return True
  else:
    return False

#-------------------------------------------------------------------------------
# Returns True if there is a list declaration and an assignment. So
# if there are at least 4 tokens and the 3rd token is a "=".
# There is no check on the validity of the variable name.
def isListDeclarationAndAssignment(scriptLine):
  
  # Get the keyword.
  keyword = getKeyword(scriptLine)

  # No list?
  if keyword!="LIST":
    return False
  
  # Get the var declaration.
  varDeclaration = Utils.strAfter(scriptLine.line," ")
  
  # No valid declaration and assignment.
  if not isDeclarationAndAssignment(varDeclaration):
    return False
  else:
    return True

#-------------------------------------------------------------------------------
def isMsgCall(scriptLine):
  if scriptLine.line.find("(")<0:
    return False
  else:
    keyword = Utils.strBefore(scriptLine.line,"(").upper()
    if keyword == "MSG":
      return True
    else:
      return False

#-------------------------------------------------------------------------------
def isReservedWord(keyword):
  if keyword.upper() in GLOB.reservedWords:
    return True
  else:
    return False

#-------------------------------------------------------------------------------
def isRun(scriptLine):
  keyword = getKeyword(scriptLine)
  if (keyword=="RUN") or \
     (keyword=="RUN_SCENARIO") or \
     (keyword=="RUN_MODULE"):
    return True
  else:
    return False

#-------------------------------------------------------------------------------
def isType(typeName):
  if typeName in GLOB.types:
    return True
  else:
    return False

#-------------------------------------------------------------------------------
# Replace refences ($name) in the values of the list by door the strValue of
# the referenced variable.
# OK
def resolveReferencesInValues(strValues,refParent,scriptLine):
  
  resolvedValues = []

  # Loop through the values.
  for strValue in strValues:
    #Log.dbg("resolveReferencesInValues - strValue - "+str(strValue))
    # Get the first reference name and search name.
    refName, searchName = getReferenceNameSearchName(strValue)
    #Log.dbg("resolveReferencesInValues - refName "+refName)
    # Do while there still are references.
    while refName is not None:
      
      # Get the variable.
      pRefVar = getVariable(refName,refParent)

      # Variable not found?
      if pRefVar is None:
        Err.raiseSyntaxError(Err.VariableNotFound1,scriptLine,refName)
        
      # Replace the reference link by the strValue of the
      # reference variable.
      strValue = strValue.replace(searchName,pRefVar.strValue)

      # Get the next reference name and search name.
      refName, searchName = getReferenceNameSearchName(strValue)
      
    #Log.dbg("resolveReferencesInValues - resolved strValue - "+str(strValue))
    resolvedValues.append(strValue) 

  return resolvedValues    

#-------------------------------------------------------------------------------
def runGlobioCalculation(calcName,*args):

  # Get the class,
  ClassObj = getGlobioCalculationClassByName(calcName)

  # Create a class instance.
  pCalc = ClassObj()

  # Run.
  pCalc.run(*args)

#-------------------------------------------------------------------------------
# Set the values of the argument variables.
# The callValues may not contain any references.
# Also checks the values on base of the argument type IN or OUT.
def updateArgumentsWithValues(declArgVarNames,callValues,scriptLine):
  
  # First check if the number of call arguments are equal to the
  # declaration.
  if len(declArgVarNames)!=len(callValues):
    Err.raiseSyntaxError(Err.InvalidNumberOfArgumentsInCall, scriptLine) 

  # Set the values of the argument variables.
  index = 0
  for varFullName in declArgVarNames:
    # Get the variable.
    pVar = GLOB.variables[varFullName]
    # Get the corresponding value of the call.
    strValue = callValues[index]
    # Check on references.
    if hasReference(strValue):
      Err.raiseSyntaxError(Err.NoValidVariableValueReference1,scriptLine,pVar.name)
    # Update the string value of the variable.
    pVar.setStrValue(strValue,None,scriptLine)
    # Increment the index.
    index += 1
  
