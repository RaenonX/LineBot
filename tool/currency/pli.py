# -*- coding: utf-8 -*-

import os
import gzip

import ext

class pypli(object):
    """
    This class uses the data of ICP 2011(International Comparison Program) to get the PLI(Price Level Index) of specified country.
    
    Data can be queried by country code(alpha-3) or country name.
    """
    FIELD_DELIM = ","
    DATA_COLUMN_INDEX_MAX = 23
    SOURCE = 'World Bank ICP 2011'

    def __init__(self):
        self._res_path = os.path.join(os.path.dirname(__file__), 'pli.txt.gz')
        self._res = None

    def _match_conditions(self, line, country_names, country_codes, least_condition_match=1):
        condition_match = 0
        if country_names is not None and line[int(pli_category.CountryName)] in country_names:
            condition_match += 1
        if country_codes is not None and line[int(pli_category.CountryCode)] in country_codes:
            condition_match += 1

        if condition_match >= least_condition_match:
            return True

    def _get_lines(self, country_names, country_codes, single_result):
        ret = []

        with gzip.open(self._res_path, "r") as f:
            for line in f:
                line = line.strip().rsplit(pypli.FIELD_DELIM, pypli.DATA_COLUMN_INDEX_MAX)
                if self._match_conditions(line, country_names, country_codes):
                    ret.append(line)

                    if single_result:
                        break
        
        return ret

    def get_pli(self, country_names=None, country_codes=None, single_result=False):
        """
        Parameters:
            country_names: country name to query(full match only). This can be list to do the batch task.
            country_codes: country code (ISO 3166) to query(full match only). This can be list to do the batch task.

        Returns:
            List of pli_result. Return empty list if no result.
        """
        country_names = ext.to_list(country_names)
        country_codes = ext.to_list(country_codes)

        ret = self._get_lines(country_names, country_codes, single_result)

        return [pli_result(line) for line in ret]

class pli_category(ext.EnumWithName):
    CountryName = 0, '國家名稱'
    CountryCode = 1, '國家代碼'
    GrossDomesticProduct = 2, '商品(含稅)'
    IndividualConsumption = 3, '個人消費'
    FoodAndNonAlcoholicBeverages = 4, '食物/非酒精飲料'
    AlcoholicBeveragesAndTobacco = 5, '菸酒/藥物'
    ClothingAndFootwear = 6, '衣裝鞋'
    HousingAndEnergy = 7, '住居/能源'
    FurnishingsAndHousehold = 8, '裝飾/持家'
    Health = 9, '醫療'
    Transport = 10, '交通'
    Communication = 11, '通信'
    RecreationAndCulture = 12, '休閒/文化'
    Education = 13, '教育'
    RestaurantsAndHotels = 14, '餐廳/旅館'
    MiscGoodsAndService = 15, '雜項/服務'
    IndividualExpenditureHousehold = 16, '個人支出(家庭)'
    IndividualExpenditureHouseholdNoHousing = 23, '個人支出(家庭，不含住居)'
    IndividualExpenditureGov = 17, '個人支出(政府)'
    CollectiveExpenditureGov = 18, '整體支出(政府)'
    GrossFixedCapitalFormation = 19, 'GFCF'
    MachineryAndEquipment = 20, '機械裝置'
    Construction = 21, '建築/施工'
    DomesticAbsorption = 22, '收支逆差'

class pli_result(object):
    UNKNOWN_VAL = -1

    def __init__(self, data_line):
        self._data = { cat: data_line[int(cat)] for cat in pli_category }

    def get_data(self, category):
        data = self._data.get(category, pli_result.UNKNOWN_VAL)
        if not category in (pli_category.CountryCode, pli_category.CountryName):
            data = float(data)

        return data

    def display_data(self, categories, separator=u'\n'):
        """
        Parameters:
            categories: categories to display. This can be list to display multiple categories.
            separator: separator to separate different data. In unicode would be better.

        Returns:
            String in unicode.
        """
        categories = ext.to_list(categories)

        return u'{}\n{}'.format(
            u'{} ({})'.format(self.get_data(pli_category.CountryName), self.get_data(pli_category.CountryCode)), 
            separator.join([u'{}: {:.2f}'.format(unicode(category), self.get_data(category)) for category in categories]))

    def __repr__(self):
        return '{} - Product: {} | AIC: {}'.format(self.get_data(pli_category.CountryName), self.get_data(pli_category.GrossDomesticProduct), self.get_data(pli_category.IndividualConsumption))
