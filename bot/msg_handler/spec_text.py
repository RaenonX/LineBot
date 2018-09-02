# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

import db, bot, tool, game, error

class special_text_handler(object):
    def __init__(self, mongo_client, line_api_wrapper, weather_reporter):
        self._line_api_wrapper = line_api_wrapper
        self._weather_reporter = weather_reporter
        self._weather_config = db.weather_report_config(mongo_client)
        self._system_stats = db.system_statistics(mongo_client)
        self._luck_gen_record = db.sc_gen_data_manager(mongo_client)

        self._special_keyword = {
            u'天氣': (self._handle_text_spec_weather, (False,)),
            u'詳細天氣': (self._handle_text_spec_weather, (True,)),
            u'運勢': (self._handle_text_spec_luck, ()),
            u'運勢統計': (self._handle_text_spec_luck_rec, ()),
            u'我的運勢': (self._handle_text_spec_luck_self, ()),
            u'時間': (self._handle_text_spec_time, ()),
            u'抽老婆': (self._handle_text_spec_rand_wife, ())
        }

    def handle_text(self, event):
        """Return replied or not."""
        token = event.reply_token
        msg_text = event.message.text
        
        cid = bot.line_api_wrapper.source_channel_id(event.source)
        uid = bot.line_api_wrapper.source_user_id(event.source)

        spec = self._special_keyword.get(msg_text, None)
        
        if spec is not None:
            spec_func, spec_param = spec
            rep_text = spec_func(*(spec_param + (uid, cid)))

            if isinstance(rep_text, (str, unicode)):
                self._line_api_wrapper.reply_message_text(token, rep_text)
            else:
                self._line_api_wrapper.reply_message(token, rep_text)

            return True

        return False

    def _handle_text_spec_weather(self, detailed, uid, cid):
        self._system_stats.extend_function_used(db.extend_function_category.REQUEST_WEATHER_REPORT)

        config_data = self._weather_config.get_config(uid) 
        if config_data is not None and len(config_data.config) > 0:
            ret = [self._weather_reporter.get_data_by_owm_id(cfg.city_id, tool.weather.output_type(cfg.mode), cfg.interval, cfg.data_range) for cfg in config_data.config]

            return u'\n===========================\n'.join(ret)
        else:
            command_head = bot.msg_handler.text_msg_handler.CH_HEAD + u'天氣查詢 '

            template_title = u'快速天氣查詢'
            template_title_alt = u'快速天氣查詢樣板，請使用手機查看。'
            template_actions = { 
                tool.weather.owm.DEFAULT_TAICHUNG.name: command_head + str(tool.weather.owm.DEFAULT_TAICHUNG.id),
                tool.weather.owm.DEFAULT_TAIPEI.name: command_head + str(tool.weather.owm.DEFAULT_TAIPEI.id),
                tool.weather.owm.DEFAULT_KAOHSIUNG.name: command_head + str(tool.weather.owm.DEFAULT_KAOHSIUNG.id),
                tool.weather.owm.DEFAULT_HONG_KONG.name: command_head + str(tool.weather.owm.DEFAULT_HONG_KONG.id),
                tool.weather.owm.DEFAULT_KUALA_LUMPER.name: command_head + str(tool.weather.owm.DEFAULT_KUALA_LUMPER.id),
                tool.weather.owm.DEFAULT_MACAU.name: command_head + str(tool.weather.owm.DEFAULT_MACAU.id)
            }

            if detailed:
                template_actions = { k: v + (u'詳' if detailed else u'簡') for k, v in template_actions.iteritems() }

            return bot.line_api_wrapper.wrap_template_with_action(template_actions, template_title_alt, template_title)

    def _handle_text_spec_luck(self, uid, cid):
        score_package = game.score_gen.sc_gen.generate_score()
        score = score_package.get_score()

        if uid is not None:
            self._luck_gen_record.record(score, uid)

        now = datetime.now()
        seconds_past_today = (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()

        m_score = self._luck_gen_record.get_max_sc_gen_data().score
        m_score_1d = self._luck_gen_record.get_max_sc_gen_data(seconds_past_today).score

        return u'運勢分數(0~10): {:.3f}\n高於此分數的機率: {:.3%}\n{}日內最高分: {:.5f} ({:.3%})\n本日最高分(AM 8起算): {:.5f} ({:.3%})\n\n其他運勢使用方式請參見說明書。\n運勢專區/小水母洗版區: https://line.me/R/ti/g/uI3tAfrqvE'.format(
            score, 
            score_package.get_opportunity_greater(), 
            db.score_gen.sc_gen_data_manager.DATA_EXPIRE_DAYS,
            float(str(m_score)), game.sc_gen_data.calculate_opportunity_greater(m_score), 
            float(str(m_score_1d)), game.sc_gen_data.calculate_opportunity_greater(m_score_1d))

    def _handle_text_spec_luck_rec(self, uid, cid):
        data_today = self._luck_gen_record.get_analyzed_data_today()
        max_data_today = self._luck_gen_record.get_max_user_data(db.sc_gen_data_manager.get_today_past_seconds())
        print max_data_today.user_id_ref
        max_name_today = self._line_api_wrapper.profile_name_safe(max_data_today.user_id_ref)
        min_data_today = self._luck_gen_record.get_min_user_data(db.sc_gen_data_manager.get_today_past_seconds())
        min_name_today = self._line_api_wrapper.profile_name_safe(min_data_today.user_id_ref)

        data_all = self._luck_gen_record.get_analyzed_data()
        max_data_all = self._luck_gen_record.get_max_user_data()
        max_name_all = self._line_api_wrapper.profile_name_safe(max_data_all.user_id_ref)
        min_data_all = self._luck_gen_record.get_min_user_data()
        min_name_all = self._line_api_wrapper.profile_name_safe(min_data_all.user_id_ref)

        return u'本日統計: {}\n\n最高分紀錄使用者 {} 之統計資料:\n{}\n\n最低分紀錄使用者 {} 之統計資料:\n{}\n\n{}日內統計: {}\n \
                \n最高分紀錄使用者 {} 之統計資料:\n{}\n\n最低分紀錄使用者 {} 之統計資料:\n{}'.format(
            data_today.get_status_string(), max_name_today, max_data_today.get_status_string(), min_name_today, min_data_today.get_status_string(),
            db.score_gen.sc_gen_data_manager.DATA_EXPIRE_DAYS,
            data_all.get_status_string(), max_name_all, max_data_all.get_status_string(), min_name_all, min_data_all.get_status_string())

    def _handle_text_spec_luck_self(self, uid, cid):
        if uid is not None:
            data = self._luck_gen_record.get_spec_user_data(uid)
            data_today = self._luck_gen_record.get_spec_user_data(uid, db.sc_gen_data_manager.get_today_past_seconds())
            return u'全時統計\n{}\n\n本日統計(8 AM起算)\n{}'.format(data.get_status_string(), data_today.get_status_string())
        else:
            return u'因無法獲取LINE UID，本功能無法使用。\n{}'.format(error.error.line_bot_api.unable_to_receive_user_id())

    def _handle_text_spec_time(self, uid, cid):
        # Location (CH), Abbreviation, Time offset in hr
        LOCALE = [(u'中台港澳星馬', None, 8), 
                  (u'日本標準', u'JST', 9), 
                  (u'世界標準', u'UTC', 0), 
                  (u'美東標準', u'EST', -5), 
                  (u'美東日光', u'EDT', -4), 
                  (u'太平洋標準', u'PST', -8), 
                  (u'太平洋日光', u'PDT', -7)]
        
        utcnow = datetime.utcnow()
        
        ret = [datetime.strftime(utcnow, u'第%U周 第%j日 (以UTC日期為準)'.encode('utf-8')).decode('utf-8')]

        for location in LOCALE:
            name, abbr, offset = location

            ret.append(u'{}時間 - UTC{:+}{}: {}'.format(
                name,
                offset,
                u' ({})'.format(abbr) if abbr is not None else u'',
                (utcnow + timedelta(hours=offset)).strftime('%Y-%m-%d (%a.) %p %I:%M:%S')))

        ret.append(u'')
        ret.append(u'目前世界以世界標準時間為基準，依照各地區不同而偏移。基本上以經度0度算起，每往東15度，時間加一小時；往西則減一小時。部分地區會因為政府及領土和經度線重疊，為了管轄方便，而不會完全按照這個規則。')

        return u'\n'.join(ret)

    def _handle_text_spec_rand_wife(self, uid, cid):
        if cid not in ["C1912ff5e639fe002a453771502a75cb2", "C42fb1c93c7793f56661e3c87de3e80ef", "Cea209343322a907266b6f2cd510761d0"]:
            data = [(0.02, ["愛麗絲", "尤吉歐", "亞絲娜", "桐人", "LLENN"]),
                    (0.3, ["結衣", "莉法", "詩乃", "有紀", "西莉卡", "莉茲", "幸", "Pitohui", "阿爾戈", "斯朵蕾雅", "菲莉雅", "普蕾米亞", "伶茵", "黑雪姬", "賽玟", "朔夜", "尤娜"]),
                    (0.68, ["克萊茵", "艾基爾", "希茲克利夫", "克拉蒂爾", "PoH", "牙王", "科巴茲", "瑛二", "...沒，你沒老婆", "你自己", "你的右手", "你的左手"])]
            return u"你的老婆是{} :D".format(tool.random_gen.random_drawer.choice_with_weight(data).decode('utf-8'))
        else:
            return u"本群組禁止使用此指令。欲使用者，請至洗版區 (https://line.me/R/ti/g/uI3tAfrqvE) 使用，謝謝。"
