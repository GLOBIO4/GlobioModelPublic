# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************
#---------------------------------------------------------------------------------
# Modified: 27 nov 2016, ES, ARIS B.V.
#           - __init__ modified, precision added.
#           - elapsedStr modified, precision added.
#           7 dec 2020, ES, ARIS B.V.
#           - Version 4.1.0
#           - several methods modified because of self.stopTime.
#---------------------------------------------------------------------------------

import time
import GlobioModel.Common.Utils as UT

#---------------------------------------------------------------------------------
class Timer(object):
  
  precision = 3
  
  #-------------------------------------------------------------------------------
  def __init__(self,precision=3):
    self.precision = precision
    self.startTime = time.time()
    self.stopTime = None

  #-------------------------------------------------------------------------------
  def elapsed(self):
    if self.stopTime is None:
      self.stopTime = time.time()
    secs = self.stopTime - self.startTime
    self.startTime = time.time()
    self.stopTime = None
    return secs

  #-------------------------------------------------------------------------------
  def elapsedStr(self,Nl = False):
    return UT.sec2str(self.elapsed(),Nl,self.precision)

  #-------------------------------------------------------------------------------
  def show(self,title="",precision=3):
    self.precision = precision
    print(title + self.elapsedStr())

  #-------------------------------------------------------------------------------
  def reset(self):
    self.stopTime = None
    self.startTime = time.time()

  #-------------------------------------------------------------------------------
  def start(self):
    self.stopTime = None
    self.startTime = time.time()

  #-------------------------------------------------------------------------------
  def stop(self):
    self.stopTime = time.time()

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":

  nmax = 1000*100
  cnt = 0

  pTim = Timer()
  
  for i in range(nmax):
    cnt += 1
  pTim.show()
  for i in range(nmax):
    cnt += 1
  pTim.show()
  
  for i in range(nmax):
    cnt += 1
  print(pTim.elapsedStr())
  for i in range(nmax):
    cnt += 1
  print(pTim.elapsedStr())
  
