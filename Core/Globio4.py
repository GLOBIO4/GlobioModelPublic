# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
# ******************************************************************************

#-------------------------------------------------------------------------------
# Modified: 2 nov 2016, ES, ARIS B.V.
#           - Version 4.0.2
#           - run modified, self.mainFileName = os.path.abspath(self.mainFileName).
#           22 mar 2017, ES, ARIS B.V.
#           - Version 4.0.5
#           - setLogFileName removed, now using initLogFileName.
#           9 sep 2017, ES, ARIS B.V.
#           - Version 4.0.9
#           - run modified, now searching for Globio_ConfigLinux.glo when
#             running on Linux.
#           27 jan 2021, ES, ARIS B.V.
#           - Version 4.1.1
#           - run modified, now only shows traceback error info when
#             GLOB.debug is True.
#-------------------------------------------------------------------------------

import sys
import os

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Common.Timer as TI
import GlobioModel.Common.Utils as UT

import GlobioModel.Core.AppUtils as AU
import GlobioModel.Core.DocUtils as DU

from GlobioModel.Core.Constants import ConstantList
from GlobioModel.Core.ScriptBase import ScriptBaseList
from GlobioModel.Core.Types import TypeList
from GlobioModel.Core.Variables import VariableList

from GlobioModel.Core.ScriptBase import ConfigScript,MainScript

from GlobioModel.Config.Constants_Config import defineConstants
from GlobioModel.Config.Types_Config import defineTypes
from GlobioModel.Config.Variables_Config import defineVariables

#GLOB.SHOW_TRACEBACK_ERRORS = True

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Globio4(object):

  # The timer.
  timer = None
  
  # Globio config script.
  configFileName = ""
  configScript = None

  # Main script.
  mainFileName = ""
  mainScript = None

  # The usage message.
  usageMsg = ""

  # Is set when option -debug is used.
  forceDebug = False

  # When there are errors in scripts.
  hasErrors = False

  # Is set when the documentation should be shown.
  showDoc = False

  #-------------------------------------------------------------------------------
  def checkScriptHasErrors(self,script,errorNr):
    # Are there errors?
    if script.hasErrors:
      self.hasErrors = True
      # Show error message and stop.
      Err.raiseGlobioError(errorNr)

  #-------------------------------------------------------------------------------
  def parseArguments(self):
    
    args = sys.argv

    # Set the usage message.  
    self.usageMsg = "\n"+ \
                    "globio "+GLOB.globioVersion+" - "+GLOB.globioReleaseDate+"  "+ \
                    "(Framework: "+GLOB.appVersion+")\n"+"\n"+ \
                    "usage: globio [option] [file]"+"\n"+"\n"+ \
                    "Options and arguments:"+"\n"+ \
                    "-help   : "+"show this message"+"\n"+ \
                    "-doc    : "+"show documentation"+"\n"+ \
                    "-debug  : "+"execute in debug mode"+"\n"+ \
                    "-version: "+"show the build version"+"\n"+ \
                    "file    : "+"globio run configuration file "+"\n"
    
    try:
      # The first argument is globio4.py.
      if len(args)==1:
        # 1 argument.
        self.usage()
        return False
      elif len(args)==2:
        # 2 argument.
        if args[1]=="-doc":
          # Show the documentatie.
          self.showDoc = True
          return True
        elif args[1]=="-help":
          # Show the usage.
          self.usage()
          return False
        elif args[1]=="-debug":
          # Show the usage.
          self.usage()
          return False
        elif args[1]=="-version":
          # Show the buildversions.
          self.showBuildVersions()
          return False
        elif args[1].startswith("-"):
          Err.raiseGlobioError(Err.InvalidOption1,args[1])
        else:
          # OK, get the name of the script.
          self.mainFileName = args[1]
          # Een geldig script?
          if not os.path.isfile(self.mainFileName):
            Err.raiseGlobioError(Err.FileNotFound1,self.mainFileName)
          # OK, the script can be run.  
          return True
      elif len(args)==3:
        # 3 argumenten.
        if args[1]=="-debug":
          self.forceDebug = True
          GLOB.debug = True
          # OK, get the name of the script.
          self.mainFileName = args[2]
          # A valid script?
          if not os.path.isfile(self.mainFileName):
            Err.raiseGlobioError(Err.FileNotFound1,self.mainFileName)
          # OK, the script can be run.  
          return True
        else:
          Err.raiseGlobioError(Err.InvalidCommand)
      else:
        # More than 3 arguments.
        self.usage()
        return False
       
    except (Err.GlobioError,SyntaxError):
      # Only show the error and dont't insert the error in the logfile.
      Err.showError()
      self.usage()
      return False

  #-------------------------------------------------------------------------------
  def run(self):

    # Get the Core directory name.
    coreDir = os.path.abspath(os.path.dirname(__file__))
    
    # No main script?
    if len(self.mainFileName)==0:
      # It is an ordinary run.
      # Set the config directory.
      GLOB.configDir = os.path.abspath(os.path.join(coreDir,"..","Config"))
      # Get and check the arguments.
      if not self.parseArguments():
        return
    else:
      # There is already a main script, so this is a test run.
      # Set the config directory.
      GLOB.configDir = os.path.abspath(os.path.join(coreDir,"..","Config"))
      # Set the config dir dependend from where this script is run.
      if not os.path.isdir(GLOB.configDir):
        GLOB.configDir = os.path.abspath(os.path.join(coreDir,"..","..","Config"))

    try:
      # Show the start message.
      self.showStartMsg()

      # Show debug message if debugging.
      Log.dbg("DEBUG is TRUE")
    
      # Start the timer.
      self.startTimer()
      
      #-----------------------------------------------------------------------------
      # Create global lists.
      #-----------------------------------------------------------------------------

      # Create the global lists for types, constants and variables.
      GLOB.types = TypeList()
      GLOB.constants = ConstantList()
      GLOB.variables = VariableList()

      # Create the global lists for runables (Runs,scenario's,modules,lists etc.).
      GLOB.runables = ScriptBaseList()

      #-----------------------------------------------------------------------------
      # Define types, constants and build-in variables.
      #-----------------------------------------------------------------------------
       
      # Set the global constants and types.
      defineTypes(GLOB.types)
      defineConstants(GLOB.constants)
      
      # Define the buildin variables and set the default value.
      defineVariables(GLOB.variables)

      #-----------------------------------------------------------------------------
      # Read the GLOBIO config script.
      #-----------------------------------------------------------------------------

      # 20170909
