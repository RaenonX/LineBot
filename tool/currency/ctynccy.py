# -*- coding: utf-8 -*-

import os
import json
import gzip

import ext

class countries_and_currencies(object):
    FIELD_DELIM = ","
    DATA_COLUMN_INDEX_MAX = 3
    
    def __init__(self):
        self._res_path = os.path.join(os.path.dirname(__file__), 'ctynccy.txt.gz')
        self._res = None

    def _match_conditions(self, line, country_names, country_codes, currency_names, currency_codes, least_condition_match=1):
        condition_match = 0
        if country_names is not None and line[int(country_entry_column.CountryName)] in country_names:
            condition_match += 1
        if country_codes is not None and line[int(country_entry_column.CountryCode)] in country_codes:
            condition_match += 1
        if currency_names is not None and line[int(country_entry_column.CurrencyName)] in currency_names:
            condition_match += 1
        if currency_codes is not None and line[int(country_entry_column.CurrencyCode)] in currency_codes:
            condition_match += 1

        if condition_match >= least_condition_match:
            return True

    def _get_lines(self, country_names, country_codes, currency_names, currency_codes, single_result):
        ret = []

        with gzip.open(self._res_path, "r") as f:
            for line in f:
                line = line.strip().rsplit(countries_and_currencies.FIELD_DELIM, countries_and_currencies.DATA_COLUMN_INDEX_MAX)
                if self._match_conditions(line, country_names, country_codes, currency_names, currency_codes):
                    ret.append(line)

                    if single_result:
                        break
        
        return ret

    def get_country_entry(self, country_names=None, country_codes=None, currency_names=None, currency_codes=None, single_result=False):
        """
        Parameters:
            country_names: country name to query(full match only). This can be list to do the batch task.
            country_codes: country code (ISO 3166) to query(full match only). This can be list to do the batch task.
            currency_names: currency name to query(full match only). This can be list to do the batch task.
            currency_codes: currency code (ISO 4217) to query(full match only). This can be list to do the batch task.

        Returns:
            List of country_entry. Return empty list if no result.
        """
        country_names = ext.to_list(country_names)
        country_codes = ext.to_list(country_codes)
        currency_names = ext.to_list(currency_names)
        currency_codes = ext.to_list(currency_codes)

        ret = self._get_lines(country_names, country_codes, currency_names, currency_codes, single_result)

        return [country_entry(line) for line in ret]

class country_entry_column(ext.EnumWithName):
    CountryName = 0, '國家名稱'
    CountryCode = 1, '國家代碼'
    CurrencyName = 2, '貨幣名稱'
    CurrencyCode = 3, '貨幣代碼'

class country_entry(object):
    UNKNOWN_VAL = '(Unknown)'

    def __init__(self, data_line):
        self._data = { cat: data_line[int(cat)] for cat in country_entry_column }

    def get_data(self, category):
        data = self._data.get(category, country_entry.UNKNOWN_VAL)

        return data

    def __repr__(self):
        return 'Country Entry of {} - {}'.format(self.get_data(country_entry_column.CountryCode), self.get_data(country_entry_column.CountryName))
