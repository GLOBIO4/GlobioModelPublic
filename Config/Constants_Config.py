
#-------------------------------------------------------------------------------
# Modified: 30 sept 2016, ES, ARIS B.V.
#           - Version 4.0.2
#           - cellSize_10deg etc. added.
#           - Extent aliasses eu and wrld added.
#           11 jan 2021, ES, ARIS B.V.
#           - Version 4.1.1
#           - cellSize* etc. moved to Globals to make these constants easier
#             to access.
#-------------------------------------------------------------------------------

import GlobioModel.Core.Globals as GLOB

#-------------------------------------------------------------------------------
def defineConstants(constantList):
  
  # Boolean.
  constantList.add("True","","BOOLEAN",True)
  constantList.add("False","","BOOLEAN",False)

  # System.
  constantList.add("UserName","","STRING",GLOB.userName)
  constantList.add("UserTempDir","","DIR",GLOB.userTempDir)
    
  # Cellsize in decimal degrees.
  constantList.add("10deg","","CELLSIZE",GLOB.cellSize_10deg)
  constantList.add("1deg","","CELLSIZE",GLOB.cellSize_1deg)
  constantList.add("30min","","CELLSIZE",GLOB.cellSize_30min)
  constantList.add("5min","","CELLSIZE",GLOB.cellSize_5min)
  constantList.add("30sec","","CELLSIZE",GLOB.cellSize_30sec)
  constantList.add("10sec","","CELLSIZE",GLOB.cellSize_10sec)
  
  # Set valid cellsizes.
  constantList.add("ValidCellSizes","","STRING",GLOB.validCellSizes)
  
  # Extent in degrees.
  constantList.add("world","","EXTENT",GLOB.extent_World)
  # Main europian countries.
  constantList.add("europe","","EXTENT",GLOB.extent_Europe)
  # Nederland.
  constantList.add("nl","","EXTENT",GLOB.extent_NL)

  # Extent aliasses.
  constantList.add("wrld","","EXTENT",GLOB.extent_World)
  constantList.add("eu","","EXTENT",GLOB.extent_Europe)

  # Test integer/float.
  if GLOB.testing:
    constantList.add("test_int","","INTEGER",1000)
    constantList.add("test_float","","FLOAT",1.234)
