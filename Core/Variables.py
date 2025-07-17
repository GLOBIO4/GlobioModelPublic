# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 22 mar 2017, ES, ARIS B.V.
#           - Version 4.0.5
#           - parseStrValue - Log.updateLogFileDirectory added.
#           17 nov 2020, ES, ARIS B.V.
#           - Version 4.0.16
#           - Variable.parseStrValue modified. When parsing OUTDIR the full 
#             path is created if not exists and need to be created because of
#             the GLOB.createOutDir flag.
#-------------------------------------------------------------------------------

import os

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Common.Utils as UT
import GlobioModel.Core.AppUtils as AU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Variable(object):
  name = ""
  fullName = ""
  description = ""
  type = None                        # The type.
  strValue = None                    # The value as string, so not evaluated.
  parsedValue = None                 # The geparsed value. So refs are replaced.
  scriptLine = None                  # The script line with the declaration.
  
  # The parent script where the declaration takes place. Can also be None.
  parent = None
  # The name of a eventually linked python variable.
  pythonName = None
  
  # Is True when a variable is an argument. Only these variables will be tested
  # if exists or not-exists, dependent from the argument type IN/OUT. 
  isArgument = False
  
  # Is True when variable is an IN argument (is used in: parseStrValue()).
  # Is only used when isArgument=True.
  isInput = True                      
  
  runCheck = False
  simulateIsCreated = False
  
  #-------------------------------------------------------------------------------
  # If parent is None a global variable is used.
  def __init__(self,name,description,typeName,parent,scriptLine):
    self.name = name
    self.description = description
    self.type = GLOB.types[typeName]
    self.scriptLine = scriptLine
    self.parent = parent
    self.pythonName = None
    self.isArgument = False
    self.isInput = True                      
    self.runCheck = False
    self.simulateIsCreated = False

    if parent is None:
      self.fullName = AU.getVariableGlobalName(name)
    else:
      if parent.isGlobalScript():
        self.fullName = AU.getVariableGlobalName(name)
      else:
        self.fullName = AU.getVariableFullName(name,parent)

  #-------------------------------------------------------------------------------
  # Check the strValue type.
  # When the value of a variable is set, the refParent must be known.
  # Because, a check must be done if a $DIR exist and if of the correct type.
  def checkStrValue(self,strValue,refParent,scriptLine):
    #Log.dbg("Variable.checkStrValue - "+strValue)
    self.parseStrValue(strValue,refParent,scriptLine)

  #-------------------------------------------------------------------------------
  def isSameVariable(self,otherVar):
    fullName1 = AU.getVariableFullName(self.name,self.parent)
    fullName2 = AU.getVariableFullName(otherVar.name,otherVar.parent)
    return (fullName1==fullName2)

  #-------------------------------------------------------------------------------
  # Get the first refname and the searchname.
  # When $a a and $a is returned.
  # When $a; a and $a; is returned.
  # When $a;$b a and $a; is returned. 
  def getRefNameSearchName(self,strValue):
    # Get the reference name.
    refName = UT.strAfter(strValue,"$")
    # Is there a ";"?
    if refName.find(";")>=0:
      # Modify the reference name.
      refName = UT.strBefore(refName,";")
      # Set the full name.
      searchName = "$"+refName + ";"
    else:
      # Set the full name.
      searchName = "$"+refName
    return (refName,searchName)

  #-------------------------------------------------------------------------------
  # Returns if it is a value with multiple references.
  # So:  $indir;$filename     True
  # So:  $indir               False
  # So:  aaa$indir            False
  def isConcatenationValue(self,strValue):
    # Get the searchname, so $a of $a;.
    _, searchName = self.getRefNameSearchName(strValue)
    # searchname the same as the strValue, then there is only 1.
    if searchName == strValue:
      return False
    else:
      return True

  #-------------------------------------------------------------------------------
  # Parse the value and return it. References will be resolved.
  def parseStrValue(self,strValue,refParent,scriptLine):

    #Log.dbg("Variable.parseStrValue")

    # Is the value not set?
    if strValue is None:
      return None
      
    # No references to other variables?
    if strValue.find("$")<0:
      
      #---------------------------------------------------------
      # No reference ($name).
      #---------------------------------------------------------

      #Log.dbg("Variable.parseStrValue No Ref")

      # Check if it is a valid value for the type.
      self.type.checkStrValue(strValue,self.name,scriptLine)
    else:

      #---------------------------------------------------------
      # A reference ($name).
      #---------------------------------------------------------

      #Log.dbg("Variable.parseStrValue Ref")

      # Check the refparent.
      if refParent is None:
        Err.raiseSyntaxError(Err.InvalidVariableDeclaration,scriptLine,self.name)
      
      # See if there is a concatenation.
      concatenation = self.isConcatenationValue(strValue)

      # Is there a concatenation?
      if concatenation:
        # Can a concatenation been used?
        if not self.type.canAssignedByConcat():
          Err.raiseSyntaxError(Err.VariableTypeNotAllowedConcatenation2,scriptLine,self.name,self.type.name)
        
      # Replace the references.
      while strValue.find("$")>=0:
  
        # Get the reference name.
        refName,searchName = self.getRefNameSearchName(strValue)

        #----------------------------------------------------------------
        # Check the gerefereerde variable.
        #----------------------------------------------------------------

        #Log.dbg("Variable.parseStrValue RefName,RefParent - %s %s" % (refName,refParent))
        #Log.dbg("Variable.parseStrValue RefParent - %s %s" % (refParent.name,refParent.fileName))
  
        pRefVar = AU.getVariable(refName,refParent)
        
        #Log.dbg("Variable.parseStrValue pRefVar FOUND? %s " % pRefVar)
        
        if not pRefVar is None:

          #Log.dbg("Variable.parseStrValue pRefVar not None")
          
          # Recursion?
          if self.isSameVariable(pRefVar):
            # Declaration?
            if AU.isDeclarationAndAssignment(scriptLine):
              Err.raiseSyntaxError(Err.InvalidVariableDeclarationRecursive,scriptLine)

          # Do we have a concatenation?
          if concatenation:
            # Refvar not allowed for concatenation?
            if not pRefVar.type.canUsedInConcat():
              Err.raiseSyntaxError(Err.VariableTypeCanNotUsedInConcatenation2,scriptLine,pRefVar.name,pRefVar.type.name)
            else:
              # Recursion?
              if self.isSameVariable(pRefVar):
                refValue = self.strValue
              else:
                refValue = pRefVar.updateParsedValue(refParent,scriptLine)
          else:  
            # No concatenation, check the type.
            if not pRefVar.type.canAssignTo(self.type):
              Err.raiseSyntaxError(Err.InvalidVariableReferenceType1,scriptLine,refName)
            else:
              # Recursion?
              if self.isSameVariable(pRefVar):
                refValue = self.strValue
              else:
                refValue = pRefVar.updateParsedValue(refParent,scriptLine)
        else:
          # Does the constant exist?
          if GLOB.constants.exists(refName):
            pRefConst = GLOB.constants[refName]
            # Do we have a concatenation?
            if concatenation:
              # RefConst not allowd for concatenation?
              if not pRefConst.type.canUsedInConcat():
                Err.raiseSyntaxError(Err.ConstantTypeCanNotUsedInConcatenation2,scriptLine,pRefConst.name,pRefConst.type.name)
              else:
                # 20210104
                # TODO: Warning, statement has no effect. Commented out.
                #pRefConst.value
                pass
            else:
              # No concatenation, check the type.
              if not pRefConst.type.canAssignTo(self.type):
                Err.raiseSyntaxError(Err.InvalidConstantReferenceType1,scriptLine,refName)
              else:
                refValue = pRefConst.value
          else:
            Err.raiseSyntaxError(Err.VariableOrConstantNotFound1,scriptLine,refName)

        #Log.dbg("Variable.parseStrValue - searchName - "+str(searchName))
        #Log.dbg("Variable.parseStrValue - strValue - "+str(strValue))
        #Log.dbg("Variable.parseStrValue - refValue - "+str(refValue))

        # Replace the reference with the reference value.
        strValue = strValue.replace(searchName,str(refValue))

    # Is the variable an argument?
    if self.isArgument:
      # Are we doing a run check?
      if self.runCheck:
        # Is it an input variable?
        if self.isInput:
          # Don't really check the existance, but first look at 
          # the simulateIsCreated flag.
          if self.simulateIsCreated:
            pass
          else:
            # Perform original test.
            self.type.checkExists(strValue,scriptLine)
        else:
          # Do check if aleady exists.
          self.type.checkNotExists(strValue,scriptLine)
      else:
        # Is it an input variable?
        if self.isInput:
          self.type.checkExists(strValue,scriptLine)
        else:
          self.type.checkNotExists(strValue,scriptLine)

    # Set the parsed value. Parse value according to the type.
    parsedValue = self.type.parseStrValue(strValue)

    # Setting the special variable OUTDIR?
    if self.name.upper() == "OUTDIR":

      # 20201117
      # Create the OutDir if not exists and need to be created.
      # Do we have a value?
      if parsedValue != "":
        # Does the OutDir not already exist and must create?
        if (not os.path.isdir(parsedValue)) and (GLOB.createOutDir):
          # The create the full OutDir.
          os.makedirs(parsedValue)

      # Update the location of the log file.
      Log.updateLogFileDirectory(parsedValue,True)

    # Return the parsed value.
    return parsedValue

  #-------------------------------------------------------------------------------
  # Sets the string value and checks the value.
  # When an error occurs the linenumber will be shown of the given scriptline.
  # If scriptline = None, then the linenumber of the declaration is shown.
  def setStrValue(self,strValue,refParent,scriptLine=None):

    # No scriptLine?
    if scriptLine is None:
      scriptLine = self.scriptLine
      
    # Check the strValue.    
    if strValue is None:
      Log.dbg("Variable.setStrValue - strValue = None!!!")
      return
    
    # Force a string.
    strValue = str(strValue)

    #Log.dbg("Variable.setStrValue - strValue = " + str(strValue))
    
    # Check the strValue type, $ref and $ref type.
    # and op recursie.
    self.checkStrValue(strValue,refParent,scriptLine)
    
    # Set the string value.
    self.strValue = strValue
    
    # Update a the corresponding GLOBAL python variable, if exist.
    self.updatePythonVariable()

  #-------------------------------------------------------------------------------
  def updateParsedValue(self,refParent,scriptLine):
    self.parsedValue = self.parseStrValue(self.strValue,refParent,scriptLine)
    return self.parsedValue

  #-------------------------------------------------------------------------------
  # Update a corresponding GLOBAL python variable if exist.
  def updatePythonVariable(self):
    # Is there a global variable?
    if (self.parent is None) and (self.pythonName is not None):
      value = self.parseStrValue(self.strValue,None,None)
      # Update the python variable.
      setattr(GLOB,self.pythonName,value)
        
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class VariableList(dict):

  list = []

  #-------------------------------------------------------------------------------
  def __init__(self):
    super(VariableList,self).__init__()
    self.list = []

  #-------------------------------------------------------------------------------
  # Override because of uppercase keys/names.
  def __getitem__(self,fullName):
    return super(VariableList,self).__getitem__(fullName.upper())

  #-------------------------------------------------------------------------------
  # Override because of uppercase "name in variables".
  def __contains__(self, fullName):
    return super(VariableList,self).__contains__(fullName.upper())

  #-------------------------------------------------------------------------------
  def __iter__(self):
    return iter(self.list)

  #-------------------------------------------------------------------------------
  def __setitem__(self,fullName,value):
    super(VariableList,self).__setitem__(fullName.upper(),value)
    self.list.append(fullName.upper())

  #-------------------------------------------------------------------------------
  def add(self,variable):
    
    # Add the the variable.
    self[variable.fullName.upper()] = variable

  #-------------------------------------------------------------------------------
  def addGlobalVar(self,varName,description,typeName,strValue,scriptLine,pythonName=None):
    
    # Check if the variable name is valid.
    AU.checkVariableName(varName,scriptLine)

    # Get the fullname.
    varFullName = AU.getVariableGlobalName(varName)
    
    # Check if the type and variable name is valid.
    # If typeName is given then it is a declaration and the variable
    # must not already been declarated as global or private variable.
    # If typeName is None then it is an assignment and the variable
    # should already been declarated as global or private variable.
    AU.checkTypeVariableName(typeName,varFullName,scriptLine)

    # Create the variable without parent.
    pVar = Variable(varName,description,typeName,None,scriptLine)

    # Set the pythonName.
    pVar.pythonName = pythonName
                  
    # Set the value.
    pVar.setStrValue(strValue,None,scriptLine)        
    
    # Add the variable.
    self.add(pVar)

  #-------------------------------------------------------------------------------
  # Adds variables of an other list.
  def addList(self,variableList):
    for varFullName in variableList:
      self[varFullName.upper()] = variableList[varFullName]

  #-------------------------------------------------------------------------------
  def exists(self,fullName):
    return fullName in self

  #-------------------------------------------------------------------------------
  def keys(self):
    return self.list

  #-------------------------------------------------------------------------------
  def values(self):
    v = []
    for k in self.list:
      v.append(self[k])
    return v

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  pass
  # import Globio4TestRun
  # Globio4TestRun.globio4TestRun()
