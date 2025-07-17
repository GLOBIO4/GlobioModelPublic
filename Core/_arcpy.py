#
# Dummy arcpy file.
#
# Usage:
#   import GlobioModel.Core._arcpy as arcpy
#

class Info:
  noDataValue = 1
  height = 1
  # def getOutput(self,index):
  #   return ""

class PropResult:
  def getOutput(self,index):
    return ""

class Raster:
  def save(self,arg1):
    pass

class GP:
  def EucDistance_sa(self,arg1,arg2,arg3,arg4):
    pass
  def ExtractByAttributes_sa(self,arg1,arg2,arg3):
    pass
  def Minus_sa(self,arg1,arg2,arg3):
    pass  
  def Plus_sa(self,arg1,arg2,arg3):
    pass
  def RasterCalculator_sa(self,arg1,arg2):
    pass
  def Times_sa(self,arg1,arg2,arg3):
    pass

class SA:
  def CreateRandomRaster(self,arg1,arg2,arg3):
    return Raster()
  def Int(self,arg1):
    return Raster()

class ENV:
  extent = None
  cellSize = None

def CheckOutExtension(arg1):
  pass

def CopyRaster_management(arg1,arg2,arg3,arg4,arg5,arg6,arg7,arg8,arg9,arg10):
  pass

def Delete_management(arg1):
  pass

def Describe(arg1):
  return Info()

def Exists(arg1):
  return True

def Extent(arg1,arg2,arg3,arg4):
  return ()

def GetRasterProperties_management(arg1,arg2):
  return PropResult()

gp = GP()

sa = SA()

env = ENV()

