# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
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
    IN RASTER LanduseMSA
    IN RASTER HumanEncroachmentMSA
    IN RASTER NDepositionMSA
    IN RASTER ClimateChangeMSA
    IN RASTER InfraDisturbanceMSA
    IN RASTER InfraFragmentationMSA
    IN RASTER TerrestrialMSA
    OUT RASTER LanduseMSA_contribution
    OUT RASTER HumanEncroachmentMSA_contribution
    OUT RASTER NDepositionMSA_contribution
    OUT RASTER ClimateChangeMSA_contribution
    OUT RASTER InfraDisturbanceMSA_contribution
    OUT RASTER InfraFragmentationMSA_contribution
    OUT RASTER TotalLossTerrestrialMSA
    """
    self.showStartMsg(args)

    # Check number of arguments.
    if len(args)<=15:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2,len(args),self.name)

    # Get arguments.
    extent = args[0]
    cellSize = args[1]
    landuseMSAName = args[2]
    humanEncMSAName = args[3]
    nDepMSAName = args[4]
    climChangeMSAName = args[5]
    infraDistMSAName = args[6]
    infraFragMSAName = args[7]
    terrRasterName = args[8]
    outRasterNameLU = args[9]
    outRasterNameHE = args[10]
    outRasterNameND = args[11]
    outRasterNameCC = args[12]
    outRasterNameID = args[13]
    outRasterNameIF = args[14]
    outRasterNameTL = args[15]

    # Check arguments.
    self.checkExtent(extent)
    self.checkCellSize(cellSize)
    self.checkRaster(landuseMSAName,optional=True)
    self.checkRaster(humanEncMSAName,optional=True)
    self.checkRaster(nDepMSAName,optional=True)
    self.checkRaster(climChangeMSAName,optional=True)
    self.checkRaster(infraDistMSAName,optional=True)
    self.checkRaster(infraFragMSAName,optional=True)
    self.checkRaster(terrRasterName)
    self.checkRaster(outRasterNameLU,asOutput=True,optional=True)
    self.checkRaster(outRasterNameHE,asOutput=True,optional=True)
    self.checkRaster(outRasterNameND,asOutput=True,optional=True)
    self.checkRaster(outRasterNameCC,asOutput=True,optional=True)
    self.checkRaster(outRasterNameID,asOutput=True,optional=True)
    self.checkRaster(outRasterNameIF,asOutput=True,optional=True)
    self.checkRaster(outRasterNameTL,asOutput=True,optional=True)

    # Align extent.
    extent = RU.alignExtent(extent,cellSize)

    # Set members.
    self.extent = extent
    self.cellSize = cellSize
    self.outDir = os.path.dirname(outRasterNameLU)

    # Enable monitor and show memory and disk space usage.
    MON.showMemDiskUsage(Log,"- ","",self.outDir)

    # Create a list with all msa rasters.
    msaRasterNames = [landuseMSAName,humanEncMSAName,
                      nDepMSAName,climChangeMSAName,
                      infraDistMSAName,infraFragMSAName,terrRasterName]
    msaDescriptions = ["landuse","human encroachment",
                       "N-deposition","climate change",
                       "infrastructure disturbance","infrastructure fragmentation","terrestrial MSA"]
    msaOutRasterNames = [outRasterNameLU,outRasterNameHE,
                         outRasterNameND,outRasterNameCC,
                         outRasterNameID,outRasterNameIF,outRasterNameTL]

    # Create summed terrestrial MSA loss raster.
    Log.info("Creating terrestrial MSA loss raster...")
    noDataValue = -999.0
    outRasterLoss = Raster(msaOutRasterNames[-1])
    outRasterLoss.initRaster(extent,cellSize,np.float32,noDataValue)

    # Calculate total MSA.
    Log.info("Calculating total terrestrial MSA loss raster...")
    for i in range(len(msaRasterNames)-1):
      msaRasterName = msaRasterNames[i]
      msaDescription = msaDescriptions[i]

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
              outRasterLoss.r[firstmask] = (1-msaRaster.r[firstmask])
          else:
              mask = (outRasterLoss.r != outRasterLoss.noDataValue) & (msaRaster.r != msaRaster.noDataValue)
              outRasterLoss.r[mask] += (1-msaRaster.r[mask])

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

    msaRasterNameOverall = msaRasterNames[-1]
    msaDescriptionOverall = msaDescriptions[-1]
    msaRasterOverall = self.readAndPrepareInRaster(extent,cellSize,msaRasterNameOverall,msaDescriptionOverall)

    outRasterLossTotal = self.readAndPrepareInRaster(extent,cellSize,msaOutRasterNames[-1],"msa loss")

    for i in range(len(msaRasterNames)-1):
      msaRasterName = msaRasterNames[i]
      msaDescription = msaDescriptions[i]

      if (not self.isValueSet(msaRasterName)):
          continue
      else:

          # Create terrestrial MSA raster.
          # Initialize with noDataValue.
          noDataValue = -999.0
          outRasterLossInd = Raster(msaOutRasterNames[i])
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
    inDir = r"Y:\data\GLOBIO\GLOBIO4\Beheer\Terra\SourceCode\GLOBIO_411_src20180925\src\Globio\Test\Calculations"
    mapDir = r"Y:\data\GLOBIO\GLOBIO4\Models\Terra\Shared\geodata\GlobalTifs\res_10sec"
    lookupDir = r"Y:\data\GLOBIO\GLOBIO4\Models\Terra\Shared\LookupGlobal"
    outDir = r"Y:\data\GLOBIO\GLOBIO4\Beheer\Terra\SourceCode\GLOBIO_411_src20180925\src\Globio\Test\Calculations"
    if not os.path.isdir(outDir):
      outDir = r"S:\hilbersj"

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
    ter = os.path.join(inDir,"TerrestrialMSA_test.tif")
    luco = os.path.join(outDir,"LanduseMSA_test1.tif")
    heco = os.path.join(outDir,"HumanEncroachmentMSA_test1.tif")
    ndco = os.path.join(outDir,"NDepositionMSA_test1.tif")
    ccco = os.path.join(outDir,"ClimateChangeMSA_test1.tif")
    idco = os.path.join(outDir,"InfraDisturbanceMSA_test1.tif")
    ifco = os.path.join(outDir,"InfraFragmentationMSA_test1.tif")
    ttl = os.path.join(outDir,"TotalMSAloss_test1.tif")

    pCalc.run(ext,cs,lu,he,nd,cc,di,fr,ter,luco,heco,ndco,ccco,idco,ifco,ttl)

  except:
    Log.err()
