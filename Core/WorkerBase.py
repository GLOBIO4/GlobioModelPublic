# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 21 nov 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           - __init__ modified, useAll=False.
#           10 feb 2019, ES, ARIS B.V.
#           - Version 4.0.12
#           - WorkerProgress - progress modified, now with % 10.
#           - joinDictChunksSum modified, now with "key in".
#           - getParts removed, was not ok.
#           - getWorkMultilineSubLists added.
#           - getWorkFragmentSubLists added.
#           18 sep 2020, ES, ARIS B.V.
#           - Version 4.0.15
#           - WorkerBase.__init__ modified.
#           4 dec 2020, ES, ARIS B.V.
#           - Version 4.1.0
#           - RasterSH added, because shared global vars doesn't work anymore.
#           - SharedData added, because shared global vars doesn't work anymore.
#-------------------------------------------------------------------------------

import sys

import logging
import multiprocessing as mp
import numpy as np

from shapely.geometry import box
from shapely.strtree import STRtree

import GlobioModel.Core.Logger as Log

import GlobioModel.Common.Utils as UT
import GlobioModel.Core.RasterUtils as RU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
# A wrapper for the Raster class, used as a lighweight class to share rasters
# between pool/worker subprocesses.
# Using the original Raster class results in WINAPI errors, cause by GDAL objects?
class RasterSH:
  raster = None
  extent = None
  cellSize = None
  nrCols = None
  nrRows = None
  dataType = None
  noDataValue = 0
  #-----------------------------------------------------------------------------
  def __init__(self,raster):
    self.raster = raster.raster
    self.extent = raster.extent
    self.cellSize = raster.cellSize
    self.nrCols = raster.nrCols
    self.nrRows = raster.nrRows
    self.dataType = raster.dataType
    self.noDataValue = raster.noDataValue
  #-------------------------------------------------------------------------------
  # Shortcut to self.raster.
  @property
  def r(self):
    return self.raster

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
# A class to share global data between pool/worker subprocesses.
# class SharedData:
#   zoneRaster = None
#   valueRaster = None
#   areaRaster = None
#   labelRaster = None
#   catchRaster = None
#   catchRCIDict = None
#   damTree = None
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class SharedData:
  zoneRaster: RasterSH = None
  valueRaster: RasterSH = None
  areaRaster: RasterSH = None
  labelRaster: RasterSH = None
  catchRaster: RasterSH = None
  catchRCIDict: dict = None
  damTree = None
  riverTree = None

# #-------------------------------------------------------------------------------
# #-------------------------------------------------------------------------------
# # A wrapper for Raster objects for creating multiprocessing shared arrays
# # which can be accessed by multiple processes.
# class SharedRaster:
#   extent = None
#   cellSize = None
#   nrCols = None
#   nrRows = None
#   noDataValue = 0
#   raster = None
#   shArray = None
#   npArray = None
#   #-----------------------------------------------------------------------------
#   def __init__(self,raster=None):
#     # Check raster.
#     if raster is None:
#       return
#     # Set extent.
#     self.extent = raster.extent
#     # Set cellSize.
#     self.cellSize = raster.cellSize
#     # Set nrCols.
#     self.nrCols = raster.nrCols
#     # Set nrRows.
#     self.nrRows = raster.nrRows
#     # Set nodata value.
#     self.noDataValue = raster.noDataValue
#     # Set raster.
#     self.raster = raster
#     # Get ctype.
#     cType = RU.dataTypeNumpyToC(raster.dataType)
#     # Create shared array space.
#     self.shArray = mp.Array(cType,raster.r.size)
#     # Convert to numpy array space.
#     self.npArray = np.frombuffer(self.shArray.get_obj(),raster.dataType)
#     # Copy raster data to shared space.
#     self.npArray[:] = raster.r.flatten()
#
#   #-------------------------------------------------------------------------------
#   @property
#   def r(self):
#     if not self.npArray is None:
#       return self.npArray.reshape(self.raster.nrRows,self.raster.nrCols)
#     else:
#       return None

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class WorkerProgress(object):
  lock = None
  coreId = None
  coreIdStr = ""
  progCount = None
  progPrevPerc = None
  progTotalCount = None
  progResolution = 1
  #-------------------------------------------------------------------------------
  def __init__(self,lock,coreId,totalCount,resolution=1):
    self.lock = lock
    self.coreId = coreId
    self.progCount = 1
    self.progPrevPerc = None
    self.progTotalCount = totalCount
    self.progResolution = resolution
    if self.coreId is None:
      self.coreIdStr = ""
    else:
      self.coreIdStr = "%2s - " % self.coreId
  #-------------------------------------------------------------------------------
  def progress(self):
    # Calculate percentage.
    perc = UT.trunc(self.progCount / float(self.progTotalCount) * 100)
    
    # Check resolution and percentage.
    # 20201118
    #if self.progResolution <> 1:
    if self.progResolution != 1:
      # 20201118
      #if perc % self.progResolution <> 0:
      if perc % self.progResolution != 0:
        return
    
    self.progCount += 1
    # 20201118
    #if perc <> self.progPrevPerc:
    if perc != self.progPrevPerc:
      if not self.lock is None:
        self.lock.acquire()
      # Don't add progress to log.
      #Log.info("".join(["  ",self.coreIdStr,"Progress ",str(perc),"%..."]))
      sys.stdout.write("".join(["  ",self.coreIdStr,"Progress ",str(perc),"%...\r"]))
      sys.stdout.flush()
      if not self.lock is None:
        self.lock.release()
      self.progPrevPerc = perc

