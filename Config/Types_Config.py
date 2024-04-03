# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License,  EUPL v1.2
# ******************************************************************************

#-------------------------------------------------------------------------------
# Modified: 19 jan 2017, ES, ARIS B.V.
#           - Version 4.0.5
#           - RasterList added.
#-------------------------------------------------------------------------------

import GlobioModel.Core.Types as Types

#-------------------------------------------------------------------------------
def defineTypes(typeList):
  
  typeList.add(Types.Obj())
  
  typeList.add(Types.Boolean())
  typeList.add(Types.Integer())
  typeList.add(Types.Float())
  typeList.add(Types.String())
  
  typeList.add(Types.CellSize())
  typeList.add(Types.Extent())

  typeList.add(Types.Dir())
  typeList.add(Types.File())
  typeList.add(Types.Raster())
  typeList.add(Types.RasterList())
  typeList.add(Types.Vector())
 
