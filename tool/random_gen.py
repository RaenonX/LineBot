# coding: utf-8

import random
import string
import scipy.special
from scipy.stats import norm
from math import sqrt

from collections import Counter

class random_drawer(object):
    @staticmethod
    def draw_number(start, end):
        start = int(start)
        end = int(end)
        return random.randint(start, end)

    @staticmethod
    def draw_number_string(start, end, count=1):
        results = [random_drawer.draw_number(start, end) for i in range(count)]

        return u'抽選範圍【{}~{}】\n統計次數:\n{}\n抽選結果【{}】'.format(start, end, 
            u'\n'.join([u'{}: {}次'.format(item, count) for item, count in Counter(results).iteritems()]),
            u'、'.join([unicode(i) for i in results]))
        
    @staticmethod
    def draw_from_list(item_list):
        random.shuffle(item_list)
        return random.choice(item_list)

    @staticmethod
    def draw_text_string(text_list, count=1):
        results = [random_drawer.draw_from_list(text_list) for i in range(count)]

        return u'抽選項目【{}】\n統計次數:\n{}\n抽選結果:\n{}'.format(
            u'、'.join(text_list), 
            u'\n'.join([u'{}: {}次'.format(item, count) for item, count in Counter(results).iteritems()]),
            u'\n'.join([u'{}. {}'.format(i, result) for i, result in enumerate(results, start=1)]))

    @staticmethod
    def draw_probability(probability, is_value=True):
        if is_value:
            probability /= 100.0
        return random.random() <= probability

    @staticmethod
    def draw_probability_string(probability, is_value=True, count=1, prediction_count=2):
        probability = float(probability)
        if is_value:
            probability /= 100.0

        count = int(count)
        result_list = {i: random_drawer.draw_probability(probability, False) for i in range(1, count + 1)}
        shot_count = sum(x for x in result_list.values())
        miss_count = count - shot_count
        
        variance = count * probability * (1 - probability)
        sd = sqrt(variance)
        cdf = norm.cdf((shot_count - probability*count) / sd)

        text = u'機率抽選【{:.2%}、{}次】，期望值【中{:.0f}次】'.format(probability, count, round(probability * count))
        text += u'\n方差【{}】'.format(variance)
        text += u'\n抽選結果【中{}次 | 失{}次】'.format(shot_count, miss_count)
        text += u'\n中選位置【{}】'.format(u'、'.join([str(key) for key, value in result_list.iteritems() if value]))
        text += u'\n實際中率【{:.2%}】'.format(shot_count / float(len(result_list)))

        prediction_probability = 1
        for i in range(0, shot_count if shot_count >= prediction_count else prediction_count):
            prediction_probability -= scipy.special.comb(count, i) * probability**i * (1 - probability)**(count - i)
            if i < prediction_count and prediction_probability >= 0.0001:
                text += u'\n中{}+機率【{:.2%}】'.format(i + 1, prediction_probability)
            elif i == shot_count - 1:
                text += u'\n中{}+機率【{:.2%}】'.format(i + 1, prediction_probability)

        return text

    @staticmethod
    def generate_random_string(length):
        return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(length))