#-------------------------------------------------------------------------------
# Helper function.
def calculate(arg,**kwarg):
  return WorkerBase.calculate(*arg,**kwarg)    

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class WorkerBase(object):

  debug = False
  logger = None
  nrOfCores = 0

  showProgress = False
  lock = None
  
  #-------------------------------------------------------------------------------
  # nrOfCores: The number of cores to be used. 
  #  >=1 = This number of cores will be used.
  #  0   = All number of available cores will be used.
  #  <0  = All number of available cores will be used minus the specified number.
  def __init__(self,nrOfCores):
    self.debug = False
    self.logger = None
    self.showProgress = False
    self.lock = None
    
    print("WorkerBase - cpu_count() = %s" % mp.cpu_count())

    # Set number of cores.
    if nrOfCores==0:
      # Use all avialable cores.
      self.nrOfCores = mp.cpu_count()
    elif nrOfCores<0:
      # Use all avialable cores minus the number specified.
      self.nrOfCores = mp.cpu_count()
      self.nrOfCores += nrOfCores
      # 20201204
      # if nrOfCores < 1:
      #   self.nrOfCores = 1
      if self.nrOfCores < 1:
        self.nrOfCores = 1
    else:
      # Use the specified number of cores. 
      self.nrOfCores = nrOfCores
      if self.nrOfCores > mp.cpu_count():
        self.nrOfCores = mp.cpu_count()
        
