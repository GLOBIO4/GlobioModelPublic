# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: mar 2022, MB, PBL
#           - added code to calculate the mean year reference raster from monthly
#             reference stream flow input maps
#-------------------------------------------------------------------------------

import os
import numpy as np

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Globals as GLOB
import GlobioModel.Core.Logger as Log
import GlobioModel.Core.Monitor as MON

from GlobioModel.Core.CalculationBase import CalculationBase
from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
# Step 2
class GLOBIO_CalcAquaticAAPFD(CalculationBase):
  """
  Creates a raster with the Ammended Annual Proportional Flow Deviation.
  """
  
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN RASTERLIST ScenarioStreamflowMonths
    IN RASTERLIST ReferenceStreamflowMonths
    IN RASTER RiverFractions
    IN RASTER FloodPlainFractions
    OUT RASTER AAPFD
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=6:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    scenStreamflowMonthsRasterNamesStr = args[2]
    refStreamflowMonthsRasterNamesStr = args[3]
    #refStreamflowMonthsMeanRasterNamesStr = args[4]
    rivFractionsRasterName = args[4]
    floodFractionsRasterName = args[5]
    outRasterName = args[6]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkRasterList(scenStreamflowMonthsRasterNamesStr)
    self.checkRasterList(refStreamflowMonthsRasterNamesStr)
    self.checkListCount(scenStreamflowMonthsRasterNamesStr,refStreamflowMonthsRasterNamesStr,"rasters")
    #self.checkRasterList(refStreamflowMonthsMeanRasterNamesStr)
    #self.checkListCount(refStreamflowMonthsMeanRasterNamesStr,scenStreamflowMonthsRasterNamesStr,"rasters")
    self.checkRaster(rivFractionsRasterName)
    self.checkRaster(floodFractionsRasterName)
    self.checkRaster(outRasterName,True)

    # Convert rasternames to arrays.
    scenStreamflowMonthsRasterNames = self.splitStringList(scenStreamflowMonthsRasterNamesStr)
    refStreamflowMonthsRasterNames = self.splitStringList(refStreamflowMonthsRasterNamesStr)
    #refStreamflowMonthsMeanRasterNames = self.splitStringList(refStreamflowMonthsMeanRasterNamesStr)

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
    fracRasterNames = [rivFractionsRasterName,floodFractionsRasterName]
    fracDescriptions = ["river","floodplain"]
    
    fracMask = None    
    for i in range(len(fracRasterNames)):
      fracRasterName = fracRasterNames[i]
      fracDescription = fracDescriptions[i]

      # Reads the raster and resizes to extent and resamples to cellsize.
      fracRaster = self.readAndPrepareInRaster(extent,cellSize,fracRasterName,fracDescription+" fractions")

      # Create the mask. Select fraction > 0.0.
      tmpMask = (fracRaster.r > 0.0)

      # Select all cells where river/floodplain fractions are. Extend mask.
      if fracMask is None:
        fracMask = tmpMask
      else:
        fracMask = np.logical_or(fracMask,tmpMask)
        
      # Close and free the fractions raster.
      fracRaster.close()
      fracRaster = None

      # Cleanup mask.
      tmpMask = None

    #-----------------------------------------------------------------------------
    # Create output raster.
    #-----------------------------------------------------------------------------

    # Create AAPFD raster.
    # Initialize with 0.0.
    Log.info("Creating AAPFD raster...")
    noDataValue = -999.0
    outRaster = Raster(outRasterName)
    outRaster.initRaster(extent,cellSize,np.float32,noDataValue,0.0)

    #-----------------------------------------------------------------------------
    # Process month reference raster to create mean year reference raster
    #-----------------------------------------------------------------------------
    # Create Reference annual mean raster
    refMeanRaster = Raster()
    refMeanRaster.initRaster(extent,cellSize,np.float32,noDataValue,0.0)
    refMonthCntRaster = Raster()
    refMonthCntRaster.initRaster(extent,cellSize,np.int16,0,0)

    #refMeanRaster = 5.0
    
    for i in range(len(refStreamflowMonthsRasterNames)):
      # Set raster names.
      refRasterName = refStreamflowMonthsRasterNames[i]

      # Reads the raster and resizes to extent and resamples to cellsize.
      refRaster = self.readAndPrepareInRaster(extent,cellSize,refRasterName,"reference streamflow")

      # Select valid data.
      dataMask = refRaster.getDataMask()
      
      # Select mean > 0.0.
      dataMask = np.logical_and(dataMask,refRaster.r > 0.0) 

      refMeanRaster.r[dataMask] += refRaster.r[dataMask]
      refMonthCntRaster.r[dataMask] += 1
      #refMeanRaster.r[dataMask] = refMeanRaster.r[dataMask] + refRaster.r[dataMask]
      #refMeanRaster.r += 5.0

      # Clear mask.
      dataMask = None

      # Close and free the rasters.
      refRaster.close()
      refRaster = None

    # Calculate mean year reference raster, divide by number of months with valid data
    # Select valid data.
    #dataMask = refRaster.getDataMask()
      
    # Select mean > 0.0.
    dataMask = (refMonthCntRaster.r > 0.0) 

    refMeanRaster.r[dataMask] = refMeanRaster.r[dataMask] / refMonthCntRaster.r[dataMask]

    #-----------------------------------------------------------------------------
    # Process month rasters.
    #-----------------------------------------------------------------------------

    # Process month rasters.
    for i in range(len(scenStreamflowMonthsRasterNames)):
      # Set raster names.
      scenRasterName = scenStreamflowMonthsRasterNames[i]
      refRasterName = refStreamflowMonthsRasterNames[i]
      #refMeanRasterName = refStreamflowMonthsMeanRasterNames[i]
      
      # Reads the raster and resizes to extent and resamples to cellsize.
      scenRaster = self.readAndPrepareInRaster(extent,cellSize,scenRasterName,"scenarion streamflow")
      refRaster = self.readAndPrepareInRaster(extent,cellSize,refRasterName,"reference streamflow")
      #refMeanRaster = self.readAndPrepareInRaster(extent,cellSize,refMeanRasterName,"reference mean streamflow")
      
      # Select valid data.
      dataMask = scenRaster.getDataMask()
      dataMask = np.logical_and(dataMask,refRaster.getDataMask())  
      #dataMask = np.logical_and(dataMask,refMeanRaster.getDataMask())  

      # Select mean > 0.0.
      dataMask = np.logical_and(dataMask,refMeanRaster.r > 0.0)  
         
      # Combine with fractions mask.
      dataMask = np.logical_and(dataMask,fracMask)  
         
      # Calculate sum ((Q - Qref) / Qmean)^2.
      outRaster.r[dataMask] += np.square((scenRaster.r[dataMask] - refRaster.r[dataMask]) / refMeanRaster.r[dataMask])  

      # Clear mask.
      dataMask = None

      # Close and free the rasters.
      scenRaster.close()
      scenRaster = None
      refRaster.close()
      refRaster = None

    # Close and free the reference annual mean raster  
    refMeanRaster.close()
    refMeanRaster = None

    # Calculate squareroot of sum.
    outRaster.r = np.sqrt(outRaster.r)  

    # Set nodata.
    outRaster.r[~fracMask] = outRaster.noDataValue      # pylint: disable=invalid-unary-operand-type

    #-----------------------------------------------------------------------------
    # Write output raster.
    #-----------------------------------------------------------------------------

    # Save the AAPFD raster.
    Log.info("Writing AAPFD raster...")
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
    outDir = r"C:\Temp\_Globio4\out"
    if not os.path.isdir(outDir):
      outDir = r"G:\Data\out_v3"
    inDir = outDir

    pCalc = GLOBIO_CalcAquaticAAPFD()
    
    ext = GLOB.extent_World
    cs = GLOB.cellSize_30sec
    
    nrMonths = 1
    scens = [os.path.join(inDir,"scen_streamflow_%s.tif" % m) for m in range(1,nrMonths+1)]
    scens = "|".join(scens)
    refs = [os.path.join(inDir,"ref_streamflow_%s.tif" % m) for m in range(1,nrMonths+1)]
    refs = "|".join(refs)
    mrefs = [os.path.join(inDir,"ref_mean_streamflow_%s.tif" % m) for m in range(1,nrMonths+1)]
    mrefs = "|".join(mrefs)
    rivfrac = os.path.join(inDir,"river_fractions.tif")
    flofrac = os.path.join(inDir,"floodplain_fractions.tif")
    out = os.path.join(outDir,"aapfd.tif")
   
    pCalc.run(ext,cs,scens,refs,mrefs,rivfrac,flofrac,out)
  except:
    Log.err()
