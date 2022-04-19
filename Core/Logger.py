# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************
#-------------------------------------------------------------------------------
# Remarks:
# - When using the same outdir for different runs (run each module in one run)
#   the logging info is appended to the existing logfile.
# - Log files will also contain info about runs with errors.
# - The dbg,err,info methods adds the messages to the logger test results.
#
# Modified: 30 nov 2016, ES, ARIS B.V.
#           - Version 4.0.2
#           - printArray added.
#           22 mar 2017, ES, ARIS B.V.
#           - Version 4.0.5
#           - updateLogFileDirectory added.
#           - flushStartupBufferToFile modified, cache not cleared.
#-------------------------------------------------------------------------------

import os

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Common.Utils as UT

# 20210104
#logger = None

#-------------------------------------------------------------------------------
def dbg(s):
  if GLOB.debug:
    logger.info(s)

#-------------------------------------------------------------------------------
def decIndent():
  logger.decIndent()

#-------------------------------------------------------------------------------
def err():
  logger.resetIndent()
  logger.err()

#-------------------------------------------------------------------------------
def errWithTraceback():
  logger.resetIndent()
  logger.errWithTraceback()

#-------------------------------------------------------------------------------
# Saves the startup buffer to the logfile.
# The startupBuffer is used to save messages while the logfile dir/outdir
# is not yet known.
def flushStartupBufferToFile():
  logger.flushStartupBufferToFile()

#-------------------------------------------------------------------------------
def getBaseLogFileName():
  return logger.getBaseLogFileName()

#-------------------------------------------------------------------------------
def getTestResults():
  return logger.getTestResults()

#-------------------------------------------------------------------------------
# Show a header line with the character c.
def headerLine(c):
  s = c*GLOB.logfileHeaderLength
  logger.info(s)

#-------------------------------------------------------------------------------
def incIndent():
  logger.incIndent()

#-------------------------------------------------------------------------------
def info(s):
  logger.info(s)

#-------------------------------------------------------------------------------
# width = number of digits before the decimal point.
# precision = number of decimals for floats.
def printArray(name,data,width=6,precision=1):
  logger.printArray(name,data,width,precision)

#-------------------------------------------------------------------------------
def reset():
  logger.reset()

#-------------------------------------------------------------------------------
def startTest():
  logger.startTest()

