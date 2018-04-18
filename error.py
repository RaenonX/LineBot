# -*- coding: utf-8 -*-

import time
import httplib

from enum import Enum

class mode(Enum):
    FUNNY = 1
    NORMAL = 2

class UndefinedModeException(Exception):
    def __init__(self, *args):
        return super(UndefinedModeException, self).__init__(*args)

class error(object):
    MODE = mode.NORMAL

    USER_MANUAL_URL = 'https://sites.google.com/view/jellybot'

    class webpage(object):

        @staticmethod
        def no_content():
            d = { mode.NORMAL: u'沒有內容。',
                  mode.FUNNY: u'我不記得有這東西啊？可能我忘掉了，嘿嘿嘿' }
            return d[error.MODE]

    class main(object):
        @staticmethod
        def incorrect_password_or_insufficient_permission():
            d = { mode.NORMAL: u'密碼錯誤或權限不足。',
                  mode.FUNNY: u'你密碼打錯或是你太廢XD' }
            return d[error.MODE]

        @staticmethod
        def invalid_thing(name_of_thing, thing):
            d = { mode.NORMAL: u'不合法的{}: {}。請查看使用說明書( {} )。'.format(name_of_thing, thing, error.USER_MANUAL_URL),
                  mode.FUNNY: u'你打的{} ({})我聽不懂，去看說明書( {} )87次再來用吧030'.format(name_of_thing, thing, error.USER_MANUAL_URL) }
            return d[error.MODE]
        
        @staticmethod
        def invalid_thing_with_correct_format(name_of_thing, correct_format, thing):
            d = { mode.NORMAL: u'不合法的{nt}: {t}。{nt}應為{fmt}。\n詳情請查看使用說明書( {um} )。'.format(nt=name_of_thing, t=thing, fmt=correct_format, um=error.USER_MANUAL_URL),
                  mode.FUNNY: u'你打的{} ({})應該是{}才對啊，去看說明書( {} )487次再來用吧030'.format(name_of_thing, thing, correct_format, error.USER_MANUAL_URL) }
            return d[error.MODE]

        @staticmethod
        def lack_of_thing(name_of_thing):
            d = { mode.NORMAL: u'缺少{nm}。請修正您所提供的{nm}成正確的格式。詳細說明請參閱使用說明書( {um} )'.format(nm=name_of_thing, um=error.USER_MANUAL_URL),
                  mode.FUNNY: u'{}少了，去看說明書，渾蛋QQ'.format(name_of_thing, error.USER_MANUAL_URL) }
            return d[error.MODE]

        @staticmethod
        def no_result():
            d = { mode.NORMAL: u'無結果。',
                  mode.FUNNY: u'找不到你要的東西~' }
            return d[error.MODE]

        @staticmethod
        def incorrect_channel(available_in_1v1=True, available_in_room=False, available_in_group=False):
            available = u'{} {} {}'.format(u'[ 私訊 ]' if available_in_1v1 else u'[ - ]',
                                           u'[ 群組 ]' if available_in_group else u'[ - ]',
                                           u'[ 房間 ]' if available_in_room else u'[ - ]')

            d = { mode.NORMAL: u'無法於此類型的頻道使用。請至下列頻道:\n{}\n詳細使用說明請參閱使用說明書( {} )'.format(available, error.USER_MANUAL_URL),
                  mode.FUNNY: u'這個功能只有在 {} 中可以使用哦'.format(available) }
            return d[error.MODE]

        @staticmethod
        def incorrect_param(param_name, correct):
            d = { mode.NORMAL: u'無法辨認。如果要使用這個功能，{}必須為{}。詳細使用方法請參閱使用說明書( {} )。'.format(param_name, correct, error.USER_MANUAL_URL),
                  mode.FUNNY: u'不懂你要幹嘛...{}不是應該是{}嗎？去看說明書吧 ( {} )'.format(param_name, correct, error.USER_MANUAL_URL) }
            return d[error.MODE]

        @staticmethod
        def unable_to_determine():
            d = { mode.NORMAL: u'無法判斷指令。請檢閱使用說明書( {} )。'.format(error.USER_MANUAL_URL),
                  mode.FUNNY: u'聽不懂，去看說明書 ( {} )'.format(error.USER_MANUAL_URL) }
            return d[error.MODE]

        @staticmethod
        def pair_not_exist_or_insuffieicnt_permission():
            d = { mode.NORMAL: u'回覆組不存在，或字組改變權限不足。權限相關說明請參閱使用說明書( {} )。'.format(error.USER_MANUAL_URL),
                  mode.FUNNY: u'我不記得有你指定的回覆組，不然就是你不夠猛讓我想起來 :P' }
            return d[error.MODE]

        @staticmethod
        def invalid_length(thing, length):
            d = { mode.NORMAL: u'長度不符。{}的長度應為{}。'.format(thing, length),
                  mode.FUNNY: u'{}的長度不是應該要這~麼長({})嗎？'.format(thing, length) }
            return d[error.MODE]

        @staticmethod
        def unable_to_receive_user_id():
            return u'因LINE政策問題，如果要使用這個功能的話，請先將LINE更新到v7.5.0以上，或是在私訊頻道中重試。\n\n詳細說明請點此查看: https://developers.line.me/messaging-api/obtaining-user-consent'

        @staticmethod
        def illegal_user_id():
            return u'不合法的使用者ID。'

        @staticmethod
        def line_account_data_not_found():
            return u'無對應LINE帳號資料。'

        @staticmethod
        def user_name_not_found():
            return u'找不到使用者名稱。'

        @staticmethod
        def miscellaneous(content):
            return u'{}\n\n小水母使用說明: {}'.format(content, error.USER_MANUAL_URL)

        @staticmethod
        def error_report(error_id, email_sent):
            return u'發生錯誤。錯誤ID: {}{}'.format(error_id, u' (錯誤報告已寄送)' if email_sent else u'')

    class permission(object):
        @staticmethod
        def user_is_resticted():
            return u'您遭到群組管理員設為「限制用戶」，所有系統功能將無法在這個群組觸發。若有任何問題，請洽詢管理員。'

        @staticmethod
        def restricted(permission=None):
            return u'已限制的功能。{}'.format(
                u'\n需求權限: {}+\n\n權限相關說明請參閱使用說明書( {} )'.format(permission, error.USER_MANUAL_URL) if permission is not None else u'')

    class line_bot_api(object):
        MAX_TEMPLATE_ACTIONS = 30
        MAX_CHARACTER_COUNT = 2000 # Ref: https://developers.line.me/en/docs/messaging-api/reference/#text
        MAX_NEWLINE = 35

        @staticmethod
        def unable_to_receive_user_id():
            return u'無法獲取LINE UID。請確定達成全部以下條件後重試:\n1.LINE版本7.5.0或以上\n2.已加入小水母好友\n\n如果全部符合上述條件仍然跳出此錯誤訊息的話，請輸入"小水母"填寫問題回報單。'

        @staticmethod
        def illegal_room_group_id(illegal_gid):
            return error.main.invalid_thing_with_correct_format(u'LINE房間/群組', u'C(群組)或R(房間)開頭，並且長度為33字元，後32碼為0~9或a~f.', illegal_gid)

        @staticmethod
        def illegal_user_id(illegal_uid):
            return error.main.invalid_thing_with_correct_format(u'LINE用戶ID', u'U開頭，並且長度為33字元，後32碼為0~9或a~f.', illegal_uid)

        @staticmethod
        def text_length_too_long(length, max_length, external_link):
            return u'因訊息長度({}字)超過LINE API限制({}字)，故無法顯示。請點下方連結以查看訊息。\n{}'.format(length, max_length, external_link)

        @staticmethod
        def too_many_newlines(newlines, max_newlines, external_link):
            return u'因訊息行數({}行)超過最大限制({}行)，故不顯示訊息。請點下方連結以查看訊息。\n{}'.format(newlines, max_newlines, external_link)

        @staticmethod
        def too_many_linked_words(count):
            MAX = error.line_bot_api.MAX_TEMPLATE_ACTIONS
            return u'因相關關鍵字數量({}個)超過系統限制({}個)，故無法顯示。請刪除{}組相關關鍵字以後重試。'.format(count, MAX, count - MAX)

        @staticmethod
        def text_too_long():
            LIMIT = error.line_bot_api.MAX_CHARACTER_COUNT
            return u'任何文字相關的項目長度不得大於{}字元，請重新輸入。'.format(LIMIT)

    class oxford_api(object):
        @staticmethod
        def no_result(vocabulary):
            return u'No result of {}.'.format(vocabulary)

        @staticmethod
        def err_with_status_code(status_code):
            return u'An error has occurred while querying the data. Status Code: {} ({})'.format(status_code, httplib.responses[status_code])

        @staticmethod
        def disabled():
            return u'Oxford dictionary has beed disabled. The reason might be an illegal api key or over quota.'

        @staticmethod
        def sense_not_found():
            return u'No sense found in the entry.'

    class mongo_db(object):
        @staticmethod
        def op_fail(err_instance):
            return u'資料庫指令執行失敗。\n錯誤碼: {}\n錯誤訊息: {}'.format(err_instance.code, err_instance.message)

    class sys_command(object):
        @staticmethod
        def unable_to_parse(result):
            if error.MODE == mode.FUNNY:
                return u'傻逼，說明書看好看滿再來叫我做事，都沒看好就在那邊想打指令，Hen煩捏！\n\n{}'.format(result)
            else:
                return u'參數解析失敗:\n\n{}'.format(result)

        @staticmethod
        def parameter_error(index, content):
            if error.MODE == mode.FUNNY:
                return u'你第{}個參數手殘打錯了，你看看: {}'.format(index, content)
            else:
                return u'參數{}發生錯誤，請查閱說明書以獲取使用方法。錯誤訊息:\n{}'.format(index, content)

        @staticmethod
        def must_https(obj):
            return u'必須是https連結。({})'.format(obj)

        @staticmethod
        def must_https_image(link, content_type):
            return u'必須是https的圖片連結(瀏覽器直接開啟時，只會顯示圖片)。\n連結: {}\n內容種類: {}'.format(link, content_type)

        @staticmethod
        def must_gt_0(obj):
            return u'整數需要大於0。({} - {})'.format(type(obj), obj)

        @staticmethod
        def must_int(obj):
            return u'必須是整數或整數陣列。({} - {})'.format(type(obj), obj)

        @staticmethod
        def must_sha(obj):
            return u'必須是SHA224雜湊結果。({})'.format(obj)

        @staticmethod
        def lack_of_parameters(indexes=None):
            if indexes is None:
                indexes = u'參數'
            else:
                indexes = u'、'.join([u'參數{}'.format(num) for num in indexes])

            return error.main.lack_of_thing(indexes)
        
        @staticmethod
        def syntax_error(function_code):
            return u'語法有誤。請檢查輸入的指令是否正確。\n嘗試使用功能代號: {}\n\n使用說明書: {}'.format(function_code, error.USER_MANUAL_URL)

        @staticmethod
        def action_not_implemented(function_code, match_at, action_text):
            return u'於{}的驗證式第{}句中，發生未定義的行為: {}。請檢查語法是否正確。'.format(function_code, match_at, action_text)

        @staticmethod
        def regex_not_implemented(function_code, match_at, regex):
            return u'未定義{}的驗證式第{}句({})的處理。請檢查語法是否正確。'.format(function_code, match_at, regex)

        @staticmethod
        def same_source_target(gid):
            return u'指令來源和目的地不得相同。({})'.format(gid)

        @staticmethod
        def no_available_target_pair():
            return u'指令執行失敗，無可用回覆組。'

        @staticmethod
        def unknown_func_K_ranking_category(obj):
            return u'不明的排名種類。({})'.format(obj)

        @staticmethod
        def unknown_func_P_record_category(obj):
            return u'不明的系統紀錄種類。({})'.format(obj)

        @staticmethod
        def unknown_func_GA_group_config(obj):
            return u'不明的系統設定種類。({})'.format(obj)

        @staticmethod
        def unknown_func_GA2_permission(obj):
            return u'不明的使用者權限代號。({})'.format(obj)
        
        @staticmethod
        def unknown_func_L_category(obj):
            return u'不明的最近資料種類。({})'.format(obj)\

        @staticmethod
        def unknown_func_W_output_type(obj):
            return u'不明的天氣資料輸出種類。({})'.format(obj)

        @staticmethod
        def unknown_func_W_action(obj):
            return u'不明的天氣資料操作種類。({})'.format(obj)

        @staticmethod
        def unknown_func_STK_ranking_category(obj):
            return u'不明的貼圖排行種類。({})'.format(obj)

        @staticmethod
        def func_C_currency_symbol_unrecognizable(obj):
            return u'無法分析貨幣種類。({})'.format(obj)

    class string_calculator(object):
        @staticmethod
        def result_is_not_numeric(org_text=None, calc_text=None):
            return u'計算結果為非數字型態，請重新檢查輸入的算式是否正確。{}{}'.format(
                u'' if org_text is None else u'\n輸入資料型態: {}\n輸入原始字串: {}'.format(type(org_text), org_text),
                u'' if calc_text is None else u'\n輸出資料型態: {}\n輸出原始字串: {}'.format(type(calc_text), calc_text))

        @staticmethod
        def error_on_calculating(ex):
            return u'發生錯誤，計算失敗。\n錯誤訊息: {}'.format(ex.message)

        @staticmethod
        def calculation_timeout(timeout_sec, org_text=None):
            return u'因計算超時({}秒)，故終止運算。請嘗試拆解算式以後重新計算。{}'.format(
                timeout_sec,
                u'' if org_text is None else u'\n資料型態: {}\n原始字串: {}'.format(type(org_text), org_text))

        @staticmethod
        def wrong_format_to_calc_equations():
            return u'方程式計算格式錯誤。請確認輸入格式為:\n第一行 - 有使用的變數，以逗號分隔(例: x, y)\n第二行以後 - 方程式，例如:\n  2x+3y=7\n  5x+8=9'

        @staticmethod
        def overflow(org_text=None):
            return u'發生溢位。請嘗試拆解算式以後重新計算。{}'.format(
                u'' if org_text is None else u'\n原始字串: {}'.format(org_text))

        @staticmethod
        def unknown_calculate_type():
            return u'無法辨認要使用的計算項目。正確格式請參閱使用說明書( {} )'.format(error.USER_MANUAL_URL)

    class keyword_pair(object):
        @staticmethod
        def too_many_matched_data(data_count, limit):
            return u'符合條件的資料筆數過多(找到{}筆，最多{}筆)，請縮小搜尋範圍後重試。'.format(data_count, limit)

    class rss(object):
        @staticmethod
        def cannot_create(id):
            return u'無法新增公告，可能是權限不足所造成。'

        @staticmethod
        def cannot_be_deleted(id):
            return error.rss.action_failed(id, u'刪除')

        @staticmethod
        def cannot_be_updated(id):
            return error.rss.action_failed(id, u'更新')

        @staticmethod
        def action_failed(id, action):
            return u'公告 #{} {}失敗。可能是因為您不是該公告的作者、該公告不存在或權限不足所造成。'.format(id, action)

class warning(object):
    class txt_calc(object):
        @staticmethod
        def possible_wrong_operator_pow():
            return u'偵測到符號"^"。此符號於python中代表XOR運算，並非次方運算。若要次方運算，請使用"**"取代"^"。'

    class currency(object):
        @staticmethod
        def data_not_enough():
            return u'(資料不足，無法計算)'
