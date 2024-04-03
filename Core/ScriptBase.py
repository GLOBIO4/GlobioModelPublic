# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
# ******************************************************************************

#-------------------------------------------------------------------------------
# Modified: 22 mar 2017, ES, ARIS B.V.
#           - Version 4.0.5
#           - ScriptBase - trace added.
#           30 nov 2020, ES, ARIS B.V.
#           - Version 4.1.0
#           - ScriptBase - getNoListParent added.
#-------------------------------------------------------------------------------

from os import path

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Common.Utils as UT
import GlobioModel.Core.AppUtils as AU

from GlobioModel.Core.Commands import Command,CommandList
from GlobioModel.Core.ScriptLines import ScriptLine,ScriptLineList
from GlobioModel.Core.Variables import Variable

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class ScriptBase(object):

  # The basename of the filename.
  name = ""

  # The filename.
  fileName = ""

  # These are the names of the declared arguments.
  declArgumentFullNames = None

  # Are only used in configscript,mainscript,runs,scenario's, modules and lists.
  commands = None

  # Set if errors are occured.
  hasErrors = False
  
  #-------------------------------------------------------------------------------
  def __init__(self,fileName):
    self.name = path.basename(fileName)
    self.fileName = fileName
    self.declArgumentFullNames = None
    self.commands = None
    self.hasErrors = False

  #-------------------------------------------------------------------------------
  # Binds the runables to the commands. This can be done now because run commands 
  # can occur earlier in scripts than the definition.
  # In both cases the NAME is used for the link.
  def bindCommands(self):
    
    #Log.dbg("ScriptBase.bindCommands - "+self.name)
    
    # No commands?
    if self.commands is None:
      return
    
    # Loop through all commands.
    for pCommand in self.commands:
      try:
        if pCommand.isVariable():
          # It is a variable and is already linked.
          pass
        else:
          # It is a runable.
          
          # No corresponding runable?
          if not GLOB.runables.exists(pCommand.name):
            # Show a error message.
            if pCommand.isRun():
              Err.raiseSyntaxError(Err.RunNotFound1,pCommand.scriptLine,pCommand.name)
            elif pCommand.isScenario():
              Err.raiseSyntaxError(Err.ScenarioNotFound1,pCommand.scriptLine,pCommand.name)
            elif pCommand.isModule():
              Err.raiseSyntaxError(Err.ModuleNotFound1,pCommand.scriptLine,pCommand.name)
            elif pCommand.isMsg():
              Err.raiseSyntaxError(Err.MsgNotFound1,pCommand.scriptLine,pCommand.name)
            elif pCommand.isGlobioCalculation():
              Err.raiseSyntaxError(Err.GlobioCalculationNotFound1,pCommand.scriptLine,pCommand.name)
            elif pCommand.isList():
              Err.raiseSyntaxError(Err.ListNotFound1,pCommand.scriptLine,pCommand.name)

          # Get the runable.
          pRunable = GLOB.runables[pCommand.name]
          
          # Check the runable type.
          if (isinstance(pRunable,Run) and (not pCommand.isRun())) or \
             (isinstance(pRunable,Scenario) and (not pCommand.isScenario())) or \
             (isinstance(pRunable,Module) and (not pCommand.isModule())):
            keyword = AU.getKeyword(pCommand.scriptLine)
            Err.raiseSyntaxError(Err.NoValidRunCommand2,pCommand.scriptLine,keyword,pRunable.name)
            
          # Bind the runable.
          pCommand.commandObj = pRunable
        
          # Bind the commands in the runable too.
          pRunable.bindCommands()

          # Check for errors.
          if pRunable.hasErrors:
            self.hasErrors = True
          
      except SyntaxError:
        self.hasErrors = True
        Log.err()

  #-------------------------------------------------------------------------------
  # Check if it is a valid line for this script.
  # Accoring to the script type (Script,Run,Scenario,Module) there are some
  # keywords valid or not.
  # Must be overriden in subclasses.
  def checkScriptLine(self,scriptLine):
    pass

  #-------------------------------------------------------------------------------
  # Creates a command.
  # Is called in parseLines.
  # Examples:
  #   GLOBIO_CreateMaps
  #   RUN RunName()
  #   RUN_SCENARIO Scenario1()
  #   RUN_MODULE Module2()
  #   LIST INTEGER Year = 2012|2013
  def createCommand(self,scriptLine):

    #Log.dbg("ScriptBase.createCommand")

    # Process the line.
    if AU.isDeclarationAndAssignment(scriptLine):

      #----------------------------------------------------------
      # Variable declaration.
      #----------------------------------------------------------
      #Log.dbg("ScriptBase.createCommand - isDeclarationAndAssignment ")

      # Get the name.
      _, varName = AU.getDeclarationTypeAndVariableName(scriptLine)
      # Create a Command.
      pCommand = Command(varName,self,scriptLine)
    
    elif AU.isAssignment(scriptLine):
 
      #----------------------------------------------------------
      # Variable assignment.
      #----------------------------------------------------------
      #Log.dbg("ScriptBase.createCommand - isAssignment - "+scriptLine.line)
 
      # Get the variable name.    
      varName = AU.getAssignmentVariableName(scriptLine)
 
      # Get the variable.
      pVar = AU.getVariable(varName,self)

      # Not found?
      if pVar is None:
        Err.raiseSyntaxError(Err.VariableNotFound1,scriptLine,varName)

      # Get the value.
      strValue = AU.getAssignmentValue(scriptLine)
      
      #Log.dbg("ScriptBase.createCommand - isAssignment - setStrValue")
      
      # Update the strValue so settings in the config scripts becomes
      # effective immediately.
      pVar.setStrValue(strValue,self,scriptLine)

      # Create a Command.
      pCommand = Command(varName,self,scriptLine)
      pCommand.commandObj = pVar

    elif AU.isListDeclarationAndAssignment(scriptLine):

      #----------------------------------------------------------
      # List Variable declaration.
      #----------------------------------------------------------
 
      #Log.dbg("ScriptBase.createCommand - isListDeclarationAndAssignment ")
     
      # Get the name and add the name of the parent.
      listName = AU.getListName(scriptLine)
 
      # A list in a list?
      if self.isList():
        # Get the first parent which is no List.
        parent = self.getNoListParent()
      else:
        parent = self

      # Get the full name.
      listFullName = AU.getListFullName(listName,parent) 
           
      # Create a Command.
      # Because lists are private for a particulary runable and
      # for example a LIST YEAR should occur more than ones,
      # the fullName must be used.
      # By this name the correspondingrunable and variable 
      # can be found.
      pCommand = Command(listFullName,self,scriptLine)

    elif AU.isMsgCall(scriptLine):
      
      #------------------------------------------------------------
      # MSG
      #
      # Is actualy a build-in "GlobioCalculation".
      #------------------------------------------------------------
 
      # Create a Command.
      pCommand = Command("MSG",self,scriptLine)

    elif AU.isGlobioCalculationCall(scriptLine):

      #------------------------------------------------------------
      # GlobioCalculation
      #------------------------------------------------------------
      #Log.dbg("createCommand - checkGlobioCalculationName")
 
      # Check if it is a valid globio calculation declaration/call.
      # So if the <name>.py exists, a class is defined,
      # and the class the necessary methods contains. 
      # Does not check the arguments. 
      AU.checkGlobioCalculationName(scriptLine)
 
      #Log.dbg("createCommand - checkGlobioCalculationArgumentsFromDeclaration")
 
      # Check if it is a valid globio calculation declaration.
      # So if the argument declarations in the documentation are valid. 
      # Does not check the actual arguments. 
      AU.checkGlobioCalculationArgumentsFromDeclaration(scriptLine)
 
      # Get the name.
      name = AU.getGlobioCalculationName(scriptLine)
  
      # Create a Command.
      pCommand = Command(name,self,scriptLine)
    else:
      #------------------------------------------------------------
      # It is a runable.
      #
      # The declaration arguments will be read at BEGIN_RUN and so on.
      # The declaration arguments and the actual ones are checked in bindCommand.
      #------------------------------------------------------------
      
      # Check if there is a name.
      AU.checkRunableName(scriptLine)

      # Get the name.
      name = AU.getRunableName(scriptLine)

      # Create a Command.
      pCommand = Command(name,self,scriptLine)

    # Add the Command.
    self.commands.add(pCommand)

    return pCommand

  #-------------------------------------------------------------------------------
  # Is called in parseLines.
  def createRunable(self,scriptLine,scriptLines):

    # Check if there is a name.
    AU.checkRunableName(scriptLine)

    # Get the name.
    name = AU.getRunableName(scriptLine)

    # Is there already a runable with the same name?
    if GLOB.runables.exists(name):
      Err.raiseSyntaxError(Err.RunableAlreadyExists1,scriptLine,name)

    # Check the argument declaration.
    AU.checkArgumentDeclaration(scriptLine)
      
    # Get the keyword.
    keyword = AU.getKeyword(scriptLine)
    
    # Create a scriptblock.
    if keyword == "BEGIN_RUN":
      #Log.dbg("ScriptBase.createRunable - RUN: "+name+"...")
      # Create a run. with a link to the script in which the run is declared.
      pRunable = Run(name,self.fileName)
    elif keyword == "BEGIN_SCENARIO":
      #Log.dbg("ScriptBase.createRunable - SCENARIO: "+name+"...")
      # Create a scenario. with a link to the script in which the scenario is declared.
      pRunable = Scenario(name,self.fileName)
    elif keyword == "BEGIN_MODULE":
      #Log.dbg("ScriptBase.createRunable - MODULE: "+name+"...")
      # Create a module. with a link to the script in which the module is declared.
      pRunable = Module(name,self.fileName)

    # Get the arguments definitions.
    # Returns a VariableList: RASTER LandUseCov, INTEGER Year
    declArguments = AU.createArgumentVariablesFromDeclaration(scriptLine,pRunable)

    # Add the arguments to the list with global variables.
    GLOB.variables.addList(declArguments)

    # Set the declArgumentFullNames.
    pRunable.declArgumentFullNames = declArguments.keys()

    # Process the lines.
    pRunable.parseLines(scriptLines)

    # Check if there are errors.
    if pRunable.hasErrors:
      self.hasErrors = True
    
    # Add the runable to the runables.
    GLOB.runables.add(pRunable)

  #-------------------------------------------------------------------------------
  # Creates the build-in GlobalCalculation runable.
  # Is called in parseLines.
  def createRunableGlobioCalculation(self,scriptLine):
 
    #Log.dbg("ScriptBase.createRunableGlobioCalculation")

    # Get the name.
    name = AU.getGlobioCalculationName(scriptLine)
    
    # Does the GlobalCalculation runable exists?
    if GLOB.runables.exists(name):
      return GLOB.runables[name]

    # Check if it is a valid globio calculation declaration/call.
    # So if the <name>.py exists, a class is defined,
    # and the class the necessary methods contains. 
    # Does not check the arguments. 
    AU.checkGlobioCalculationName(scriptLine)
 
    #Log.dbg("ScriptBase.createRunableGlobalCalculation - checkGlobioCalculationArgumentsFromDeclaration")

    # Check if it is a valid globio calculation declaration.
    # So if the argument declarations in the documentation are valid. 
    # Does not check the actual arguments. 
    AU.checkGlobioCalculationArgumentsFromDeclaration(scriptLine)

    #Log.dbg("ScriptBase.createRunableGlobalCalculation - pRunable = GlobioCalculation()")
  
    # Create the runable.
    pRunable = GlobioCalculation(name,"")

    # Get the arguments definitions.
    # Returns a VariableList: VECTOR LandUseCov, INTEGER Year
    declArguments = AU.createGlobioCalculationArgumentVariablesFromDeclaration(scriptLine,pRunable)

    # Add the arguments to the list with global variables.
    GLOB.variables.addList(declArguments)

    # Set the declArgumentFullNames.
    pRunable.declArgumentFullNames = declArguments.keys()

    # Add the runable to the runables.
    GLOB.runables.add(pRunable)

    return pRunable
  
  #-------------------------------------------------------------------------------
  # Is called in parseLines.
  def createRunableList(self,scriptLine,scriptLines):

    # A list in a list?
    if self.isList():
      # Get the first parent which is no List.
      parent = self.getNoListParent()
    else:
      parent = self

    # Check the declaration.
    AU.checkListDeclaration(scriptLine,parent)

    # Get the type and name.
    typeName,varName = AU.getListTypeAndVariableName(scriptLine)

    # Set the list name.
    listName = varName
    listFullName = AU.getListFullName(listName,parent)
     
    #Log.dbg("ScriptBase.createRunableList "+listFullName)
           
    # Create the list.
    pList = List(listFullName,"")
    
    # Set the parent. Necessary to find variable references later on.
    pList.parent = self

    # Create a variable.
    pVar = Variable(varName,"",typeName,parent,scriptLine)

    # Get the values in the assignment, so A|B|C.
    strListValue = AU.getAssignmentValue(scriptLine)
    # Get the separate values.
    strValues = UT.strSplit(strListValue,"|")
    # Get the first value.
    strValue = strValues[0]
    # Set the value of the variable with the command parent as source.
    pVar.setStrValue(strValue,parent,scriptLine)

    GLOB.variables.add(pVar)

    # Process the lines.
    pList.parseLines(scriptLines)

    # Check if there are errors.
    if pList.hasErrors:
      self.hasErrors = True

    # Add the list to the runables.
    GLOB.runables.add(pList)

    return pList
  
  #-------------------------------------------------------------------------------
  # Creates the build-in Msg runable.
  # Is called in parseLines.
  def createRunableMsg(self):
 
    #Log.dbg("ScriptBase.createRunableMsg")

    # Set the name.
    name = "MSG"
    
    # Does the Msg runable exist?
    if GLOB.runables.exists(name):
      return
    
    # Create a scripline with the definition.
    scriptLine = ScriptLine("MSG(IN OBJ S)",0,"Build-in MSG")

    # Check the argument declaration.
    AU.checkArgumentDeclaration(scriptLine)

    # Create the runable.
    pRunable = Msg(name,"")

    # Get the arguments definitions.
    # Returns a VariableList terug: INFEAT LandUseCov, INTEGER Year
    declArguments = AU.createArgumentVariablesFromDeclaration(scriptLine,self)

    # Add the arguments to a list with global variables.
    GLOB.variables.addList(declArguments)

    # Set the declArgumentFullNames.
    pRunable.declArgumentFullNames = declArguments.keys()
    
    # Add the runable to the runables.
    GLOB.runables.add(pRunable)

  #-------------------------------------------------------------------------------
  # Process a line with a variable assignment and create the variable.
  #
  #  <type> varname = <constant>            type.isValidConstant(str)
  #  <type> varname = value (string)       type.isValidValue(str)
  #  <type> varname = $<varname>;+value (string)       type.isValidValue(str)
  #  varname = value (string)              bestaande (buildin) var zetten
  #
  def createVariable(self,scriptLine):

    #Log.dbg("ScriptBase.createVariable")
    
    # A variable in a list?    
    if self.isList():
      # Get the first parent which is no List is.
      parent = self.getNoListParent()
    else:
      parent = self

    #Log.dbg("ScriptBase.createVariable - parent.name "+parent.name)

    # Get the type and variable name.
    typeName, varName = AU.getDeclarationTypeAndVariableName(scriptLine)

    # Check the variable name.
    AU.checkVariableName(varName,scriptLine)   

    # Get the full name.
    varFullName = AU.getVariableFullName(varName,parent)
    
    # Check type and variable.
    # Is a typeName is given than is it a declaration and the variable
    # should not already been declarated as global or private variable.
    # Is the typeName None than it is an assignment and the variable
    # should already been declarated as global or private variable.
    AU.checkTypeVariableName(typeName,varFullName,scriptLine)

    #Log.dbg("ScriptBase.createVariable strValue = "+strValue)
    
    # Create a variable.
    pVar = Variable(varName,"",typeName,parent,scriptLine)

    #Log.dbg("ScriptBase.createVariable pVar.fullName - "+pVar.fullName)
    
    GLOB.variables.add(pVar)

    # Get the value.
    strValue = AU.getAssignmentValue(scriptLine)

    #Log.dbg("ScriptBase.createVariable setStrValue - "+strValue)

    # Set the value.
    pVar.setStrValue(strValue,parent)

    return pVar
  
  #-------------------------------------------------------------------------------
  # Returns the index of the end of a block.
  # For nested constructions a startKeywordCount will be used.
  # Returns -1 if not found.
  def getEndOfBlock(self,index,scriptLines,startKeyword,endKeyword):
    startKeywordCount = 0
    index += 1
    while index < len(scriptLines):
      scriptLine = scriptLines[index]
      keyword = AU.getKeyword(scriptLine)
      if keyword == startKeyword:
        startKeywordCount += 1
      elif keyword == endKeyword:
        if startKeywordCount == 0:
          return index
        else:
          startKeywordCount -= 1
      index += 1
    return -1  

  #-------------------------------------------------------------------------------
  # Returns the index of the start of the header of a block.
  # Returns index if no header found.
  def getBlockHeader(self,index,scriptLines):
    # Search back till a line which is no comment
    # (empy lines are already removed).
    startIndex = index
    index -= 1
    while index >= 0:
      # Comment?
      if scriptLines[index].line[0]=="#":
        startIndex = index
        index -= 1
      else:
        # No comment.
        break
    # Return the doclines.  
    docLines = scriptLines[startIndex:index]  
    return docLines

  #-------------------------------------------------------------------------------
  # Returns the first parent which is no List.
  def getNoListParent(self):
    return self

  #-------------------------------------------------------------------------------
  def includeScript(self,scriptLine):
     
    # Get the filename.
    fileName = UT.strAfter(scriptLine.line," ").strip()
 
    # No file name specified?
    if fileName=="":
      Err.raiseSyntaxError(Err.NoFileSpecified,scriptLine)         

    # Show debug message.
    Log.dbg("Including file: "+fileName)

    # No path?
    if path.dirname(fileName)=="":
      # Add path of the current script.
      incFileName = path.join(path.dirname(self.fileName),fileName)
      # Does file not exists.
      if not path.isfile(incFileName):
        # Add path of config directory.
        incFileName = path.join(GLOB.configDir,fileName)
        # Does file not exists.
        if not path.isfile(incFileName):
          Err.raiseSyntaxError(Err.IncludeFileNotFound1,scriptLine,fileName)
      # Show debug message.
      Log.dbg("  Using file: "+incFileName)
    elif not path.isabs(path.dirname(fileName)):
      # No absolute path? Add path of the current script.
      incFileName = path.join(path.dirname(self.fileName),fileName)
      # Create a full path.
      incFileName = path.abspath(incFileName)
      # Does the file not exist?
      if not path.isfile(incFileName):
        Err.raiseSyntaxError(Err.FileNotFound1,scriptLine,incFileName)
      # Show debug message.
      Log.dbg("  Using file: "+incFileName)
    else:
      # Set the include filename.
      incFileName = fileName
      # Does the file not exist?
      if not path.isfile(incFileName):
        Err.raiseSyntaxError(Err.FileNotFound1,scriptLine,incFileName)
      
    # Create the script.
    pScript = IncludedScript(incFileName)
 
    # Load script.
    pScript.load()

    # Are there errors?    
    if pScript.hasErrors:
      self.hasErrors = True

  #-------------------------------------------------------------------------------
  def isGlobalScript(self):
    if isinstance(self,ConfigScript):
      return True
    elif isinstance(self,MainScript):
      return True
    elif isinstance(self,IncludedScript):
      return True
    else:
      return False

  #-------------------------------------------------------------------------------
  def isList(self):
    if isinstance(self,List):
      return True
    else:
      return False

  #-------------------------------------------------------------------------------
  def mergeLines(self,scriptLines):
    pTmpScriptLines = []
    pTmpScriptLine = None
    pScriptLine = None
    keyword = ""
    i = 0

    #Log.dbg("ScriptBase.mergeLines")

    # Loop through all lines.
    while i < len(scriptLines):
      pScriptLine = scriptLines[i]
      # Is it comment?
      if pScriptLine.line[0] == "#":
        pTmpScriptLines.append(pScriptLine)
        i += 1
        continue

      keyword = AU.getKeyword(pScriptLine)
      if (keyword=="BEGIN_SCENARIO") or \
         (keyword=="BEGIN_MODULE") or \
         (keyword=="RUN_SCENARIO") or \
         (keyword=="RUN_MODULE") or \
         (keyword.startswith("GLOBIO_")):
        if pScriptLine.line.find(")")<0:
          pTmpScriptLine = pScriptLine
          i += 1
          while i < len(scriptLines):
            pScriptLine = scriptLines[i]
            pTmpScriptLine.line += " " + pScriptLine.line.strip()
            i += 1
            if pScriptLine.line.find(")")>=0:
              pTmpScriptLines.append(pTmpScriptLine)
              break
          continue
        else:
          pTmpScriptLines.append(pScriptLine)
          i += 1
          continue

      pTmpScriptLines.append(pScriptLine)
      i += 1

    return pTmpScriptLines
      
  #-------------------------------------------------------------------------------
  def parseLines(self,scriptLines):
    pScriptLine = None
    keyword = ""
    i = 0

    #Log.dbg("ScriptBase.parseLines")

    # Loop through all lines.
    while i < len(scriptLines):
      
      pScriptLine = scriptLines[i]

      #Log.dbg("#### ScriptBase.parseLines - "+pScriptLine.line)

      try:
      
        # Is it comment?
        if pScriptLine.line[0] == "#":
          i += 1
          continue

        # A valid line for this script type?
        # Check on variables declarations/assigments and keywords.
        self.checkScriptLine(pScriptLine)
        
        # Process the line.
        if AU.isDeclarationAndAssignment(pScriptLine):

          #----------------------------------------------------------
          # Variable declaration.
          #----------------------------------------------------------
          #Log.dbg("ScriptBase.parseLines - isDeclarationAndAssignment")
          
          # Create the variable,    
          pVar = self.createVariable(pScriptLine)
      
          # A valid var?
          if pVar is not None:
            # Create the command.          
            pCommand = self.createCommand(pScriptLine)
            # Bind the variable.
            pCommand.commandObj = pVar
          i += 1
          
        elif AU.isAssignment(pScriptLine):

          #----------------------------------------------------------
          # Variable assignment.
          #----------------------------------------------------------
          #Log.dbg("ScriptBase.parseLines - isAssignment - " + pScriptLine.line)

          self.createCommand(pScriptLine)
          i += 1
          
        elif AU.isInclude(pScriptLine):
          
          #----------------------------------------------------------
          # Inlude script.
          #----------------------------------------------------------
          self.includeScript(pScriptLine)
          i += 1
          
        elif AU.isMsgCall(pScriptLine):
          
          #----------------------------------------------------------
          # MSG.
          #----------------------------------------------------------
          # Create the build-in Msg runable.
          self.createRunableMsg()
          # Create the command.
          self.createCommand(pScriptLine)
          i += 1
          
        elif AU.isGlobioCalculationCall(pScriptLine):
          
          #----------------------------------------------------------
          # GlobioCalculation.
          #----------------------------------------------------------
          #Log.dbg("ScriptBase.parseLines - isGlobioCalculationCall")

          # Create the build-in Msg runable.
          pRunable = self.createRunableGlobioCalculation(pScriptLine)
          if pRunable is not None:
            # Create the command.
            #Log.dbg("ScriptBase.parseLines - isGlobioCalculationCall - createCommand")
            self.createCommand(pScriptLine)
          i += 1
          
        elif AU.isRun(pScriptLine):
          
          #----------------------------------------------------------
          # Run (RUN, RUN_SCENARIO of RUN_MODULE).
          #----------------------------------------------------------
          #Log.dbg("ScriptBase.parseLines - isRun")

          self.createCommand(pScriptLine)
          i += 1
          
        elif AU.isListDeclarationAndAssignment(pScriptLine):

          #----------------------------------------------------------
          # List declaration.
          #----------------------------------------------------------

          # Set the start tag.
          startKeyword = "LIST"
          # Set the eind tag.
          endKeyword = "END_LIST"
          # Set the startindex of the block.
          startIndex = i
          # Get the line index of the end tag.
          endIndex = self.getEndOfBlock(startIndex,scriptLines,startKeyword,endKeyword)
          # Not found?
          if endIndex<=0:
            Err.raiseSyntaxError(Err.RelatedKeywordOfKeywordNotFound1,pScriptLine,endKeyword,startKeyword)
          # Set the next line index.            
          i = endIndex + 1

          #Log.dbg("ScriptBase.parseLines - isList - createRunableList")
          
          # Create the list runable.
          pRunable = self.createRunableList(pScriptLine,scriptLines[startIndex+1:endIndex])
          
          # A valid runable?
          if pRunable is not None:
            # Create the command.
            #Log.dbg("ScriptBase.parseLines - isList - createCommand")
            self.createCommand(pScriptLine)

          i += 1
        else:
          #----------------------------------------------------------
          # Runable code.
          #----------------------------------------------------------

          # Get the keyword?
          keyword = AU.getKeyword(pScriptLine)

          #Log.dbg("ScriptBase.parseLines - " + pScriptLine.line)
          #Log.dbg("ScriptBase.parseLines - " + keyword)
          
          # Set the end tag.
          endKeyword = keyword.replace("BEGIN","END")
          # Set the startindex of the blok.
          startIndex = i
          # Get the line index of the end tag.
          endIndex = self.getEndOfBlock(startIndex,scriptLines,keyword,endKeyword)

          #Log.dbg("ScriptBase.parseLines - %s" % startIndex)
          #Log.dbg("ScriptBase.parseLines - %s" % scriptLines[startIndex].line)
          #Log.dbg("ScriptBase.parseLines - %s" % endIndex)
          #Log.dbg("ScriptBase.parseLines - %s" % scriptLines[endIndex].line)

          # Not found?
          if endIndex<=0:
            Err.raiseSyntaxError(Err.RelatedKeywordOfKeywordNotFound1,pScriptLine,endKeyword,keyword)
          # Set the next line index.
          i = endIndex
          # Create the scriptblock.
          self.createRunable(pScriptLine,scriptLines[startIndex+1:endIndex])

          i += 1

      except SyntaxError:
        self.hasErrors = True
        Log.err()
        i += 1
          
  #-------------------------------------------------------------------------------
  def run(self,check=False):

    # Just a run to check?
    if check:
      pass
    else:
      Log.dbg("Running "+self.name+"...")

    try:
      # Run the corresponding commands.
      for pCommand in self.commands:
        pCommand.run(check)
        # Check op errors.
        if not isinstance(pCommand.commandObj,Variable):
          if pCommand.commandObj.hasErrors:
            self.hasErrors = True
    except:
      if check:
        self.hasErrors = True
        Log.err()
      else:
        raise

  #-------------------------------------------------------------------------------
  def trace(self,indent):
    for pCommand in self.commands:
      Log.dbg("%s%s" % (indent,pCommand.scriptLine.line))
      if pCommand.isVariable():
        Log.dbg("%sVar: %s = %s" % (indent,pCommand.commandObj.name,pCommand.commandObj.strValue))
      elif pCommand.isRun():
        pCommand.commandObj.trace(indent+"  ")

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class ScriptBaseList(dict):

  #-------------------------------------------------------------------------------
  # Override because of uppercase keys/names.
  def __getitem__(self,name):
    return super(ScriptBaseList,self).__getitem__(name.upper())

  #-------------------------------------------------------------------------------
  # Override because of uppercase "name in dict".
  def __contains__(self, key):
    return super(ScriptBaseList,self).__contains__(key.upper())


  #-------------------------------------------------------------------------------
  def add(self,scriptBase):
    self[scriptBase.name.upper()] = scriptBase

  #-------------------------------------------------------------------------------
  def exists(self,name):
    return name in self

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Script(ScriptBase):

  #-------------------------------------------------------------------------------
  def load(self):
    pScriptLines = ScriptLineList()
    line = ""
    lineNr = 1

    # Does the file exist?
    if not path.isfile(self.fileName):
      Err.raiseGlobioError(Err.FileNotFound1,self.fileName)

    # Is it a config script instance?
    if isinstance(self,ConfigScript):
      Log.dbg("Loading file "+self.fileName)
    else:
      Log.info("Loading file "+self.fileName)

    # Read the config file.
    with open(self.fileName,"r") as f:
      pTmpLines = f.readlines()

    # Cleanup the lines.
    for line in pTmpLines:
      # Replace tabs through spaces (tabstop=2).
      line = UT.strReplaceTabs(line)
      # Remove leading and tailing spaces.
      line = line.strip()
      # Skip empty lines.
      if line == "":
        lineNr += 1
        continue
      # Add the line to the list.
      pScriptLines.add(line,lineNr,self.name)
      lineNr += 1

    #Log.dbg("Script.load - Merge lines...")
    
    # Merge the lines.
    pScriptLines = self.mergeLines(pScriptLines)

    #Log.dbg("Script.load - Parse lines...")
    
    # Process the lines.
    self.parseLines(pScriptLines)

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class ConfigScript(Script):

  #-------------------------------------------------------------------------------
  def __init__(self,fileName):
    super(ConfigScript,self).__init__(fileName)
    self.commands = CommandList()

  #-------------------------------------------------------------------------------
  # Checks if it is a valid line for this script.
  def checkScriptLine(self,scriptLine):

    # A MSG call.
    if AU.isMsgCall(scriptLine):
      # OK
      return
    
    # A variable definition ofr assignment (so a "=")?
    if AU.isDeclarationOrAssignment(scriptLine):
      # OK
      return

    # Get the keyword?
    keyword = AU.getKeyword(scriptLine)
    
    # A valid keyword for this script type?
    # No: RUN, LIST, DO_LIST.
    keywords = ["INCLUDE",
                "BEGIN_RUN","END_RUN",
                "BEGIN_SCENARIO","END_SCENARIO",
                "BEGIN_MODULE","END_MODULE",
                "MSG"]
    if not keyword in keywords:
      Err.raiseSyntaxError(Err.NoValidKeywordOrVariable1,scriptLine,keyword)

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class IncludedScript(Script):

  #-------------------------------------------------------------------------------
  # Checks if it is a valid line for this script.
  def checkScriptLine(self,scriptLine):
    
    # A MSG call.
    if AU.isMsgCall(scriptLine):
      # OK
      return
    
    # A variable definition or assignment (s a "=")?
    if AU.isDeclarationOrAssignment(scriptLine):
      Err.raiseSyntaxError(Err.VariablesNotAllowedInIncludedScripts,scriptLine)

    # Get the keyword?
    keyword = AU.getKeyword(scriptLine)
    
    # A valid keyword for this script type?
    # No: RUN, LIST, DO_LIST.
    keywords = ["INCLUDE",
                "BEGIN_RUN","END_RUN",
                "BEGIN_SCENARIO","END_SCENARIO",
                "BEGIN_MODULE","END_MODULE",
                "MSG"]
    if not keyword in keywords:
      Err.raiseSyntaxError(Err.NoValidKeywordOrVariable1,scriptLine,keyword)

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class MainScript(Script):

  #-------------------------------------------------------------------------------
  def __init__(self,fileName):
    super(MainScript,self).__init__(fileName)
    self.commands = CommandList()

  #-------------------------------------------------------------------------------
  # Checks if it is a valid line for this script.
  def checkScriptLine(self,scriptLine):
    
    # A MSG call.
    if AU.isMsgCall(scriptLine):
      # OK
      return
    
    # A variable definition or assignment (so a "=")?
    if AU.isDeclarationOrAssignment(scriptLine):
      # OK
      return

    # Get the keyword?
    keyword = AU.getKeyword(scriptLine)
    
    # A valid keyword for this script type?
    # No: RUN.
    keywords = ["INCLUDE",
                "BEGIN_RUN","END_RUN",
                "RUN",
                "BEGIN_SCENARIO","END_SCENARIO",
                "BEGIN_MODULE","END_MODULE",
                "MSG"]
    if not keyword in keywords:
      Err.raiseSyntaxError(Err.NoValidKeywordOrVariable1,scriptLine,keyword)

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Run(ScriptBase):

  #-------------------------------------------------------------------------------
  def __init__(self,name,fileName):
    super(Run,self).__init__(fileName)
    self.name = name
    self.commands = CommandList()

  #-------------------------------------------------------------------------------
  def checkInvalidType(self,scriptLine):
    # Is there no "="?
    if scriptLine.line.find("=") < 0:
      return
    # Add spaces around the =.
    line = scriptLine.line.replace("="," = ")
    # Split the line.
    tokens = UT.strSplit(line," ")
    # Less then 4 tokens?
    if len(tokens)<4:
      return
    # Token 3 not is "=".
    if tokens[2]!="=":
      return
    # Check 1-st token as type.
    if not AU.isType(tokens[0]):
      Err.raiseSyntaxError(Err.TypeNotFound1,scriptLine,tokens[0])

  #-------------------------------------------------------------------------------
  # Checks if it is a valid line for this script.
  def checkScriptLine(self,scriptLine):
    
    # A MSG call.
    if AU.isMsgCall(scriptLine):
      # OK
      return

    # A variable definition or assignment (so a "=")?
    if AU.isDeclarationOrAssignment(scriptLine):
      # OK
      return
    
    # Check if line has "=" and valid type name.
    # Could be combined with isDeclarationOrAssignment?
    self.checkInvalidType(scriptLine)

    # Get the keyword?
    keyword = AU.getKeyword(scriptLine)

    # Check for RUN command for special error messages.
    if keyword == "RUN":
      Err.raiseSyntaxError(Err.NoValidRunCommandInRunBlock,scriptLine)
    
    # A valid keyword for this script type?
    keywords = ["RUN_SCENARIO","RUN_MODULE","LIST","MSG"]
    if not keyword in keywords:
      Err.raiseSyntaxError(Err.NoValidKeyword1,scriptLine,keyword)

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Scenario(ScriptBase):

  #-------------------------------------------------------------------------------
  def __init__(self,name,fileName):
    super(Scenario,self).__init__(fileName)
    self.name = name
    self.commands = CommandList()

  #-------------------------------------------------------------------------------
  # Checks if it is a valid line for this script.
  def checkScriptLine(self,scriptLine):
    
    # A MSG call.
    if AU.isMsgCall(scriptLine):
      # OK
      return
    
    # A variable definition or assignment (so a "=")?
    if AU.isDeclarationOrAssignment(scriptLine):
      # OK
      return

    # Is the a globio calculation?
    if AU.isGlobioCalculationCall(scriptLine):
      # OK
      return

    # Get the keyword?
    keyword = AU.getKeyword(scriptLine)
    
    # A valid keyword for this script type?
    keywords = ["RUN_MODULE","LIST","MSG"]
    if not keyword in keywords:
      Err.raiseSyntaxError(Err.NoValidKeyword1,scriptLine,keyword)

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Module(ScriptBase):

  #-------------------------------------------------------------------------------
  def __init__(self,name,fileName):
    super(Module,self).__init__(fileName)
    self.name = name
    self.commands = CommandList()

  #-------------------------------------------------------------------------------
  # Checks if it is a valid line for this script.
  def checkScriptLine(self,scriptLine):
    
    # A MSG call.
    if AU.isMsgCall(scriptLine):
      # OK
      return
    
    # A variable definition or assignment (so a "=")?
    if AU.isDeclarationOrAssignment(scriptLine):
      # OK
      return

    # Is the a globio calculation?
    if AU.isGlobioCalculationCall(scriptLine):
      # OK
      return

    # Get the keyword?
    keyword = AU.getKeyword(scriptLine)
    
    # A valid keyword for this script type?
    keywords = ["LIST","MSG"]
    if not keyword in keywords:
      Err.raiseSyntaxError(Err.NoValidKeyword1,scriptLine,keyword)

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GlobioCalculation(ScriptBase):

  #-------------------------------------------------------------------------------
  def __init__(self,name,fileName):
    super(GlobioCalculation,self).__init__(fileName)
    self.name = name

  #-------------------------------------------------------------------------------
  def run(self,check=False):

    # Loop through the names of the arguments of the call.
    args = []
    for varFullName in self.declArgumentFullNames:
      # Get the variable.
      pVar = GLOB.variables[varFullName]
      # Add the actual value to the list.
      args.append(pVar.parsedValue)

    #Log.dbg("GlobioCalculation.run - args - %s" % args)
    
    # Just a run to check?
    if check:
      # Simulate the creation of the OUT variables.
      for varFullName in self.declArgumentFullNames:
        # Get the variable.
        pVar = GLOB.variables[varFullName]
        # OUT variable?
        if not pVar.isInput:
          pVar.simulateIsCreated = True
      # Don't really run the calculation.    
    else:
      # Run the GlobioCalculation with the actual reference.
      AU.runGlobioCalculation(self.name,*args)

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Msg(ScriptBase):

  #-------------------------------------------------------------------------------
  def __init__(self,name,fileName):
    super(Msg,self).__init__(fileName)
    self.name = name

  #-------------------------------------------------------------------------------
  def run(self,check=False):

    # Get the name of the first argument.
    varFullName =  self.declArgumentFullNames[0]
    
    #Log.dbg("Msg.run - varFullName "+varFullName)

    # Get the variable.
    pVar = GLOB.variables[varFullName]

    # Get the value.
    value = pVar.updateParsedValue(None,None)

    # Is it a constant?
    # Remark: does not solve concatenated constant names.
    if GLOB.constants.exists(value):
      # Replace with real value.
      pConst = GLOB.constants[value]
      value = pConst.value

    # Just a run to check.
    if check:
      return
   
    # Print the value.
    Log.info(value)

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class List(ScriptBase):

  # Reference to the parent runable (Run,Scenario,Module,List).
  parent = None                   
  
  #-------------------------------------------------------------------------------
  def __init__(self,name,fileName):
    super(List,self).__init__(fileName)
    # Override the name (is the filename by default).
    self.name = name                 # The name of the variabel.
    self.commands = CommandList()
    self.parent = None

  #-------------------------------------------------------------------------------
  # Checks if it is a valid line for this script.
  def checkScriptLine(self,scriptLine):
    
    # A MSG call.
    if AU.isMsgCall(scriptLine):
      # OK
      return

    # A variable definition or assignment (so a "=")?
    if AU.isDeclarationOrAssignment(scriptLine):
      # OK
      return

    # Is it a globio calculation?
    if AU.isGlobioCalculationCall(scriptLine):
      # OK
      return

    # A list?
    if AU.isListDeclarationAndAssignment(scriptLine):
      # OK
      return

    # Get the keyword?
    keyword = AU.getKeyword(scriptLine)
    
    # A valid keyword for this script type?
    keywords = ["RUN_SCENARIO","RUN_MODULE","MSG"]
    if not keyword in keywords:
      Err.raiseSyntaxError(Err.NoValidKeyword1,scriptLine,keyword)

  #-------------------------------------------------------------------------------
  # Returns the first parent which is no List.
  def getNoListParent(self):
    if self.parent.isList():
      return self.parent.getNoListParent()
    else:
      return self.parent

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  pass
  # import Globio4TestRun
  # Globio4TestRun.globio4TestRun()
