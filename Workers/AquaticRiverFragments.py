# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 24 nov 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           19 dec 2018, ES, ARIS B.V.
#           - run aangepast ivm. VU.shpPolygonFromBounds.
#           18 jan 2019, ES, ARIS B.V.
#           - Version 4.0.12
#           - calculate - degreeToKM_v2 replaced with degreeToKM.
#           18 sep 2020, ES, ARIS B.V.
#           - Version 4.0.15
#           - __init__ modified.
#           9 dec 2020, ES, ARIS B.V.
#           - Version 4.1.0.
#           - run modified, list(map(..)) added.
#           - Use of sharedDataSH etc. added.
#-------------------------------------------------------------------------------

import multiprocessing as mp

from shapely.geometry import MultiLineString
from shapely.strtree import STRtree

import GlobioModel.Core.Logger as Log
import GlobioModel.Core.RasterUtils as RU
from GlobioModel.Core.WorkerBase import WorkerBase
from GlobioModel.Core.WorkerBase import SharedData
import GlobioModel.Core.VectorUtils as VU

# Shared data for multiprocessing.
# TODO: Initialize with None???
sharedDataSH: SharedData

# # Multiprocessing shared dam tree.
# damTreeSH = None

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class River(object):
  rivId = None
  line = None
  #-------------------------------------------------------------------------------
  def __init__(self,rivId,line):
    self.rivId = rivId
    self.line = line

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Fragment(object):
  rivId = None
  fragId = None
  line = None
  lengthKM = None
  #-------------------------------------------------------------------------------
  def __init__(self,rivId,fragId,line,lengthKM):
    self.rivId = rivId
    self.fragId = fragId
    self.line = line
    self.lengthKM = lengthKM

#-------------------------------------------------------------------------------
# Helper function.
# Creates a global variable to share data between pool subprocesses.
def initPool(sharedData):
  global sharedDataSH
  sharedDataSH = sharedData