#-------------------------------------------------------------------------------
def updateLogFileDirectory(logDir,showMsg=False):
  logger.updateLogFileDirectory(logDir,showMsg)

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Logger(object):
  indent = ""
  indentSize = 2
  testResults = None
  startupBuffer = None
  
  #-------------------------------------------------------------------------------
  def __init__(self):
    self.indent = ""
    self.indentSize = 2
    self.testResults = []
    self.startupBuffer = []

  #-------------------------------------------------------------------------------
  def decIndent(self):
    if len(self.indent)>0:
      index = self.indentSize * -1
      self.indent = self.indent[:index]

  #-------------------------------------------------------------------------------
  def err(self):
    s = Err.getErrorMsg()
    self.info(s)
    if GLOB.SHOW_TRACEBACK_ERRORS:
      self.errWithTraceback()
      
  #-------------------------------------------------------------------------------
  def errWithTraceback(self):
    msgs = Err.getErrorMsgWithTraceBack()
    for msg in msgs:
      self.info(msg)

  #-------------------------------------------------------------------------------
  # Saves the startup buffer to the logfile.
  # The startupBuffer is used to save messages while the logfile dir/outdir
  # is not yet known.
  def flushStartupBufferToFile(self):
    if GLOB.logToFile:
      if self.startupBuffer is None:
        return
      for s in self.startupBuffer:
        self.msgToFile(s)

  #-------------------------------------------------------------------------------
  def getBaseLogFileName(self):
    if GLOB.logfileBaseName=="":
      fileName = "globio"+UT.dateTimeToStrShort()+".log"
    else:
      fileName = GLOB.logfileBaseName
    return fileName
      
  #-------------------------------------------------------------------------------
  def getFullLogFileName(self):
    # No default logfile name?
    if GLOB.logfileName=="":
      path = GLOB.userTempDir
      fileName = self.getBaseLogFileName()
      fileName = os.path.join(path,fileName)
    else:
      fileName = GLOB.logfileName
    return fileName

  #-------------------------------------------------------------------------------
  def getTestResults(self):
    return self.testResults

  #-------------------------------------------------------------------------------
  def incIndent(self):
    self.indent = self.indent + (" " * self.indentSize)

  #-------------------------------------------------------------------------------
  def info(self,s):
    
    print(self.indent + str(s))
    
    if GLOB.testing:
      self.testResults.append(self.indent + str(s))

    if not self.startupBuffer is None:
      self.startupBuffer.append(self.indent + str(s))
      
    if GLOB.logToFile:
      self.msgToFile(self.indent + str(s))

  #-------------------------------------------------------------------------------
  # Write a msg to the logfile.
  def msgToFile(self,s):
    try:
      fileName = self.getFullLogFileName()
      with open(fileName,"a") as logFile:
        if not s.endswith("\n"):
          s += "\n"
        logFile.write(s)
    except:
      pass

  #-------------------------------------------------------------------------------
  # width = number of digits before the decimal point.
  # precision = number of decimals for floats.
  def printArray(self,name,data,width=6,precision=1):
    import numpy as np
    
    def formatValue(v):
      if isinstance(value,float):
        fmt = "{:"+str(width+1)+"."+str(precision)+"f}"
        return fmt.format(value)
      elif isinstance(value,np.float16):
        fmt = "{:"+str(width+1)+"."+str(precision)+"f}"
        return fmt.format(value)
      elif isinstance(value,np.float32):
        fmt = "{:"+str(width+1)+"."+str(precision)+"f}"
        return fmt.format(value)
      elif isinstance(value,np.uint8):
        fmt = "{:"+str(width)+"d}"
        return fmt.format(value)
      elif isinstance(value,np.int):
        fmt = "{:"+str(width)+"d}"
        return fmt.format(value)
      elif isinstance(value,np.int64):
        fmt = "{:"+str(width)+"d}"
        return fmt.format(value)
      else:
        fmt = "{:^"+str(width+1)+"s}"
        return fmt.format(str(value))
  
    if (not name is None) and (name != ""):
      self.info(name + ":")
      
    #maxLineLen = 80  
    maxLineLen = 120  
    if data.ndim == 1:
      s = ""
      for i in range(len(data)):
        value = data[i]
        valueStr = formatValue(value)
        if len(s+valueStr) > maxLineLen:
          self.info(s)
          s = ""
        s += valueStr
      if s != "":
        self.info(s)
    elif data.ndim == 2:
      nrRows,nrCols = data.shape
      for r in range(nrRows):
        s = ""
        for c in range(nrCols):
          value = data[r,c]
          valueStr = formatValue(value)
          if len(s+valueStr) > maxLineLen:
            self.info(s)
            s = ""
          s += valueStr
        if s != "":
          self.info(s)

  #-------------------------------------------------------------------------------
  # Removes a logfile if exist.
  def reset(self):
    self.resetIndent()
    fileName = self.getFullLogFileName()
    if os.path.isfile(fileName):
      try:
        os.remove(fileName)
      except:
        pass

  #-------------------------------------------------------------------------------
  def resetIndent(self):
    self.indent = ""

  #-------------------------------------------------------------------------------
  def startTest(self):
    # Reset test results.
    self.testResults = []

  #-------------------------------------------------------------------------------
  def updateLogFileDirectory(self,logDir,showMsg=False):

    # Get base filename.    
    baseFileName = self.getBaseLogFileName()
    # Does the directory exist?
    if os.path.isdir(logDir):
      # Log file in output dir.
      logfileName = os.path.join(logDir,baseFileName)
    else:
      # Log file in user temp.
      logfileName = os.path.join(GLOB.userTempDir,baseFileName)

    # New logfilename same as current?
    if logfileName.lower() == GLOB.logfileName.lower():
      return
    
    # Update global log filename.
    GLOB.logfileName = logfileName

    # Save the startup buffer to the logfile.
    self.flushStartupBufferToFile()

    # Show message?  
    if showMsg and (GLOB.logfileName == ""):
      self.info("New Logfile: %s" % logfileName)
      
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------

# Create the logger.
logger = Logger()

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  
  import GlobioModel.Core.Logger as Log
  
  GLOB.logToFile = True

  logger.reset()

  print(logger.getFullLogFileName())
    
  Log.info("ok")
  
  Log.incIndent()
  Log.info("----")
  Log.decIndent()
  
  try:
    Err.raiseSyntaxError(Err.FileNotFound1, None, "sdasdasd.dat")
  except:
    Log.err()
