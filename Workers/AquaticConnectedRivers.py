# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Creates from a list of separate lines a list of multilines where each 
# multiline is a set of connected lines.
# All multilines and sublines are labled with an unique id.
#
# Modified: 24 nov 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           18 sep 2020, ES, ARIS B.V.
#           - Version 4.0.15
#           - __init__ modified.
#           9 dec 2020, ES, ARIS B.V.
#           - Version 4.1.0.
#           - Use of sharedDataSH etc. added.
#-------------------------------------------------------------------------------

import multiprocessing as mp

from shapely.geometry import Point,MultiLineString
from shapely.strtree import STRtree

import GlobioModel.Core.Logger as Log

from GlobioModel.Core.WorkerBase import WorkerBase
from GlobioModel.Core.WorkerBase import SharedData
import GlobioModel.Core.VectorUtils as VU

# Shared data for multiprocessing.
# TODO: Initialize with None???
sharedDataSH: SharedData

# # Multiprocessing shared river tree.
# riverTreeSH = None

#-------------------------------------------------------------------------------
# Helper function.
# Creates a global variable to share data between pool subprocesses.
def initPool(sharedData):
  global sharedDataSH
  sharedDataSH = sharedData

#-------------------------------------------------------------------------------
# Helper function.
def calculate(arg,**kwarg):
  return AquaticConnectedRivers.calculate(*arg,**kwarg)    

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class AquaticConnectedRivers(WorkerBase):
  """
  Converts connected riversegments to rivers (multi-lines).
  """

  #-------------------------------------------------------------------------------
  def __init__(self,nrOfCores):
    super(AquaticConnectedRivers,self).__init__(nrOfCores)

  #-------------------------------------------------------------------------------
  # Returns all lines in the lineTree which are connected to the input line.
  # The input line is NOT included in the found lines.  
  # This method runs without recusion.
  # searchDist - max. distance to search for connected lines.
  def getConnectedLines(self,line,lineTree,searchDist,processedProp="processed"):
  
    # Set the id.
    setattr(line,processedProp,1)
      
    # Create lists.
    foundLines = []

    # Init list with line.
    processLines = [line]
        
    # Loop while there are lines to process.
    while len(processLines)>0:
  
      # Get last line and remove.    
      processLine = processLines.pop()
      
      # Get begin and endpoint of line.
      lineBeginPnt = VU.shpLineGetBeginPoint(processLine)
      lineEndPnt = VU.shpLineGetEndPoint(processLine)

      # Get lines connected to the beginpoint and process.
      connectedLines = lineTree.query(lineBeginPnt)
      for connectedLine in connectedLines:
        # Already processed?
        if hasattr(connectedLine,processedProp):
          continue
        # Double check connected line. Get minimum distance to found line.
        dist = processLine.distance(connectedLine)
        # Distance greater than search distance?
        if dist > searchDist:
          # Ignore line (so not connected).
          continue
        # Set processed property.
        setattr(connectedLine,processedProp,1)
        # Append to foundlines.
        foundLines.append(connectedLine)
        # Append to line to be processed.
        processLines.append(connectedLine)
  
      # Get lines connected to the endpoint and process.
      connectedLines = lineTree.query(lineEndPnt)
      for connectedLine in connectedLines:
        # Already processed?
        if hasattr(connectedLine,processedProp):
          continue
        # Double check connected line. Get minimum distance to found line.
        dist = processLine.distance(connectedLine)
        # Distance greater than search distance?
        if dist > searchDist:
          # Ignore line (so not connected).
          continue
        # Set processed property.
        setattr(connectedLine,processedProp,1)
        # Append to foundlines.
        foundLines.append(connectedLine)
        # Append to line to be processed.
        processLines.append(connectedLine)
  
    return foundLines

  #-------------------------------------------------------------------------------
  # Get corresponding line (same coordinates) in tree.
  def treeGetLine(self,tree,line):
    beginPnt = Point(line.coords[0])
    tmpLines = tree.query(beginPnt)
    for tmpLine in tmpLines:
      if tmpLine.__eq__(line):
        return tmpLine
    return None
  
  #-------------------------------------------------------------------------------
  def calculate(self,args):
    # 20201209
    #global riverTreeSH
    global sharedDataSH

    # Get arguments.
    # 20201118
    #coreId = args[0]
    cellSize = args[1]
    damLines = args[2]

    # 20201209
    #lineTree = riverTreeSH
    lineTree = sharedDataSH.riverTree

    searchDist = cellSize / 2.0
    
    # Loop lines with dams.
    multiLines = []
    for line in damLines:
      
      # Get same line from tree.
      line = self.treeGetLine(lineTree,line)
      if line is None:
        print("  ### No corresponding damline found in tree. Skipping damline.")
        continue
      
      # Not already connected?
      if not hasattr(line,"processed"):
        # Add current line to list.
        subLines = [line]
        # Get connected lines.
        connectedLines = self.getConnectedLines(line,lineTree,searchDist)
        subLines.extend(connectedLines)
        # Create multiline.        
        multiLine = MultiLineString(subLines)
        # Add to list.
        multiLines.append(multiLine)
      else:
        pass
        #print "  ## DamLine already processed."
    
    return (multiLines,)

  #-------------------------------------------------------------------------------
  # nrOfChunks: number of parts in with the data is devided.
  #             If 0 then nrOfChunks is the same as the nrOfCores.
  def run(self,extent,cellSize,lines,nrOfChunks=0):
    # 20201209
    #global riverTreeSH
    pool = None
    try:

      # Check nrOfChunks.
      if nrOfChunks==0:
        nrOfChunks = self.nrOfCores

      self.dbgPrint("  Getting rivers in extent...")

      # Create line tree and get worklines within extent.
      lineTree = STRtree(lines)
      extentLines = lineTree.query(VU.shpPolygonFromBounds(extent))
      
      self.dbgPrint("  Found rivers in extent: %s" % (len(extentLines)))

      # 20201209
      # # Create new line tree and set shared tree.
      # lineTree = STRtree(extentLines)
      # riverTreeSH = lineTree

      # 20201209
      # Create new line tree and set shared tree.
      lineTree = STRtree(extentLines)
      sharedData = SharedData()
      sharedData.riverTree = lineTree

      # Get rivers connected to dams.
      damLines = []
      for line in extentLines:
        if line.Connected == 1:
          damLines.append(line)
          
      self.dbgPrint("  Found rivers with dams: %s" % (len(damLines)))

      Log.info("  Preparing...")
      
      # Split the damLines in parts.
      workDamLines = self.getWorkSubLists(damLines,nrOfChunks)
      
      # Create the input list with tuples of (id,cellSize,lines).
      args = []
      for i in range(len(workDamLines)):
        args.append([i,cellSize,workDamLines[i]])

      #---------------------------------------------------------------------------
      # Calculate. 
      #---------------------------------------------------------------------------

      Log.info("  Starting calculation...")
    
      # Create the pool.
      # 20201209
      #pool = mp.Pool(processes=self.nrOfCores)
      pool = mp.Pool(processes=self.nrOfCores,
                     initializer=initPool, initargs=(sharedData,))
      results = pool.map(calculate,zip([self]*len(args),args))
      
      self.dbgPrint("  Results found: %s" % len(results))

      #---------------------------------------------------------------------------
      # Process results. 
      #---------------------------------------------------------------------------

      # The results are a list of (multiLine Chunks) tuples. Get separate results.
      multiLineChunks = [r[0] for r in results]
      self.dbgPrint("  Multiline chunks found: %s" % len(multiLineChunks))

      # Merge the list.
      multiLines = self.joinListChunks(multiLineChunks)
      self.dbgPrint("  Multilines found: %s" % len(multiLines))

      #---------------------------------------------------------------------------
      # When using multiprocessing duplicate rivers can be created. Remove 
      # duplicates.  
      #---------------------------------------------------------------------------

      self.dbgPrint("  Removing duplicate multilines...")
      
      # Create list.
      totalMultiLines = []
      # Create tree.
      lineTree = STRtree(totalMultiLines)
      
      minDist = cellSize / 10.0
      for multiLine in multiLines:
        # No overlap thus check only one segment.
        segm = multiLine.geoms[0]
        # Find from start point.
        foundLines = lineTree.query(Point(segm.coords[0]))
        if len(foundLines)==0:
          # Find from end point.
          foundLines = lineTree.query(Point(segm.coords[-1]))
        # No lines found?
        if len(foundLines)==0:
          # Add line.
          totalMultiLines.append(multiLine)
          # Update tree.
          lineTree = STRtree(totalMultiLines)
        else:
          # Contains same line?
          found = False
          for foundLine in foundLines:
            dist = foundLine.distance(multiLine)
            if dist < minDist:
              found = True
              break
          # Not found?
          if not found:
            # Add line.
            totalMultiLines.append(multiLine)
            # Update tree.
            lineTree = STRtree(totalMultiLines)
            
      self.dbgPrint("  Total multilines found: %s" % len(totalMultiLines))
      
      return totalMultiLines

    except KeyboardInterrupt:
      if not pool is None:
        print("^C received, shutting down the workers.")
        pool.close()
        pool.terminate()
        pool = None
      return []
