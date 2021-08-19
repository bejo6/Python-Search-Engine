import os
import re
import hashlib
import http.cookiejar
from html import unescape
from urllib.parse import urlparse, urldefrag, urlsplit
from urllib.request import Request, HTTPCookieProcessor, build_opener, urlopen
from urllib.error import HTTPError, URLError
from blacklist import DOMAIN_BLACKLIST
from socket import timeout


def list_charset() -> list:
    _list_charset = ['utf_8', 'iso8859_1', 'ascii', 'big5', 'big5hkscs', 'cp037', 'cp424', 'cp437', 'cp500', 'cp720', 'cp737', 'cp775', 'cp850', 'cp852', 'cp855', 'cp856',
                     'cp857', 'cp858', 'cp860', 'cp861', 'cp862', 'cp863', 'cp864', 'cp865', 'cp866', 'cp869', 'cp874', 'cp875', 'cp932', 'cp949', 'cp950',
                     'cp1006', 'cp1026', 'cp1140', 'cp1250', 'cp1251', 'cp1252', 'cp1253', 'cp1254', 'cp1255', 'cp1256', 'cp1257', 'cp1258', 'euc_jp',
                     'euc_jis_2004', 'euc_jisx0213', 'euc_kr', 'gb2312', 'gbk', 'gb18030', 'hz', 'iso2022_jp', 'iso2022_jp_1', 'iso2022_jp_2',
                     'iso2022_jp_2004', 'iso2022_jp_3', 'iso2022_jp_ext', 'iso2022_kr', 'latin_1', 'iso8859_2', 'iso8859_3', 'iso8859_4', 'iso8859_5',
                     'iso8859_6', 'iso8859_7', 'iso8859_8', 'iso8859_9', 'iso8859_10', 'iso8859_11', 'iso8859_13', 'iso8859_14', 'iso8859_15', 'iso8859_16',
                     'johab', 'koi8_r', 'koi8_u', 'mac_cyrillic', 'mac_greek', 'mac_iceland', 'mac_latin2', 'mac_roman', 'mac_turkish', 'ptcp154', 'shift_jis',
                     'shift_jis_2004', 'shift_jisx0213', 'utf_32', 'utf_32_be', 'utf_32_le', 'utf_16', 'utf_16_be', 'utf_16_le', 'utf_7', 'utf_8_sig']

    return _list_charset


def decode_bytes(val) -> tuple:
    decoded = ''
    charset = ''

    for _charset in list_charset():
        charset = _charset
        try:
            decoded = val.decode(charset)
            break
        except UnicodeDecodeError:
            pass
        except LookupError:
            pass

    if decoded and charset:
        return decoded, charset

    charset = 'utf-8'
    decoded = val.decode(charset, 'replace')
    return decoded, charset


def cookie_file(url, ext='_cookie'):
    _cookieFile = ''
    o = urlparse(url)
    if not o.netloc:
        _cookieStr = o.path
    else:
        _cookieStr = f'{o.scheme}{o.netloc}'

    if _cookieStr:
        _cookieName = hashlib.md5(_cookieStr.encode()).hexdigest()
        _cookieFile = f'{_cookieName}{ext}'

    return _cookieFile


def fetch_url(url, delete_cookie=False, headers: dict = None):
    _result = ''
    _response = None
    _userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0'
    _request = Request(url)
    _request.add_header('User-Agent', _userAgent)
    if headers:
        for key in headers:
            _request.add_header(key, headers.get(key))

    _cookieFile = cookie_file(url)
    if _cookieFile:
        if delete_cookie:
            if os.path.exists(_cookieFile) and os.path.isfile(_cookieFile):
                os.remove(_cookieFile)

        if os.path.exists(_cookieFile) and os.path.isfile(_cookieFile):
            cookie = http.cookiejar.MozillaCookieJar()
            cookie.load(_cookieFile, ignore_discard=True, ignore_expires=True)
        else:
            cookie = http.cookiejar.MozillaCookieJar(_cookieFile)

        handler = HTTPCookieProcessor(cookie)
        opener = build_opener(handler)
        try:
            _response = opener.open(_request, timeout=10)
            cookie.save(_cookieFile, ignore_discard=True, ignore_expires=True)
        except HTTPError as err:
            print(err)
        except URLError as err:
            print(err)
    else:
        try:
            _response = urlopen(_request, timeout=10)
        except HTTPError as err:
            print(err)
        except URLError as err:
            print(err)
        except timeout as err:
            print(err)
        except Exception as err:
            print(err)

    if _response:
        _result, _ = decode_bytes(_response.read())

    return _result


def clean_url(url):
    url = urldefrag(url).url
    surl = urlsplit(url)
    lower = surl.netloc.lower()
    url = url.replace(surl.netloc, lower)
    url = unescape(url)
    return url


def valid_url(url):
    if not re.match(r'^https?://', url, re.I):
        url = re.sub(r'^:?//', '', url)
        url = f'http://{url}'

    parse_url = urlparse(url, allow_fragments=False)
    patern_domain = r'[a-z0-9-]{1,63}\.[a-z]{2,6}(:\d+)?$'
    domain_name = re.search(patern_domain, parse_url.netloc, re.I)
    if domain_name:
        return clean_url(url)

    return ''


def is_blacklisted(url: str):
    patern_domain = r'[a-z0-9-]{1,63}\.[a-z]{2,6}(:\d+)?$'
    parse = urlparse(url)
    domain_name = re.search(patern_domain, parse.netloc, re.I)
    if domain_name:
        try:
            domain = domain_name.group(0).lower()
            if domain in DOMAIN_BLACKLIST:
                return True
        except IndexError:
            pass
    return False
