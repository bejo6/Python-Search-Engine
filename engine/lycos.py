import re
from logging import DEBUG
from urllib.parse import urljoin, urlencode, urlparse, parse_qs
from utils.blacklist import is_blacklisted
from utils.helper import setup_logger, validate_url, split_url
from libs.html_parser import NativeHTMLParser
from libs.fetch import FetchRequest

logger = setup_logger(name='Lycos')


class Lycos:
    base_url = 'https://www.lycos.com'
    search_url = 'https://search.lycos.com/web'

    def __init__(self, debug=False):
        self.debug = debug
        self.fetch = FetchRequest()
        self.query = {}
        self.filtering = True

        if self.debug:
            logger.setLevel(DEBUG)

    def search(self, keyword):
        search_url = self.build_query(keyword=str(keyword))
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

            next_page = self.get_next_page(html)
            if next_page and next_page != url:
                headers.update({'Referer': url})
                url = next_page
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

        patern_keyvol = r'\#keyvol[.)"\'\s]+val[("\'\s]+([a-f0-9]+)[)"\'\s]+;'
        match_keyvol = re.search(patern_keyvol, str(html), re.I)
        if match_keyvol:
            try:
                self.query.update({
                    'q': keyword,
                    'keyvol': match_keyvol.group(1)
                })
            except IndexError:
                pass

        _parser = NativeHTMLParser()
        _parser.feed(str(html))
        _parser.close()

        if _parser.root is None:
            return search_url

        form_search = _parser.root.find('.//form[@id="form_query"]')

        if form_search:
            search_url = form_search.get('action')
            _input = form_search.find('.//input[@id="keyvol"]')
            if _input:
                _name = _input.get('name')
                _value = _input.get('value')
                if _name == 'keyvol':
                    if 'keyvol' not in self.query:
                        self.query.update({
                            'q': keyword,
                            'keyvol': _value
                        })

        if search_url and self.query:
            self.search_url = search_url
            search_url = '%s?%s' % (search_url, urlencode(self.query))
        elif self.query:
            search_url = '%s?%s' % (self.search_url, urlencode(self.query))

        return search_url

    @staticmethod
    def get_links(html):
        result = []
        if not html:
            return result

        _parser = NativeHTMLParser()
        _parser.feed(str(html))
        _parser.close()

        if _parser.root is None:
            return result

        links = _parser.root.findall('.//li//a[@class="result-link"]')

        for link in links:
            _href = link.get('href')
            _urlparse = urlparse(_href)
            if _urlparse:
                _query = _urlparse.query
                if not _query:
                    continue

                _parse_qs = parse_qs(_query)
                if not isinstance(_parse_qs, dict):
                    continue

                # noinspection PyTypeChecker
                urls = _parse_qs.get('as')
                if not isinstance(urls, (list, tuple)):
                    continue

                valid_url = validate_url(urls[0])
                if valid_url:
                    if '..' in valid_url:
                        p = split_url(valid_url, allow_fragments=False)
                        if p.get('url'):
                            valid_url = '%s://%s' % (p.get('scheme'), p.get('domain'))

                    result.append(valid_url)

        if result:
            result = list(dict.fromkeys(result))

        return result

    def get_next_page(self, html):
        next_page = ''
        if not html:
            return next_page

        _parser = NativeHTMLParser()
        _parser.feed(str(html))
        _parser.close()

        if _parser.root is None:
            return next_page

        page_items = _parser.root.find('.//ul[@class="pagination"]')
        if not page_items:
            return next_page

        links = page_items.findall('li//a')
        for link in links:
            _href = link.get('href')
            _title = link.get('title')
            if re.search(r'next', _title, re.I):
                next_page = validate_url(urljoin(self.search_url, _href))

        return next_page


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
                            help='Output results (default lycos_results.txt)',
                            default='lycos_results.txt',
                            action='store')

        args = parser.parse_args()
        if not args.keyword:
            parser.print_help()
            sys.exit('[!] Keyword required')

        eng = Lycos()
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