#-------------------------------------------------------------------------------
# Helper function.
def calculate(arg,**kwarg):
  return AquaticRiverFragments.calculate(*arg,**kwarg)    

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class AquaticRiverFragments(WorkerBase):
  """
  Creates river fragments (i.e. parts separated by dams) from river segments.
  """

  #-------------------------------------------------------------------------------
  def __init__(self,nrOfCores):
    super(AquaticRiverFragments,self).__init__(nrOfCores)

  #-------------------------------------------------------------------------------
  # Get connected segments to start point. Stops at endpoints or at dam.
  def getConnectedLines(self,startPnt,segmentTree,damTree,
                        searchDist,processedProp="processed"):
  
    # Create segments.
    connectedSegments = []

    # Init list with startPnt.
    processPnts = [startPnt]
        
    # Loop while there are points to process.
    while len(processPnts)>0:
  
      # Get last point and remove.    
      processPnt = processPnts.pop()

      # Check if point is dam.
      queryDams = damTree.query(processPnt.buffer(searchDist,1))
      damFound = False
      #  print "  queryDams %s" % len(queryDams)
      for queryDam in queryDams:
        # Check found dam. Get distance to processPnt.
        dist = queryDam.distance(processPnt)
        # Distance less than search distance?
        if dist < searchDist:
          damFound = True
          break

      # Dam found?
      if damFound:
        # Continue with next point.
        continue
      
      # Get segments connected to the processPnt.
      querySegments = segmentTree.query(processPnt)
      for querySegment in querySegments:
        # Already processed?
        if hasattr(querySegment,processedProp):
          continue
        # Double check connected segments. Get minimum distance to found segment.
        dist = processPnt.distance(querySegment)
        # Distance greater than search distance?
        if dist > searchDist:
          # Ignore segment (so not connected).
          continue
        # Set processed property.
        setattr(querySegment,processedProp,1)
        # Append to foundlines.
        connectedSegments.append(querySegment)
        # Append begin- and endpoint of segement to be processed.
        processPnts.append(VU.shpLineGetBeginPoint(querySegment))
        processPnts.append(VU.shpLineGetEndPoint(querySegment))
  
    return connectedSegments

  #-------------------------------------------------------------------------------
  # Returns a list of Fragment objects.
  def calculate(self,args):
    # 20201209
    #global damTreeSH
    global sharedDataSH

    # Get arguments.
    coreId = args[0]
    cellSize = args[1]
    riverObjects = args[2]             # Rivers objects with ids.
    maxNrOfFragments = args[3]

    searchDist = cellSize / 2.0

    # 20201209
    # # Get shared dam tree.
    # damTree = damTreeSH

    # 20201209
    # Get shared dam tree.
    damTree = sharedDataSH.damTree

    # Create the fragments list.
    fragments = []

    # Set the starting fragment id. 
    fragId = coreId * maxNrOfFragments
    
    # Loop rivers (multiline).
    for riverObject in riverObjects:
      
      # Get river and rivId from object.
      river = riverObject.line
      rivId = riverObject.rivId
      
      # Force to multiline.
      river = VU.shpLineToMultiLine(river)
      
      # Get dams in river bounds.
      poly = VU.shpPolygonFromBounds(river.bounds)
      riverDams = damTree.query(poly)

      #self.dbgPrint("  Found riverDams: %s" % (len(riverDams)))

      # Get river multiline segments.
      riverSegments = river.geoms

      #self.dbgPrint("  Found riverSegments: %s" % (len(riverSegments)))

      # Create tree.
      riverDamTree = STRtree(riverDams)
      segmentTree = STRtree(riverSegments)

      # Loop river segments. 
      for segment in riverSegments:
        
        # Already processed?
        if hasattr(segment,"processed"):
          continue
        
        # Set processed.
        setattr(segment,"processed",1)
        
        # Get begin and endpoint of line.
        beginPnt = VU.shpLineGetBeginPoint(segment)
        endPnt = VU.shpLineGetEndPoint(segment)

        # Get connected to begin point. Stop at end or at dam.
        conLines = self.getConnectedLines(beginPnt,segmentTree,riverDamTree,searchDist)

        # Get connected to end point. Stop at end or at dam.
        conLines2 = self.getConnectedLines(endPnt,segmentTree,riverDamTree,searchDist)
        
        # Merge the two lists.
        conLines.extend(conLines2)
        # Connected lines found?
        if len(conLines)>0:
          # Include current segment.
          conLines.append(segment)
          
          # Calculate length.
          lengthKM = 0.0
          for conLine in conLines:
            for i in range(0,len(conLine.coords)-1):
              c1 = conLine.coords[i]
              c2 = conLine.coords[i+1]
              lengthKM += RU.degreeToKM(c1[0],c1[1],c2[0],c2[1])
              
          # Create multiline fragment.
          fragmentLine = MultiLineString(conLines)
          
          # Create Fragment object and add to list.
          fragment = Fragment(rivId,fragId,fragmentLine,lengthKM)
          fragments.append(fragment)

          # Increment id.
          fragId += 1
        
    return (fragments,)
  
  #-------------------------------------------------------------------------------
  # Arguments:
  #   extent
  #   cellSize
  #   dams: snapped dams
  #   rivers: multilines with RivId.
  #   nrOfChunks
  #
  # Returns fragmentLines with rivId,fragId,lengthKM
  #
  def run(self,extent,cellSize,dams,rivers,nrOfChunks=0):
    # 20201209
    #global damTreeSH
    pool = None
    try:
    
      # Check nrOfChunks.
      if nrOfChunks==0:
        nrOfChunks = self.nrOfCores

      #---------------------------------------------------------------------------
      # Calculate fragment lengths. 
      #---------------------------------------------------------------------------

      # 20201209
      # Create shared dam tree.
      #damTreeSH = STRtree(dams)

      # Create shared dam tree.
      sharedData = SharedData()
      sharedData.damTree = STRtree(dams)

      self.dbgPrint("  Getting rivers in extent...")

      # Create line tree and get worklines within extent.
      riverTree = STRtree(rivers)
      selRivers = riverTree.query(VU.shpPolygonFromBounds(extent))
      
      self.dbgPrint("  Found rivers in extent: %s" % (len(selRivers)))

      Log.info("  Preparing...")
      
      # Convert selected rivers to river objects.
      # 20201209
      #selRiverObjects = map(lambda r: River(r.rivId,r),selRivers)
      selRiverObjects = list(map(lambda r: River(r.rivId,r),selRivers))

      # Split the selected rivers in parts.
      workRiverObjects = self.getWorkSubLists(selRiverObjects,nrOfChunks)

      # Set maximum number of fragments per chunck.
      # The are used for unique fragment id's. 
      maxNrOfFragments = 100000
      
      # Create the input list with tuples of (id,cellSize,rivers,maxNrOfFragments).
      args = []
      for i in range(len(workRiverObjects)):
        args.append([i,cellSize,workRiverObjects[i],maxNrOfFragments])

      #---------------------------------------------------------------------------
      # Calculate fragments. 
      # Returns a dict with fragment lines, i.e. the parts of a river between dams
      # or between dams and endpoints of rivers (sources,sinks).
      # Each fragment has an unique id.
      #---------------------------------------------------------------------------

      Log.info("  Calculating fragments...")

      # 20201209
      # Create the pool.
      # pool = mp.Pool(processes=self.nrOfCores)
      pool = mp.Pool(processes=self.nrOfCores,
                     initializer=initPool, initargs=(sharedData,))
      results = pool.map(calculate,zip([self]*len(args),args))
      
      self.dbgPrint("  Results found: %s" % len(results))

      #---------------------------------------------------------------------------
      # Process fragment results.
      #---------------------------------------------------------------------------

      # The results are a list of tuples. Get separate results.
      fragmentObjecsChunks = [r[0] for r in results]
      self.dbgPrint("  Fragment chunks found: %s" % len(fragmentObjecsChunks))

      # Merge the list.
      fragmentObjects = self.joinListChunks(fragmentObjecsChunks)
      self.dbgPrint("  Fragments found: %s" % len(fragmentObjects))

      #---------------------------------------------------------------------------
      # Convert fragment objects to fragment lines.
      #---------------------------------------------------------------------------

      Log.info("  Converting to fragment lines...")

      # Create a dict for fragments.
      fragmentLines = []
      for fragmentObject in fragmentObjects:
        # Set fragment line.
        fragmentLine = fragmentObject.line
        # Set line properties.
        fragmentLine.rivId = fragmentObject.rivId
        fragmentLine.fragId = fragmentObject.fragId
        fragmentLine.lengthKM = fragmentObject.lengthKM
        # Add to list.
        fragmentLines.append(fragmentLine)
        
      return fragmentLines

    except KeyboardInterrupt:
      if not pool is None:
        print("^C received, shutting down the workers.")
        pool.close()
        pool.terminate()
        pool = None
      return None
