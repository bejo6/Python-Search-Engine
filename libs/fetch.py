import os
import gzip
import hashlib
import http.cookiejar
import urllib.request
import urllib.parse
from utils.helper import split_url, validate_path, file_exist, random_agent, decode_bytes


class FetchRequest:
    def __init__(self, **kwargs):
        self.debug = kwargs.get('debug') or False
        self.user_agent = kwargs.get('user_agent') or random_agent()
        self.timeout = kwargs.get('timeout') or 10
        self.cookie_dir = kwargs.get('cookie_dir') or 'cookie'
        self.cookie_ext = kwargs.get('cookie_ext') or '_cookie'
        self.cookie_file = None
        self.cookie = None

    def set_cookie_file(self, url):
        cookieStr = self.cookie_file

        spliturl = split_url(url)
        if spliturl.get('url'):
            cookieStr = '%s%s' % (spliturl.get('scheme'), spliturl.get('domain'))

        cookieName = hashlib.md5(cookieStr.encode()).hexdigest()
        cookieFile = '%s%s' % (cookieName, self.cookie_ext)

        if validate_path(self.cookie_dir):
            self.cookie_file = os.path.join(self.cookie_dir, cookieFile)

    def get(self, url, headers=None):
        response = self.request(url=url, method='GET', headers=headers)

        return self.get_response(response)

    def post(self, url, headers=None, data=None):
        response = self.request(url=url, method='POST', headers=headers, data=data)

        return self.get_response(response)

    def request(self, url, **kwargs):
        method = kwargs.get('method') or 'GET'
        headers = kwargs.get('headers') or {}
        data = kwargs.get('data') or {}

        self.set_cookie_file(url)

        # https://developpaper.com/python-cookie-read-and-save-method/
        if file_exist(self.cookie_file):
            cookie = http.cookiejar.MozillaCookieJar()
            cookie.load(self.cookie_file, ignore_discard=True, ignore_expires=True)
        else:
            cookie = http.cookiejar.MozillaCookieJar(self.cookie_file)

        handler = urllib.request.HTTPCookieProcessor(cookie)
        opener = urllib.request.build_opener(handler)
        request = urllib.request.Request(url=url, method=method)

        if isinstance(headers, dict):
            for k, v in headers.items():
                request.add_header(k, v)

        if not request.has_header('User-Agent') and self.user_agent:
            request.add_header('User-Agent', self.user_agent)

        if isinstance(data, dict):
            request.data = urllib.parse.urlencode(data).encode()

        try:
            response = opener.open(request, timeout=self.timeout)
            cookie.save(self.cookie_file, ignore_discard=True, ignore_expires=True)

            return response
        except Exception as err:
            print(err)

        return

    @staticmethod
    def get_response(response):
        if response:
            try:
                content_encoding = response.getheader('Content-Encoding')
                if content_encoding and content_encoding.lower() == 'gzip':
                    result, _ = decode_bytes(gzip.decompress(response.read()))
                else:
                    result, _ = decode_bytes(response.read())

                return result
            except Exception as err:
                print('_response error', err)

        return
