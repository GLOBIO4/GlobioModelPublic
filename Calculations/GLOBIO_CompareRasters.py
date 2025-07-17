# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 10 may 2017, ES, ARIS B.V.
#           - Version 4.0.6
#           - Statistics modified.
#           15 dec 2020, ES, ARIS B.V.
#           - Version 4.1.0
#           - Statistics modified, now using absolute differences.
#           - Run modified, now checking for nan values.
#-------------------------------------------------------------------------------

import os
import numpy as np

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Logger as Log

from GlobioModel.Core.CalculationBase import CalculationBase
from GlobioModel.Core.Raster import Raster
import GlobioModel.Core.RasterUtils as RU

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class GLOBIO_CompareRasters(CalculationBase):
  """
  Compares two rasters and calculates the differences.

  This script can be used to compare a raster to its reference to check
  if changes in the code has no effect on the results.
  """
  
  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN RASTER InputRaster
    IN RASTER ReferenceRaster
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args)<=1:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)
    
    # Get arguments.
    inRasterName = args[0]
    refRasterName = args[1]
  
    # Check arguments.
    self.checkRaster(inRasterName)
    self.checkRaster(refRasterName)

    #-----------------------------------------------------------------------------
    # Read the input raster.
    #-----------------------------------------------------------------------------

    # Reads the input raster.
    Log.info("Reading input raster %s..." % inRasterName)
    inRaster = Raster(inRasterName)
    inRaster.read()

    #-----------------------------------------------------------------------------
    # Read the reference raster.
    #-----------------------------------------------------------------------------

    # Reads the reference raster.
    Log.info("Reading reference raster %s..." % refRasterName)
    refRaster = Raster(refRasterName)
    refRaster.read()
    
    #-----------------------------------------------------------------------------
    # Check cellsize and extent.
    #-----------------------------------------------------------------------------

    # Set flags.
    hasNoValidCellSize = False
    hasNoValidExtent = False 

    Log.info("Checking cellsize and extent...")

    # Check cellsize.    
    if not RU.isEqualCellSize(inRaster.cellSize,refRaster.cellSize):
      Log.info("  The rasters have no valid cellsize.")
      Log.info("  - Input raster: %s" % inRaster.cellSize)
      Log.info("  - Reference raster: %s" % refRaster.cellSize)
      hasNoValidCellSize = True
      
    # Check extent.    
    if not RU.isEqualExtent(inRaster.extent,refRaster.extent,inRaster.cellSize):
      Log.info("  The rasters have no valid extent.")
      Log.info("  - Input raster: %s" % inRaster.extent)
      Log.info("  - Reference raster: %s" % refRaster.extent)
      hasNoValidExtent = True
      
    # No valid cellsize or extent.
    if hasNoValidCellSize or hasNoValidExtent:
      # Close and free the rasters.
      inRaster.close()
      inRaster = None
      refRaster.close()
      refRaster = None
      # Exit.
      exit(1)

    #-----------------------------------------------------------------------------
    # Check raster nodata value.
    #-----------------------------------------------------------------------------

    Log.info("Checking raster nodata values...")
    
    # Check nodata value.
    if inRaster.noDataValue != refRaster.noDataValue:
      Log.info("  The rasters have different NoData values.")
      Log.info("  - Input raster: %s" % inRaster.noDataValue)
      Log.info("  - Reference raster: %s" % refRaster.noDataValue)

    #-----------------------------------------------------------------------------
    # Check raster data masks.
    #-----------------------------------------------------------------------------

    Log.info("Checking raster data masks...")

    # 20201229
    # Check of NAN values.
    if np.isnan(inRaster.r).any():
      # Set nodata.
      inRaster.r[np.isnan(inRaster.r)] = inRaster.noDataValue

    # 20201229
    # Check of NAN values.
    if np.isnan(refRaster.r).any():
      # Set nodata.
      refRaster.r[np.isnan(refRaster.r)] = refRaster.noDataValue

    # Get raster data masks.  
    inDataMask = inRaster.getDataMask()
    refDataMask = refRaster.getDataMask()

    # Add masks. False = 0, True = 1.
    combRas = inDataMask  + refDataMask.astype(np.uint8)

    # Set combined mask to 0 where True + True is 2. 
    combRas[combRas==2] = 0

    # Check where combRas is 1 (False + True).
    if np.sum(combRas) > 0:
      Log.info("  The rasters data masks are different.")

    del combRas
    
    inNrOfValues = np.sum(inDataMask)
    refNrOfValues = np.sum(refDataMask)
    if inNrOfValues != refNrOfValues:
      Log.info("  The rasters value counts are different.")
      Log.info("  - Input raster number of values: %s" % inNrOfValues)
      Log.info("  - Reference raster number of values: %s" % refNrOfValues)

    #-----------------------------------------------------------------------------
    # Calculate raster data difference.
    #-----------------------------------------------------------------------------

    Log.info("Calculating difference...")

    # Set nodata values to 0.
    inRaster.r[~inDataMask] = 0
    refRaster.r[~refDataMask] = 0

    # Free reference mask.
    del inDataMask
    del refDataMask

    # Calculate difference between rasters.
    #inRaster.r -= refRaster.r
    diffRas = np.absolute(inRaster.r - refRaster.r)

    # print(inRaster.dataType)
    # print(np.nan)
    # print(np.isnan(inRaster.r).sum())
    # print(np.isnan(refRaster.r).sum())
    # print(np.min(refRaster.r))
    # print(np.min(inRaster.r))
    # print(np.max(inRaster.r))
    # print(np.min(refRaster.r))
    # print(np.max(refRaster.r))
    # print(np.min(diffRas))
    # print(np.max(diffRas))

    # Free ref raster.
    del refRaster

    # 20201215
    # Calculate absolute differences.
    # negMask = (inRaster.r < 0)
    # inRaster.r[negMask] *= -1
    # print(inRaster.r)
    #diffRas[(diffRas < 0)] *= -1

    # # Free mask.
    # del negMask

    # 20201215
    # Create masked array with mask=nodata.
    #maskDiffRas = np.ma.masked_equal(diffRas,inRaster.noDataValue)
    maskDiffRas = np.ma.masked_equal(diffRas,diffRas>0)

    # 20201229
    del diffRas
    del inRaster

    # Get number of diff. values.
    inNrOfDifferences = maskDiffRas.count()

    # print(maskDiffRas)
    # nans = np.isnan(maskDiffRas)
    # print(nans.count())

    # Show difference statistics.
    # Std = SQRT(Variance)
    Log.info("Rasters difference statistics:")
    Log.info("- Nr. of total input values: %s" % inNrOfValues)
    Log.info("- Nr. of different values : %s" % inNrOfDifferences)
    if inNrOfDifferences > 0:
      Log.info("- Min. of differences : %.12f" % np.min(maskDiffRas))
      Log.info("- Max. of differences : %.12f" % np.max(maskDiffRas))
      Log.info("- Mean of differences : %.12f" % np.mean(maskDiffRas))
      Log.info("- Std. of differences : %.12f" % np.std(maskDiffRas))

    del maskDiffRas

    self.showEndMsg()

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":

  #-----------------------------------------------------------------------------
  def test1():
    try:
      # 20170510
      refDir = r""
      inDir = r""

      pCalc = GLOBIO_CompareRasters()
      RasterName = "TerrestrialMSA.tif"
      inRasterName = os.path.join(inDir,RasterName)
      refRasterName = os.path.join(refDir,RasterName)

      pCalc.run(inRasterName,refRasterName)
    except:
      Log.err()

  #-----------------------------------------------------------------------------
  # inRas:
  # 0.0    0.1    0.1    0.3    0.0    0.8
  # 0.0    0.6    0.2    0.2    0.0    0.9
  # 0.0    0.0    0.5    0.4    0.0    0.0
  # 0.0    0.0    0.0    0.0    0.0    0.0
  # refRas:
  # 0.0    0.0    0.0    0.3    0.0    0.8
  # 0.0    0.5    0.1    0.2    0.0    0.9
  # 0.0    0.0    0.6    0.5    0.0    0.1
  # 0.0    0.0    0.0    0.0    0.0    0.7
  #
  # --------------------------------------------------------------------------------
  # - Running GLOBIO_CompareRasters
  # --------------------------------------------------------------------------------
  # Arguments:
  # C:\Temp\test2.tif
  # C:\Temp\test2.tif
  # Starting run...
  # Reading input raster C:\Temp\test2.tif...
  # Reading reference raster C:\Temp\test2.tif...
  # Checking cellsize and extent...
  # Checking raster nodata values...
  # Checking raster data masks...
  # Calculating difference...
  # Rasters difference statistics:
  # - Nr. of total input values: 10
  # - Nr. of different values : 0
  # --------------------------------------------------------------------------------
  # - Execution time: 0.015 sec
  # --------------------------------------------------------------------------------
  #
  # --------------------------------------------------------------------------------
  # - Running GLOBIO_CompareRasters
  # --------------------------------------------------------------------------------
  # Arguments:
  # C:\Temp\test1.tif
  # C:\Temp\test2.tif
  # Starting run...
  # Reading input raster C:\Temp\test1.tif...
  # Reading reference raster C:\Temp\test2.tif...
  # Checking cellsize and extent...
  # Checking raster nodata values...
  # Checking raster data masks...
  # The rasters data masks are different.
  # Calculating difference...
  # Rasters difference statistics:
  # - Nr. of total input values: 10
  # - Nr. of different values : 8
  # - Min. of differences : 0.099999994040
  # - Max. of differences : 0.699999988079
  # - Mean of differences : 0.174999997020
  # - Std. of differences : 0.198431342135
  # --------------------------------------------------------------------------------
  # - Execution time: 0.015 sec
  # --------------------------------------------------------------------------------
  def test2():
    import GlobioModel.Common.Utils as UT
    import GlobioModel.ArisPythonTest.TestData as TD

    try:
      td = TD.TestData()

      inRas = td.createRasterSuitForestry_v3()
      UT.printArray("inRas",inRas)

      inRasName = r""
      RU.rasterDelete(inRasName)
      td.createTestGrid(inRasName,inRas,td.extent,td.cellSize)

      refRas = td.createRasterSuitForestry_v2()
      UT.printArray("refRas",refRas)

      refRasName = r""
      RU.rasterDelete(refRasName)
      td.createTestGrid(refRasName,refRas,td.extent,td.cellSize)

      pCalc = GLOBIO_CompareRasters()
      pCalc.run(refRasName,refRasName)

      pCalc = GLOBIO_CompareRasters()
      pCalc.run(inRasName,refRasName)

      del pCalc
      del inRas
      del refRas

    except:
      Log.err()

  # --------------------------------------------------------------------------------
  def test3():
    import GlobioModel.Common.Utils as UT

    try:
      inRasName = r""
      refRasName = r""

      pCalc = GLOBIO_CompareRasters()
      pCalc.run(inRasName,refRasName)

      del pCalc
    except:
      Log.err()

  #-----------------------------------------------------------------------------
  #-----------------------------------------------------------------------------
  #
  # run41 Calculations\GLOBIO_CompareRasters.py
  #
  #test1()
  #test2()
  test3()
