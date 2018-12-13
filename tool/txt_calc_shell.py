# -*- coding: utf-8 -*-

from __future__ import division

import time

from sympy import *
from sympy.core.sympify import SympifyError
from sympy.abc import x, y, z

from error import error

class calc_shell(object):
    @staticmethod
    def calc(init_time, text, debug):
        result_data = calc_result_data(text)

        start_time = init_time
        result = u''

        try:
            if u'result=' not in text or u'result = ' not in text:
                exec(u'result={}'.format(text))
            else:
                exec(text)

            result = simplify(result)
        except OverflowError:
            result_data.success = False # Indicate the calculation is failed
            result_data.calc_result = error.string_calculator.overflow()
            result_data.auto_record_time(start_time) # Record the time at calculation ended, no conversion
        except SympifyError:
            result_data.success = False # Indicate the calculation is failed
            result_data.calc_result = error.string_calculator.result_is_not_numeric(text)
            result_data.auto_record_time(start_time) # Record the time at calculation ended, no conversion
        except Exception as ex:
            result_data.success = False # Indicate the calculation is failed
            result_data.calc_result = ex.message
            result_data.auto_record_time(start_time) # Record the time at calculation ended, no conversion
        else:
            n_t = result_data.auto_record_time(start_time) # Record the time at the moment that exec() is completed
            calc_result_str = str(result) # Result type conversion

            result_data.success = result_data.formula_str != calc_result_str # Check if the formula is calculated, indicating the calculation occurred or not
            result_data.calc_result = calc_result_str # Store the calculation result in str

            latex_result_str = latex(result)

            result_data.latex_avaliable = latex_result_str != calc_result_str # Set flag latex available to true if latex script available
            result_data.latex = latex_result_str # Store latex result
            result_data.auto_record_time(n_t) # Record the time at the moment that type conversion is completed
        if debug:
            print result_data.get_debug_text().encode('utf-8')

        return result_data

class calc_result_data(object):
    def __init__(self, formula_str, latex_avaliable=False):
        self._formula_str = formula_str
        self._latex = None
        self._calc_time = -1.0
        self._type_cast_time = -1.0
        self._calc_result = None
        self._timeout = False
        self._success = False
        self._latex_avaliable = latex_avaliable
        self._token = None # Prevent Data reply in the wrong chatting instance

    @property
    def formula_str(self):
        return self._formula_str

    @formula_str.setter
    def formula_str(self, value):
        if isinstance(value, (str, unicode)):
            self._formula_str = value
        else:
            raise Exception('Calculate result should be string or unicode.')
    
    @property
    def calc_result(self):
        return self._calc_result

    @calc_result.setter
    def calc_result(self, value):
        if isinstance(value, (str, unicode)):
            self._calc_result = value
        else:
            raise Exception('Calculate result should be string or unicode.')
    
    @property
    def latex(self):
        return self._latex

    @latex.setter
    def latex(self, value):
        if isinstance(value, str):
            self._latex = value
        else:
            raise Exception('LaTeX should be string.')

    @property
    def calc_time(self):
        return self._calc_time

    @calc_time.setter
    def calc_time(self, value):
        self._calc_time = value
    
    @property
    def type_cast_time(self):
        return self._type_cast_time

    @type_cast_time.setter
    def type_cast_time(self, value):
        self._type_cast_time = value
    
    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, value):
        self._timeout = value
        
    @property
    def success(self):
        return self._success

    @success.setter
    def success(self, value):
        self._success = value

    @property
    def latex_avaliable(self):
        return self._latex_avaliable and self._latex is not None

    @latex_avaliable.setter
    def latex_avaliable(self, value):
        self._latex_avaliable = value

    @property
    def token(self):
        return self._token

    @token.setter
    def token(self, value):
        self._token = value

    def auto_record_time(self, start_time):
        """
        First time record: calculation_time, at calculation completed
        Second time record: type_cast_time, at type conversion completed

        Return new time point at the point after the time had been record.
        """
        n_tp = time.time()

        if self._calc_time == -1.0:
            self._calc_time = n_tp - start_time
        elif self._type_cast_time == -1.0:
            if self._calc_time == -1.0:
                self._calc_time = n_tp - start_time
            else:
                self._type_cast_time = n_tp - start_time
                
        return n_tp

    # POSSIBLE DEPRECATE - Calc type
    def get_basic_text(self):
        return u'算式:\n{}\n結果:\n{}\n計算 {} | 顯示 {}'.format(
            self._formula_str,
            self._calc_result,
            u'(未執行)' if self._calc_time == -1.0 else u'{:.3f}秒'.format(self._calc_time),
            u'(未執行)' if self._type_cast_time == -1.0 else u'{:.3f}秒'.format(self._type_cast_time))

    def get_debug_text(self):
        return u'計算{}\n\n{}'.format(
            u'成功' if self._success else u'失敗', 
            self.get_basic_text())