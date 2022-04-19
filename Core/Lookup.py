# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under Gnu Public License, GPL v3.
# ******************************************************************************
#-------------------------------------------------------------------------------
# The dict is modified to preserve the original order of keys.
# This is important for lookup with class bounds.
#
# Uses ; as field separator.
# Uses . or , as decimal sign.
#
# Key/value pairs can be specified as <key>;<value>. For example: 130;7.
#   
# A default value for not-specified keys can be specified using the 
# special key token '*'. For example: *;9999.
#
# Example csv file:
#
#   LANDCOVER;SUITABILITY
#   *;0.0
#   120;0.666
#   130;1.0
#   150;0.333
# 
# When no valid field separators are found the following error is given:
#   "Could not determine delimiter"
#
# Modified: 25 apr 2016, ES, ARIS B.V.
#           - loadCSVMultipleFields added.
#           - loadCSVOneField added.
#           - loadCSV modified.
#           24 nov 2016, ES, ARIS B.V.
#           - use of defaultValue added.
#           2 dec 2020, ES, ARIS B.V.
#           - Version 4.1.0
#           - loadCSVMultipleFields modified, because of next().
#           - loadCSVMultipleFields modified, because of open(fileName,newline="").
#           - loadCSVOneField modified, because of open(fileName,newline="").
#           - loadPivotCSV modified, because of open(fileName,newline="").
# TODO:
#           15 jan 2021, ES, ARIS B.V.
#           - Merge with CSVFile?
#-------------------------------------------------------------------------------

import os
import csv

