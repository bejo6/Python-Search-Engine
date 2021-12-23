import re
from urllib.parse import urlparse
from static import domain_tlds
from helper import split_url

DOMAIN_COMPANY_NAME = [
    'google',
    'bing',
    'wikipedia',
    'blogspot',
    'yahoo',
    'amazon',
    'ebay',
    'wordpress',
    'facebook'
]

DOMAIN_BLACKLIST = [
    'msn.com',
    'live.com',
    'microsoft.com',
    'bingj.com',
    'youtube.com',
    'googleadservices.com',
    'quora.com',
    'ask.com',
    'yandex.com',
    'yandex.ru',
    'naver.com',
    'seznam.cz',
    'stackoverflow.com',
    'twitter.com',
    'instagram.com',
    'alibaba.com',
    'reddit.com',
    'github.com',
    # 'archive.org',
]


def is_blacklisted(url):
    spliturl = split_url(url)
    domain = spliturl.get('domain')
    if domain:
        rdomain = r'^(.*\.)?(%s)$' % '|'.join([re.escape(d) for d in DOMAIN_BLACKLIST])
        if re.search(rdomain, domain, re.I):
            return True

        dcompany = '(%s)(\\.co|go)?\\.(%s)' % ('|'.join(DOMAIN_COMPANY_NAME), '|'.join(domain_tlds))
        rcompany = r'^(.*\.)?%s$' % dcompany
        if re.search(rcompany, domain, re.I):
            return True

    return False
