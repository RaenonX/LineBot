# coding: utf-8

import numpy as np

class mff_dmg_calc(object):

  @staticmethod
  def code_dict():
    return {
      'SKP': dmg_bonus([u'SKP', u'SK', u'技能威力', u'威力', u'技能'], u'技能威力 (アビリティパーワー)'),
      'ABL': dmg_bonus([u'ABL', u'AB', u'屬強', u'屬性', u'屬性強化'], u'屬性強化 (属性強化)'),
      'SKC': dmg_bonus([u'SKC', u'SC', u'連發', u'連擊', u'技能連擊'], u'技能連擊傷害加成 (アビリティチェーン)'),
      'ELC': dmg_bonus([u'ELC', u'EC', u'同屬連發', u'同屬連擊'], u'同屬技能連擊傷害加成 (同属性チェーン)'),
      'CRT': dmg_bonus([u'CRT', u'CT', u'爆擊', u'爆擊加成'], u'爆擊傷害加成 (クリティカルダメージアップ)', 1.5),
      'WKP': dmg_bonus([u'WKP', u'WK', u'弱點', u'弱點加成'], u'弱點屬性傷害加成 (弱点ダメージアップ)', 2.0, 1.3),
      'BRK': dmg_bonus([u'BRK', u'BK', u'破防', u'破防加成'], u'破防傷害加成 (ブレイクダメージアップ)', 2.0),
      'MGC': dmg_bonus([u'MGC', u'MG', u'魔力'], u'魔力', 1.0)
    }
  
  @staticmethod
  def _dmg_obj():
    return {'first': 0, 'continual': 0, 'list': list(), 'list_of_sum': list()}
  
  @staticmethod
  def _generate_dmg_list(dict):
    dict['list'] = [dict['first']]
    for i in range(4):
      dict['list'].append(dict['continual'])
    
    dict['list_of_sum'] = np.cumsum(dict['list']).tolist()
    return dict
  
  @staticmethod
  def dmg(job):
    """first, continual, list of sum"""
    ret = mff_dmg_calc._dmg_obj()
    
    ret['first'] = job.data['SKP'].value * (1.0 + job.data['ABL'].value) * job.data['MGC'].value / 2.0
    
    ret['continual'] = job.data['SKP'].value * (1.0 + job.data['ABL'].value + job.data['SKC'].value + job.data['ELC'].value) * job.data['MGC'].value / 2.0
    
    ret = mff_dmg_calc._generate_dmg_list(ret)
    return ret
  
  @staticmethod
  def dmg_crt(job):
    """first, continual, list of sum"""
    ret = mff_dmg_calc._dmg_obj()
    
    ret['first'] = job.data['SKP'].value * (1.0 + job.data['ABL'].value) * job.data['CRT'].value * job.data['MGC'].value / 2.0
    
    ret['continual'] = job.data['SKP'].value * (1.0 + job.data['ABL'].value + job.data['SKC'].value + job.data['ELC'].value) * job.data['CRT'].value * job.data['MGC'].value / 2.0
    
    ret = mff_dmg_calc._generate_dmg_list(ret)
    return ret
  
  @staticmethod
  def dmg_break(job):
    """first, continual, list of sum"""
    ret = mff_dmg_calc._dmg_obj()
    
    ret['first'] = job.data['SKP'].value * (1.0 + job.data['ABL'].value) * job.data['WKP'].value * job.data['BRK'].value * job.data['MGC'].value 
    
    ret['continual'] = job.data['SKP'].value * (1.0 + job.data['ABL'].value + job.data['SKC'].value + job.data['ELC'].value) * job.data['BRK'].value * job.data['MGC'].value 
    
    ret = mff_dmg_calc._generate_dmg_list(ret)
    return ret
  
  @staticmethod
  def dmg_break_crt(job):
    """first, continual, list of sum"""
    ret = mff_dmg_calc._dmg_obj()
    
    ret['first'] = job.data['SKP'].value * (1.0 + job.data['ABL'].value) * job.data['WKP'].value * job.data['BRK'].value * job.data['CRT'].value * job.data['MGC'].value
    
    ret['continual'] = job.data['SKP'].value * (1.0 + job.data['ABL'].value + job.data['SKC'].value + job.data['ELC'].value) * job.data['BRK'].value * job.data['CRT'].value * job.data['MGC'].value
    
    ret = mff_dmg_calc._generate_dmg_list(ret)
    return ret
    
  @staticmethod
  def dmg_weak(job):
    """first, continual, list of sum"""
    ret = mff_dmg_calc._dmg_obj()
    
    ret['first'] = job.data['SKP'].value * (1.0 + job.data['ABL'].value) * job.data['WKP'].val(False) * job.data['MGC'].value / 2.0
    
    ret['continual'] = job.data['SKP'].value * (1.0 + job.data['ABL'].value + job.data['SKC'].value + job.data['ELC'].value) * job.data['WKP'].val(False) * job.data['MGC'].value / 2.0
    
    ret = mff_dmg_calc._generate_dmg_list(ret)
    return ret
  
  @staticmethod
  def dmg_crt_weak(job):
    """first, continual, list of sum"""
    ret = mff_dmg_calc._dmg_obj()
    
    ret['first'] = job.data['SKP'].value * (1.0 + job.data['ABL'].value) * job.data['WKP'].val(False) * job.data['CRT'].value * job.data['MGC'].value / 2.0
    
    ret['continual'] = job.data['SKP'].value * (1.0 + job.data['ABL'].value + job.data['SKC'].value + job.data['ELC'].value) * job.data['CRT'].value * job.data['WKP'].val(False) * job.data['MGC'].value / 2.0
    
    ret = mff_dmg_calc._generate_dmg_list(ret)
    return ret
  
  @staticmethod
  def dmg_break_weak(job):
    """first, continual, list of sum"""
    ret = mff_dmg_calc._dmg_obj()
    
    ret['first'] = job.data['SKP'].value * (1.0 + job.data['ABL'].value) * job.data['WKP'].value * job.data['BRK'].value * job.data['MGC'].value 
    
    ret['continual'] = job.data['SKP'].value * (1.0 + job.data['ABL'].value + job.data['SKC'].value + job.data['ELC'].value) * job.data['BRK'].value * job.data['WKP'].value * job.data['MGC'].value 
    
    ret = mff_dmg_calc._generate_dmg_list(ret)
    return ret
  
  @staticmethod
  def dmg_break_crt_weak(job):
    """first, continual, list of sum"""
    ret = mff_dmg_calc._dmg_obj()
    
    ret['first'] = job.data['SKP'].value * (1.0 + job.data['ABL'].value) * job.data['WKP'].value * job.data['BRK'].value * job.data['CRT'].value * job.data['MGC'].value
    
    ret['continual'] = job.data['SKP'].value * (1.0 + job.data['ABL'].value + job.data['SKC'].value + job.data['ELC'].value) * job.data['BRK'].value * job.data['CRT'].value * job.data['WKP'].value * job.data['MGC'].value
    
    ret = mff_dmg_calc._generate_dmg_list(ret)
    return ret
    
  @staticmethod
  def help_code():
    txt = u'代號說明:\n'
    txt += u'\n'.join(u'代號: {} - {}'.format(u', '.join(value.key), 
                                               value.description) for key, value in mff_dmg_calc.code_dict().items())
    return txt

  @staticmethod
  def help_sample():
      txt = u'MFF\n技能威力 1230\n屬性強化 94%\n技能連擊 70%\n同屬連擊 10%\n爆擊加成 70%\n弱點加成 70%\n破防 80%\n魔力 1263%'
      return txt
    
  @staticmethod
  def text_job_parser(input):
    dataobj = [x.split(' ') for x in input.split('\n')]
    
    ret_job = job()
    for key, value in ret_job.data.items():
      if not value.value_set:
        for pair in dataobj:
          if pair[0] in value.key:
            if '%' in pair[1]:
              pair[1] = pair[1].replace('%', '')
              value.value = float(pair[1]) / 100.0
            else:
              value.value = float(pair[1])
              
    return ret_job
    
