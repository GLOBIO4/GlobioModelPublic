# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: 9 nov 2019, JH
#           - Version 4.11
#           19 mar 2019, JH
#           -Include the possibility to calculate individal impacts of limited 
#            number of pressures if raster names equal ""
#            NOTE: the selected pressures should be the same as in GLOBIO_CalcTerrestrialMSA
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
class GLOBIO_CalcSplitImpactsMSA(CalculationBase):
  """
  Creates a raster with total terrestrial MSA.
  """

  #-------------------------------------------------------------------------------
  def run(self,*args):
    """
    IN EXTENT Extent
    IN CELLSIZE CellSize
    IN RASTERLIST ImpactsMSA
    IN RASTER TerrestrialMSA
    OUT RASTERLIST ImpactContributionsMSA
    OUT RASTER TotalLossTerrestrialMSA
    """
    self.showStartMsg(args)

    # Check number of arguments.
    if len(args)!=6:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)

    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    impactsRasterNames = args[2]
    terrRasterName = args[3]
    impactContributionsRasterNames = args[4]
    totalLossRasterName = args[5]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkRasterList(impactsRasterNames)
    self.checkRaster(terrRasterName)
    self.checkListCount(impactContributionsRasterNames, impactsRasterNames)
    self.checkRasterList(impactContributionsRasterNames, asOutput=True)
    self.checkRaster(totalLossRasterName,asOutput=True,optional=True)

    impactsRasterNames = self.splitStringList(impactsRasterNames)
    impactContributionsRasterNames = self.splitStringList(impactContributionsRasterNames)

    # Align extent.
    extent = RU.alignExtent(extent,cellSize)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.outDir = os.path.dirname(totalLossRasterName)

    # Enable monitor and show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    # Create summed terrestrial MSA loss raster.
    Log.info("Creating terrestrial MSA loss raster...")
    noDataValue = -999.0
    outRasterLoss = Raster(totalLossRasterName)
    outRasterLoss.initRaster(extent,cellSize,np.float32,noDataValue)

    # Calculate total MSA.
    Log.info("Calculating total terrestrial MSA loss raster...")
    for i in range(len(impactsRasterNames)):
      msaRasterName = impactsRasterNames[i]
      msaDescription = f"impact msa raster {i}"

      if (not self.isValueSet(msaRasterName)):
          continue
      else:

          #-----------------------------------------------------------------------------
          # Read the MSA raster and prepare.
          #-----------------------------------------------------------------------------

          # Reads the raster and resizes to extent and resamples to cellsize.
          msaRaster = self.readAndPrepareInRaster(extent,cellSize,msaRasterName,msaDescription)

          # Calculate msa where no nodata.
          Log.info("- Calculating...")

          if i == 0:
              firstmask = (msaRaster.r != msaRaster.noDataValue)
              outRasterLoss.r[firstmask] = (1 - msaRaster.r[firstmask])
          else:
              mask = (outRasterLoss.r != outRasterLoss.noDataValue) & (msaRaster.r != msaRaster.noDataValue)
              outRasterLoss.r[mask] += (1 - msaRaster.r[mask])

          # Clear mask.
          mask = None
          firstmask = None

          # Close and free the msa raster.
          msaRaster.close()
          msaRaster = None

    # Save the terrestrial MSA raster.
    Log.info("Writing total terrestrial MSA lossraster...")
    outRasterLoss.write()

    outRasterLoss.close()
    outRasterLoss = None

  # Calculate individual MSA impacts.
    Log.info("Calculating individual MSA impacts raster...")

    msaRasterNameOverall = terrRasterName
    msaDescriptionOverall = "terrestrial msa"
    msaRasterOverall = self.readAndPrepareInRaster(extent,cellSize,msaRasterNameOverall,msaDescriptionOverall)

    outRasterLossTotal = self.readAndPrepareInRaster(extent,cellSize,totalLossRasterName,"msa loss")

    for i in range(len(impactsRasterNames)):
      msaRasterName = impactsRasterNames[i]
      msaDescription = f"impact msa raster {i}"

      if (not self.isValueSet(msaRasterName)) or (not self.isValueSet(impactContributionsRasterNames[i])):
          continue
      else:

          # Create terrestrial MSA raster.
          # Initialize with noDataValue.
          noDataValue = -999.0
          outRasterLossInd = Raster(impactContributionsRasterNames[i])
          outRasterLossInd.initRaster(extent,cellSize,np.float32,noDataValue)

          #-----------------------------------------------------------------------------
          # Read the MSA raster and prepare.
          #-----------------------------------------------------------------------------

          # Reads the raster and resizes to extent and resamples to cellsize.
          msaRaster = self.readAndPrepareInRaster(extent,cellSize,msaRasterName,msaDescription)

          # Calculate msa where no nodata.
          Log.info("- Calculating...")

          # Create mask where total loss = 0.0..
          zerolossMask = (msaRaster.r != msaRaster.noDataValue) & (msaRasterOverall.r != msaRasterOverall.noDataValue) & (outRasterLossTotal.r == 0.0)
          outRasterLossInd.r[zerolossMask] = 0.0

          lossMask = (msaRasterOverall.r != msaRasterOverall.noDataValue) & (msaRaster.r != msaRaster.noDataValue) & (outRasterLossTotal.r > 0.0)
          outRasterLossInd.r[lossMask] = (1-msaRaster.r[lossMask])*(1-msaRasterOverall.r[lossMask])/(outRasterLossTotal.r[lossMask])

            # Clear mask.
          #zerolossMask = None
          lossMask = None

          # Close and free the msa raster.
          msaRaster.close()
          msaRaster = None

          # Save the terrestrial MSA raster.
          Log.info("Writing individual loss MSA raster...")
          outRasterLossInd.write()

          # Cleanup.
          outRasterLossInd.close()
          outRasterLossInd = None

    # Show used memory and disk space.
    MON.showMemDiskUsage()

    self.showEndMsg()

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  try:
    inDir = r""
    mapDir = r""
    lookupDir = r""
    outDir = r""

    pCalc = GLOBIO_CalcSplitImpactsMSA()

    ext = [-52,-51,0,1]
    #ext = GLOB.constants["world"].value
    cs = GLOB.cellSize_10sec    
    lu = os.path.join(inDir,"LanduseMSA_test.tif")
    he = os.path.join(inDir,"HumanEncroachmentMSA_test.tif")
    nd = os.path.join(inDir,"NDepositionMSA_test.tif")
    cc = os.path.join(inDir,"ClimateChangeMSA_test.tif")
    di = os.path.join(inDir,"InfraDisturbanceMSA_test.tif")
    fr = os.path.join(inDir,"InfraFragmentationMSA_test.tif")
    impacts = "|".join([lu, he, nd, cc, di, fr])
    ter = os.path.join(inDir,"TerrestrialMSA_test.tif")
    luco = os.path.join(outDir,"LanduseMSA_test1.tif")
    heco = os.path.join(outDir,"HumanEncroachmentMSA_test1.tif")
    ndco = os.path.join(outDir,"NDepositionMSA_test1.tif")
    ccco = os.path.join(outDir,"ClimateChangeMSA_test1.tif")
    idco = os.path.join(outDir,"InfraDisturbanceMSA_test1.tif")
    ifco = os.path.join(outDir,"InfraFragmentationMSA_test1.tif")
    contrib = "|".join(luco, heco, ndco, ccco, idco, ifco)
    ttl = os.path.join(outDir,"TotalMSAloss_test1.tif")

    pCalc.run(ext,cs,impacts,ter,contrib,ttl)

  except:
    Log.err()
