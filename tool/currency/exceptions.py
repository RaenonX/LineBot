# -*- coding: utf-8 -*-

class CurrencyExchangeException(Exception):
    def __init__(self, err_json):
        self._status_code = err_json.get('status', 500) 
        self._message = err_json.get('message', 'Application Error') 
        self._description = err_json.get('description') 
    
    def __str__(self):
        return 'Status Code: {} - {}\nDescription: {}'.format(self._status_code, self._message, self._description)