# -*- coding: utf-8 -*-
from datetime import datetime

import os
import gzip

import ext

class ppp_manager(object):
    ###################################################################################################
    # Data downloaded from: http://www.imf.org/external/datamapper/PPPEX@WEO/OEMDC/ADVEC/WEOWORLD/AFG #
    ###################################################################################################
    
    FIELD_DELIM = ","
    START_YEAR = 1980
    END_YEAR = 2022
    CURRENT_YEAR = datetime.today().year
    
    FILE_NAME = "ppp{}{}-{}.txt.gz".format(START_YEAR, END_YEAR, CURRENT_YEAR % 100)

    def __init__(self):
        self._res_path = os.path.join(os.path.dirname(__file__), ppp_manager.FILE_NAME)
        self._res = None

    def _get_lines(self, country_names, single_result):
        ret = []

        with gzip.open(self._res_path, "r") as f:
            for line in f:
                line_arr = line.strip().rsplit(ppp_manager.FIELD_DELIM, ppp_manager.END_YEAR - ppp_manager.START_YEAR + 1)
                if self._match_conditions(line_arr, country_names):
                    ret.append(line_arr)

                    if single_result:
                        break
        
        return ret
    
    def _match_conditions(self, line_arr, country_names, least_condition_match=1):
        condition_match = 0
        if country_names is not None and line_arr[0] in country_names:
            condition_match += 1

        if condition_match >= least_condition_match:
            return True

    def get_data(self, country_names=None, single_result=False):
        """
        Parameters:
            country_names: country name to query(full match only). This can be list to do the batch task.

        Returns:
            List of data_entry. Return empty list if no result.
        """
        country_names = ext.to_list(country_names)

        ret = self._get_lines(country_names, single_result)

        return [data_entry(line_arr, ppp_manager.START_YEAR) for line_arr in ret]

class data_entry(object):
    NA = -1

    def __init__(self, line, start_year):
        self._country_name = line[0]
        self._data_array = [float(d) for d in line[1:]]
        self._start_year = start_year

    @property
    def country_name(self):
        return self._country_name

    def get_data(self, year=None, close=False):
        if year is None:
            year = ppp_manager.CURRENT_YEAR

        while year >= self._start_year:
            data = self._data_array[year - self._start_year]

            if data != data_entry.NA or close:
                return data

            year -= 1
        return data_entry.NA