import GlobioModel.Core.Error as Err
import GlobioModel.Common.Utils as UT

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
# A class for value lookup.
class Lookup(dict):

  list = []

  fileName = ""
  fieldTypes = None
  
  # The value assigned to keys which are not in the lookup list.
  # Can be specified in the CSV file as '*;value'.
  defaultValue = None 
  
  #-------------------------------------------------------------------------------
  def __init__(self):
    super(Lookup,self).__init__()
    self.list = []
    self.fileName = ""
    self.fieldTypes = None

  #-------------------------------------------------------------------------------
  def __iter__(self):
    return iter(self.list)
  
  #-------------------------------------------------------------------------------
  def __setitem__(self,fullName,value):
    super(Lookup,self).__setitem__(fullName,value)
    self.list.append(fullName)

  #-------------------------------------------------------------------------------
  def checkFieldTypes(self,fieldCount):
    # Check length.
    if len(self.fieldTypes)!=fieldCount:
      Err.raiseGlobioError(Err.InvalidNumberOfCSVFieldtypes2,len(self.fieldTypes),fieldCount)
    # Check types.
    for fieldType in self.fieldTypes:
      if fieldType not in ["I","F","S"]:
        Err.raiseGlobioError(Err.InvalidCSVFieldtype1,fieldType)

  #-------------------------------------------------------------------------------
  def keys(self):
    return self.list

  #-------------------------------------------------------------------------------
  # Reads a 1 or 2 column table in CSV format.
  # When 1 column table is read the file should have 2 lines: a header, a value.
  # fieldTypes can be: I,F of S.
  # If there is 1 column/row the key value is '1'!
  def loadCSV(self,fileName,fieldTypes=["I","I"]):
    if len(fieldTypes) == 1:
      self.loadCSVOneField(fileName,fieldTypes)
    else:
      self.loadCSVMultipleFields(fileName,fieldTypes)

  #-------------------------------------------------------------------------------
  # Reads a 2 column table in CSV format.
  # fieldTypes can be: I,F of S.
  def loadCSVMultipleFields(self,fileName,fieldTypes=["I","I"]):
    self.fileName = fileName
    self.fieldTypes = fieldTypes

    # Check fieldtypes.
    self.checkFieldTypes(2)

    # Set default 'virtual' fieldnames.
    fieldNames = ["field1","field2"]

    # 20201202    
    #with open(fileName,"rb") as f:
    with open(fileName,newline="") as f:
      dialect = csv.Sniffer().sniff(f.read(1024),delimiters=";")
      f.seek(0)
      reader = csv.DictReader(f,fieldNames,dialect=dialect)

      # 20201130
      #fieldNames = reader.next()
      fieldNames = next(reader)
      for row in reader:
        # Get key.
        key = row["field1"]
        # Check for defaultValue.
        if key == "*":
          value = row["field2"]
          value = self.parseFieldValue(value,self.fieldTypes[1])
          self.defaultValue = value
        else:
          key = self.parseFieldValue(key,self.fieldTypes[0])
          value = row["field2"]
          value = self.parseFieldValue(value,self.fieldTypes[1])
          self[key] = value

  #-------------------------------------------------------------------------------
  # Reads a 1 column/row table in CSV format.
  # fieldTypes can be: I,F of S.
  # The dict has one key with value 1.
  def loadCSVOneField(self,fileName,fieldTypes=["I"]):
    self.fileName = fileName
    self.fieldTypes = fieldTypes

    # Check fieldtypes.
    self.checkFieldTypes(1)

    # Check the file.
    if not os.path.isfile(fileName):
      Err.raiseGlobioError(Err.FileNotFound1,fileName)
    
    try:
      # 20201202
      #with open(fileName,"r") as f:
      with open(fileName,newline="") as f:
        pLines = f.readlines()
    except:
      Err.raiseGlobioError(Err.ErrorReadingFile1,fileName)

    # Check the lines.
    if len(pLines)<2:
      Err.raiseGlobioError(Err.InvalidNumberOfCSVLines1,fileName)

    # Get key and value.          
    key = 1
    value = pLines[1]
    if value.find(";")>=0:
      value = UT.strBefore(value,";")
    value = self.parseFieldValue(value,self.fieldTypes[0])

    # Add the key/value.
    self[key] = value

  #-------------------------------------------------------------------------------
  # Reads a pivot table in CSV format.
  #
  # Example:
  #              Biome
  #    Landuse     7       8
  #    ------------------------------
  #       1       0.5     0.6
  #       2       0.7     0.8
  #
  # In the CSV file:
  #
  # LANDUSE;7;8;9;10;11;12;13;14;15;16;17;18;19;20;21
  # 1;1,000;1,000;1,000;1,000;1,000;1,000;1,000;1,000;1,000;1,000;1,000;1,000;1,000;1,000;1,000
  # 2;1,000;1,000;1,000;1,000;1,000;1,000;1,000;1,000;1,000;1,000;1,000;1,000;1,000;1,000;1,000
  # 3;1,000;1,000;1,000;1,000;1,000;1,000;1,000;1,000;1,000;1,000;1,000;1,000;1,000;1,000;1,000
  # ...
  #
  # Creates a combined key of the series. Values will be concatenated
  # by "_".
  # In the example the table will be transformed to:
  #   1_7   0.5
  #   1_8   0.6
  #   2_7   0.7
  #   2_8   0.8
  #     
  # fieldTypes can be: I,F of S.
  # The 2 first fieldtypes (the keys) should be "I".
  def loadPivotCSV(self,fileName,mainFieldName,fieldTypes=["I","I","I"]):
    self.fileName = fileName
    self.fieldTypes = fieldTypes

    # Check fieldtypes.
    self.checkFieldTypes(3)

    #TODO: Handling default value specification, i.e. *;<value>

    fieldNames = None
    # 20201202
    #with open(fileName,"rb") as f:
    with open(fileName,newline="") as f:
      # Read csv.
      dialect = csv.Sniffer().sniff(f.read(1024),delimiters=";")
      f.seek(0)
      reader = csv.DictReader(f,dialect=dialect)
      # Get data rows.
      for row in reader:
        # Get fieldnames.
        if fieldNames is None:
          fieldNames = row.keys()
        # Get main key.
        key1 = row[mainFieldName]
        # Get other keys.
        for key2 in fieldNames:
          if key2.lower() == mainFieldName.lower():
            continue
          # Create the full key.
          key = "%s_%s" % (key1,key2)
          # Get value.
          value = row[key2]
          value = self.parseFieldValue(value,self.fieldTypes[2])
          self[key] = value

  #-------------------------------------------------------------------------------
  def parseFieldValue(self,fieldValue,fieldType):
    # Replace "," with ".".
    fieldValue = fieldValue.replace(",",".")
    # Convert to type.
    if fieldType=="I":
      if not UT.isInteger(fieldValue):
        Err.raiseSyntaxError(Err.InvalidIntegerInCSVFile2,None,fieldValue,self.fileName)
      value = int(fieldValue)
    elif fieldType=="F":
      if not UT.isFloat(fieldValue):
        Err.raiseSyntaxError(Err.InvalidFloatInCSVFile2,None,fieldValue,self.fileName)
      value = float(fieldValue)
    else:
      value = str(fieldValue)
    return value      

  #-------------------------------------------------------------------------------
  def show(self):
    if not self.defaultValue is None:
      print("default: %s" % self.defaultValue)
    for key in self:
      print("%s = %s" % (key,self[key]) )

  #-------------------------------------------------------------------------------
  def values(self):
    v = []
    for k in self.list:
      v.append(self[k])
    return v

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  
  #-------------------------------------------------------------------------------
  def testLookup():
  
    fileName = r"P:\Project\Globio4\prg\src\Globio\Lookup\LanduseMSA.csv"
    fieldTypes = ["I","F"]
    
    #print "--------------"
    lut = Lookup()
    lut.loadCSV(fileName,fieldTypes)
    lut.show()
    
    lut = None
    print("Ready")

  #-------------------------------------------------------------------------------
  def testLookupOrder():
  
    fileName = r"P:\Project\Globio4\prg\src\Globio\Lookup\PatchAreaMSA.csv"
    fieldTypes = ["F","F"]
    
    lut = Lookup()
    lut.loadCSV(fileName,fieldTypes)
    lut.show()
    lut = None
    print("Ready")

  #-------------------------------------------------------------------------------
  def testLookupPivot():
  
    #fileName = r"P:\Project\Globio4\prg\src\Globio\Lookup\LanduseBiomeMSA.csv"
    fileName = r"P:\Project\Globio4\prg\src\Globio\Lookup\TestPivotMSA.csv"
    fieldTypes = ["I","I","F"]
    
    #print "--------------"
    lut = Lookup()
    lut.loadPivotCSV(fileName,"LANDUSE",fieldTypes)
    lut.show()
    
    print(lut["1_9"])
    print(lut["2_10"])
    print(lut["3_8"])
    print(lut["3_10"])

    lut = None

    fileName = r"P:\Project\Globio4\prg\src\Globio\Lookup\LanduseBiomeMSA.csv"
    lut = Lookup()
    lut.loadPivotCSV(fileName,"LANDUSE",fieldTypes)
    lut.show()
    
    print("Ready")

  #-------------------------------------------------------------------------------
  def testLookupOneField():
  
    fileName = r"P:\Project\Globio4\prg\src\Globio\Lookup\InfraDisturbanceMSA.csv"
    fieldTypes = ["F"]
    
    #print "--------------"
    lut = Lookup()
    lut.loadCSV(fileName,fieldTypes)
    lut.show()
    
    lut = None
    print("Ready")

  #-------------------------------------------------------------------------------
  def testLookup20161124():
  
    #fileName = r"P:\Project\Globio4LA\data\referentie\v402\30sec_wrld\in_20161124\LandcoverToLanduseCodes.csv"
    fileName = r"P:\Project\Globio4LA\data\referentie\v402\30sec_wrld\in_20161124\LandcoverToLanduseCodes_nok.csv"
    fieldTypes = ["I","I"]
    
    lut = Lookup()
    lut.loadCSV(fileName,fieldTypes)
    lut.show()

    print("defaultValue: %s" % lut.defaultValue)
    print("--------------")
    print(lut.keys())
    print("--------------")
    print(lut.values())
    print("--------------")
    
    print(lut[30])
    
    lut = None
    print("Ready")

  #-------------------------------------------------------------------------------
  #testLookup()
  #testLookupOrder()
  #testLookupPivot()
  #testLookupOneField()
  testLookup20161124()

