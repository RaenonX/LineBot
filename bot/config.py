# -*- coding: utf-8 -*-

from ConfigParser import SafeConfigParser
import ext

class config_category(ext.EnumWithName):
    KEYWORD_DICT = 0, 'KeywordDictionary'
    TIMEOUT = 1, 'Timeout'
    STICKER_RANKING = 2, 'StickerRanking'
    SYSTEM = 3, 'System'
    ERROR_REPORT = 4, 'ErrorReport'
    WEATHER_REPORT = 5, 'WeatherReport'

class config_category_kw_dict(ext.EnumWithName):
    CREATE_DUPLICATE = 0, 'PossibleDuplicateCDSeconds'
    REPEAT_CALL = 1, 'RepeatCallCDSeconds'
    MAX_QUERY_OUTPUT_COUNT = 3, 'MaxQueryOutputCount'
    MAX_SIMPLE_STRING_LENGTH = 4, 'MaxSimpleStringLength'
    MAX_INFO_OUTPUT_COUNT = 5, 'MaxInfoOutputCount'
    MAX_MESSAGE_TRACK_OUTPUT_COUNT = 6, 'MaxMessageTrackOutputCount'
    DEFAULT_RANK_RESULT_COUNT = 7, 'DefaultRankResultCount'

class config_category_timeout(ext.EnumWithName):
    CALCULATOR = 0, 'Calculator'

class config_category_sticker_ranking(ext.EnumWithName):
    LIMIT_COUNT = 0, 'LimitCount'
    HOUR_RANGE = 1, 'HourRange'

class config_category_system(ext.EnumWithName):
    DUPLICATE_CONTENT_BAN_COUNT = 0, 'DuplicateContentBanCount'
    UNLOCK_PASSWORD_LENGTH = 1, 'UnlockPasswordLength'
    MAX_ERROR_LIST_OUTPUT = 2, 'MaxErrorListOutput'

class config_category_error_report(ext.EnumWithName):
    DEFAULT_SUBJECT_PREFIX = 0, 'DefaultSubjectPrefix'

class config_category_weather_report(ext.EnumWithName):
    DEFAULT_INTERVAL_HR = 0, 'DefaultIntervalHR'
    DEFAULT_DATA_RANGE_HR = 1, 'DefaultDataRangeHR'
    MAX_BATCH_SEARCH_COUNT = 2, 'MaxBatchSearchCount'

class config_manager(object):
    def __init__(self, file_path):
        self._parser = SafeConfigParser()
        self._parser.read(file_path)

    def get(self, cat_enum, key_enum):
        config = self._parser.get(str(cat_enum), str(key_enum))
        if config.startswith('"') and config.endswith('"'):
            config = config[1:-1]

        return config

    def getint(self, cat_enum, key_enum):
        return self._parser.getint(str(cat_enum), str(key_enum))


