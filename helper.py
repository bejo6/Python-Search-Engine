import os
import re
import hashlib
import http.cookiejar
from html import unescape
from urllib.parse import urlparse, urldefrag, urlsplit
from urllib.request import Request, HTTPCookieProcessor, build_opener, urlopen
from blacklist import DOMAIN_BLACKLIST


def cookie_file(url, ext='_cookie'):
    o = urlparse(url)
    if not o.netloc:
        _cookieStr = o.path
    else:
        _cookieStr = f'{o.scheme}{o.netloc}'

    if not _cookieStr:
        return False

    _cookieName = hashlib.md5(_cookieStr.encode()).hexdigest()
    _cookieFile = f'{_cookieName}{ext}'
    return _cookieFile


def fetch_url(url, delete_cookie=False, headers: dict = None):
    _result = None
    _userAgent = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'
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
        response = opener.open(_request)
        cookie.save(_cookieFile, ignore_discard=True, ignore_expires=True)
    else:
        response = urlopen(_request)

    try:
        _result = response.read().decode('utf-8')
    except UnicodeDecodeError:
        _result = response.read().decode('ascii')

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
