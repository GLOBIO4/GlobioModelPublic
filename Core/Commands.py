# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************

#-------------------------------------------------------------------------------
# Modified: -
#-------------------------------------------------------------------------------

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Common.Utils as UT
import GlobioModel.Core.AppUtils as AU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Command(object):
  # Is used for binding to the runables. 
  name = ""
  
  # A variable or a runable: Run, Scenario, Module, List.
  commandObj = None

  # The parent script in which the call resides.
  # This is therefore the source for private variables. 
  # Is the parent a list, then the parent of the List will be used.
  parent = None
  
  # The line with the call.
  scriptLine = None
  
  #-------------------------------------------------------------------------------
  def __init__(self,name,parent,scriptLine):
    self.name = name
    self.commandObj = None
    self.parent = parent
    self.scriptLine = scriptLine

  #-------------------------------------------------------------------------------
  def isGlobioCalculation(self):
    if self.scriptLine.line.startswith("GLOBIO_"):
      return True
    else:
      return False

  #-------------------------------------------------------------------------------
  def isList(self):
    if AU.isListDeclarationAndAssignment(self.scriptLine):
      return True
    else:
      return False
    
  #-------------------------------------------------------------------------------
  def isModule(self):
    keyword = AU.getKeyword(self.scriptLine)
    if keyword == "RUN_MODULE":
      return True
    else:
      return False

  #-------------------------------------------------------------------------------
  def isMsg(self):
    if AU.isMsgCall(self.scriptLine):
      return True
    else:
      return False

  #-------------------------------------------------------------------------------
  def isRun(self):
    keyword = AU.getKeyword(self.scriptLine)
    if keyword == "RUN":
      return True
    else:
      return False

  #-------------------------------------------------------------------------------
  def isScenario(self):
    keyword = AU.getKeyword(self.scriptLine)
    if keyword == "RUN_SCENARIO":
      return True
    else:
      return False

  #-------------------------------------------------------------------------------
  def isVariable(self):
    if AU.isDeclarationOrAssignment(self.scriptLine):
      return True
    else:
      return False

  #-------------------------------------------------------------------------------
  # Run the MSG commando.
  def msg(self,value):
    print(value)
    
  #-------------------------------------------------------------------------------
  # Run the command.
  # A command is:
  # - var declaratie          Yes, only the value is been set.
  # - var assignment
  # - RUN_* Module1($DIR)
  # - MSG($FILE)
  # - GLOBIO_Calc($A,$B)
  def run(self,check=False):

    #Log.dbg("Command.run ##### "+self.scriptLine.line)
  
    if self.parent.isList():
      #Log.dbg("Command.run - isList(self.parent) "+self.parent.name)
      runableName = UT.strBefore(self.parent.name,".")
      parent = GLOB.runables[runableName]
    else:
      parent = self.parent
        
    # Is it a variable?
    if self.isVariable():
      
      # Get the value in the assignment.
      strValue = AU.getAssignmentValue(self.scriptLine)

      #Log.dbg("    Command.run - isVariable - self: "+self.name)
      #Log.dbg("    Command.run - isVariable - self.parent: "+self.parent.name)
      #Log.dbg("    Command.run - isVariable - strValue: "+strValue)

      # Set the value of the variable with the command parent as source.
      self.commandObj.setStrValue(strValue,parent,self.scriptLine)

    elif self.isList():
      
      # Get the values in the assignment, i.e. A|B|C.
      strListValue = AU.getAssignmentValue(self.scriptLine)
      # Get the seperate values.
      strValues = UT.strSplit(strListValue,"|")
      # Loop through the values.
      for strValue in strValues:
        #Log.dbg("Command.loop - "+strValue)
        actualValues = [strValue]
        # Set the actual strValue values of the corresponding variable.
        pVar = GLOB.variables[self.name]

        # Set the value of the variable with the command parent as source.
        pVar.setStrValue(strValue,parent,self.scriptLine)
        
        # Run the list code.
        self.commandObj.run(check)

    else:

      #Log.dbg("Command.run - parent - "+parent.name)

      # Get the actuel argument values of the call.
      # Example: RUN_MODULE CalcMSA(world,30min,$LandUseCov)
      # Return a list with strings, like: $LandUseCov, 30min, 123.
      actualValues = AU.getArgumentsAsStrings(self.scriptLine)
      
      #Log.dbg("Command.run - actualValues - "+str(actualValues))

      # Replace references ($name) in the actual argument values by
      # the strValue of the referenced variable.
      resolvedValues = AU.resolveReferencesInValues(actualValues,parent,self.scriptLine)

      #Log.dbg("Command.run - resolvedValues - "+str(resolvedValues))

      # Get the names of the arguments (i.e. the names of the variables).
      argVarFullNames = self.commandObj.declArgumentFullNames
      
      # Check number of arguments.
      if len(actualValues)!=len(argVarFullNames):
        Err.raiseSyntaxError(Err.InvalidNumberOfArgumentsInCall,self.scriptLine)
        
      #Log.dbg("Command.run - argVarFullNames - "+str(argVarFullNames))

      # A run check?
      if check:
        #Log.dbg("Command.run - getRefVarsFromActualValues")
        # Get reference variables (if any) from actual values. 
        pRefVars = AU.getReferenceVariablesFromValues(actualValues,parent)
        # Copy the simulateIsCreated flag from the reference variables
        # to the argument variables.
        AU.copyReferenceVariablesSimulateIsCreated(pRefVars,argVarFullNames)

      #Log.dbg("Command.run - updateArgumentsWithValues")
      # Set the actual strValue values of the private variables of the script.
      # Also checks the values on base of the argument type IN or OUT.
      AU.updateArgumentsWithValues(argVarFullNames,resolvedValues,self.scriptLine)

      #Log.dbg("Command.run - updateParsedValue")
      for varFullName in argVarFullNames:
        # Get the variable.
        pVar = GLOB.variables[varFullName]
        # Update the parsed value.
        pVar.updateParsedValue(parent,self.scriptLine)

      #Log.dbg("Command.run - self.commandObj.run")

      # Run code of het script with the set variables. 
      self.commandObj.run(check)

      # A run check?
      if check:
        # The arguments for the runned command can contain variables.
        # Simulate the creation of these OUT variables.
        
        # Loop through the actual values.  
        for value in actualValues:
          # Get the first reference name and search name.
          refName,searchName = AU.getReferenceNameSearchName(value)

          #Log.dbg("Command.run - refName - "+refName+" "+searchName)

          # Reference variable found?
          if not refName is None:
            # Is the value just a variable name.
            if value.replace(searchName,"")=="":
              # Get variable.
              pVar = AU.getVariable(refName,parent)
              # Found?
              if not pVar is None:
                #Log.dbg("Command.run - pVar - "+AU.getVariableFullName(pVar.name, parent))
                pVar.simulateIsCreated = True

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class CommandList(list):

  #-------------------------------------------------------------------------------
  def add(self,command):
    self.append(command)

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  pass
  # import Globio4TestRun
  # Globio4TestRun.globio4TestRun()
