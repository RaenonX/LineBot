# coding: utf-8

import re

import ext

class regex_finder(object):

    @staticmethod
    def find_match(regex_list, text, is_case_sensitive=True):
        """
        Parameters:
            regex_list: Check if the provided text match the provided pattern. This should be list, and the element of the list can be a tuple. If the element of the list is a list, regex check will iterate through it.
            text: text to check.

        Returns:
            Has result: RegexFindResult
            No result: None
        """
        for num, regex in enumerate(regex_list):
            if not isinstance(regex, (list, tuple)):
                regex = ext.to_list(regex)

            for re_pattern in regex:
                if re_pattern is not None:
                    pattern = ur"^" + re_pattern + ur"$"
                    if not is_case_sensitive:
                        pattern = ur"(?iu)" + pattern

                    match_result = re.match(pattern, text)
                    
                    if match_result is not None:
                        return RegexFindResult(num, match_result, pattern)

        return None

class RegexFindResult(object):
    def __init__(self, match_at, match_obj, pattern):
        self._match_at = match_at
        self._match_obj = match_obj
        self._pattern = pattern

    @property
    def match_at(self):
        return self._match_at

    @property
    def regex(self):
        return self._pattern
    
    def group(self, index):
        """Return None if no such group"""

        try:
            return self._match_obj.group(index)
        except IndexError:
            return None