#   #-------------------------------------------------------------------------------
#   # nrOfCores: When set this number of cores will be used, else the number
#   #            of available cores.
#   # useAll: When True all available cores are used, else all minus one.
#   #         This param is only used when nrOfCores=0.
#   def __init__(self,nrOfCores=0,useAll=False):
#     self.debug = False
#     self.logger = None
#     self.showProgress = False
#     self.lock = None
#     
#     # Set number of cores.
#     if nrOfCores==0:
#       # Set number of cores.
#       self.nrOfCores = mp.cpu_count()
#       # Don't use all cores.
#       if not useAll:
#         # More than 1 core?
#         if self.nrOfCores > 1:
#           # Leave one for other tasks.
#           self.nrOfCores -= 1
#     else:
#       # Set specified number of cores. 
#       if nrOfCores > mp.cpu_count():
#         self.nrOfCores = mp.cpu_count()
#       else:
#         self.nrOfCores = nrOfCores

  #-------------------------------------------------------------------------------
  # The worker function. 
  def calculate(self,args):
    pass

  #-------------------------------------------------------------------------------
  # Show debug message.
  def dbgPrint(self,s,indent="  "):
    if not self.debug:
      return
    Log.info("%s# %s" % (indent,s))

  #-------------------------------------------------------------------------------
  def enableLogging(self,flag=True):
    self.logger = mp.log_to_stderr()
    if flag:
      self.logger.setLevel(logging.DEBUG)  
    else:
      self.logger.setLevel(logging.INFO)  

  #-------------------------------------------------------------------------------
  # Returns a lock for syncing process actions.
  def getLock(self):
    if self.lock is None:
      # 20201118
      #self.lock = mp.Manager().Lock()
      self.lock = mp.Lock()
    return self.lock
  
  #-------------------------------------------------------------------------------
  # Divides a sequence as good as posible in equal sized parts.
  # Returns a tuple with the offset of the first element in the parts, and with
  # the sizes of the parts.
  # length:    length of the sequence (i.e. array or raster rows).
  # nrOfParts: number of parts.
  def getOffsetsAndSizes(self,length,nrOfParts):
    k, m = divmod(length,nrOfParts)
    nrOfParts = min(length,nrOfParts)
    # 20201118
    #offsets = [i * k + min(i, m) for i in xrange(nrOfParts)]
    offsets = [i * k + min(i, m) for i in range(nrOfParts)]
    sizes = np.diff(offsets).tolist()
    sizes = sizes + [length-offsets[-1]]
    return offsets,sizes

  #-------------------------------------------------------------------------------
  # Returns a list of fragments sublists.
  # The fragment multilines are distributed over the sublists so that
  # the longest ones are in different sublists and will be processed by
  # different cores.
  # The fragments in each sublist are sorted from long to short so
  # that long lines are processed first.  
  def getWorkFragmentSubLists(self,fragments,nrOfChunks):
    # Sort the fragments from short to long (i.e. from few to many segments).
    sortedFragments = sorted(fragments,key=lambda frag: len(frag.line.geoms))
    # Create the sublists.
    subLists = []
    for _ in range(nrOfChunks):
      subLists.append([])
    idx = 0
    # Distribute the fragments over the sublists.
    for fragment in sortedFragments:
      subLists[idx].append(fragment)
      idx += 1
      if idx >= nrOfChunks:
        idx = 0
    # Reverse the sublists.    
    for subList in subLists:
      subList.reverse()
    return subLists

  #-------------------------------------------------------------------------------
  # Returns a list of multiline sublists.
  # The multilines are distributed over the sublists so that the longest ones
  # are in different sublists and will be processed by different cores.
  # The lines in each sublist are sorted from long to short so that long lines
  # are processed first.  
  def getWorkMultilineSubLists(self,multiLines,nrOfChunks):
    # Sort the lines from short to long (i.e. from few to many segments).
    sortedMultiLines = sorted(multiLines,key=lambda ml: len(ml.geoms))
    # Create the sublists.
    subLists = []
    for _ in range(nrOfChunks):
      subLists.append([])
    idx = 0
    # Distribute the lines over the sublists.
    for multiLine in sortedMultiLines:
      subLists[idx].append(multiLine)
      idx += 1
      if idx >= nrOfChunks:
        idx = 0
    # Reverse the sublists.    
    for subList in subLists:
      subList.reverse()
    return subLists
 
  #-------------------------------------------------------------------------------
  # Returns a list of sublists.
  def getWorkSubLists(self,fullList,nrOfChunks):
    # Split the list in parts.
    offsets,sizes = self.getOffsetsAndSizes(len(fullList),nrOfChunks)
    # Create list of sub lists.
    subLists = []
    for i in range(len(offsets)):
      offset = offsets[i]
      size = sizes[i]
      subLists.append(fullList[offset:offset+size][:])
    return subLists   

  #-------------------------------------------------------------------------------
  # Divides the extent in nrOfChunks bands of horizontal workextents.
  def getWorkExtents(self,extent,cellSize,nrOfChunks):
      
    # Get total number of vertical cells.
    _,totNrCells = RU.calcNrColsRowsFromExtent(extent,cellSize)
  
    # Divide total of vertical cells in almost equal parts.
    _,chunks = self.getOffsetsAndSizes(totNrCells,nrOfChunks)
  
    # Create list of working extents.
    yMin = extent[1]
    workExtents = []
    for vertSize in chunks:
      yMax = yMin + vertSize * cellSize
      workExtent = [extent[0],yMin,extent[2],yMax]
      workExtents.append(workExtent)
      yMin = yMax
    
    return workExtents   

  #-------------------------------------------------------------------------------
  # Get a list with per workextent a list of SHAPELY features.
  # A feature can be in more then one workfeature list.
  # Result:
  #   [[feat1,feat2],[feat2,feat3],[feat4,feat5]...]
  def getWorkFeatures(self,workExtents,features):
    # Create feature tree.
    featureTree = STRtree(features)
    # Get features within working extents.
    workFeaturesList = [featureTree.query(box(x1,y1,x2,y2)) for x1,y1,x2,y2 in workExtents]
    return workFeaturesList

  #-------------------------------------------------------------------------------
  # Get a list ids of the workfeatures.
  # Result:
  #   [[feat-id1,feat-id2],[feat-id2,feat-id3],[feat-id4,feat-id5]...]
  def getWorkFeatureIds(self,workFeaturesList):
    idsList = []
    for i in range(len(workFeaturesList)):
      ids = []
      for wf in workFeaturesList[i]:
        ids.append(wf.id)
      idsList.append(ids)
    return idsList
  
  #-------------------------------------------------------------------------------
  # Join the numpy arrays to one array.
  def joinArrays(self,results):
    return np.concatenate(results)

  #-------------------------------------------------------------------------------
  # Join the dict chunks. They should have no key overlap!
  def joinDictChunks(self,results):
    allResults = results[0].copy()
    for i in range(1,len(results)):
      allResults.update(results[i])
    return allResults

  #-------------------------------------------------------------------------------
  # Join the dict chunks to one dict by summing the values.
  def joinDictChunksSum(self,valueDicts):
    # Check.
    if len(valueDicts)==0:
      return dict()
    if len(valueDicts)==1:
      return dict(valueDicts[0])
    # Copy the first valueDict.
    joinDict = dict(valueDicts[0])
    # Combine next valueDicts.
    for i in range(1,len(valueDicts)):
      # 20201204
      #for key,value in valueDicts[i].iteritems():
      for key,value in valueDicts[i].items():
        # Check key.
        if key in joinDict:
          joinDict[key] += value
        else:
          joinDict[key] = value
    return joinDict

  #-------------------------------------------------------------------------------
  def joinListChunks(self,results):
    allResults = []
    for result in results:
      allResults += list(result)
    return allResults

  #-------------------------------------------------------------------------------
  # Join the raster chunks to one raster.
  def joinRasterChunks(self,extent,cellSize,rasterChunks,reverse=False):
    # Get nrCols and nrRows.    
    nrCols,nrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)
    # Reverse?
    if reverse:
      # The first one contains the results from the lowest extent, so reverse.
      rasterChunks.reverse()
    # Combine raster chunks and reshape.
    ras = np.concatenate(rasterChunks)
    ras.reshape(nrRows,nrCols)
    return ras
  
  #-------------------------------------------------------------------------------
  # Join the results to one array.
  def joinResults(self,results):
    if type(results) is list:
      allResults = []
      for result in results:
        allResults += list(result) 
      return allResults
    else:
      return np.concatenate(results)

  #-------------------------------------------------------------------------------
  def msgInfo(self,msg):
    if not self.logger is None:
      self.logger.info(msg)

  #-------------------------------------------------------------------------------
  def run(self):
    pool = None
    try:
      args = []
      pool = mp.Pool(processes=self.nrOfCores)
      results = pool.map(calculate,zip([self]*len(args),args))
      results = self.joinResults(results)
      return results
    except KeyboardInterrupt:
      if not pool is None:
        print("^C received, shutting down the workers.")
        pool.close()
        pool.terminate()
        # noinspection PyUnusedLocal
        pool = None
      return None