class job(object):
  def __init__(self, **kwargs):
    self._data = mff_dmg_calc.code_dict()
    for key, value in kwargs.items():
      self._data[key].value = value
      
  @property
  def data(self):
    return self._data

  def __repr__(self):
      return u'\n'.join(u'{} - {}'.format(value.description.decode('utf-8'), value.value) for key, value in self._data.items())
    
class dmg_bonus(object):
  """NOTICE: enter value without percentage."""
  def __init__(self, key, description, base=0.0, nonbreak_base=-1.0):
    self._key = [key] if not isinstance(key, list) else key
    self._description = description
    self._base = float(base)
    self._nbase = base if nonbreak_base == -1.0 else float(nonbreak_base)
    self._value = 0.0
    self._value_set = False
    
  def val(self, is_break=True):
    if is_break:
      return self._base + self._value
    else:
      return self._nbase + self._value
    
  @property
  def description(self):
    return self._description
    
  @property
  def key(self):
    return self._key
    
  @property
  def value(self):
    return self._base + self._value
    
  @property
  def value_set(self):
    return self._value_set
    
  @value.setter
  def value(self, value):
    self._value_set = True
    self._value = float(value)
    
  def __repr__(self):
    return u'Description: {}, Key: {}, Data Set: {}, Value: (B){} / (NB){}'.format(self._description, 
                                                                                   self._key, 
                                                                                   self._value_set, 
                                                                                   self.val(), 
                                                                                   self.val(False))

