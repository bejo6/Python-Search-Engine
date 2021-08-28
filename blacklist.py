import re
from urllib.parse import urlparse


DOMAIN_BLACKLIST = [
    'msn.com',
    'bing.com',
    'bingj.com',
    'yahoo.com',
    'wikipedia.org',
    'youtube.com',
    'google.com',
    'googleadservices.com',
    'quora.com',
    'amazon.com',
    'ask.com',
    'facebook.com',
    'yandex.com',
    'yandex.ru',
    'naver.com',
    'seznam.cz',
]


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
