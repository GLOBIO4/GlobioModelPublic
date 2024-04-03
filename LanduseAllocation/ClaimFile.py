# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
# ******************************************************************************
#-------------------------------------------------------------------------------
# Modified: -
#-------------------------------------------------------------------------------

from GlobioModel.Core.CSVFile import CSVFile
from GlobioModel.Core.Lookup import Lookup

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class ClaimFile():
  
  #-------------------------------------------------------------------------------
  def __init__(self):
    self.csvFile = None
    self.landuseFieldName = ""
    self.regionFieldName = ""
    self.areaFieldName = ""

  #-------------------------------------------------------------------------------
  def landuse(self,row):
    return row[self.landuseFieldName]

  #-------------------------------------------------------------------------------
  def region(self,row):
    return row[self.regionFieldName]

  #-------------------------------------------------------------------------------
  def area(self,row):
    return row[self.areaFieldName]

  #-------------------------------------------------------------------------------
  # Aggregates and summarize the values of simular rows.
  # SumFieldName is the name of the field to summarize.
  def aggregateRowValue(self,sumFieldName):
    self.csvFile.aggregateRowValue(sumFieldName)

  #-------------------------------------------------------------------------------
  def read(self,fileName,landuseFieldName,regionFieldName,areaFieldName):
    self.landuseFieldName = landuseFieldName
    self.regionFieldName = regionFieldName
    self.areaFieldName = areaFieldName
    fieldNames = [landuseFieldName,regionFieldName,areaFieldName]
    fieldTypes = ["S","I","F"]
    self.csvFile = CSVFile()
    self.csvFile.read(fileName,fieldNames,fieldTypes)

  #-------------------------------------------------------------------------------
  def reclassRowValue(self,reclassFieldName,lookupFileName,lookupFieldTypes):

    if len(self.rows) == 0:
      return
    
    # Read lookup dict.
    pLookup = Lookup()
    pLookup.loadCSV(lookupFileName,lookupFieldTypes)

    # Get fieldnames.
    fieldNames = self.rows[0].keys()

    # Check the key and value fieldname.
    self.csvFile.checkFieldNames(fieldNames,[reclassFieldName])

    # Create fieldname lookup.
    fieldNameLookup = self.csvFile.createFieldNameLookup(fieldNames,[reclassFieldName])
    
    for row in self.rows:
      orgKeyFieldName = fieldNameLookup[reclassFieldName]
      key = row[orgKeyFieldName]
      if key in pLookup:
        newValue = pLookup[key]
        row[orgKeyFieldName] = newValue

  #-------------------------------------------------------------------------------
  @property
  def rows(self):
    return self.csvFile.rows

  #-------------------------------------------------------------------------------
  def show(self):
    for row in self.rows:
      print("{ "+"{:s}: {:s}, {:s}: {:d}, {:s} :{:f}".format(
                  self.landuseFieldName,
                  self.landuse(row),
                  self.regionFieldName,
                  self.region(row),
                  self.areaFieldName,
                  self.area(row)) + " }")
    
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":

  #-------------------------------------------------------------------------------
  # OK
  def testReclass():
  
    fileName = r"P:\Project\Globio4LA\data\PBL_20160916\Claims_2050.csv"
    lookupFileName = r"P:\Project\Globio4LA\data\PBL_20160916\LanduseClassToLanduse.csv"
    
    landuseFieldName = "AggLUClass"
    regionFieldName = "IMGREGCD"
    areaFieldName = "totalArea"
    
    lookupFieldTypes = ["S","S"]
    
    pClaimFile = ClaimFile()
    pClaimFile.read(fileName,landuseFieldName,regionFieldName,areaFieldName)
    pClaimFile.show()
    
    pClaimFile.reclassRowValue(landuseFieldName,lookupFileName,lookupFieldTypes)
    pClaimFile.show()
    
    pClaimFile.aggregateRowValue(areaFieldName)
    pClaimFile.show()

  testReclass()
  
