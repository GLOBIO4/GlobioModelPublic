# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 18 jan 2019, ES, ARIS B.V.
#           - Version 4.0.12
#           - CellArea_v2 replaced with CellArea.
#           18 sep 2020, ES, ARIS B.V.
#           - Version 4.0.15
#           - Modified some comments and messages.
#           - New version, instead of using a constant river width, the river
#             width is now calculated based on the discharge using the
#             formula: w = a * Q^b  (in meters).
#           - Argument NumberOfCores added.
#           8 oct 2020, ES, ARIS B.V.
#           - Version 4.0.16
#           - Parameter LakesReservoirs added.
#           - Run modified, use of vectorIntersectByExtent is added.
#           - Run modified, use of excludeVector is added to subtract the 
#             lakes and reservoirs from the rivers.
#-------------------------------------------------------------------------------

import os
import numpy as np

from shapely.wkb import loads

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

import GlobioModel.Core.CellArea as CA
#import GlobioModel.Common.Utils as UT

from GlobioModel.Core.CalculationBase import CalculationBase
from GlobioModel.Core.Grass import Grass
from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU
from GlobioModel.Workers.AquaticRiverFractions import AquaticRiverFractions
from GlobioModel.Core.Vector import Vector
import GlobioModel.Core.VectorUtils as VU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_AquaticRiverFractions_V2(CalculationBase):
  """
  Calculates fractions for rivers.
  """
    
  #-----------------------------------------------------------------------------
  # Creates a new shapefile with all features from in input shapefile
  # that intersects (i.e. crosses) the extent.
  # 
  # Remark: A new shapefile file is only created if there are features that are
  #         outside the extent.
  #
  # Remark: Writes the new shapefile in the self.outDir.
  #
  # Returns the name of new shapefile or "" when no intersection is needed.
  #
  def intersectByExtent(self,vectorName,extent,displayName):
    
    # Check the vector extent.
    if VU.vectorInExtent(vectorName,extent):
      # All features are within the extent.
      return ""

    Log.info("Selecting %s..." % displayName)

    # Need to write intersecting features. Set the name of the new 
    # temporary shapefile.
    tmpVectorName = "tmp_inter_"+os.path.basename(vectorName)
    tmpVectorName = os.path.join(self.outDir,tmpVectorName)

    # Check the tmp shapefile.
    if VU.vectorExists(tmpVectorName):
      VU.vectorDelete(tmpVectorName)

    # Select intersecting features and write these to the tmp shapefile.
    VU.vectorIntersectByExtent(vectorName,extent,tmpVectorName)

    return tmpVectorName
    
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN VECTOR Rivers
    IN VECTOR LakesReservoirs
    IN RASTER RiverDischarge
    IN FLOAT RiverWidthA
    IN FLOAT RiverWidthB
    IN INTEGER NumberOfCores
    OUT RASTER RiverFractions
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=8:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    riverShapeFileName = args[2]
    lakeresvShapeFileName = args[3]
    disRasterName = args[4]
    rivWidthA = args[5]
    rivWidthB = args[6]
    nrOfCores = args[7]
    outRasterName = args[8]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkVector(riverShapeFileName)
    self.checkVector(lakeresvShapeFileName,False,True)
    self.checkRaster(disRasterName)
    self.checkFloat(rivWidthA,0.0,9999.0)
    self.checkFloat(rivWidthB,0.0,9999.0)
    self.checkInteger(nrOfCores,-9999,9999)    
    self.checkRaster(outRasterName,True)

    # Align extent.
    extent = RU.alignExtent(extent,cellSize)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.outDir = os.path.dirname(outRasterName)
    
    # Enable monitor en show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    #---------------------------------------------------------------------------
    # Exclude the lakes/reservoirs from the rivers.
    #---------------------------------------------------------------------------

    newRiverShapeFileName = ""
    newLakeresvShapeFileName = ""

    # Need to exclude the lakes/reservoirs?
    if self.isValueSet(lakeresvShapeFileName):
      
      # Select only rivers within the extent.
      newRiverShapeFileName = self.intersectByExtent(riverShapeFileName,
                                                     extent,"rivers")

      # Select only lakes/reservoirs within the extent.
      newLakeresvShapeFileName = self.intersectByExtent(lakeresvShapeFileName,
                                                        extent,"lakes/reservoirs")

      # Set temporary shapefile name for excluded lakes/reservoirs.
      tmpExcludedShapeFileName = "tmp_rivers_no_lakesresv.shp"
      tmpExcludedShapeFileName = os.path.join(self.outDir,tmpExcludedShapeFileName)

      # Check the temporary shapefile.
      if VU.vectorExists(tmpExcludedShapeFileName):
        VU.vectorDelete(tmpExcludedShapeFileName)

      Log.info("Excluding lakes/reservoirs...")

      # Set the proper river input vector.
      if newRiverShapeFileName == "":
        grRiverShapeFileName = riverShapeFileName
      else:
        grRiverShapeFileName = newRiverShapeFileName
        
      # Set the proper lakes/reservoirs input vector.
      if newLakeresvShapeFileName == "":
        grLakeresvShapeFileName = lakeresvShapeFileName
      else:
        grLakeresvShapeFileName = newLakeresvShapeFileName

      # Exclude the lakes/reservoirs from the rivers.
      gr = Grass()
      gr.init()
      gr.excludeVector(grRiverShapeFileName,grLakeresvShapeFileName,tmpExcludedShapeFileName)
      gr = None

    else:
      # No lakes/reservoirs specified. Use the original rivers shapefile.
      tmpExcludedShapeFileName = riverShapeFileName
        
    #---------------------------------------------------------------------------
    # Read (new) river features. 
    #---------------------------------------------------------------------------

    # Is there a new river shapefile?
    if newRiverShapeFileName != "":
      Log.info("Reading new rivers...")
    else:
      Log.info("Reading rivers...")

    # Read shapefile.
    inVector = Vector(tmpExcludedShapeFileName)
    inVector.read()

    # Get lines.
    lines = [loads(feat.GetGeometryRef().ExportToWkb()) for feat in inVector.layer]

    Log.info("Total number of features found: %s" % len(lines))    

    # Clean up.
    inVector.close()
    inVector = None

    # Clean up. Are lakes/reservoirs specified?
    if self.isValueSet(lakeresvShapeFileName):
      # Not saving temporary data?
      if not GLOB.saveTmpData:
        # Remove temporary river shapefile.
        VU.vectorDelete(tmpExcludedShapeFileName)
        # Did we use intersected rivers?
        if VU.vectorExists(newRiverShapeFileName):
          VU.vectorDelete(newRiverShapeFileName)
        # Did we use intersected lakes/reservoirs?
        if VU.vectorExists(newLakeresvShapeFileName):
          VU.vectorDelete(newLakeresvShapeFileName)
        
    #-----------------------------------------------------------------------------
    # Calculate the river length raster.
    #-----------------------------------------------------------------------------

    # Create worker.
    w = AquaticRiverFractions(nrOfCores)
    nrOfChunks = w.nrOfCores * 4

    # Calculate river length raster (km).
    w.debug = self.debugPrint
    Log.info("  Using: %s cores, %s chunks." % (w.nrOfCores,nrOfChunks))
    rivLenRaster = w.run(extent,cellSize,lines,nrOfChunks)

    # Save temporary data?
    if GLOB.saveTmpData:
      Log.info("Writing river length raster...")
      # Create tmp raster name.
      tmpRasterName = os.path.join(self.outDir,"tmp_"+os.path.basename(outRasterName))
      # Remove tmp data.
      RU.rasterDelete(tmpRasterName)
      # Write river length.
      rivLenRaster.writeAs(tmpRasterName)

    # Clean up.
    lines = None

    # Save temporary data?
    if GLOB.saveTmpData:
      self.writeTmpRaster(rivLenRaster,"tmp_river_length.tif","- Writing river lengths")

    #-----------------------------------------------------------------------------
    # Read the discharge raster, prepare and select.
    #-----------------------------------------------------------------------------
  
    # Reads the raster and resizes to extent and resamples to cellsize.
    disRaster = self.readAndPrepareInRaster(extent,cellSize,disRasterName,"discharge")

    # Replace NaN with nodata.
    disRaster.r[np.isnan(disRaster.r)] = disRaster.noDataValue

    #-----------------------------------------------------------------------------
    # Create the river fraction raster.
    #-----------------------------------------------------------------------------

    Log.info("Creating river fraction raster...")

    # Create the output raster.
    outRaster = Raster(outRasterName)
    noDataValue = -999.0
    outRaster.initRaster(extent,cellSize,np.float32,noDataValue)

    #-----------------------------------------------------------------------------
    # Calculate river width: w = a * Q^b
    #-----------------------------------------------------------------------------

    # Select valid q cells.
    mask = disRaster.getDataMask()
    mask = np.logical_and(mask,(disRaster.r >= 0.0))
    
    # Calculate river width w = a * Q^b (km). 
    outRaster.r[mask] = disRaster.r[mask] ** rivWidthB
    outRaster.r[mask] *= rivWidthA
    outRaster.r[mask] /= 1000

    # Cleanup.
    disRaster.close()
    disRaster = None
    mask = None
    
    # Save temporary data?
    if GLOB.saveTmpData:
      self.writeTmpRaster(outRaster,"tmp_river_width.tif","- Writing river width")
    
    #-----------------------------------------------------------------------------
    # Calculate the river area.
    #-----------------------------------------------------------------------------

    # Select valid river cells.
    mask = (rivLenRaster.r > 0.0) & (outRaster.r > 0.0)
      
    Log.info("Calculating river area...")

    # Set nodata.
    outRaster.r[~mask] = outRaster.noDataValue

    # Calculate area (km2).
    outRaster.r[mask] *= rivLenRaster.r[mask]

    # Clean up.
    rivLenRaster.close()
    rivLenRaster = None

    # Save temporary data?
    if GLOB.saveTmpData:
      self.writeTmpRaster(outRaster,"tmp_river_area.tif","- Writing river area")

    #-----------------------------------------------------------------------------
    # Correct the river area for high/low lattitude.
    #-----------------------------------------------------------------------------

    Log.info("Correcting river area...")

    # Create the cell area ratio raster array.
    ratioRas = CA.createCellAreaRatioRaster(extent,cellSize)

    # Correct the area.
    outRaster.r[mask] *= ratioRas[mask]

    # Clean up.
    ratioRas = None

    # Save temporary data?
    if GLOB.saveTmpData:
      self.writeTmpRaster(outRaster,"tmp_river_area_corr.tif","- Writing corrected river area")

    #-----------------------------------------------------------------------------
    # Create the cell area raster.
    #-----------------------------------------------------------------------------

    Log.info("Creating cell area raster...")
    
    # Create the cell area raster array.
    areaRas = CA.createCellAreaRaster(extent,cellSize)

    #-----------------------------------------------------------------------------
    # Calculate the river fraction raster.
    #-----------------------------------------------------------------------------
       
    Log.info("Calculating fractions...")

    # Calculate fraction.
    outRaster.r[mask] /= areaRas[mask]

    # Clean up.
    areaRas = None

    # Correct fractions (not greater than 1.0).
    corrMask = np.logical_and(mask,(outRaster.r > 1.0))
    outRaster.r[corrMask] = 1.0

    # Cleanup.
    mask = None
    corrMask = None

    #-----------------------------------------------------------------------------
    # Write fraction raster.
    #-----------------------------------------------------------------------------

    Log.info("Writing river fraction raster...")

    # Write river fraction.
    outRaster.write()

    # Cleanup.
    outRaster.close()
    outRaster = None

    # Show used memory and disk space.
    MON.showMemDiskUsage()

    self.showEndMsg()
    
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  
  pass

