# -*- coding: utf-8 -*-

import requests
import json
import os, sys, errno, shutil
import zipfile
import time

import ext

class sticker_content_type(ext.EnumWithName):
    ANIMATED = 0, '動態貼圖'
    SOUND = 1, '音效'
    STATIC = 2, '靜態貼圖'

class line_sticker_downloader(object):
    DOWNLOAD_SOUND_CODE = 'S'

    def __init__(self, file_proc_path):
        self._file_proc_path = file_proc_path
    
    def _get_content(self, sticker_content_type, pack_id, list_ids):
        """\
        Parameters:
            `sticker_content_type`: The type of content to download. (sticker_content_type)
            `pack_id`: line sticker package ID.
            `pack_name`: line sticker package ID.
            `list_ids`: id list of the content to download.

        Returns:
            Returns path of the writed contents in list.

        Errors: 
            raise `MetaNotFoundException` if status code of getting pack meta is not 200.
        """
        act = line_sticker_downloader.get_download_action(sticker_content_type)
        if act is None:
            raise ValueError(u'Url function and file extension of specified sticker type not handled. {}'.format(repr(sticker_content_type)))

        url_func, file_ext = act

        stk_dir = os.path.join(self._file_proc_path, str(pack_id))
        files_path = []

        try:
            os.makedirs(stk_dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        for stk_id in list_ids:
            save_path = os.path.join(stk_dir, str(stk_id) + file_ext)

            url = url_func(pack_id, stk_id)
            request_result = requests.get(url, stream=True)

            with open(save_path, 'wb') as f:
                for chunk in request_result.iter_content(chunk_size=20480):
                    if chunk:
                        f.write(chunk)

            files_path.append(save_path)

        return files_path

    def download_stickers(self, sticker_metadata, download_sound_if_available=False):
        """\
        Parameters:
            `sticker_metadata`: metadata of sticker package.

        Returns:
            Returns path of compressed sticker package(zip).
        """
        stk_ids = sticker_metadata.stickers
        pack_id = sticker_metadata.pack_id
        pack_name = str(pack_id) + (line_sticker_downloader.DOWNLOAD_SOUND_CODE if download_sound_if_available else '')
        comp_file_path = os.path.join(self._file_proc_path, pack_name + '.zip')

        if os.path.isfile(comp_file_path):
            time_consumed_dl = 0.0
            time_consumed_comp = 0.0
        else:
            content_type_to_download = sticker_content_type.ANIMATED if sticker_metadata.is_animated_sticker else sticker_content_type.STATIC

            _start = time.time()
            path_list = self._get_content(content_type_to_download, pack_id, stk_ids)
            
            if download_sound_if_available and sticker_metadata.is_animated_sticker:
                path_list.extend(self._get_content(sticker_content_type.SOUND, pack_id, stk_ids))
            time_consumed_dl = time.time() - _start

            _start = time.time()
            
            with zipfile.ZipFile(comp_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for path in path_list:
                    try:
                        zipf.write(path, os.path.basename(path))
                    except OSError:
                        return None

            try:
                shutil.rmtree(os.path.join(self._file_proc_path, pack_name))
            except OSError as exc:
                if exc.errno == errno.ENOENT:
                    pass
                else:
                    raise exc

            time_consumed_comp = time.time() - _start

        return line_sticker_download_result(comp_file_path, stk_ids, time_consumed_dl, time_consumed_comp)
    
    def get_pack_meta(self, pack_id):
        """\
        Parameters:
            `pack_id`: line sticker package ID.

        Returns:
            Returns the meta data of the sticker pack in line_sticker_metadata.

        Errors: 
            raise `MetaNotFoundException` if status code of getting pack meta is not 200.
        """
        pack_meta = requests.get(line_sticker_downloader.get_meta_url(pack_id))

        if pack_meta.status_code == 200:
            json_dict = json.loads(pack_meta.text)
            return line_sticker_metadata(json_dict)
        else:
            raise MetaNotFoundException(pack_meta.status_code)

    @staticmethod
    def get_meta_url(pack_id):
        """\
        Parameters:
            `pack_id`: line sticker package ID.

        Returns:
            Returns the url of the metadata file in string.
        """
        return 'http://dl.stickershop.line.naver.jp/products/0/0/1/{}/android/productInfo.meta'.format(pack_id)

    @staticmethod
    def get_sticker_url(pack_id, sticker_id):
        """\
        Parameters:
            `pack_id`: line sticker package ID.
            `sticker_id`: line sticker ID.

        Returns:
            Returns the url of the sticker in string.
        """
        return 'http://dl.stickershop.line.naver.jp/stickershop/v1/sticker/{}/android/sticker.png'.format(sticker_id)

    @staticmethod
    def get_apng_url(pack_id, sticker_id):
        """\
        Parameters:
            `pack_id`: line sticker package ID.
            `sticker_id`: line sticker ID.

        Returns:
            Returns the url of the animated sticker in string.
        """
        return 'https://sdl-stickershop.line.naver.jp/products/0/0/1/{}/android/animation/{}.png'.format(pack_id, sticker_id)

    @staticmethod
    def get_sound_url(pack_id, sticker_id):
        """\
        Parameters:
            `pack_id`: line sticker package ID.
            `sticker_id`: line sticker ID.

        Returns:
            Returns the url of the SE of the specified sticker in string.
        """
        return 'https://stickershop.line-scdn.net/stickershop/v1/sticker/{}/IOS/sticker_sound.m4a'.format(sticker_id)

    @staticmethod
    def get_download_action(content_type):
        """\
        Parameters:
            `content_type`: The content type of download action's target.

        Returns:
            Returns a tuple:
                [0]: function to get the url.
                [1]: extension of downloaded content.
        """
        STICKER_DOWNLOAD_DICT = { 
            sticker_content_type.ANIMATED: (line_sticker_downloader.get_apng_url, '.apng'),
            sticker_content_type.STATIC: (line_sticker_downloader.get_sticker_url, '.png'),
            sticker_content_type.SOUND: (line_sticker_downloader.get_sound_url, '.m4a')
        }

        return STICKER_DOWNLOAD_DICT.get(content_type)

class line_sticker_metadata(object):
    UNKNOWN = u'(不明)'

    def __init__(self, meta_dict):
        self._dict = meta_dict

    @property
    def pack_id(self):
        """\
        Returns:
            Returns the id of sticker package in int.
        """
        return self._dict['packageId']

    @property
    def title(self):
        """\
        Returns:
            Returns the title of the sticker package. Default is set to english (en).
        """
        return self._get_localized_object('title', 'en')

    @property
    def author(self):
        """\
        Returns:
            Returns the author of the sticker package. Default is set to english (en).
        """
        return self._get_localized_object('author', 'en')

    @property
    def stickers(self):
        """\
        Returns:
            Returns stickers' id inside the package in list(int).
        """
        stk_obj = self._dict.get('stickers', [])
        if len(stk_obj) > 0:
            return [stk['id'] for stk in stk_obj]
        else:
            return stk_obj

    @property
    def is_animated_sticker(self):
        """\
        Returns:
            Returns boolean indicates whether stickers inside the package in animated.
        """
        return self._dict.get('hasAnimation', False)

    @property
    def has_se(self):
        """\
        Returns:
            Returns boolean indicates whether stickers inside the package has SE.
        """
        return self._dict.get('hasSound', False)

    def _get_localized_object(self, key, default):
        localized_object = self._dict.get(key, {})
        if len(localized_object) > 0:
            localized_str_ret = localized_object.get('en', line_sticker_metadata.UNKNOWN)

            if localized_str_ret == line_sticker_metadata.UNKNOWN:
                return [localized_str for lang, localized_str in localized_object.iteritems()][0]
            else:
                return localized_str_ret
        else:
            return line_sticker_metadata.UNKNOWN

class line_sticker_download_result(object):
    def __init__(self, compressed_file_path, sticker_ids, downloading_consumed_time, compression_consumed_time):
        self._compressed_file_path = compressed_file_path
        self._sticker_ids = sticker_ids
        self._downloading_consumed_time = downloading_consumed_time
        self._compression_consumed_time = compression_consumed_time
        
    @property
    def compressed_file_path(self):
        """\
        Returns:
            Returns the path of compressed sticker package file in str.
        """
        return self._compressed_file_path
    
    @property
    def sticker_ids(self):
        """\
        Returns:
            Returns id array (list(int)) of downloaded stickers.
        """
        return self._sticker_ids
    
    @property
    def sticker_count(self):
        """\
        Returns:
            Returns count of downloaded stickers in int.
        """
        return len(self._sticker_ids)
    
    @property
    def downloading_consumed_time(self):
        """\
        Returns:
            Returns time used in downloading (sec in float).
        """
        return self._downloading_consumed_time
    
    @property
    def compression_consumed_time(self):
        """\
        Returns:
            Returns time used in compression (sec in float).
        """
        return self._compression_consumed_time

class MetaNotFoundException(Exception):
    def __init__(self, *args):
        return super(MetaNotFoundException, self).__init__(*args)