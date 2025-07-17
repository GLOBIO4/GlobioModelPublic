# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************

#-------------------------------------------------------------------------------
#
# Remarks:
#           Supports lookup by key based on multiple fields.
#           The key is made of the first n-a row values, the value is the last
#           value.
#           Before using getValue(keyValues) the index must be created.
#
# Modified: 31 may 2017, ES, ARIS B.V.
#           - Version 4.0.6
#           - read modified, delimiter argument added.
#           - Row() added and read modified. Field order is now preserved.
#           2 dec 2020, ES, ARIS B.V.
#           - Version 4.1.0
#           - read modified, because of because of open(,newline="").
#           11 jan 2021, ES, ARIS B.V.
#           - Version 4.1.1
#           - CSVFIle - createIndex, createKey and getValue added for lookup by key.
#           - CSVFIle - write added.
#           - Row - count added.
#           - Row - getKeyValues added.
#           - Row - getValue added.
#           - CSVFIle - parseFieldValue modified.
#           - CSVFIle - aggregateRowValue modified because of sumValue.
#-------------------------------------------------------------------------------

import os
import csv

import GlobioModel.Core.Error as Err
import GlobioModel.Common.Utils as UT

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
# Class for csv rows. Inherited from dict because of preserving correct
# field order (dict field order are random).
# Fieldnames are case sensitive!!!
class Row(dict):

  list = []    # fieldNames

  #-------------------------------------------------------------------------------
  def __init__(self):
    super(Row,self).__init__()
    self.list = []

  #-------------------------------------------------------------------------------
  def __iter__(self):
    return iter(self.list)

  #-------------------------------------------------------------------------------
  def __setitem__(self,key,value):
    super(Row,self).__setitem__(key,value)
    self.list.append(key)

  #-------------------------------------------------------------------------------
  def __str__(self):
    s = "{"
    for key in self.list:
      v = self.__getitem__(key)
      if UT.isString(v):
        s += "'%s': '%s', " % (key,v)
      else:
        s += "'%s': %s, " % (key,v)
    s = s.strip(", ")
    s += "}"
    return s

  #-------------------------------------------------------------------------------
  # Returns the number of fields.
  def count(self):
    return len(self.list)

  #-------------------------------------------------------------------------------
  # Returns a list of values of the first n-1 fields.
  def getKeyValues(self):
    return list(self.values())[:self.count()-1]

  #-------------------------------------------------------------------------------
  # Returns the value of the last field.
  def getValue(self):
    return list(self.values())[self.count()-1]

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class CSVFile(object):
  
  #-------------------------------------------------------------------------------
  def __init__(self):
    self.fileName = ""
    # 20210115
    #self.fieldNames = None

    # A list of rows. Each row is a dict[fieldName] and has a .list which
    # constains all fieldnames.
    self.rows = []

    # A snapshot dict of the data to fast access the values by key.
    # The key is the first n-1 fields, the value is the n field.
    self.index = None

  #-------------------------------------------------------------------------------
  # Usage:
  #
  #  addValues(fieldNames,1,2,3)
  #  v = [2,2,3]
  #  pNewCSV.addValues(fieldNames,*v)
  #
  def addValues(self,fieldNames,*values):

    # Already rows (and fields)?
    if len(self.rows)>0:
      # Get fieldnames.
      rowFieldNames = list(self.rows[0].keys())

      # Check nr. of fieldnames.
      if len(fieldNames) != len(rowFieldNames):
        Err.raiseGlobioError(Err.UserDefined1,"No valid number of fieldnames (addValues).")

      # Check fieldnames are equal.
      if "".join(rowFieldNames)!="".join(fieldNames):
        Err.raiseGlobioError(Err.UserDefined1,"No valid fieldnames (addValues).")

    # Check nr. of values.
    if len(values) != len(fieldNames):
      Err.raiseGlobioError(Err.UserDefined1,"No valid number of values (addValues).")

    # Create row dict and add row.
    row = Row()
    for k,v in list(zip(fieldNames,values)):
      row[k] = v
    self.rows.append(row)

  #-------------------------------------------------------------------------------
  # Aggregates and summarize the values of simular rows.
  # SumFieldName is the name of the field to summarize.
  def aggregateRowValue(self,sumFieldName):
    
    if len(self.rows) == 0:
      return

    # Get fieldnames.
    fieldNames = self.rows[0].keys()

    # Check the key and value fieldname.
    self.checkFieldNames(fieldNames,[sumFieldName])

    # Create fieldname lookup.
    fieldNameLookup = self.createFieldNameLookup(fieldNames,[sumFieldName])
    
    sumValues = dict()
        
    for row in self.rows:
      # Create key of other field values.
      key = ""
      # 20210212
      sumValue = 0
      for fieldName in fieldNames:
        if fieldName.upper() == sumFieldName.upper():
          sumValue = row[fieldName]
        else:
          key += str(row[fieldName]) + "_"

      if key in sumValues:
        _, currValue = sumValues[key]
        sumValues[key]= (row, currValue + sumValue)
      else:
        sumValues[key] = (row, sumValue)
                      
    orgSumFieldName = fieldNameLookup[sumFieldName]
    newRows = []                        
    for key in sumValues:
      row, sumValue = sumValues[key]
      row[orgSumFieldName] = sumValue
      newRows.append(row)

    self.rows = newRows
    
  #-------------------------------------------------------------------------------
  # Checks case-insensitive if fieldNames are found in orgFieldNames.
  def checkFieldNames(self,orgFieldNames,fieldNames):
    newOrgFieldNames = []
    for orgFieldName in orgFieldNames:
      newOrgFieldNames.append(orgFieldName.upper())
    for fieldName in fieldNames:
      if not fieldName.upper() in newOrgFieldNames:
        Err.raiseGlobioError(Err.FieldNotFound1,fieldName)
    
  #-------------------------------------------------------------------------------
  # Creates a fieldname lookup for case-insensitive fieldnames. 
  def createFieldNameLookup(self,orgFieldNames,fieldNames):
    fieldNameLookup = dict()
    for fieldName in fieldNames:
      for orgFieldName in orgFieldNames:
        if fieldName.upper()==orgFieldName.upper():
          fieldNameLookup[fieldName] = orgFieldName
    return fieldNameLookup

  #-------------------------------------------------------------------------------
  # Creates the index dict.
  # When the data (in the rows) is modified, the index should be re-created.
  def createIndex(self):
    # Create dict.
    self.index = dict()
    # Get the fieldnames.
    fieldNames = list(self.rows[0].keys())
    # Get key fieldnames, i.e. all except last fieldname.
    keyFieldNames = fieldNames[:-1]
    # Get value fieldname, i.e. last fieldname.
    valueFieldName = fieldNames[-1:][0]
    #print(keyFieldNames)
    #print(valueFieldName)
    # Loop rows.
    for row in self.rows:
      # Get key values and create key.
      keyValues = [row.get(keyFieldName) for keyFieldName in keyFieldNames]
      #print(keyValues)
      key = self.createKey(*keyValues)
      #print(key)
      # Get value and add to dict.
      self.index[key] = row[valueFieldName]

  #-------------------------------------------------------------------------------
  # Creates a key for the index dict. Field values are joined by "_".
  def createKey(self,*keyValues):
    #print(len(keyValues))
    #print(keyValues)
    # TODO: Check on join char in key values.
    # Convert key values to strings.
    values = list(map(lambda x: str(x),keyValues))
    # Join key values.
    key = "_".join(values)
    return key

  # #-------------------------------------------------------------------------------
  # # Creates a key for the row.
  # def createKeyFromRow(self,row):
  #
  #   #print(len(keyValues))
  #   #print(keyValues)
  #   # TO DO: Check on join char in key values.
  #   # Convert key values to strings.
  #   values = list(map(lambda x: str(x),keyValues))
  #   # Join key values.
  #   key = "_".join(values)
  #   return key

  #-------------------------------------------------------------------------------
  # Before getting a value the index must be created.
  # Returns None if not found.
  # Usage:
  #       value = pCSV.getValue(27,3)
  #
  #       key = [27,0]
  #       value = pCSV.getValue(*key)
  #
  def getValue(self,*keyValues):
    if self.index is None:
      # TODO: Constante van maken.
      Err.raiseGlobioError(Err.UserDefined1,"No index available (getValue).")
    key = self.createKey(*keyValues)
    if key in self.index:
      return self.index[key]
    else:
      return None

  #-------------------------------------------------------------------------------
  # Parse the fieldvalue according to the fieldtype.
  # Valid fieldtypes are: I,F,S.
  def parseFieldValue(self,fieldValue,fieldType):
    # Convert to type.
    if fieldType.upper()=="I":
      if not UT.isInteger(fieldValue):
        Err.raiseSyntaxError(Err.InvalidIntegerInCSVFile2,None,fieldValue,self.fileName)
      value = int(fieldValue)
      return value
    elif fieldType.upper()=="F":
      # Replace "," with ".".
      fieldValue = fieldValue.replace(",",".")
      if not UT.isFloat(fieldValue):
        Err.raiseSyntaxError(Err.InvalidFloatInCSVFile2,None,fieldValue,self.fileName)
      value = float(fieldValue)
      return value
    elif fieldType.upper()=="S":
      value = str(fieldValue)
      return value
    else:
      Err.raiseSyntaxError(Err.InvalidFieldType1,fieldType)
  # 20210212
  # def parseFieldValue(self,fieldValue,fieldType):
  #   # Convert to type.
  #   if fieldType.upper()=="I":
  #     if not UT.isInteger(fieldValue):
  #       Err.raiseSyntaxError(Err.InvalidIntegerInCSVFile2,None,fieldValue,self.fileName)
  #     value = int(fieldValue)
  #   elif fieldType.upper()=="F":
  #     # Replace "," with ".".
  #     fieldValue = fieldValue.replace(",",".")
  #     if not UT.isFloat(fieldValue):
  #       Err.raiseSyntaxError(Err.InvalidFloatInCSVFile2,None,fieldValue,self.fileName)
  #     value = float(fieldValue)
  #   elif fieldType.upper()=="S":
  #     value = str(fieldValue)
  #   else:
  #     Err.raiseSyntaxError(Err.InvalidFieldType1,fieldType)
  #   return value

    #-------------------------------------------------------------------------------
  # Reads a csv file.
  # Values should be separated by ; or ,.
  # Gets the data from the specified fieldnames and converts the data to the
  # specified types.
  # The data is read in the rows array. Each row contains a dict with
  # (fieldName: value). 
  # The fieldnames are case-insensitive. The specified fieldnames are used
  # as (new) fieldnames.
  # Floats can have . or , as decimal delimiter.
  # Delimiter is the field separator and is tested with the values ";" 
  # and ",". When using "," text field values which are quoted by an " and
  # which contains a , are read correctly.
  def read(self,fileName,fieldNames,fieldTypes,delimiter=";"):

    # Check filename.
    if not os.path.isfile(fileName):
      Err.raiseGlobioError(Err.FileNotFound1,fileName)

    # Set filename.
    self.fileName = fileName

    # Clear rows.
    self.rows = []

    # Open the file.
    # 20201202
    #with open(fileName,"rb") as f:
    with open(fileName,newline="") as f:
      
      if delimiter==";":
        # Create a dialect.
        dialect = csv.Sniffer().sniff(f.read(1024),delimiters=";")
        f.seek(0)
      else:
        # Use the default dialeg 'excel'.
        dialect = None
        
      # Create a dictionary reader.
      reader = csv.DictReader(f,dialect=dialect)

      # Loop the rows.
      fieldNameLookup = None
      for row in reader:
        
        # Check the fieldnames and make a fieldname lookup for dealing with
        # case-insensitive fieldnames.
        if fieldNameLookup is None:
          # Check the fieldnames.
          self.checkFieldNames(reader.fieldnames,fieldNames)
          # Create a fieldname lookup for case-insensitive fieldnames. 
          fieldNameLookup = self.createFieldNameLookup(reader.fieldnames,fieldNames)

        # Process row data.
        newRow = Row()
        i = 0
        for fieldName in fieldNames:
          orgFieldName = fieldNameLookup[fieldName]
          orgValue = row[orgFieldName]
          value = self.parseFieldValue(orgValue,fieldTypes[i])
          newRow[fieldName] = value
          i += 1
                  
        self.rows.append(newRow)

  #-------------------------------------------------------------------------------
  def show(self):
    for row in self.rows:
      print(row)

  #-------------------------------------------------------------------------------
  # Writes the data to disk.
  # Includes a header with all fieldnames.
  def write(self, fileName: str,overwrite: bool=False):

    # No overwrite?
    if not overwrite:
      if os.path.isfile(fileName):
        Err.raiseGlobioError(Err.FileAlreadyExists1,fileName)
    else:
      if os.path.isfile(fileName):
        os.remove(fileName)

    # Loop rows.
    lines = []
    # 20210212
    fieldNames = []
    for i in range(len(self.rows)):
      # First row?
      if i == 0:
        # Add fieldnames.
        fieldNames = list(self.rows[0].keys())
        line = ";".join(fieldNames)
        lines.append(line)

      # Add data.
      values = [str(self.rows[i].get(fieldName)) for fieldName in fieldNames]
      line = ";".join(values)
      lines.append(line)

    # Write lines to file.
    UT.fileWrite(fileName,lines)

    # Free lines.
    del lines

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  
  #-------------------------------------------------------------------------------
  # OK
  def testRead():
  
    fileName = r""
    fieldNames = ["IMGREGCD","AggLUClass","totalArea"]
    fieldTypes = ["I","S","F"]
    pCSV = CSVFile()
    print("Reading %s..." % fileName)
    pCSV.read(fileName,fieldNames,fieldTypes)
    pCSV.show()

    fileName = r""
    fieldNames = ["IMGREGCD","AggLUClass","totalArea"]
    fieldTypes = ["I","S","F"]
    pCSV = CSVFile()
    print("Reading %s..." % fileName)
    pCSV.read(fileName,fieldNames,fieldTypes)
    pCSV.show()

    fileName = r""
    fieldNames = ["IMGREGCD","AggLUClass","totalArea"]
    fieldTypes = ["I","S","F"]
    pCSV = CSVFile()
    print("Reading %s..." % fileName)
    pCSV.read(fileName,fieldNames,fieldTypes)
    pCSV.show()

    fileName = r""
    fieldNames = ["VDM_NUMMER","WAARDE_POSITIEBEPALING_LADEN","LADEN_GPS_LOCATIE"]
    fieldTypes = ["I","S","S"]
    print("Reading %s..." % fileName)
    pCSV = CSVFile()
    pCSV.read(fileName,fieldNames,fieldTypes,delimiter=",")
    pCSV.show()

  #-------------------------------------------------------------------------------
  # OK
  def testReadTwoColumns():

    fileName = r""
    fieldNames = ["ImgRegCd","TotalArea"]
    fieldTypes = ["I","F"]
    
    pCSV = CSVFile()
    pCSV.read(fileName,fieldNames,fieldTypes)
    pCSV.show()

    sumFieldName = "totalArea"
    pCSV.aggregateRowValue(sumFieldName)
    pCSV.show()

  #-------------------------------------------------------------------------------
  # NOK, 20170531, reclassRowValue bestaat niet meer.
  # OK
  def testReclass():
    # 20201118
    pass

  #-------------------------------------------------------------------------------
  # OK
  def testRead2021():
    # region;landuse;area_km2
    # 7;0;504554.53125
    # 7;1;4643.12451171875

    fileName = "ReferenceClaims2015.csv"
    fieldNames = ["region","landuse","area_km2"]
    fieldTypes = ["I","I","F"]

    pCSV = CSVFile()
    pCSV.read(fileName,fieldNames,fieldTypes)

    pCSV.show()

    test = False
    if test:
      print()
      fieldNames = list(pCSV.rows[0].keys())
      print(fieldNames)
      for row in pCSV.rows:
        print("%s %s %s" % (row[fieldNames[0]],row[fieldNames[1]],row[fieldNames[2]]))

    key = pCSV.createKey(27,3)
    print(key)

    pCSV.createIndex()
    print(pCSV.index)
    value = pCSV.getValue(27,3)
    print(value)
    value = pCSV.getValue(25,3)
    print(value)

    key = [27,0]
    value = pCSV.getValue(*key)
    print(value)

    fieldNames = list(pCSV.rows[0].keys())
    row = pCSV.rows[1]
    print(fieldNames)
    values = [str(row.get(fieldName)) for fieldName in fieldNames]
    print(values)
    line = ";".join(values)
    print(line)

    print("Writing...")
    fileName = "tmp.csv"
    pCSV.write(fileName,True)

    a = ["a","b"]
    v = [3,4]
    d = dict(zip(a,v))
    print(d)

    pNewCSV = CSVFile()
    fieldNames = ["a","b","c"]
    pNewCSV.addValues(fieldNames,1,2,3)
    v = [2,2,3]
    pNewCSV.addValues(fieldNames,*v)
    pNewCSV.show()

    # 20210118
    fieldNames = ["a","b","c"]
    pNewCSV1 = CSVFile()
    pNewCSV1.addValues(fieldNames,1,2,30)
    pNewCSV1.addValues(fieldNames,2,2,40)

    pNewCSV2 = CSVFile()
    pNewCSV2.addValues(fieldNames,1,2,130)
    pNewCSV2.addValues(fieldNames,2,2,140)

    #sum = 0
    for row in pNewCSV1.rows:
      k = list(row.keys())[0]
      v1 = list(row.values())[0]
      v2 = list(row.values())[1]
      v3 = list(row.values())[2]
      print("%s %s %s %s" % (k,v1,v2,v3))
    # v = [2,2,3]
    # pNewCSV.addValues(fieldNames,*v)
    # pNewCSV.show()

  #-------------------------------------------------------------------------------
  # OK
  # [1, 2]
  # 3
  # 30
  # lookup 130
  # [2, 2]
  # 3
  # 40
  # lookup 140
  def testRead2021Row():

    fieldNames = ["a","b","c"]
    pNewCSV1 = CSVFile()
    pNewCSV1.addValues(fieldNames,1,2,30)
    pNewCSV1.addValues(fieldNames,2,2,40)

    pNewCSV2 = CSVFile()
    pNewCSV2.addValues(fieldNames,1,2,130)
    pNewCSV2.addValues(fieldNames,2,2,140)

    pNewCSV2.createIndex()

    for row in pNewCSV1.rows:
      keyvals = row.getKeyValues()
      print(keyvals)
      val = row.getValue()
      print(val)

      # Lookup.
      val2 = pNewCSV2.getValue(*keyvals)
      print("lookup %s" % val2)

  #-------------------------------------------------------------------------------
  #-------------------------------------------------------------------------------
  # run Core\CSVFile.py

  #testRead()
  #testReadTwoColumns()
  #testReclass()
  #testRead2021()
  testRead2021Row()
