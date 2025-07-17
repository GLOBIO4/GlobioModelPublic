# ******************************************************************************
## GLOBIO - https://www.globio.info
## PBL Netherlands Environmental Assessment Agency - https://www.pbl.nl.
## Reuse permitted under European Union Public License, EUPL v1.2
# ******************************************************************************

import pandas as pd
import numpy as np
from typing import Union

import GlobioModel.Core.Error as Err
import GlobioModel.Core.Logger as Log
import GlobioModel.Common.Utils as UT
from GlobioModel.Core.CalculationBase import CalculationBase

CSV_IO_KWARGS = {
   "encoding": "utf-8",
   "sep": ";"
}

#-------------------------------------------------------------------------------
class GLOBIO_CalcBIFs(CalculationBase):
  """
  Creates a summary file of Biodiversity Impact Factors (BIFs)
  """
  
  #-------------------------------------------------------------------------------
  def run(self, *args):
    """
    IN FILE region_name_map
    IN FILE iso_region_map
    IN FILE iso_tm5_map
    IN FILE iso_landuse_areas
    IN FILE iso_road_lengths
    IN FILE iso_nitrogen_deposition
    IN FILE iso_nitrogen_emissions
    IN FILE MSA_loss_area_LU_plants
    IN FILE MSA_loss_area_LU_wbvert
    IN FILE MSA_loss_area_CC_plants
    IN FILE MSA_loss_area_CC_wbvert
    IN FILE MSA_loss_area_MD_wbvert
    IN FILE MSA_loss_area_RD_wbvert
    IN FILE MSA_loss_area_IF_full_wbvert
    IN FILE MSA_loss_area_IF_noroads_wbvert
    IN FILE MSA_loss_area_IF_nolu_wbvert
    IN FILE MSA_loss_area_ND_plants
    IN FILE NH3_TM5_source_receptor_matrix
    IN FILE NOx_TM5_source_receptor_matrix
    IN STRING landuse_codes
    IN STRING landuse_names
    IN STRING frag_landuse_codes
    IN STRING mining_landuse_code
    IN FLOAT GMTI
    IN FLOAT IAGTP
    OUT FILE BIF_summary
    """
    self.showStartMsg(args)
    
    # Check number of arguments.
    if len(args) != 26:
      Err.raiseGlobioError(Err.InvalidNumberOfArguments2, len(args), self.name)

    region_name_map_file = args[0]
    iso_region_map_file = args[1]
    iso_tm5_map_file = args[2]
    iso_landuse_areas_file = args[3]
    iso_road_lengths_file = args[4]
    iso_nitrogen_deposition_file = args[5]
    iso_nitrogen_emissions_file = args[6]
    msa_loss_area_lu_plants_file = args[7]
    msa_loss_area_lu_wbvert_file = args[8]
    msa_loss_area_cc_plants_file = args[9]
    msa_loss_area_cc_wbvert_file = args[10]
    msa_loss_area_md_wbvert_file = args[11]
    msa_loss_area_rd_wbvert_file = args[12]
    msa_loss_area_if_full_wbvert_file = args[13]
    msa_loss_area_if_noroads_wbvert_file = args[14]
    msa_loss_area_if_nolu_wbvert_file = args[15]
    msa_loss_area_nd_plants_file = args[16]
    nh3_tm5_source_receptor_matrix = args[17]
    nox_tm5_source_receptor_matrix = args[18]
    landuse_codes = args[19]
    landuse_names = args[20]
    frag_landuse_codes = args[21]
    mining_landuse_code = args[22]
    gmti = args[23]
    iagtp = args[24]
    bif_summary_file = args[25]

    self.checkFile(region_name_map_file)
    self.checkFile(iso_region_map_file, optional=True)
    self.checkFile(iso_tm5_map_file)
    self.checkFile(iso_landuse_areas_file)
    self.checkFile(iso_road_lengths_file)
    self.checkFile(iso_nitrogen_deposition_file)
    self.checkFile(iso_nitrogen_emissions_file, optional=True)
    self.checkFile(msa_loss_area_lu_plants_file)
    self.checkFile(msa_loss_area_lu_wbvert_file)
    self.checkFile(msa_loss_area_cc_plants_file)
    self.checkFile(msa_loss_area_cc_wbvert_file)
    self.checkFile(msa_loss_area_md_wbvert_file)
    self.checkFile(msa_loss_area_rd_wbvert_file)
    self.checkFile(msa_loss_area_if_full_wbvert_file)
    self.checkFile(msa_loss_area_if_noroads_wbvert_file)
    self.checkFile(msa_loss_area_if_nolu_wbvert_file)
    self.checkFile(msa_loss_area_nd_plants_file)
    self.checkFile(nh3_tm5_source_receptor_matrix)
    self.checkFile(nox_tm5_source_receptor_matrix)
    self.checkIntegerList(landuse_codes)
    self.checkListCount(landuse_codes,landuse_names)
    self.checkIntegerList(frag_landuse_codes)
    self.checkInteger(mining_landuse_code, 0, 255)
    self.checkFloat(gmti, -100.0, 100.0)
    self.checkFloat(iagtp, 0.0, 1e-10)
    self.checkFile(bif_summary_file, asOutput=True)

    landuse_codes_names = dict(zip(self.splitIntegerList(landuse_codes), self.splitStringList(landuse_names)))
    frag_landuse_codes = self.splitIntegerList(frag_landuse_codes)
    mining_landuse_code = int(mining_landuse_code)

    self.iso_regid_map = self.loadIsoRegidMap(iso_region_map_file)
    
    # prepare land use areas and road lengths
    region_landuse_areas = self.loadLanduseAreas(iso_landuse_areas_file)
    region_road_lengths = self.loadRoadLengths(iso_road_lengths_file)

    # calculate the bifs per pressure group
    lu_bif_df = self.calculateLanduseBIF(msa_loss_area_lu_plants_file, msa_loss_area_lu_wbvert_file, region_landuse_areas, landuse_codes_names)
    cc_bif_df = self.calculateClimateChangeBIF(msa_loss_area_cc_plants_file, msa_loss_area_cc_wbvert_file, gmti, iagtp)
    dist_bif_df = self.calculateDisturbanceBIF(msa_loss_area_rd_wbvert_file, msa_loss_area_md_wbvert_file, region_landuse_areas, region_road_lengths, mining_landuse_code)
    frag_bif_df = self.calculateFragmentationBIF(msa_loss_area_if_full_wbvert_file, msa_loss_area_if_noroads_wbvert_file, msa_loss_area_if_nolu_wbvert_file, region_landuse_areas, region_road_lengths, frag_landuse_codes)
    ndep_bif_df = self.calculateNitrogenDepositionBIF(msa_loss_area_nd_plants_file, nh3_tm5_source_receptor_matrix, nox_tm5_source_receptor_matrix, iso_nitrogen_deposition_file, iso_nitrogen_emissions_file, iso_tm5_map_file)

    # basis of the final dataframe with all BIFs
    bif_df = pd.read_csv(region_name_map_file, **CSV_IO_KWARGS)
    region_code_key = bif_df.columns[0]
    region_name_key = bif_df.columns[1]
    bif_df = bif_df.set_index(region_code_key)
    # prepare the bif dataframe for being concatenated into a single dataframe
    bif_df.columns = pd.MultiIndex.from_tuples([('', index, '') for index in bif_df.columns])

    # combine all bifs into a single dataframe
    bif_df = pd.concat([bif_df, lu_bif_df, cc_bif_df, dist_bif_df, frag_bif_df, ndep_bif_df],
                       axis=1, keys=['', 'Land use', 'Climate change', 'Disturbance', 'Fragmentation', 'Nitrogen deposition'])
    # move the 'GLOBAL' index label to the top
    bif_df = bif_df.reindex(['GLOBAL'] + [i for i in bif_df.index if i!='GLOBAL'])
    # set the region name as a second index next to the region code
    bif_df = bif_df.set_index([('','', region_name_key)], append=True)
    # name the axes
    bif_df = bif_df.rename_axis([region_code_key, region_name_key], axis=0)
    bif_df = bif_df.rename_axis(['Pressure','Subpressure','Unit','Species group'], axis=1)

    # export the resulting dataframe to a csv
    bif_df.to_csv(bif_summary_file, **CSV_IO_KWARGS)

  def loadIsoRegidMap(self, iso_region_map_file : str):
    # loads the mapping from iso-numeric code to region id
    # if iso_region_map_file is not set (NONE), it is assumed that the output regions are country-level
    if UT.isValueSet(iso_region_map_file):
      # first column contains iso-numeric values, second column contains region identifiers
      iso_regid_map = pd.read_csv(iso_region_map_file, index_col=0, **CSV_IO_KWARGS).iloc[:,0]
    else:
      # output regions are country-level, so one on one mapping
      iso_regid_map = lambda x: x
    return iso_regid_map
  
  def loadLanduseAreas(self, iso_landuse_areas_file : str):
    iso_landuse_areas = pd.read_csv(iso_landuse_areas_file, index_col=0, **CSV_IO_KWARGS)
    iso_landuse_areas = self.splitCombinedIndex(iso_landuse_areas, regidxname="isonum")
    region_landuse_areas = self.sumISOtoRegion(iso_landuse_areas, iso_indexname="isonum")
    return region_landuse_areas["area"]
  
  def loadRoadLengths(self, iso_road_lengths_file : str):
    iso_road_lengths = pd.read_csv(iso_road_lengths_file, index_col=0, **CSV_IO_KWARGS)
    # sum roads of type 1, 2 and 3
    iso_road_lengths["roadlength"] = iso_road_lengths['Type 1'] + iso_road_lengths['Type 2'] + iso_road_lengths['Type 3']
    region_road_lengths = self.sumISOtoRegion(iso_road_lengths["roadlength"])
    return region_road_lengths
  
  def loadMsaLossAreas(self, iso_msa_loss_area_file : str, name) -> pd.Series:
     iso_msa_loss_area = pd.read_csv(iso_msa_loss_area_file, index_col=0, **CSV_IO_KWARGS)
     iso_msa_loss_area = self.splitCombinedIndex(iso_msa_loss_area, regidxname="isonum")
     msa_loss_area = self.sumISOtoRegion(iso_msa_loss_area, iso_indexname="isonum")
     return msa_loss_area["area"].rename(name)

  def sumISOtoRegion(self,
                     iso_data : Union[pd.Series, pd.DataFrame],
                     iso_indexname : str = None
                     ) -> Union[pd.Series, pd.DataFrame]:
    if not iso_indexname:
      # simple single-index data containing iso codes
      return iso_data.groupby(self.iso_regid_map).sum()
    # in case of a multiindex, we need some more steps
    # get the index names minus the one indicating the iso index
    index_names = list(iso_data.index.names)
    index_names.remove(iso_indexname)
    # add a new column with the region identifier
    iso_data["regid"] = iso_data.index.get_level_values(iso_indexname).map(self.iso_regid_map)
    region_data = iso_data.groupby(["regid"] + index_names).sum()
    return region_data

  def splitCombinedIndex(self,
                         df : pd.DataFrame,
                         regidxname : str = "reg",
                         lucidxname : str = "luc"
                         ) -> pd.DataFrame:
    # split a dataframe index with combined region and land use code into a multiindex
    # assumed is that the last three digits of the index are land use code, in front of that the region index
    def splitCode(code : int) -> pd.Series:
        code = str(code)
        return pd.Series([int(code[:-3]), int(code[-3:])], index=[regidxname, lucidxname])
    df["combined"] = df.index
    df[[regidxname, lucidxname]] = df["combined"].apply(splitCode)
    df = df.drop(columns=["combined"])
    df = df.set_index([regidxname, lucidxname])
    return df

  def calculateLanduseBIF(self,
                          msa_loss_area_lu_plants_file : str,
                          msa_loss_area_lu_wbvert_file : str,
                          region_landuse_area : pd.Series,
                          landuse_names : dict
                          ) -> pd.DataFrame:
    """Calculates land use impact factors for each land use category.

    Args:
      msa_loss_area_lu_plants_file : File name of the csv containing the contribution of land use
        to MSA loss areas per country, for the plant species group.
        The index (first column) should be the combined region and land use code.
        The unit of the MSA loss area should be MSAloss*km^2.
        The GLOBIO module CalcMSARegion produces an output that can be used for this.
      msa_loss_area_lu_wbvert_file : same as msa_loss_area_lu_plants_file, but for the wbvert species group.
      region_landuse_area : Series containing the total area per BIF region.
      landuse_names : Dict with names of the land use categories, with land use codes as keys.
        Only for these land use categories will an impact factor be calculated.

      Returns: 
        A DataFrame with a region index based on the MSA loss inputs, and a multiindex column containing
        land use impact factors in MSAloss*km^2/km^2 for each of the given land use categories
        and for each species group plus an overall impact factor calculated as the average over the species groups. 
    """
    Log.info("Calculating land use BIF...")
    plants_df = pd.read_csv(msa_loss_area_lu_plants_file, index_col=0, **CSV_IO_KWARGS).rename(columns={'area': 'loss_area'})
    wbvert_df = pd.read_csv(msa_loss_area_lu_wbvert_file, index_col=0, **CSV_IO_KWARGS).rename(columns={'area': 'loss_area'})
    msa_loss_area_iso_df = pd.merge(plants_df, wbvert_df, left_index=True, right_index=True, suffixes=('_plants', '_wbvert'))

    # split region and land use codes and set as index
    msa_loss_area_iso_df = self.splitCombinedIndex(msa_loss_area_iso_df, regidxname="isonum")
    msa_loss_area_df = self.sumISOtoRegion(msa_loss_area_iso_df, iso_indexname="isonum")
    msa_loss_area_df = msa_loss_area_df.merge(region_landuse_area, how='left', left_index=True, right_index=True)
    
    # reindex land use codes to only include the land use types we are interested in
    new_index = pd.MultiIndex.from_product([msa_loss_area_df.index.levels[0], landuse_names.keys()], names=["regid", "luc"])
    msa_loss_area_df = msa_loss_area_df.reindex(new_index, fill_value=np.nan)

    # calculate the BIFs
    msa_loss_area_df['wbvert'] = msa_loss_area_df['loss_area_wbvert'] / msa_loss_area_df['area']
    msa_loss_area_df['plants'] = msa_loss_area_df['loss_area_plants'] / msa_loss_area_df['area']
    msa_loss_area_df['overall'] = msa_loss_area_df[['wbvert', 'plants']].mean(axis=1)

    # replace the land use codes with their names
    msa_loss_area_df.index = msa_loss_area_df.index.set_levels(msa_loss_area_df.index.levels[1].map(landuse_names), level=1)
    # restructure results by adding a separate column per land use type
    landuse_bif_df = msa_loss_area_df.reset_index(level=1)
    landuse_bif_df = landuse_bif_df.pivot(columns='luc', values=['wbvert', 'plants', 'overall'])
    landuse_bif_df.columns = pd.MultiIndex.from_tuples([index + ('MSAloss*km^2/km^2',) for index in landuse_bif_df.columns])
    landuse_bif_df = landuse_bif_df.reorder_levels([1, 2, 0], axis=1).sort_index(axis=1)
    
    return landuse_bif_df
  
  def calculateClimateChangeBIF(self,
                                msa_loss_area_cc_plants_file : str,
                                msa_loss_area_cc_wbvert_file : str,
                                gmti : float,
                                iagtp : float
                                ) -> pd.DataFrame:
    """Calculates global climate change impact factors.

    Args:
      msa_loss_area_cc_plants_file : File name of the csv containing the contribution of climate change
        to MSA loss areas per region, for the plant species group.
        The index (first column) should be the combined region and land use code.
        The unit of the MSA loss area should be MSAloss*km^2.
        The GLOBIO module CalcMSARegion produces an output that can be used for this.
      msa_loss_area_cc_wbvert_file : same as msa_loss_area_cc_plants_file, but for the wbvert species group.
      gmti : Global mean temperature increase in degrees Celsius.
      iagtp : Integrated average global temperature change potential in degrees Celsius per kg of emitted CO2 per year

      Returns: 
        A DataFrame with a single index label 'GLOBAL' and columns containing
        climate change impact factors in MSAloss*km^2*year/kgCO2 for each species group
        plus an overall impact factor calculated as the average over the species groups. 
    """
    Log.info("Calculating climate change BIF...")
    plants_df = pd.read_csv(msa_loss_area_cc_plants_file, index_col=0, **CSV_IO_KWARGS).rename(columns={'area': 'loss_area'})
    wbvert_df = pd.read_csv(msa_loss_area_cc_wbvert_file, index_col=0, **CSV_IO_KWARGS).rename(columns={'area': 'loss_area'})
    msa_loss_area_df = pd.merge(plants_df, wbvert_df, left_index=True, right_index=True, suffixes=('_plants', '_wbvert'))

    # split region and land use codes and set as index
    msa_loss_area_df = self.splitCombinedIndex(msa_loss_area_df, regidxname="isonum")

    # calculate mean msa loss area between plants and wbverts
    msa_loss_area_df['loss_area_overall'] = msa_loss_area_df[['loss_area_plants', 'loss_area_wbvert']].mean(axis=1)
  
    # climate change bif calculation
    cc_bif = msa_loss_area_df[['loss_area_plants', 'loss_area_wbvert', 'loss_area_overall']].sum(axis=0) * iagtp / gmti
    cc_bif_df = cc_bif.to_frame('GLOBAL').rename(mapper=lambda x: x.replace('loss_area_','')).transpose().sort_index(axis=1)
    cc_bif_df.columns = pd.MultiIndex.from_tuples([('', index, 'MSAloss*km^2*yr/kgCO2') for index in cc_bif_df.columns])
    cc_bif_df = cc_bif_df.swaplevel(axis=1)

    return cc_bif_df
  
  def calculateDisturbanceBIF(self,
                              msa_loss_area_rd_wbvert_file : str,
                              msa_loss_area_md_wbvert_file : str,
                              region_landuse_area : pd.Series,
                              region_road_lengths : pd.Series,
                              mining_landuse_code : int
                              ) -> pd.DataFrame:
    """Calculates infrastructure disturbance impact factors for roads and mines.

    Args:
      msa_loss_area_rd_wbvert_file : File name of the csv containing the contribution of roads
        to MSA loss areas per region, for the wbvert species group.
        The index (first column) should be the combined region and land use code.
        The unit of the MSA loss area should be MSAloss*km^2.
        The GLOBIO module CalcMSARegion produces an output that can be used for this.
      msa_loss_area_md_wbvert_file : same as msa_loss_area_rd_wbvert_file, but for disturbance by mining.
      region_landuse_area : Series containing the total area in km^2 per region.
      region_road_lengths : Series containing road lengths in km per region.
      mining_landuse_code: Code representing mining in the landuse categories.

      Returns: 
        A DataFrame with a region index based on the MSA loss inputs, and a multiindex column containing
        disturbance impact factors in MSAloss*km^2/km and MSAloss*km^2/km^2 for roads and mines respectively,
        and for each species group plus an overall impact factor calculated as the average over the species groups.
    """
    Log.info("Calculating disturbance BIF...")

    road_df = self.loadMsaLossAreas(msa_loss_area_rd_wbvert_file, name="loss_area_wbvert")
    mining_df = self.loadMsaLossAreas(msa_loss_area_md_wbvert_file, name="loss_area_wbvert")

    # aggregate msa loss due to mining disturbance over all land use types, per region
    mining_agg_df = mining_df.groupby(level=0).sum()

    # get total mining area per region to divide by later
    new_index = pd.MultiIndex.from_product([region_landuse_area.index.levels[0], [mining_landuse_code]], names=["regid", "luc"])
    mining_areas_df = region_landuse_area.reindex(new_index, fill_value=np.nan)

    # calculate the mining bif by dividing MSA loss area by the area occupied by mines
    mining_bif_df = pd.merge(mining_agg_df, mining_areas_df, how='left', left_index=True, right_index=True)
    mining_bif_df['Mining'] = mining_bif_df['loss_area_wbvert'] / mining_bif_df['area']
    
    # aggregate msa loss due to road disturbance over all land use types, per region
    road_agg_df = road_df.groupby(level=0).sum()

    # calculate the road disturbance bif by dividing MSA loss area by the road length
    road_bif_df = pd.merge(road_agg_df, region_road_lengths.rename('road_length'), how='left', left_index=True, right_index=True)
    road_bif_df['Roads'] = road_bif_df['loss_area_wbvert'] / road_bif_df['road_length']
    # replace inf with nan for regions with zero road length
    road_bif_df['Roads'] = road_bif_df['Roads'].replace(np.inf, np.nan)

    # reorganize to only output the useful dataframe
    dist_bif_df = pd.merge(road_bif_df, mining_bif_df, how='outer', left_index=True, right_index=True)
    # remove land use code index
    dist_bif_df = dist_bif_df.reset_index(level=1)
    # filter to only keep bif columns
    dist_bif_df = dist_bif_df.filter(['Mining', 'Roads'])
    dist_bif_df.columns = pd.MultiIndex.from_tuples(list(zip(list(dist_bif_df.columns), ['MSAloss*km^2/km^2', 'MSAloss*km^2/km'])))

    nan_df = pd.DataFrame(index=dist_bif_df.index, columns=dist_bif_df.columns)
    dist_bif_df = pd.concat([dist_bif_df/2, nan_df, dist_bif_df], keys=['overall', 'plants', 'wbvert'], axis=1).reorder_levels([1, 2, 0], axis=1).sort_index(axis=1)

    return dist_bif_df
  
  def calculateFragmentationBIF(self,
                                msa_loss_area_if_full_wbvert_file : str,
                                msa_loss_area_if_noroads_wbvert_file : str,
                                msa_loss_area_if_nolu_wbvert_file : str,
                                region_landuse_area : pd.Series,
                                region_road_lengths : pd.Series,
                                frag_landuse_codes : list
                                ) -> pd.DataFrame:
    """Calculates infrastructure fragmentation impact factors for roads and land use.

    Args:
      msa_loss_area_if_full_wbvert_file : File name of the csv containing the contribution of infrastructure
        fragmentation to MSA loss areas per region, for the wbvert species group, for a full run including 
        both land use and roads. The index (first column) should be the combined region and land use code.
        The unit of the MSA loss area should be MSAloss*km^2.
        The GLOBIO module CalcMSARegion produces an output that can be used for this.
      msa_loss_area_if_noroads_wbvert_file : Same as msa_loss_area_if_full_wbvert_file, but for 
        a run excluding roads as a source of fragmentation.
      msa_loss_area_if_nolu_wbvert_file : Same as msa_loss_area_if_full_wbvert_file, but for 
        a run excluding land use as a source of fragmentation.
      region_landuse_area : Series containing the total area in km^2 per region.
      region_road_lengths : Series containing road lengths in km per region.
      frag_landuse_codes: List of land use codes which are deemed to contribute to fragmentation.

      Returns: 
        A DataFrame with a region index based on the MSA loss inputs, and a multiindex column containing
        fragmentation impact factors in MSAloss*km^2/km and MSAloss*km^2/km^2 for roads and land use respectively,
        and for each species group plus an overall impact factor calculated as the average over the species groups.
    """
    Log.info("Calculating fragmentation BIF...")
    # load fragmentation files with and without roads
    fullrun_df = self.loadMsaLossAreas(msa_loss_area_if_full_wbvert_file, name="loss_area_fullrun_wbvert")
    luonly_df = self.loadMsaLossAreas(msa_loss_area_if_noroads_wbvert_file, name="loss_area_luonly_wbvert")
    roadsonly_df = self.loadMsaLossAreas(msa_loss_area_if_nolu_wbvert_file, name="loss_area_roadsonly_wbvert")

    frag_bif_df = pd.merge(fullrun_df, luonly_df, how='outer', left_index=True, right_index=True)
    frag_bif_df = pd.merge(frag_bif_df, roadsonly_df, how='outer', left_index=True, right_index=True)

    # The sum of individual losses for xx_only runs does not necessarily count up to the full run loss
    # For the BIFs, we do want to assign losses to each driver that sum up to the full run loss
    # Therefore, the individual xx_only losses are corrected by a factor (full run loss)/(sum of xx_only losses)
    frag_bif_df['loss_area_sum_wbvert'] = frag_bif_df['loss_area_luonly_wbvert'] + frag_bif_df['loss_area_roadsonly_wbvert']
    frag_bif_df['loss_correction_factor'] = frag_bif_df['loss_area_fullrun_wbvert'] / frag_bif_df['loss_area_sum_wbvert']
    # if summed loss is zero, catch the nan and replace with 0.5 (assign equally across the two drivers)
    frag_bif_df['loss_correction_factor'] = frag_bif_df['loss_correction_factor'].fillna(0.5)

    # assign fractions of individual loss/summed loss of full run losses
    frag_bif_df['loss_area_lu_wbvert'] = frag_bif_df['loss_area_luonly_wbvert'] * frag_bif_df['loss_correction_factor']
    frag_bif_df['loss_area_roads_wbvert'] = frag_bif_df['loss_area_roadsonly_wbvert'] * frag_bif_df['loss_correction_factor']
    
    # aggregate land use types to get sums
    frag_bif_df = frag_bif_df.groupby(level=0).sum()

    # calculate total fragmentation areas per region
    frag_bif_df['frag_area'] = region_landuse_area.loc[:, frag_landuse_codes, :].groupby(level=0).sum()

    # calculate the BIFs
    frag_bif_df['Land use'] = frag_bif_df['loss_area_lu_wbvert'] / frag_bif_df['frag_area']
    frag_bif_df['Roads'] = frag_bif_df['loss_area_roads_wbvert'] / region_road_lengths
    # replace inf with nan for regions with zero road length
    frag_bif_df['Roads'] = frag_bif_df['Roads'].replace(np.inf, np.nan)

    frag_bif_df = frag_bif_df.filter(['Land use', 'Roads'])
    frag_bif_df.columns = pd.MultiIndex.from_tuples(list(zip(frag_bif_df.columns, ['MSAloss*km^2/km^2', 'MSAloss*km^2/km'])))
    nan_df = pd.DataFrame(index=frag_bif_df.index, columns=frag_bif_df.columns)
    frag_bif_df = pd.concat([frag_bif_df/2, nan_df, frag_bif_df], keys=['overall', 'plants', 'wbvert'], axis=1).reorder_levels([1, 2, 0], axis=1).sort_index(axis=1)

    return frag_bif_df
  
  def calculateNitrogenDepositionBIF(self,
                                     msa_loss_area_nd_plants_file : str,
                                     sr_nh3_file : str,
                                     sr_nox_file : str,
                                     iso_nitrogen_deposition_file : str,
                                     iso_nitrogen_emissions_file : str,
                                     iso_tm5_map_file : str
                                     ) -> pd.DataFrame:
    """Calculates nitrogen (NH3 and NOx) impact factors.

    Args:
      msa_loss_area_nd_plants_file : File name of the csv containing the contribution of nitrogen deposition
        to MSA loss areas per region, for the plant species group. 
        The index (first column) should be the combined region and land use code.
        The unit of the MSA loss area should be MSAloss*km^2.
        The GLOBIO module CalcMSARegion produces an output that can be used for this.
      sr_nh3_file : File name of the csv containing a source receptor matrix for nh3 deposition,
        with TM5 regions as rows and columns. There should be an additional column for ocean/sea deposition named 'OCAARC'.
        All rows of the source receptor matrices should add up to one to conserve total amount of nitrogen.
      sr_nox_file : Same as sr_nh3_file, but for NOx.
      iso_nitrogen_deposition_file : File name of the csv containing deposition data per country. Unit should be kg N.
      iso_nitrogen_emissions_file : File name of the csv containing emission data per country. Unit should be kg N. 
        The columns should be labeled 'NH3_emissions' and 'NOx_emissions'.
      iso_tm5_map_file : File name of the csv containing a mapping from country iso-numeric code to TM5 region id.
        The TM5 region column should be named 'TM5'.

    Returns:
      A Dataframe with the same index as the provided TM5 map, and a multiindex column containing
      NH3 and NOx impact factors in MSAloss*km^2/kgN for the species groups, and an overall impact factor 
      calculated as the average over the species groups.
      The current assumption is that nitrogen only affects the plants species group.
    """
    N_MASS = 14
    H_MASS = 1
    O_MASS = 16
    NH3_MASS = N_MASS + 3 * H_MASS
    NICF_NH3 = N_MASS / NH3_MASS
    NO2_MASS = N_MASS + 2 * O_MASS
    NO_MASS = N_MASS + O_MASS
    NICF_NOx = 0.9 * N_MASS / NO2_MASS + 0.1 * N_MASS / NO_MASS # photostationary conditions, Seinfeld and Pandis, 2016

    Log.info("Calculating nitrogen deposition BIF...")
    # load region -> TM5 region mapping
    iso_TM5_map = pd.read_csv(iso_tm5_map_file, index_col=0, **CSV_IO_KWARGS)["TM5"]

    deposition_iso_df = pd.read_csv(iso_nitrogen_deposition_file, index_col=0, **CSV_IO_KWARGS)
    deposition_tm5_df = deposition_iso_df.groupby(iso_TM5_map).sum()

    TM5_index_sources = pd.Index(sorted(iso_TM5_map[iso_TM5_map != 'NOT_INCLUDED'].unique()))
    # additional receptor OCAARC for deposition in oceans and arctic
    TM5_index_receptors = TM5_index_sources.append(pd.Index(["OCAARC"]))

    TM5_df = deposition_tm5_df.reindex(TM5_index_sources)

    sr_matrices = dict()
    sr_matrices['NH3'] = pd.read_csv(sr_nh3_file, index_col=0, **CSV_IO_KWARGS).reindex(TM5_index_sources, columns=TM5_index_receptors)
    sr_matrices['NOx'] = pd.read_csv(sr_nox_file, index_col=0, **CSV_IO_KWARGS).reindex(TM5_index_sources, columns=TM5_index_receptors)

    # do some checks on the SR matrices
    for n_type, sr_df in sr_matrices.items():
        # check: rows of SR matrix should sum to one (i.e. all emitted nitrogen should deposit somewhere)
        if not np.isclose(sr_df.sum(axis=1), 1.0, atol=0.01).all():
            raise ValueError(f"Not all rows of source receptor matrix {n_type} sum to 1")

    TM5_df['Total_N_deposition'] = deposition_tm5_df['deposition_kg']

    # load msa loss data, on a country level
    iso_msa_loss_df = pd.read_csv(msa_loss_area_nd_plants_file, index_col=0, **CSV_IO_KWARGS)
    iso_msa_loss_df = self.splitCombinedIndex(iso_msa_loss_df)
    # sum over all the land use types
    iso_msa_loss_df = iso_msa_loss_df.groupby(level=0).sum()

    # convert from BIF regions to TM5 regions
    TM5_df['MSA_loss_plants'] = iso_msa_loss_df['area'].groupby(iso_TM5_map).sum()

    # calculate effect factor
    TM5_df['Effect_factor_plants'] = TM5_df['MSA_loss_plants'] / TM5_df['Total_N_deposition']
    TM5_df['Effect_factor_plants'] = TM5_df['Effect_factor_plants'].fillna(0.0)

    # calculate impact factor
    TM5_df['Impact_factor_NH3_plants'] = sr_matrices['NH3'].drop("OCAARC", axis='columns') @ TM5_df['Effect_factor_plants']
    TM5_df['Impact_factor_NOx_plants'] = sr_matrices['NOx'].drop("OCAARC", axis='columns') @ TM5_df['Effect_factor_plants']

    # go back to country-level. All countries are assigned the impact factor of the TM5 region they belong to
    iso_df = pd.DataFrame(index=iso_TM5_map.index, data={'NH3': iso_TM5_map.index, 'NOx': iso_TM5_map.index})

    def get_TM5_value(BIF_region : str, TM5_column : str):
        TM5_region = iso_TM5_map.loc[BIF_region]
        if TM5_region == "NOT_INCLUDED":
            return np.nan
        return TM5_df.loc[TM5_region, TM5_column]

    iso_df['NH3'] = iso_df['NH3'].apply(get_TM5_value, args=('Impact_factor_NH3_plants',))
    iso_df['NOx'] = iso_df['NOx'].apply(get_TM5_value, args=('Impact_factor_NOx_plants',))

    # to aggregate to output region level, first calculate losses and emissions, which can be summed, then divide again
    # if output regions are already country-level, skip this step
    if UT.isValueSet(iso_nitrogen_emissions_file):
      emission_iso_df = pd.read_csv(iso_nitrogen_emissions_file, index_col=0, **CSV_IO_KWARGS).filter(['NH3_emissions', 'NOx_emissions'])

      iso_df['NH3_caused_loss'] = iso_df['NH3'] * emission_iso_df['NH3_emissions']
      iso_df['NOx_caused_loss'] = iso_df['NOx'] * emission_iso_df['NOx_emissions']

      loss_df = self.sumISOtoRegion(iso_df.filter(['NH3_caused_loss', 'NOx_caused_loss']))
      emission_df = self.sumISOtoRegion(emission_iso_df)

      nitrogen_bif_df = pd.merge(loss_df, emission_df, how='left', left_index=True, right_index=True)
      nitrogen_bif_df['NH3'] = nitrogen_bif_df['NH3_caused_loss'] / nitrogen_bif_df['NH3_emissions']
      nitrogen_bif_df['NOx'] = nitrogen_bif_df['NOx_caused_loss'] / nitrogen_bif_df['NOx_emissions']
    else:
      nitrogen_bif_df = iso_df

    # convert to per molecular mass rather than per atomic nitrogen mass
    nitrogen_bif_df['NH3'] = nitrogen_bif_df['NH3'] * NICF_NH3
    nitrogen_bif_df['NOx'] = nitrogen_bif_df['NOx'] * NICF_NOx

    nitrogen_bif_df = nitrogen_bif_df.filter(['NH3', 'NOx'])
    nitrogen_bif_df.columns = pd.MultiIndex.from_tuples([(molecule, f"MSAloss*km^2/kg{molecule}") for molecule in nitrogen_bif_df.columns])
    nan_df = pd.DataFrame(index=nitrogen_bif_df.index, columns=nitrogen_bif_df.columns)
    nitrogen_bif_df = pd.concat([nitrogen_bif_df/2, nitrogen_bif_df, nan_df], keys=['overall', 'plants', 'wbvert'], axis=1).reorder_levels([1, 2, 0], axis=1).sort_index(axis=1)

    return nitrogen_bif_df