#   try:
#     GLOB.saveTmpData = False
#     GLOB.monitorEnabled = True
#     GLOB.SHOW_TRACEBACK_ERRORS = True
# 
#     pCalc = GLOBIO_AquaticRiverFractions_V2()
#     pCalc.debugPrint = False
#     
#     extentName = "wrld"
#     #extentName = "nl"
#     cellSizeName = "30sec"
# 
#     ext = GLOB.constants[extentName].value
#     cs = GLOB.constants[cellSizeName].value
# 
#     if extentName == "nl":
#       inDir = r"G:\Data\Globio4LA\data\referentie\v4012\vector\in_20181123"
#       inShp = "rivers_nl.shp"
#     else:
#       inDir = r"G:\Data\Globio4LA\data\referentie\v4012\vector\in_20181123"
#       inShp = "rivers_%s.shp" % extentName
#     
#     outDir = r"G:\data\Globio4LA\data\referentie\v4012\%s_%s\in_20181123" % (cellSizeName,extentName)
#     out = "river_fractions.tif"
# 
#     #riverWidthKM = 1.0       # Is 30sec cellsize!!!
#     riverWidthKM = 0.1
#     
#     if os.path.isdir("/root"):
#       inDir = UT.toLinux(inDir)
#       outDir = UT.toLinux(outDir)
# 
#     # Create outdir.
#     if not os.path.isdir(outDir):
#       os.makedirs(outDir)
# 
#     # Set input/output data.
#     inShp = os.path.join(inDir,inShp)
#     out = os.path.join(outDir,out)
# 
#     # Remove output data.
#     RU.rasterDelete(out)    
#     
#     # Run.
#     pCalc.run(ext,cs,inShp,riverWidthKM,out)
#   except:
#     MON.cleanup()
#     Log.err()
