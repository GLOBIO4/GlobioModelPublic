# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************
#-------------------------------------------------------------------------------
# Usage:
#   ./run.sh GLOBIO_AquaticFractions.py
#
# Modified: 23 nov 2018, ES, ARIS B.V.
#           - Version 4.0.12
#           10 sep 2020, ES, ARIS B.V.
#           - Version 4.0.15
#           - run() modified, resize and resampling of input rasters added.
#           - calculateByRatio modified, now using copyRaster.
#           9 dec 2020, ES, ARIS B.V.
#           - Version 4.1.0.
#           - run calculateByPriorities, list(np.argsort(..)) added.
#           27 oct 2021, MB, PBL
#           - updateFromGLWD modified, added 'mask =' in else: branch
#-------------------------------------------------------------------------------

import os
import numpy as np

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

import GlobioModel.Common.Utils as UT

from GlobioModel.Core.CalculationBase import CalculationBase
from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_AquaticFractions(CalculationBase):
  """
  Merges watertype fractions from different sources to one set of watertype
  fractions.
  """

  #-----------------------------------------------------------------------------
  def calculateByPriorities(self,extent,cellSize,
                            totRaster,
                            floodpWaterTypes,
                            wetlWaterTypes,
                            priorities,
                            rivRasterName,
                            lakeShallRasterName,
                            lakeDeepRasterName,
                            reservShallRasterName,
                            reservDeepRasterName,
                            glwdRasterName,
                            aqRivRasterName,
                            aqLakeShallRasterName,
                            aqLakeDeepRasterName,
                            aqReservShallRasterName,
                            aqReservDeepRasterName,
                            aqFloodpRasterName,
                            aqWetlRasterName):

    
    # Set input raster names.
    inRasterNames = [rivRasterName,lakeShallRasterName,
                     lakeDeepRasterName,reservShallRasterName,
                     reservDeepRasterName,glwdRasterName]
    
    # Create dict with output raster properties.
    outRasterProperties = dict()
    
    # Add properties: dict[inRasterName] = (outRasterName,GLWDWatertypes)
    outRasterProperties[rivRasterName] = [(aqRivRasterName,None)]
    outRasterProperties[lakeShallRasterName] = [(aqLakeShallRasterName,None)]
    outRasterProperties[lakeDeepRasterName] = [(aqLakeDeepRasterName,None)]
    outRasterProperties[reservShallRasterName] = [(aqReservShallRasterName,None)]
    outRasterProperties[reservDeepRasterName] = [(aqReservDeepRasterName,None)]
    outRasterProperties[glwdRasterName] = [(aqFloodpRasterName,floodpWaterTypes),
                                           (aqWetlRasterName,wetlWaterTypes)]
    
    # Sort from high to low. Priority 6 = high, 1 = low.
    # 20201209
    #prioIndices = np.argsort(priorities).tolist()
    prioIndices = list(np.argsort(priorities))
    prioIndices.reverse()
  
    #---------------------------------------------------------------------------
    # Loop input rasters.
    #---------------------------------------------------------------------------

    # Loop input rasters based on priority order.
    for i in prioIndices:

      # Get input name and raster based on priority.
      inRasterName =  inRasterNames[i]   

      Log.info("Reading %s..." % os.path.basename(inRasterName))

      # Read input raster.
      inRaster = Raster(inRasterName)
      inRaster.read()

      # Create corresponding output raster(s).
      for outRasterProperty in outRasterProperties[inRasterName]: 
      
        # Get output raster name and GLWD types.
        outRasterName = outRasterProperty[0]
        glwdTypes = outRasterProperty[1]

        # Create output raster.
        dataType = np.float32
        noDataValue = RU.getNoDataValue(dataType)
        outRaster = Raster(outRasterName)
        outRaster.initRaster(extent,cellSize,dataType,noDataValue,0.0)

        #---------------------------------------------------------------------------
        # Set output fractions.
        #---------------------------------------------------------------------------

        # Do we need to select on GLWD types?            
        if not glwdTypes is None:
          
          # Create GLWD mask.
          glwdMask = None
          for glwdType in glwdTypes:
            if glwdMask is None:
              glwdMask = (inRaster.r == glwdType)
            else:  
              glwdMask = np.logical_or(glwdMask,(inRaster.r == glwdType))
        
          # Set fraction 1.0.
          outRaster.r[glwdMask] = 1.0

          # Calculate total of fractions.
          totRaster.r[glwdMask] += 1.0

          # Cleanup.
          glwdMask = None
        else:
          # No selection on GLWD types.
          
          # Get input data mask.  
          dataMask = inRaster.getDataMask()

          # Copy fractions to output.
          outRaster.r[dataMask] = inRaster.r[dataMask]

          # Calculate total of fractions.
          totRaster.r[dataMask] += inRaster.r[dataMask]

          # Cleanup.
          dataMask = None

        #---------------------------------------------------------------------------
        # Check if total of fractions > 1.0, then correct.
        #---------------------------------------------------------------------------
    
        # Get total mask.
        totMask = (totRaster.r > 1.0)
        
        # Cells found?
        if totMask.any():
          
          # Create surplus raster.
          surplusRaster = Raster()   
          dataType = np.float32
          noDataValue = RU.getNoDataValue(dataType)
          surplusRaster.initRaster(extent,cellSize,dataType,noDataValue,0.0)
          
          # Get surplus.
          surplusRaster.r[totMask] = totRaster.r[totMask] - 1.0
          
          # Correct output.
          outRaster.r[totMask] -= surplusRaster.r[totMask]

          # Correct total.
          totRaster.r[totMask] -= surplusRaster.r[totMask]
          
          # Cleanup.
          surplusRaster.close()
          surplusRaster = None
            
        # Cleanup.
        totMask = None

        #---------------------------------------------------------------------------
        # Write output.
        #---------------------------------------------------------------------------
        
        # Write output.
        Log.info("Writing %s..." % os.path.basename(outRasterName))
        outRaster.write()

        # Cleanup.
        outRaster.close()
        outRaster = None
    
  #-----------------------------------------------------------------------------
  def calculateByRatio(self,extent,cellSize,
                       totRaster,
                       floodpWaterTypes,
                       wetlWaterTypes,
                       rivRasterName,
                       lakeShallRasterName,
                       lakeDeepRasterName,
                       reservShallRasterName,
                       reservDeepRasterName,
                       glwdRasterName,
                       aqRivRasterName,
                       aqLakeShallRasterName,
                       aqLakeDeepRasterName,
                       aqReservShallRasterName,
                       aqReservDeepRasterName,
                       aqFloodpRasterName,
                       aqWetlRasterName):
      
    # Set output raster names.
    outRasterNames = [aqRivRasterName,aqFloodpRasterName,
                      aqLakeShallRasterName,aqLakeDeepRasterName,
                      aqReservShallRasterName,aqReservDeepRasterName,
                      aqWetlRasterName]
      
    # Set temporary raster names.
    tmpRivRasterName = aqRivRasterName.replace(".tif","_tmp.tif")
    tmpLakeShallRasterName = aqLakeShallRasterName.replace(".tif","_tmp.tif")
    tmpLakeDeepRasterName = aqLakeDeepRasterName.replace(".tif","_tmp.tif")
    tmpReservShallRasterName = aqReservShallRasterName.replace(".tif","_tmp.tif")
    tmpReservDeepRasterName = aqReservDeepRasterName.replace(".tif","_tmp.tif")
    tmpFloodpRasterName = aqFloodpRasterName.replace(".tif","_tmp.tif")
    tmpWetlRasterName = aqWetlRasterName.replace(".tif","_tmp.tif")
         
    tmpRasterNames = [tmpRivRasterName,tmpFloodpRasterName,
                      tmpLakeShallRasterName,tmpLakeDeepRasterName,
                      tmpReservShallRasterName,tmpReservDeepRasterName,
                      tmpWetlRasterName]
             
    Log.info("Calculating fractions...")
           
    self.updateFromFractions(extent,cellSize,rivRasterName,tmpRivRasterName,totRaster)
    self.updateFromFractions(extent,cellSize,lakeShallRasterName,tmpLakeShallRasterName,totRaster)
    self.updateFromFractions(extent,cellSize,lakeDeepRasterName,tmpLakeDeepRasterName,totRaster)
    self.updateFromFractions(extent,cellSize,reservShallRasterName,tmpReservShallRasterName,totRaster)
    self.updateFromFractions(extent,cellSize,reservDeepRasterName,tmpReservDeepRasterName,totRaster)
     
    self.updateFromGLWD(extent,cellSize,glwdRasterName,tmpFloodpRasterName,floodpWaterTypes,totRaster)
    self.updateFromGLWD(extent,cellSize,glwdRasterName,tmpWetlRasterName,wetlWaterTypes,totRaster)

    # Correct cells with fraction > 1.0.
    mask = (totRaster.r > 1.0)
    # Found?
    if np.any(mask):
      # Correct, calculate: new-frac = frac * ( 1 / tot-frac) 

      Log.info("Correcting fractions by ratio...")

      # Create reduce factor raster.
      reduceFactor = np.full_like(totRaster.r,1.0)

      # Calculate 1/total.        
      reduceFactor[mask] = np.reciprocal(totRaster.r[mask])

      Log.info("Writing fractions...")
      
      for i in range(len(tmpRasterNames)):
        tmpRasterName = tmpRasterNames[i]
        outRasterName = outRasterNames[i]
        # Read temporary raster.
        tmpRaster = Raster(tmpRasterName)
        tmpRaster.read()
        # Correct fractions..
        tmpRaster.r[mask] *= reduceFactor[mask]
        # Write output raster.
        tmpRaster.writeAs(outRasterName)
        # Cleanup.
        tmpRaster.close()
        tmpRaster = None
    else:
      Log.info("Writing fractions...")
        
      # Just copy temporary rasters. 
      for i in range(len(tmpRasterNames)):
        tmpRasterName = tmpRasterNames[i]
        outRasterName = outRasterNames[i]
        # Copy raster.
        self.copyRaster(tmpRasterName,outRasterName)
    
    # Remove tmp rasters?
    if not GLOB.saveTmpData:
      Log.info("Removing temporary rasters...")
      for i in range(len(tmpRasterNames)):
        RU.rasterDelete(tmpRasterNames[i])
    
  #-------------------------------------------------------------------------------
  def updateFromFractions(self,extent,cellSize,
                          inRasterName,outRasterName,totRaster):
    # Read input raster.
    inRaster = Raster(inRasterName)
    inRaster.read()

    # Create mask.
    mask = (inRaster.r != inRaster.noDataValue)

    # Create output raster.
    dataType = np.float32
    noDataValue = RU.getNoDataValue(dataType)
    value = 0.0
    outRaster = Raster(outRasterName)
    outRaster.initRaster(extent,cellSize,dataType,noDataValue,value)

    # Calculate fraction.
    outRaster.r[mask] = inRaster.r[mask] * 1.0

    # Calculate total fractions.
    totRaster.r[mask] += inRaster.r[mask]

    # Writing output.
    outRaster.write()
    
    # Cleanup.
    inRaster.close()
    inRaster = None
    outRaster.close()
    outRaster = None

  #-------------------------------------------------------------------------------
  def updateFromGLWD(self,extent,cellSize,
                     inRasterName,outRasterName,waterTypes,totRaster):

    # Read input raster.
    inRaster = Raster(inRasterName)
    inRaster.read()

    # Create mask.
    mask = None
    for waterType in waterTypes:
      if mask is None:
        mask = (inRaster.r == waterType)
      else:  
        mask = np.logical_or(mask,(inRaster.r == waterType))
        
    # Create output raster.
    dataType = np.float32
    noDataValue = RU.getNoDataValue(dataType)
    value = 0.0
    outRaster = Raster(outRasterName)
    outRaster.initRaster(extent,cellSize,dataType,noDataValue,value)
    
    # Set fraction 1.0.
    outRaster.r[mask] = 1.0

    # Calculate total fractions.
    totRaster.r[mask] += 1.0

    # Writing output.
    outRaster.write()
    
    # Cleanup.
    inRaster.close()
    inRaster = None
    outRaster.close()
    outRaster = None
    
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN RASTER RiverFractions
    IN RASTER LakeShallowFractions
    IN RASTER LakeDeepFractions
    IN RASTER ReservoirShallowFractions
    IN RASTER ReservoirDeepFractions
    IN RASTER GLWD
    IN STRING FloodplainGLWDWaterTypes
    IN STRING WetlandGLWDWaterTypes
    IN STRING Priorities
    OUT RASTER AqRiverFractions
    OUT RASTER AqFloodplainFractions
    OUT RASTER AqLakeShallowFractions
    OUT RASTER AqLakeDeepFractions
    OUT RASTER AqReservoirShallowFractions
    OUT RASTER AqReservoirDeepFractions
    OUT RASTER AqWetlandFractions
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=17:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    rivRasterName = args[2]
    lakeShallRasterName = args[3]
    lakeDeepRasterName = args[4]
    reservShallRasterName = args[5]
    reservDeepRasterName = args[6]
    glwdRasterName = args[7]
    floodpWaterTypesStr = args[8]
    wetlWaterTypesStr = args[9]
    prioritiesStr =  args[10]
    aqRivRasterName = args[11]
    aqFloodpRasterName = args[12]
    aqLakeShallRasterName = args[13]
    aqLakeDeepRasterName = args[14]
    aqReservShallRasterName = args[15]
    aqReservDeepRasterName = args[16]
    aqWetlRasterName = args[17]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkRaster(rivRasterName)
    self.checkRaster(lakeShallRasterName)
    self.checkRaster(lakeDeepRasterName)
    self.checkRaster(reservShallRasterName)
    self.checkRaster(reservDeepRasterName)
    self.checkRaster(glwdRasterName)
    self.checkIntegerList(floodpWaterTypesStr)
    self.checkIntegerList(wetlWaterTypesStr)
    self.checkIntegerList(prioritiesStr,True)
    self.checkRaster(aqRivRasterName,True)
    self.checkRaster(aqFloodpRasterName,True)
    self.checkRaster(aqLakeShallRasterName,True)
    self.checkRaster(aqLakeDeepRasterName,True)
    self.checkRaster(aqReservShallRasterName,True)
    self.checkRaster(aqReservDeepRasterName,True)
    self.checkRaster(aqWetlRasterName,True)

    # Convert string lists to array.
    floodpWaterTypes = self.splitIntegerList(floodpWaterTypesStr)
    wetlWaterTypes = self.splitIntegerList(wetlWaterTypesStr)
    priorities = self.splitIntegerList(prioritiesStr)

    # Align extent.
    extent = RU.alignExtent(extent,cellSize)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.outDir = os.path.dirname(aqRivRasterName)
    
    # Enable monitor en show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    # Create list for input rasters.
    inRasterNames = [rivRasterName,
                     lakeShallRasterName,lakeDeepRasterName,
                     reservShallRasterName,reservDeepRasterName,
                     glwdRasterName]

    #-----------------------------------------------------------------------------
    # Check priorities.
    #-----------------------------------------------------------------------------

    # Check priotities.
    if len(priorities) > 0:
      # Specified, then same count as input rasters?
      self.checkListCount(prioritiesStr,"|".join(inRasterNames),"priorities")
     
    #-----------------------------------------------------------------------------
    # Check input raster extent and cellsize, resize and/or resample if necessary. 
    #-----------------------------------------------------------------------------

    # Because of the large number of rasters we need to calculate the fractions
    # row by row.
    # Therefore all input rasters need to have the correct extent and cellsize.

    # Create tmp raster names for resized/resampled input rasters.
    tmpRivRasterName = "tmp_%s" % os.path.basename(rivRasterName)
    tmpLakeShallRasterName = "tmp_%s" % os.path.basename(lakeShallRasterName)
    tmpLakeDeepRasterName = "tmp_%s" % os.path.basename(lakeDeepRasterName)
    tmpReservShallRasterName = "tmp_%s" % os.path.basename(reservShallRasterName)
    tmpReservDeepRasterName = "tmp_%s" % os.path.basename(reservDeepRasterName)
    tmpGlwdRasterName = "tmp_%s" % os.path.basename(glwdRasterName)

    # Create list for resized/resampled rasters.
    tmpRasterNames = [tmpRivRasterName,
                      tmpLakeShallRasterName,tmpLakeDeepRasterName,
                      tmpReservShallRasterName,tmpReservDeepRasterName,
                      tmpGlwdRasterName]

    # Check tmp rasters and delete if exists.
    for tmpRasterName in tmpRasterNames:
      RU.rasterDelete(tmpRasterName)
      
    # Resize and/or resample input rasters if necessary.
    for i in range(len(inRasterNames)):
      inRasterName = inRasterNames[i]
      tmpRasterName = tmpRasterNames[i]
      self.resizeResampleRaster(extent,cellSize,inRasterName,tmpRasterName)

    #-----------------------------------------------------------------------------
    # Calculate total of fractions.
    #-----------------------------------------------------------------------------

    # Get nrCols/nrRows.
    #nrCols,nrRows = RU.calcNrColsRowsFromExtent(extent,cellSize)

    # Create raster for total fractions.
    dataType = np.float32
    noDataValue = RU.getNoDataValue(dataType)
    value = 0.0
    totRaster = Raster()
    totRaster.initRaster(extent,cellSize,dataType,noDataValue,value)

    # Do we need to use priorities?
    if len(priorities) > 0:
      # With priorities, so don't (or partial) use low priority fractions.
      self.calculateByPriorities(extent,cellSize,totRaster,
                                 floodpWaterTypes,wetlWaterTypes,
                                 priorities,
                                 tmpRivRasterName,
                                 tmpLakeShallRasterName,tmpLakeDeepRasterName,
                                 tmpReservShallRasterName,tmpReservDeepRasterName,
                                 tmpGlwdRasterName,
                                 aqRivRasterName,
                                 aqLakeShallRasterName,aqLakeDeepRasterName,
                                 aqReservShallRasterName,aqReservDeepRasterName,
                                 aqFloodpRasterName,aqWetlRasterName)
    else:  
      # No priorities, so reduce by ratio.
      self.calculateByRatio(extent,cellSize,totRaster,
                            floodpWaterTypes,wetlWaterTypes,
                            tmpRivRasterName,
                            tmpLakeShallRasterName,tmpLakeDeepRasterName,
                            tmpReservShallRasterName,tmpReservDeepRasterName,
                            tmpGlwdRasterName,
                            aqRivRasterName,
                            aqLakeShallRasterName,aqLakeDeepRasterName,
                            aqReservShallRasterName,aqReservDeepRasterName,
                            aqFloodpRasterName,aqWetlRasterName)

    # Don't save temporary data?
    if not GLOB.saveTmpData:
      # Delete tmp rasters.
      Log.info("Removing temporary rasters...")
      for tmpRasterName in tmpRasterNames:
        RU.rasterDelete(tmpRasterName)
      
    # Cleanup.
    totRaster.close()
    totRaster = None
    
    # Show used memory and disk space.
    MON.showMemDiskUsage()

    self.showEndMsg()
    
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  
  #-----------------------------------------------------------------------------
  def main_20200908():
    try:
      GLOB.saveTmpData = False
      GLOB.monitorEnabled = True
      GLOB.SHOW_TRACEBACK_ERRORS = True

      pCalc = GLOBIO_AquaticFractions()
      pCalc.debugPrint = True

      # Settings.
      extentName = "wrld"
      #extentName = "nl"
      cellSizeName = "30sec"

      inDir = r"G:\data\Globio4LA\data\referentie\v4012\30sec_wrld\in_20181123"
      inGlwdDir = r"G:\data\Globio4LA\data\referentie\v4012\30sec_wrld\in_20181026"

      outDir = r"G:\data\Globio4LA\data\referentie\v4012\30sec_%s\in_20181123" % extentName

      # Input.
      rivfrac = "river_fractions.tif"
      lsfrac = "shallow_lake_fractions.tif"
      ldfrac = "deep_lake_fractions.tif"
      rsfrac = "shallow_reservoir_fractions.tif"
      rdfrac = "deep_reservoir_fractions.tif"
      glwd = "glwd.tif"

      # Output.
      aqrivfrac = "aq_river_fractions.tif"
      aqflofrac = "aq_floodplain_fractions.tif"
      aqlsfrac = "aq_shallow_lake_fractions.tif"
      aqldfrac = "aq_deep_lake_fractions.tif"
      aqrsfrac = "aq_shallow_reservoir_fractions.tif"
      aqrdfrac = "aq_deep_reservoir_fractions.tif"
      aqwetfrac = "aq_wetland_fractions.tif"

      # Set input priorities (1=low).
      # Empty? Reduced by ration.
      #priorities = "5|5|5|5|5|1"
      # 20201118
      #priorities = None

      if os.path.isdir("/root"):
        inDir = UT.toLinux(inDir)
        inGlwdDir = UT.toLinux(inGlwdDir)
        outDir = UT.toLinux(outDir)

      # Create outdir.
      if not os.path.isdir(outDir):
        os.makedirs(outDir)

      # Set input fractions data.
      rivfrac = os.path.join(inDir,rivfrac)
      lsfrac = os.path.join(inDir,lsfrac)
      ldfrac = os.path.join(inDir,ldfrac)
      rsfrac = os.path.join(inDir,rsfrac)
      rdfrac = os.path.join(inDir,rdfrac)
      glwd = os.path.join(inGlwdDir,glwd)

      # Set output data.
      aqrivfrac = os.path.join(outDir,aqrivfrac)
      aqflofrac = os.path.join(outDir,aqflofrac)
      aqlsfrac = os.path.join(outDir,aqlsfrac)
      aqldfrac = os.path.join(outDir,aqldfrac)
      aqrsfrac = os.path.join(outDir,aqrsfrac)
      aqrdfrac = os.path.join(outDir,aqrdfrac)
      aqwetfrac = os.path.join(outDir,aqwetfrac)

      # Remove output data.
      RU.rasterDelete(aqrivfrac)
      RU.rasterDelete(aqflofrac)
      RU.rasterDelete(aqlsfrac)
      RU.rasterDelete(aqldfrac)
      RU.rasterDelete(aqrsfrac)
      RU.rasterDelete(aqrdfrac)
      RU.rasterDelete(aqwetfrac)

      pCalc.run(extentName,cellSizeName,rivfrac,lsfrac,rsfrac,rdfrac,glwd,
                aqrivfrac,aqflofrac,aqlsfrac,aqldfrac,aqrsfrac,aqrdfrac,aqwetfrac)
    except:
      MON.cleanup()
      Log.err()
  
  #-----------------------------------------------------------------------------
  def main():
    try:
      GLOB.saveTmpData = False
      GLOB.monitorEnabled = True
      GLOB.SHOW_TRACEBACK_ERRORS = True

      pCalc = GLOBIO_AquaticFractions()
      pCalc.debugPrint = True

      # Settings.
      #extentName = "wrld"
      #extentName = "nl"
      # 20200908
      extentName = "eu"
      # 20200908
      #cellSizeName = "30sec"
      cellSizeName = "30min"

      ext = GLOB.constants[extentName].value
      cs = GLOB.constants[cellSizeName].value

      #  [-25.0, 33.0, 45.0, 72.0]
      #  0.5
      #  /home/vbarbarossa/share_d/Globio/output/river_fractions.tif
      #  /home/vbarbarossa/share_d/Globio/output/shallow_lake_fractions.tif
      #  /home/vbarbarossa/share_d/Globio/output/deep_lake_fractions.tif
      #  /home/vbarbarossa/share_d/Globio/output/shallow_reservoir_fractions.tif
      #  /home/vbarbarossa/share_d/Globio/output/deep_reservoir_fractions.tif
      #  /home/vbarbarossa/share_d/Globio/input/glwd_ras_EU.tif
      #  4|5
      #  6|7|8|9|10|11|12
      #  None
      #  /home/vbarbarossa/share_d/Globio/output/aq_river_fractions.tif
      #  /home/vbarbarossa/share_d/Globio/output/aq_floodplain_fractions.tif
      #  /home/vbarbarossa/share_d/Globio/output/aq_shallow_lake_fractions.tif
      #  /home/vbarbarossa/share_d/Globio/output/aq_deep_lake_fractions.tif
      #  /home/vbarbarossa/share_d/Globio/output/aq_shallow_reservoir_fractions.tif
      #  /home/vbarbarossa/share_d/Globio/output/aq_deep_reservoir_fractions.tif
      #  /home/vbarbarossa/share_d/Globio/output/aq_wetland_fractions.tif
      
      inDir = r"G:\data\Globio4LA\data\referentie\v4012\30sec_wrld\in_20181123"
      inGlwdDir = r"G:\data\Globio4LA\data\pbl_20200806\globio_data"

      #outDir = r"G:\data\Globio4LA\data\referentie\v4012\30sec_%s\in_20181123" % extentName
      outDir = r"G:\data\Globio4LA\data\referentie\v4015\%s_%s\in_20200909" % (cellSizeName,extentName)

      # Input.
      rivfrac = "river_fractions.tif"
      lsfrac = "shallow_lake_fractions.tif"
      ldfrac = "deep_lake_fractions.tif"
      rsfrac = "shallow_reservoir_fractions.tif"
      rdfrac = "deep_reservoir_fractions.tif"
      #glwd = "glwd.tif"
      glwd = "glwd_ras_EU.tif"

      # Set floodplain and wetland watertypes.
      floodp = "4|5"
      wetl = "6|7|8|9|10|11|12"

      # Set input priorities (1=low).
      # Empty? Reduced by ration.
      #priorities = "5|5|5|5|5|1"
      priorities = None

      # Output.
      aqrivfrac = "aq_river_fractions.tif"
      aqflofrac = "aq_floodplain_fractions.tif"
      aqlsfrac = "aq_shallow_lake_fractions.tif"
      aqldfrac = "aq_deep_lake_fractions.tif"
      aqrsfrac = "aq_shallow_reservoir_fractions.tif"
      aqrdfrac = "aq_deep_reservoir_fractions.tif"
      aqwetfrac = "aq_wetland_fractions.tif"

      if os.path.isdir("/root"):
        inDir = UT.toLinux(inDir)
        inGlwdDir = UT.toLinux(inGlwdDir)
        outDir = UT.toLinux(outDir)

      # Create outdir.
      if not os.path.isdir(outDir):
        os.makedirs(outDir)

      # Set input fractions data.
      rivfrac = os.path.join(inDir,rivfrac)
      lsfrac = os.path.join(inDir,lsfrac)
      ldfrac = os.path.join(inDir,ldfrac)
      rsfrac = os.path.join(inDir,rsfrac)
      rdfrac = os.path.join(inDir,rdfrac)
      glwd = os.path.join(inGlwdDir,glwd)

      # Set output data.
      aqrivfrac = os.path.join(outDir,aqrivfrac)
      aqflofrac = os.path.join(outDir,aqflofrac)
      aqlsfrac = os.path.join(outDir,aqlsfrac)
      aqldfrac = os.path.join(outDir,aqldfrac)
      aqrsfrac = os.path.join(outDir,aqrsfrac)
      aqrdfrac = os.path.join(outDir,aqrdfrac)
      aqwetfrac = os.path.join(outDir,aqwetfrac)

      # Remove output data.
      RU.rasterDelete(aqrivfrac)
      RU.rasterDelete(aqflofrac)
      RU.rasterDelete(aqlsfrac)
      RU.rasterDelete(aqldfrac)
      RU.rasterDelete(aqrsfrac)
      RU.rasterDelete(aqrdfrac)
      RU.rasterDelete(aqwetfrac)

      # 20200908 - De aanroep was fout.
      #pCalc.run(extentName,cellSizeName,rivfrac,lsfrac,rsfrac,rdfrac,glwd,
      #          aqrivfrac,aqflofrac,aqlsfrac,aqldfrac,aqrsfrac,aqrdfrac,aqwetfrac)
      pCalc.run(ext,cs,rivfrac,lsfrac,ldfrac,rsfrac,rdfrac,glwd,
                floodp,wetl,priorities,
                aqrivfrac,aqflofrac,aqlsfrac,aqldfrac,aqrsfrac,aqrdfrac,aqwetfrac)
    except:
      MON.cleanup()
      Log.err()
  
  #-------------------------------------------------------------------------------
  main()