#      self.configFileName = os.path.join(GLOB.configDir,"Globio_Config.glo")
#      self.configScript = ConfigScript(self.configFileName)
#      self.configScript.load()

      # 20170909
      # Set the config file name. On linux search for Globio_ConfigLinux.glo
      # for linux specific settings. Otherwise use the default 
      # Globio_Config.glo file.
      
      # Set default config file name.
      defaultConfigFileName = os.path.join(GLOB.configDir,"Globio_Config.glo")
      # Running on linux?
      if UT.isLinux():
        # Set linux config file name.
        linuxConfigFileName = os.path.join(GLOB.configDir,"Globio_ConfigLinux.glo")
        # Linux config file found?
        if os.path.isfile(linuxConfigFileName):
          # Use linux config file.
          self.configFileName = linuxConfigFileName
        else:
          # Use default config file.
          self.configFileName = defaultConfigFileName
      else:
        # Use default config file.
        self.configFileName = defaultConfigFileName

      # Create and load the GLOBIO config script.
      # In this script the default values of the buildin variables can
      # be overriden. 
      self.configScript = ConfigScript(self.configFileName)
      self.configScript.load()

      # Check forceDebug.
      if self.forceDebug:
        GLOB.debug = True
        
      # Are there errors?
      self.checkScriptHasErrors(self.configScript,Err.NoValidGlobioConfiguration)

      #-----------------------------------------------------------------------------
      # Show documentation?
      #-----------------------------------------------------------------------------
      if self.showDoc:
        # Run config script to set default values.
        self.configScript.run(False)
        # Show documentation.
        self.showDocumentation()
        # Stop execution.
        return
      
      #-----------------------------------------------------------------------------
      # Create and read the main script.
      #-----------------------------------------------------------------------------

      # Expand path of the main script to full path.
      self.mainFileName = os.path.abspath(self.mainFileName)

      # Create the main script.
      self.mainScript = MainScript(self.mainFileName)

      # Read the main script.
      self.mainScript.load()

      # Check forceDebug.
      if self.forceDebug:
        GLOB.debug = True

      # Are there errors?
      self.checkScriptHasErrors(self.mainScript,Err.NoValidGlobioScript)

      #-----------------------------------------------------------------------------
      # Init the logfile name. 
      #-----------------------------------------------------------------------------
 
      # Init logfile name.
      self.initLogFileName()
       
      #-----------------------------------------------------------------------------
      # Bind the runables to the commands.
      #-----------------------------------------------------------------------------

      # Link the runables to the commands. This can be done just now because 
      # run commando's can be occur in the script before the definition.
      self.mainScript.bindCommands()

      # Are there errors?
      self.checkScriptHasErrors(self.mainScript,Err.NoValidGlobioScript)

      #-----------------------------------------------------------------------------
      # Check before run. 
      #-----------------------------------------------------------------------------

      # Set the variables runCheck flag.
      self.setVariablesRunCheck(True)

      # Check running the main script.
      self.mainScript.run(True)

      # Reset the variables runCheck flag.
      self.setVariablesRunCheck(False)

      # Are there errors?
      self.checkScriptHasErrors(self.mainScript,Err.NoValidGlobioScript)

      #-----------------------------------------------------------------------------
      # Run. 
      #-----------------------------------------------------------------------------

      # Run the main script.
      self.mainScript.run()

      # Check for errors.
      if self.mainScript.hasErrors:
        self.hasErrors = True

    except SyntaxError:
      self.hasErrors = True
      Log.err()
    except Err.GlobioError:
      self.hasErrors = True
      Log.err()
    except Exception:
      self.hasErrors = True
      # 20210127
      if GLOB.debug:
        Log.errWithTraceback()
      else:
        Log.info("Error:")
        Log.err()
    finally:
      # Show the end message.
      self.showEndMsg()

  #-------------------------------------------------------------------------------
  # Set initial logfile directory and name when no outdir variable is defined.
  def initLogFileName(self):

    # Get the variable "OutDir".
    pOutDirVar = AU.getVariable("OutDir",None)

    # Variable found?
    if not pOutDirVar is None:
