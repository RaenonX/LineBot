# -*- coding: utf-8 -*-
from __future__ import division

import sys
from multiprocessing import Process, Queue as MultiQueue
import Queue

import re
import time

from error import error

from .txt_calc_shell import calc_result_data, calc_shell

class text_calculator(object):
    def __init__(self, timeout=15):
        self._queue = MultiQueue()
        self._timeout = timeout

    def calculate(self, text, debug=False, token=None):
        """
        Set calc_type to None to use auto detect.

        Auto detect format:
        Polynomial Factorization: no new line, no EQUATION_KEYWORD
        Algebraic equation: contains new line, contains EQUATION_KEYWORD, 1st line means variables(use comma to separate), 2nd line or more is equation 
        """
        result_data = calc_result_data(text)
        init_time = time.time()

        if text_calculator.is_non_calc(text):
            result_data.auto_record_time(init_time)
            return result_data

        try:
            calc_proc = Process(target=self._basic_calc_proc, args=(init_time, text, debug, self._queue))
            calc_proc.start()

            result_data = self._queue.get(True, self._timeout)
        except Queue.Empty:
            result_data.auto_record_time(init_time)
            calc_proc.terminate()

            result_data.success = False
            result_data.timeout = True
            result_data.calc_result = error.string_calculator.calculation_timeout(self._timeout)

        result_data.token = token
        
        if debug:
            print result_data.get_debug_text().encode('utf-8')

        return result_data

    def _basic_calc_proc(self, init_time, text, debug, queue):
        queue.put(calc_shell.calc(init_time, text, debug))

    @staticmethod
    def is_non_calc(text):
        try:
            text.decode('ascii')
            return (text.startswith('0') and '.' not in text) or text.startswith('+') or text.endswith('.')
        except UnicodeDecodeError:
            return True
        except UnicodeEncodeError:
            return True
        else:
            return False