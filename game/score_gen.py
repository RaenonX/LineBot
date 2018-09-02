# -*- coding: utf-8 -*-

import sympy

import random

class sc_gen(object):
    ### Integral Shape Reference: https://www.integral-calculator.com/#expr=1%2F%28%2810%2F3%29%2A0.5%2B1%2F1500%29%2A%28%28%280.5-0.0001%29%2F100%2Ax%5E2%29%20-%20%28%280.5-0.0001%29%2F5%2Ax%29%20%2B%200.5%29&simplify=1

    ### FOR RECORDING THE SHAPE ONLY ###
    _x = 0
    _y = 0.5
    _A = 1 / ((10 / 3) * _y) + 1 / 1500
    _B = ((_y - 0.0001) / 100 * _x ** 2)
    _C = ((_y - 0.0001) / 5 * _x)
    _SHAPE = _A * (_B - _C + _y)
    ####################################
    
    @staticmethod
    def generate_score(count=None):
        if count is None:
            return sc_gen_data()
        else:
            return [sc_gen_data() for i in range(count)]

class sc_gen_data(object):
    def __init__(self):
        self._score = -1
        self._rand_x = -1
        self.generate()

    def generate(self):
        self._rand_x = random.random()
        
        try:
            x = sympy.Symbol('x')
            x_pos = sympy.solveset((x * (4999 * x ** 2 - 149970 * x + 1500000)) / 5002000 - self._rand_x, x, domain=sympy.S.Reals)
            if not x_pos.is_EmptySet:
                self._score = float(next(iter(x_pos)))
        except Exception as e:
            self.generate()

    def get_opportunity_greater(self):
        return 1 - self._rand_x

    def get_score(self):
        return self._score

    @staticmethod
    def calculate_opportunity_greater(score, n=25):
        score = float(str(score))
        return sympy.N(1 - (score * (4999 * score ** 2 - 149970 * score + 1500000)) / 5002000, n=n)

if __name__ == "__main__":
    import time
    _start = time.time()

    _rand_x = 0.99999999999999999999999999999999999999

    x = sympy.Symbol('x')
    x_pos = sympy.solveset((x * (4999 * x ** 2 - 149970 * x + 1500000)) / 5002000 - _rand_x, x, domain=sympy.S.Reals)
    if not x_pos.is_EmptySet:
        print(float(next(iter(x_pos))))

    print(time.time() - _start)