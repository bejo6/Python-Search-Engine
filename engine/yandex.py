import re
from logging import DEBUG
from urllib.parse import urljoin, urlencode
from utils.blacklist import is_blacklisted
from utils.helper import setup_logger, validate_url
from libs.html_parser import NativeHTMLParser
from libs.fetch import FetchRequest


logger = setup_logger(name='Yandex')


class Yandex:
    base_url = 'https://yandex.com'

    def __init__(self, debug=False):
        self.debug = debug
        self.fetch = FetchRequest()
        self.query = {}
        self.filtering = True

        if self.debug:
            logger.setLevel(DEBUG)

    def search(self, keyword):
        search_url = self.build_query(keyword=str(keyword))
        if search_url:
            search_url = urljoin(self.base_url, search_url)

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
            if next_page:
                headers.update({'Referer': url})
                url = next_page
            else:
                break
            page += 1

        result = list(dict.fromkeys(result))
        logger.info('Total links: %d' % len(result))

        return result

    def build_query(self, keyword, html=None):
        # Yandex search URL can be built directly without parsing homepage
        self.query.update({'text': str(keyword), 'lr': '114911'})
        search_url = '/search/?%s' % urlencode(self.query)
        return search_url

    @staticmethod
    def get_links(html):
        result = []
        if not html:
            return result

        _parser = NativeHTMLParser()
        _parser.feed(html)
        _parser.close()

        if _parser.root is None:
            return result

        patern_captcha = r'/(?:support|checkcaptcha)'

        if re.search(patern_captcha, html, re.I):
            logger.error('Error captcha')
            return result

        # Try multiple patterns for search results
        # Pattern 1: ul#search-result with li.serp-item (legacy)
        search_result = _parser.root.find('.//ul[@id="search-result"]')
        if search_result:
            links = search_result.findall('li[@class="serp-item"]//h2/a')
        else:
            # Pattern 2: Try organic results with class-based
            search_result = _parser.root.find('.//div[@class="main__content"]')
            if not search_result:
                search_result = _parser.root.find('.//div[@id="search-result"]')
            if search_result:
                links = search_result.findall('.//a[contains(@class, "organic__url")]')
            else:
                # Pattern 3: Fallback - find links with organic URL class
                links = _parser.root.findall('.//a[contains(@class, "OrganicTitle-Link")]')
                if not links:
                    links = _parser.root.findall('.//a[contains(@class, "serp-item")]')

        for link in links:
            _class = link.get('class')
            _href = link.get('href')
            _data_event = link.get('data-event-required')
            if _data_event:
                continue

            if _class and re.search(r'organic__url', _class, re.I):
                valid_url = validate_url(_href)
                if valid_url:
                    result.append(valid_url)

        if result:
            result = list(dict.fromkeys(result))

        return result

    def get_next_page(self, html: str = None) -> str:
        next_page = ''
        if not html:
            return next_page

        patern_captcha = r'/(?:support|checkcaptcha)'

        if re.search(patern_captcha, html, re.I):
            logger.error('Error captcha')
            return next_page

        _parser = NativeHTMLParser()
        _parser.feed(html)
        _parser.close()

        if _parser.root is None:
            return next_page

        # Pattern 1: pager__items with pager__item_kind_next (legacy)
        page_items = _parser.root.find('.//div[@class="pager__items"]')
        if page_items:
            page_links = page_items.findall('a')
            for link in page_links:
                _class = link.get('class')
                _href = link.get('href')
                if _class and re.search(r'pager__item_kind_next', _class, re.I):
                    next_page = validate_url(urljoin(self.base_url, _href))
                    if next_page:
                        break

        # Pattern 2: Try data-arrow attribute on next link
        if not next_page:
            next_link = _parser.root.find('.//a[@data-event-required][@data-counter]')
            if next_link and next_link.get('href'):
                next_page = validate_url(urljoin(self.base_url, next_link.get('href')))

        if not next_page:
            logger.debug('No next page found')

        return next_page


if __name__ == '__main__':
    import sys
    import argparse
    import json
    try:
        parser = argparse.ArgumentParser(usage='%(prog)s [options]')
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
                            help='Output results (default yandex_results.txt)',
                            default='yandex_results.txt',
                            action='store')

        args = parser.parse_args()
        if not args.keyword:
            parser.print_help()
            sys.exit('[!] Keyword required')

        eng = Yandex()
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
