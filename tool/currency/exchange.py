# -*- coding: utf-8 -*-

import requests
import urllib
import datetime
import json
from collections import OrderedDict
import exceptions

import bot, error, ext

class oxr(object):
    available_currency = []

    api_url = 'https://openexchangerates.org/api/'
    latest = 'latest.json'
    historical = 'historical/{}.json'
    available_currencies = 'currencies.json'
    usage = 'usage.json'

    def __init__(self, app_id):
        self._app_id = app_id
        self._app_available = True
        self.request_remaining = -1
        self.days_remaining = -1

        try:
            usage_dict = self.get_usage_dict()['data']['usage']
            self.request_remaining = usage_dict['requests_remaining']
            self.days_remaining = usage_dict['days_remaining']
        except KeyError:
            self._app_available = False

    def _send_request_get_dict(self, url, dict=None):
        if not self._app_available:
            raise ValueError('App not available cause by usage data getting error (in init)')

        if dict is None:
            dict = {}

        dict['app_id'] = self._app_id

        url_parameter = urllib.urlencode(dict)
        url = '{}?{}'.format(url, url_parameter)

        return_json = requests.get(url).json(object_pairs_hook=OrderedDict)

        if not (oxr.available_currencies in url or oxr.usage in url):
            self.request_remaining = self.request_remaining - 1

        if return_json is not None:
            if 'error' in return_json and return_json.get('error', True):
                raise exceptions.CurrencyExchangeException(return_json)
            else:
                return return_json
        else:
            raise ValueError('URL request returns empty content. URL: {}'.format(url))

    def get_latest_dict(self, symbols=None):
        """
        Symbols can be list or tuple or string. If symbols is not accpetable iterable, it should be string and separated by SINGLE SPACE.
        """
        url = oxr.api_url + oxr.latest

        param_dict = {'symbols': oxr.symbols_to_string(symbols), 'prettyprint': False}

        json_data = self._send_request_get_dict(url, param_dict)

        return json_data

    @staticmethod
    def latest_str(latest_dict):
        date = latest_dict.get('timestamp', None)
        if date is None:
            date_text = u'N/A'
        else:
            date_text = datetime.datetime.fromtimestamp(float(date)).strftime('%Y-%m-%d %H:%M:%S')

        return_str = u'更新時間: {} (UTC)'.format(date_text)
        
        return_str += u'\n基底貨幣: USD(美元)\n'

        rates_json = latest_dict['rates']
        return_str += u'\n'.join([u'{}: {}'.format(sym, rate) for sym, rate in rates_json.iteritems()])

        return return_str

    def get_historical_dict(self, date_8dg, symbols=None):
        """
        Symbols can be list or tuple or string. If symbols is not accpetable iterable, it should be string and separated by SINGLE SPACE.
        """
        param_dict = {'symbols': oxr.symbols_to_string(symbols), 'prettyprint': False}
        try:
            date = datetime.date(int(date_8dg[0:4]), int(date_8dg[4:6]), int(date_8dg[6:8])).strftime('%Y-%m-%d')
        except ValueError as e:
            json_data = {'error': True, 
                         'status': 500,
                         'message': 'Error occurred while parsing date.',
                         'description': e.message}
        else:
            url = oxr.api_url + oxr.historical.format(date)
            try:
                json_data = self._send_request_get_dict(url, param_dict)
            except exceptions.CurrencyExchangeException as ex:
                json_data = {'error': True, 
                             'status': ex._status_code,
                             'message': ex._message,
                             'description': ex._description}

        return json_data

    @staticmethod
    def historical_str(historical_dict):
        if 'error' in historical_dict and historical_dict.get('error', True):
            return_str = u'發生錯誤。狀態碼: {}\n訊息: {}\n說明: {}'.format(
                historical_dict.get('status', 500),
                historical_dict.get('message', u'Application Error'),
                historical_dict.get('description', u'N/A'))
        else:
            date = historical_dict.get('timestamp', None)
            if date is None:
                date_text = u'N/A'
            else:
                date_text = datetime.datetime.fromtimestamp(float(date)).strftime('%Y-%m-%d %H:%M:%S')

            return_str = u'歷史匯率 ({} UTC)'.format(date_text)
            
            return_str += u'\n基底貨幣: USD(美元)\n'

            rates_json = historical_dict['rates']
            return_str += u'\n'.join([u'{}: {}'.format(sym, rate) for sym, rate in rates_json.iteritems()])

        return return_str

    def get_available_currencies_dict(self):
        url = oxr.api_url + oxr.available_currencies
        param_dict = {'prettyprint': False}

        json_data = self._send_request_get_dict(url, param_dict)

        return json_data

    @staticmethod
    def available_currencies_str(available_currencies_dict):
        return_str = u'可用貨幣:\n'

        return_str += u'\n'.join([u'{} - {}'.format(sym, name) for sym, name in available_currencies_dict.iteritems()])

        return return_str

    def get_usage_dict(self):
        url = oxr.api_url + oxr.usage
        param_dict = {'prettyprint': False}

        json_data = self._send_request_get_dict(url, param_dict)

        return json_data

    @staticmethod
    def usage_str(usage_dict):
        usage_dict = usage_dict['data']
        return_str = u'狀態: {}'.format(usage_dict.get('status', u'(Error)'))
        
        usage_plan_json = usage_dict['plan']
        return_str += u'\n方案: {} ({})'.format(usage_plan_json.get('name'), usage_plan_json.get('quota'))
        return_str += u'\n每{}更新一次資訊'.format(usage_plan_json.get('update_frequency'))
        
        usage_stats_json = usage_dict['usage']
        return_str += u'\n本月已使用{}次'.format(usage_stats_json.get('requests', 'Error'))
        return_str += u'\n本月剩餘{}次'.format(usage_stats_json.get('requests_remaining', 'Error'))
        return_str += u'\n此方案可使用{}次'.format(usage_stats_json.get('requests_quota', 'Error'))
        return_str += u'\n還有{}日重設使用次數'.format(usage_stats_json.get('days_remaining', 'Error'))

        return return_str

    def convert(self, source, target, amount=1, json_dict=None):
        symbol_not_exist = lambda symbol: u'找不到貨幣單位{}的相關資料'.format(symbol)
        available_dict = self.get_available_currencies_dict()
        if amount < 0:
            return ConvertResult(-1, -1, error.error.main.miscellaneous(u'貨幣轉換基底量需大於0。({})'.format(amount)))

        if json_dict is None:
            if target not in available_dict:
                return ConvertResult(-1, -1, error.error.main.miscellaneous(symbol_not_exist(target)))
            elif source not in available_dict:
                return ConvertResult(-1, -1, error.error.main.miscellaneous(symbol_not_exist(source)))

            data_json_dict = self.get_latest_dict(','.join([source, target]))
            timestamp = data_json_dict.get('timestamp', None)
            data_dict = data_json_dict['rates']
        else:
            rates_json = json_dict['rates']
            currency = [source, target]
            timestamp = json_dict.get('timestamp', None)
            data_dict = {key_to_save: rates_json[key_to_save] for key_to_save in currency}

        if timestamp is None:
            timestamp = u'N/A'
        else:
            timestamp = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

        try:
            target_rate = data_dict[target]
            source_rate = data_dict[source]
        except KeyError as e:
            return ConvertResult(-1, -1, symbol_not_exist(e.message))

        exchange_rate = target_rate / float(source_rate)
        exchange_amt = exchange_rate * float(amount)

        target_full = available_dict.get(target, u'(無資料)')
        source_full = available_dict.get(source, u'(無資料)')

        return ConvertResult(exchange_rate, exchange_amt, u'{} {} ({}) →\n{} {} ({})\n\n根據{} (UTC)時的匯率計算。'.format(amount, source, source_full, exchange_amt, target, target_full, timestamp))

    @staticmethod
    def symbols_to_string(symbols):
        """
        Symbols can be list or tuple or string. If symbols is not accpetable iterable, it should be string and separated by SINGLE SPACE.
        """
        if symbols is None:
            symbols = ''
        elif not isinstance(symbols, (list, tuple)):
            symbols = symbols.split(' ')

        return ','.join(symbols)

class ConvertResult(object):
    def __init__(self, rate, result, formatted_string):
        self._result = result
        self._formatted_string = formatted_string
        self._rate = rate

    @property
    def result(self):
        return self._result
    
    @property
    def formatted_string(self):
        return self._formatted_string
    
    @property
    def rate(self):
        return self._rate