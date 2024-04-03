# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Remarks :
#           - The monitor is started as a separate thread/process.
#           - The monitor itself can take quite some memory resources!!!
#   
# Modified: 13 sep 2017, ES, ARIS B.V.
#           - Version 4.0.9
#           - cleanup added.
#-------------------------------------------------------------------------------

import os
import platform
import multiprocessing as MP
import time

import GlobioModel.Core.Globals as GLOB

import GlobioModel.Common.Utils as UT

monitor = None

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Monitor(object):

  logger = None
  rootDir = None
  intervalSec = 1
  indent = ""
  prefix = ""
  process = None
  quiet = True

  startMemAvail = -1
  startDiskAvail = -1

  valMinMemAvail = None
  valMinDiskAvail = None
  
  #------------------------------------------------------------------------------
  def __init__(self,logger=None,rootDir=None,intervalSec=1,indent="",prefix="",quiet=True):
    self.logger = logger
    self.rootDir = rootDir
    self.intervalSec = intervalSec
    self.indent = indent
    self.prefix = prefix
    self.quiet = quiet

  #-------------------------------------------------------------------------------
  # Show start memory and disk usage info.
  def showStartMemDiskUsage(self):
    # Get memory data.
    memTotalStr = UT.bytesToStr(UT.memPhysicalTotal())
    memInUseStr = UT.bytesToStr(UT.memPhysicalUsed())
    memAvailStr = UT.bytesToStr(self.startMemAvail)
    msg = "%s%sMemory total/inuse/available: %s   %s   %s" % \
                   (self.indent,self.prefix,memTotalStr,memInUseStr,memAvailStr)
    if not self.logger is None:
      self.logger.info(msg)
    else:
      print(msg)
    # Show disk usage?
    if self.startDiskAvail >= 0:
      startDiskAvailStr = UT.bytesToStr(self.startDiskAvail)
      msg = "%s%sDisk space available        : %s" % \
                                     (self.indent,self.prefix,startDiskAvailStr)
      if not self.logger is None:
        self.logger.info(msg)
      else:
        print(msg)

  #-------------------------------------------------------------------------------
  def showUsedMemDiskUsage(self):
    # Show memory usage.
    memUsed = self.startMemAvail - self.valMinMemAvail.value
    if memUsed < 0:
      memUsed = 0
    memUsedStr = UT.bytesToStr(memUsed)
    msg = "%s%sMemory used    : %s" % (self.indent,self.prefix,memUsedStr)
    if not self.logger is None:
      self.logger.info(msg)
    else:
      print(msg)
    # Show disk usage?
    if self.startDiskAvail >= 0:
      diskUsed = self.startDiskAvail - self.valMinDiskAvail.value
      if diskUsed < 0:
        diskUsed = 0
      diskUsedStr = UT.bytesToStr(diskUsed)
      msg = "%s%sDisk space used: %s" % (self.indent,self.prefix,diskUsedStr)
      if not self.logger is None:
        self.logger.info(msg)
      else:
        print(msg)

  #-------------------------------------------------------------------------------
  def start(self):
    # Save available memory usage at start.
    self.startMemAvail = UT.memPhysicalAvailable()

    # Get current available memory.
    self.valMinMemAvail = MP.Value("d",0.0)
    self.valMinMemAvail.value = UT.memPhysicalAvailable()

    # Valid root dir?
    # 20201118
    #if (self.rootDir<>"") and (os.path.isdir(self.rootDir)):
    if (self.rootDir != "") and (os.path.isdir(self.rootDir)):
      # Save available disk space usage at start.
      self.startDiskAvail = UT.diskSpaceAvailable(self.rootDir)
      # Get current available disk space.
      self.valMinDiskAvail = MP.Value("d",0.0)
      self.valMinDiskAvail.value = UT.diskSpaceAvailable(self.rootDir)

    # Show memory and disk usage at start.
    self.showStartMemDiskUsage()
    
    # Create the monitor process task.
    args = (self.rootDir,self.intervalSec,self.valMinMemAvail,self.valMinDiskAvail,
            self.quiet,self.indent,self.prefix)
    self.process = MP.Process(target=task,args=args)

    # Start the monitor process task.
    self.process.start()

  #-------------------------------------------------------------------------------
  def stop(self):
    if not self.process is None:
      self.process.terminate()

#---------------------------------------------
# Define the monitor task.
def task(rootDir,intervalSec,minMemAvail,minDiskAvail,
         quiet,indent,prefix):
  while True:
    # Get available memory.
    memAvail = UT.memPhysicalAvailable()
    # Update minimal available memory.
    if memAvail < minMemAvail.value:
      minMemAvail.value = memAvail
    # Show info?
    if not quiet:
      minMemAvailStr = UT.bytesToStr(minMemAvail.value)
      print("%s%sMemory available    : %s" % (indent,prefix,minMemAvailStr))
    # Valid root dir?
    # 20201118
    #if (rootDir<>"") and (os.path.isdir(rootDir)):
    if (rootDir!="") and (os.path.isdir(rootDir)):
      # Get available disk space.
      diskAvail = UT.diskSpaceAvailable(rootDir)
      # Update minimal available disk space.
      if diskAvail < minDiskAvail.value:
        minDiskAvail.value = diskAvail
      # Show info?
      if not quiet:
        minDiskAvailStr = UT.bytesToStr(minDiskAvail.value)
        print("%s%sDisk space available: %s" % (indent,prefix,minDiskAvailStr))
    # Wait a while.
    time.sleep(intervalSec)

#-------------------------------------------------------------------------------
# Show start or used memory and disk space usage info.
# Creates a monitor when not aleady created.
def showMemDiskUsage(logger=None,indent="",prefix="",rootDir=None,intervalSec=1,quiet=True):
  global monitor
  
  # Monitor not enabled?
  if not GLOB.monitorEnabled:
    return
  
  # First time?
  if monitor is None:
    # Get root dir.
    if rootDir is None:
      if platform.system() == "Windows":
        rootDir = "C:\\"
      else:
        rootDir = "/"
    # Create the monitor.
    monitor = Monitor(logger,rootDir,intervalSec,indent,prefix,quiet)
    # Start the monitor and show memory and disk usage.
    monitor.start()
  else:
    # Check the monitor.
    if monitor is None:
      return
    # Stop the monitor.
    monitor.stop()
    # Show used memory and disk.
    monitor.showUsedMemDiskUsage()
    # Cleanup monitor.
    monitor = None

#-------------------------------------------------------------------------------
# Cleanup monitor without showing results.
def cleanup():
  global monitor
  # Check the monitor.
  if monitor is None:
    return
  # Stop the monitor.
  monitor.stop()
  # Cleanup monitor.
  monitor = None

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  
  #-----------------------------------------------------------------------------
  def test():
    
    #rootDir = None
    rootDir = "/data"
    #quiet = False
    quiet = True

    print("-" * 80)
    showMemDiskUsage(rootDir=rootDir,quiet=quiet)
    
    maxCnt = 5
    #maxCnt = 20
    #maxCnt = 100
    for _ in range(maxCnt):
      _ = "-" * (1000 * 1000 * 1000)
      time.sleep(1)

    print("-" * 80)
    showMemDiskUsage()
    print("-" * 80)

  #-----------------------------------------------------------------------------
  test()
