# -*- coding: utf-8 -*-

import os
import tempfile
import hashlib
import time

from imgur.helpers.error import ImgurClientError

class img_msg_handler(object):
    def __init__(self, line_api, imgur_api, tmp_path):
        self._line_api = line_api
        self._imgur_api = imgur_api

        self.tmp_path = tmp_path

    def image_sha224_of_message(self, line_msg):
        message_content = self._line_api.get_content(line_msg.id)
        for chunk in message_content.iter_content(4096):
            chunk_data = chunk
            break

        return img_msg_handler.generate_sha224(chunk_data)

    def upload_imgur(self, line_msg):
        """Return upload result in type string."""
        try:
            message_content = self._line_api.get_content(line_msg.id)

            start_time = time.time()
            content = message_content.content
            sha224 = img_msg_handler.generate_sha224(content[0:4096])

            image_url = self._imgur_api.upload(content, sha224)
            end_time = time.time()

            return ImgurUploadResult(u'檔案已上傳至imgur。\n總處理時間: {:f}秒'.format(end_time - start_time), image_url)
        except ImgurClientError as e:
            return ImgurUploadResult(u'Imgur API發生錯誤，狀態碼: {}\n\n錯誤訊息: {}'.format(e.status_code, e.error_message), None)

    @staticmethod
    def generate_sha224(part_content):
        return hashlib.sha224(part_content).hexdigest()

class ImgurUploadResult(object):
    def __init__(self, result_string, image_url):
        self._result_string = result_string
        self._image_url = image_url

    @property
    def result_string(self):
        return self._result_string

    @property
    def image_url(self):
        return self._image_url