#      # 20201117
#      # Show debug message.
#      Log.dbg("Log dir: "+pOutDirVar.strValue)
      # Log file will be set when parsing variable. 
      return

    # Get the base logfile name.
    baseFileName = Log.getBaseLogFileName()
    
    # Save Log file in user temp.
    GLOB.logfileName = os.path.join(GLOB.userTempDir,baseFileName)

    # Show debug message.
    Log.dbg("Log file: "+GLOB.logfileName)

    # Flush the log startup buffer because of pending messages.
    Log.flushStartupBufferToFile()

  #-------------------------------------------------------------------------------
  # Loops through variables and set the runCheck flag.
  def setVariablesRunCheck(self,check):
    for varName in GLOB.variables:
      GLOB.variables[varName].runCheck = check

  #-------------------------------------------------------------------------------
  def showBuildVersions(self):
    Log.info("")
    globVersion = GLOB.globioVersion + "." + GLOB.globioSubSubVersion
    appVersion = GLOB.appVersion + "." + GLOB.appSubSubVersion
    Log.info("globio "+globVersion+" - "+GLOB.globioReleaseDate+ \
             "  (Framework: "+appVersion+")")
    Log.info("")

  #-------------------------------------------------------------------------------
  def showDocumentation(self):
    DU.docListConstants()
    DU.docListGlobalVariables()
    DU.docListCalculations()

  #-------------------------------------------------------------------------------
  def showEndMsg(self):
    Log.headerLine("=")
    if not self.showDoc:
      # Are there no errors?
      if not self.hasErrors:
        Log.info("# Execution successfully ended.")
      # Is there a timer?
      if self.timer is not None:
        Log.info("# Total execution time: "+self.timer.elapsedStr())
      Log.headerLine("=")
    Log.info("")

  #-------------------------------------------------------------------------------
  def showStartMsg(self):
    Log.headerLine("=")
    Log.info(UT.strConcatAlignRight("# GLOBIO "+ GLOB.globioVersion + \
                                       ", " + GLOB.globioReleaseDate,
                                       "(Framework "+GLOB.appVersion+")",
                                       GLOB.logfileHeaderLength))
    if not self.showDoc:
      Log.info("#")
      Log.info("# Execution start: "+UT.dateTimeToStr())
    Log.headerLine("=")

  #-------------------------------------------------------------------------------
  def startTimer(self):
    self.timer = TI.Timer()

  #-------------------------------------------------------------------------------
  def usage(self):
    print(self.usageMsg)

  #-------------------------------------------------------------------------------
  def test(self):
    pass

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  g = Globio4()
  g.run()
