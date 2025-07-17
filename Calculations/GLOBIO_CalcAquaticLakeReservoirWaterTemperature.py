# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: nov 2018, ES, ARIS B.V.
#           17 sep 2020, ES, ARIS B.V.
#           - Version 4.0.15
#           - run modified, added argument to readAndPrepareInRaster.
#           17 nov 2020, ES, ARIS B.V.
#           - Version 4.0.16
#           - run modified, added %.
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
# Step 4
class GLOBIO_CalcAquaticLakeReservoirWaterTemperature(CalculationBase):
  """
  Creates a raster with the median surface water temperature across months
  in lakes and reservoirs.
  """
  
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN RASTERLIST WaterTemperatureMonths
    IN FLOAT TemperatureThreshold
    IN RASTER LakeShallowFractions
    IN RASTER LakeDeepFractions
    IN RASTER ReservoirShallowFractions
    IN RASTER ReservoirDeepFractions
    OUT RASTER WaterTemperature
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=8:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    waterTempMonthsRasterNamesStr = args[2]
    temperatureThreshold = args[3]
    lakeShallowFractionsRasterName = args[4]
    lakeDeepFractionsRasterName = args[5]
    reseShallowFractionsRasterName = args[6]
    reseDeepFractionsRasterName = args[7]
    outRasterName = args[8]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkRasterList(waterTempMonthsRasterNamesStr)
    self.checkFloat(temperatureThreshold,0.0,100.0)
    self.checkRaster(lakeShallowFractionsRasterName)
    self.checkRaster(lakeDeepFractionsRasterName)
    self.checkRaster(reseShallowFractionsRasterName)
    self.checkRaster(reseDeepFractionsRasterName)
    self.checkRaster(outRasterName,True)

    # Convert threshold.
    temperatureThreshold = float(temperatureThreshold)
    
    # Convert rasternames to arrays.
    waterTempMonthsRasterNames = self.splitStringList(waterTempMonthsRasterNamesStr)

    # Align extent.
    extent = RU.alignExtent(extent,cellSize)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.outDir = os.path.dirname(outRasterName)

    # Enable monitor en show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    #-----------------------------------------------------------------------------
    # Read the fractions rasters, prepare and select.
    #-----------------------------------------------------------------------------

    # Create a list with the fraction rasters.
    fracRasterNames = [lakeShallowFractionsRasterName,lakeDeepFractionsRasterName,
                       reseShallowFractionsRasterName,reseDeepFractionsRasterName]
    fracDescriptions = ["lake(shallow)","lake(deep)",
                        "reservoir(shallow)","reservoir(deep)"]  

    fracMask = None    
    for i in range(len(fracRasterNames)):
      fracRasterName = fracRasterNames[i]
      fracDescription = fracDescriptions[i]

      # Reads the raster and resizes to extent and resamples to cellsize.
      fracRaster = self.readAndPrepareInRaster(extent,cellSize,fracRasterName,fracDescription+" fractions")

      # Select all cells where lake/reservoir fractions are. Extend mask.
      # Create the mask. Select fraction > 0.0.
      if fracMask is None:
        fracMask = (fracRaster.r > 0.0)
      else:
        fracMask = np.logical_or(fracMask,(fracRaster.r > 0.0))
        
      # Close and free the fractions raster.
      fracRaster.close()
      fracRaster = None

    #-----------------------------------------------------------------------------
    # Read the rasters with mean month temperature.
    #-----------------------------------------------------------------------------
    
    # Read info from the first raster with mean month temperature.
    rasterName = waterTempMonthsRasterNames[0]
    raster = Raster(rasterName)
    raster.readInfo()
    
    # Need to resize or resample?
    if (not RU.isEqualExtent(raster.extent,extent,cellSize)) or \
       (not RU.isEqualCellSize(raster.cellSize,cellSize)):

      # Resize and/or resample the mean month temperature rasters and save
      # as temporary raster.
      tmpWaterTempMonthsRasterNames = []
      for i in range(len(waterTempMonthsRasterNames)):
        # Set raster name.
        rasterName = waterTempMonthsRasterNames[i]
        # Reads the raster and resizes to extent and resamples to cellsize.
        # 20201117
        #raster = self.readAndPrepareInRaster(extent,cellSize,rasterName,"temperature %s" (i+1))
        raster = self.readAndPrepareInRaster(extent,cellSize,rasterName,"temperature %s" % (i+1))
        # Set temporary raster name.
        tmpRasterName = "tmp_temperature_%s" % i
        tmpRasterName = os.path.join(self.outDir,tmpRasterName)
        # Add to list.
        tmpWaterTempMonthsRasterNames.append(tmpRasterName)
        # Check temporary raster.
        if RU.rasterExists(tmpRasterName):
          RU.rasterDelete(tmpRasterName)
        # Save temporary raster.
        raster.writeAs(tmpRasterName,False)
        # Cleanup,
        raster.close()
        raster = None

      # Replace original raster names with temporary raster names.
      waterTempMonthsRasterNames = tmpWaterTempMonthsRasterNames[:]

    #-----------------------------------------------------------------------------
    # Create median watertemperature raster.
    #-----------------------------------------------------------------------------

    # Create median watertemperature raster.
    # Initialize with NoData.
    Log.info("Creating median watertemperature raster...")
    noDataValue = -999.0
    outRaster = Raster(outRasterName)
    outRaster.initRaster(extent,cellSize,np.float32,noDataValue)
       
    #-----------------------------------------------------------------------------
    # Calculate median watertemperature (middle number of the sequence).
    #-----------------------------------------------------------------------------
    
    # Create all mean month temperature rasters.
    waterTempRasters = []
    for i in range(len(waterTempMonthsRasterNames)):
      waterTempRasterName = waterTempMonthsRasterNames[i]
      waterTempRaster = Raster(waterTempRasterName)
      waterTempRaster.readInfo()
      waterTempRasters.append(waterTempRaster)

    # Get number of rows from first raster.
    nrRows = waterTempRasters[0].nrRows
    nrCols = waterTempRasters[0].nrCols
    nrMonths = len(waterTempRasters)

    # Detect if we are running within Linux.
    isLinux = False
    if os.path.isdir("/root"):
      isLinux = True
    
    Log.info("Calculating median watertemperature...")
     
    # Calculate median watertemperature per row over the months.
    for r in range(nrRows):
      # Get 1 row for all months.
      monthRows = []
      for m in range(len(waterTempRasters)):
        # Get month raster.
        waterTempRaster = waterTempRasters[m]
        # Read row.
        monthRow = waterTempRaster.readRow(r)
        # Select no nodata.
        mask = (monthRow != waterTempRaster.noDataValue)
        # Select temperature > threshold.
        mask = np.logical_and(mask,monthRow > temperatureThreshold)
        # Select in fractions mask.
        mask = np.logical_and(mask,fracMask[r])

        # Set NaN outside selection mask to ignore when calculating median.
        monthRow[~mask] = np.NaN
        # Add month row.
        monthRows.append(monthRow)
        
      # Combine month rows (vertical).
      monthRows = np.array(monthRows)
      yearRows = np.concatenate(monthRows,axis=0)
      yearRows = yearRows.reshape(nrMonths,nrCols)

      # Calculate median over not NaN values (vertical).
      if isLinux:
        #if np.isnan(yearRows).all(axis=0).any():
        #  print "Column all NaN."
        ## Gives a warning when all columns are NaN, but the result is OK.
        ## Like:
        ##   nan    nan    nan    0.3    0.6    0.7
        ##   nan    nan    nan    nan    nan    0.2
        medianRow = np.nanmedian(yearRows,axis=0)
      else:
        # MB: 20211118: changed the np.median into np.nanmedian. The np.median
        #   function gives noData when one of the months water temperature values
        #   is below the threshold. No distinction necessary between Linux and 
        #   Windows code.
        #medianRow = np.median(yearRows,axis=0)
        medianRow = np.nanmedian(yearRows,axis=0)

      # Set NaN to nodata.
      nanMask = np.isnan(medianRow)
      medianRow[nanMask] = outRaster.noDataValue
      
      # Set output row.
      outRaster.r[r][:] = medianRow[:]

    # Cleanup rasters.
    for m in range(len(waterTempRasters)):
      waterTempRasters[m].close()
      waterTempRasters[m] = None
      
    # Replace NaN with nodata.
    mask = (outRaster.r == np.NaN)
    outRaster.r[mask] = outRaster.noDataValue

    # Cleanup mask.
    mask = None
    
    #-----------------------------------------------------------------------------
    # Write output.
    #-----------------------------------------------------------------------------
     
    # Save the median watertemperature.
    Log.info("Writing median watertemperature raster...")
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
  try:
    # Enable the monitor.
    GLOB.monitorEnabled = True
    GLOB.SHOW_TRACEBACK_ERRORS = True
    
    pCalc = GLOBIO_CalcAquaticLakeReservoirWaterTemperature()
    
    extName = "world"
    ext = GLOB.constants[extName].value
    csName = "30sec"
    #csName = "5min"
    cs = GLOB.constants[csName].value

    inDir = r""
    outDir = r""
    
    if os.path.isdir("/root"):
      inDir = UT.toLinux(inDir)
      outDir = UT.toLinux(outDir)
    
    nrMonths = 12
    wtms = [os.path.join(inDir,"watertemperature_%s.tif" % m) for m in range(1,nrMonths+1)]
    wtms = "|".join(wtms)
    tth = 9.0
    lsfrac = os.path.join(inDir,"lakeshallow_fractions.tif")
    ldfrac = os.path.join(inDir,"lakedeep_fractions.tif")
    rsfrac = os.path.join(inDir,"reservoirshallow_fractions.tif")
    rdfrac = os.path.join(inDir,"reservoirdeep_fractions.tif")
    out = os.path.join(outDir,"lakereservoir_watertemperature.tif")

    RU.rasterDelete(out)

    pCalc.run(ext,cs,wtms,tth,lsfrac,ldfrac,rsfrac,rdfrac,out)
  except:
    MON.cleanup()
    Log.err()
