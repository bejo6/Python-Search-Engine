import re
import base64
from logging import DEBUG
from urllib.parse import urljoin, urlencode, urlparse, unquote, parse_qs
from utils.blacklist import is_blacklisted
from utils.helper import setup_logger, validate_url, decode_bytes, split_url
from libs.html_parser import NativeHTMLParser
from libs.fetch import FetchRequest

logger = setup_logger(name='MetaGer')


class MetaGer:
    base_url = 'https://metager.org'
    next_page = ''

    def __init__(self, debug=False):
        self.debug = debug
        self.fetch = FetchRequest()
        self.query = {}
        self.filtering = True

        if self.debug:
            logger.setLevel(DEBUG)

    def search(self, keyword):
        search_url = self.build_query(keyword=keyword)
        return self.search_run(search_url)

    def search_run(self, url):
        result = []
        if not url:
            return result

        duplicate_page = 0
        empty_page = 0
        headers = {'Referer': self.base_url}
        page = 1
        while True:
            if self.debug:
                logger.debug('Page: %s %s' % (page, url))
            else:
                logger.info('Page: %s' % page)

            html = self.fetch.get(url, headers=headers)
            links = self.get_links(html)

            if not links:
                empty_page += 1
                if page > 1:
                    break
            else:
                duplicate = True
                for link in links:
                    if self.filtering:
                        if is_blacklisted(link):
                            logger.debug('[BLACKLIST] %s' % link)
                            continue

                    if link not in result:
                        duplicate = False
                        logger.info(link)
                        result.append(link)
                    else:
                        logger.debug('[EXIST] %s' % link)

                if duplicate:
                    duplicate_page += 1

            if duplicate_page >= 3:
                break

            if empty_page >= 2:
                break

            if self.next_page and self.next_page != url:
                headers.update({'Referer': url})
                url = self.next_page
            else:
                break
            page += 1

        result = list(dict.fromkeys(result))
        logger.info('Total links: %d' % len(result))

        return result

    def build_query(self, keyword, html=None):
        search_url = ''
        if not html:
            html = self.fetch.get(self.base_url)

        _parser = NativeHTMLParser()
        _parser.feed(str(html))
        _parser.close()

        if _parser.root is None:
            return search_url

        form_search = _parser.root.find('.//form[@id="searchForm"]')

        if form_search:
            action = form_search.get('action')
            if action:
                search_url = action.strip()

            inputs = form_search.findall('.//input')
            for inp in inputs:
                _name = inp.get('name')
                _value = inp.get('value')

                if not _name:
                    continue

                if _name != 'eingabe':
                    self.query.update({_name: _value or ''})
                else:
                    self.query.update({_name: keyword})

        if search_url:
            search_url = '%s?%s' % (search_url, urlencode(self.query))

        return search_url

    def get_links(self, html):
        result = []
        if not html:
            return result

        _parser = NativeHTMLParser()
        _parser.feed(str(html))
        _parser.close()

        if _parser.root is None:
            return result

        iframe = _parser.root.find('.//iframe[@id="mg-framed"]')
        links = _parser.root.findall('.//a[@class="result-link"]')

        if not links and iframe is not None:
            iframe_src = iframe.get('src')
            iframe_url = validate_url(iframe_src)
            if iframe_url:
                iframe_html = self.fetch.get(iframe_url)
                return self.get_links(iframe_html)

        for link in links:
            _href = link.get('href')
            url = validate_url(_href)

            patern_metager = r'\/r\/metager\/'
            patern_redirect = r'\/redir\/clickGate'
            if re.search(patern_metager, url, re.I):
                url = self.get_url_base64(url)
            elif re.search(patern_redirect, url, re.I):
                url = self.get_redirect_url(url)

            if url and not re.search(r'metager\.org/partner/', url, re.I):
                result.append(url)

        self.get_next_page(_parser.root)

        if result:
            result = list(dict.fromkeys(result))

        return result

    def get_next_page(self, root):
        self.next_page = ''
        next_search_link = root.find('.//div[@id="next-search-link"]')
        if next_search_link is None:
            return

        _next = next_search_link.find('a')
        if _next is not None:
            _href = _next.get('href')
            if _href:
                self.next_page = validate_url(urljoin(self.base_url, _href))

    @staticmethod
    def get_url_base64(url):
        _url = ''
        _parse = urlparse(str(url))
        _split = _parse.path.split('/', maxsplit=5)
        if len(_split) >= 6:
            _urlbase64 = unquote(_split[-1])
            _urlbase64 = re.sub(r'<+slash>+', '/', _urlbase64, flags=re.I)
            _decode = base64.urlsafe_b64decode(_urlbase64)
            _url, _ = decode_bytes(_decode)

        return _url

    @staticmethod
    def get_redirect_url(url):
        _url = ''
        _parse = urlparse(str(url))
        _query = _parse.query
        _parse_qs = parse_qs(_query)

        urls = _parse_qs.get('url')
        if not isinstance(urls, (list, tuple)):
            return _url

        first_url = validate_url(urls[0])
        if first_url:
            if '..' in first_url:
                p = split_url(url)
                if p.get('url'):
                    first_url = '%s://%s' % (p.get('scheme'), p.get('domain'))

            _url = first_url

        return _url


if __name__ == '__main__':
    import sys
    import argparse
    import json
    try:
        parser = argparse.ArgumentParser(usage='%(prog)s [options]')
        # noinspection PyProtectedMember
        parser._optionals.title = 'Options'
        parser.add_argument('-k', '--keyword',
                            dest='keyword',
                            help='Keyword to search',
                            action='store')
        parser.add_argument('-s', '--save',
                            dest='save_output',
                            help='Save Output results',
                            action='store_true')
        parser.add_argument('-o', '--output',
                            dest='output_file',
                            help='Output results (default metager_results.txt)',
                            default='metager_results.txt',
                            action='store')

        args = parser.parse_args()
        if not args.keyword:
            parser.print_help()
            sys.exit('[!] Keyword required')

        eng = MetaGer()
        res = eng.search(args.keyword)

        if args.save_output:
            if res:
                for rlink in res:
                    with open(args.output_file, 'a', encoding='utf-8', errors='replace') as f:
                        try:
                            f.write('%s\n' % rlink)
                        except UnicodeEncodeError:
                            logger.error(rlink)
        else:
            print(json.dumps(res, indent=2, default=str))
    except KeyboardInterrupt:
        sys.exit('KeyboardInterrupt')
