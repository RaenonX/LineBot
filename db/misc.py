# -*- coding: utf-8 -*-

import error

class PackedResult(object):
    def __init__(self, limited_object, full_object):
        self._limited = limited_object
        self._full = full_object

    @property
    def limited(self):
        return self._limited

    @property
    def full(self):
        return self._full

    def __repr__(self):
        return u'LIMITED:\n{}\n\nFULL:\n{}'.format(self._limited, self._full).encode('utf-8')

class PackedStringResult(PackedResult):
    def __init__(self, limited_list, full_list, has_result=None, separator='\n'):
        if has_result is None:
            self._has_result = len(limited_list) > 0 and len(full_list) > 0
        else:
            self._has_result = has_result

        super(PackedStringResult, self).__init__(separator.join(limited_list), separator.join(full_list))

    @staticmethod
    def init_by_field(data_list, string_format_function, limit=None, append_first_list=None, no_result_text=None, separator='\n', insert_ranking=False, skip_data_count=0):
        has_result = False

        _list_limited = []
        _list_full = []

        if append_first_list is not None and not isinstance(append_first_list, list):
            append_first_list = [append_first_list]

        if append_first_list is not None:
            _list_limited.extend(append_first_list)
            _list_full.extend(append_first_list)

        count = 0 if data_list is None else len(data_list)

        if count <= 0:
            if no_result_text is None:
                no_res = error.error.main.no_result()
            else:
                no_res = no_result_text

            _list_limited.append(no_res)
            _list_full.append(no_res)
        else:
            has_result = True
            count -= skip_data_count

            _list_full.append(u'共有{}筆結果\n'.format(count))

            if limit is not None:
                _limited_data_list = data_list[:limit]
            else:
                _limited_data_list = data_list

            # increase performance (duplicate flag determination if integrate)
            if insert_ranking:
                for index, data in enumerate(data_list, start=1 - skip_data_count):
                    if not skip_data_count <= index:
                        txt = u''
                    else:
                        txt = u'第{}名:\n'.format(index)

                    txt += string_format_function(data)

                    if limit is None or index < limit:
                        _list_limited.append(txt)

                    _list_full.append(txt)
            else:
                for index, data in enumerate(data_list):
                    txt = string_format_function(data)

                    if limit is None or index < limit:
                        _list_limited.append(txt)

                    _list_full.append(txt)

            if limit is not None:
                data_left = count - limit
            else:
                data_left = -1

            if data_left > 0:
                _list_limited.append(u'...(還有{}筆)'.format(data_left))

        return PackedStringResult(_list_limited, _list_full, has_result, separator)

    @property
    def has_result(self):
        return self._has_result
