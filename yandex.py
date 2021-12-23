import re
from urllib.parse import urljoin, urlencode
from blacklist import is_blacklisted
from helper import fetch_url, setup_logger, validate_url
from html_parser import NativeHTMLParser
from config import LOG_LEVEL


logger = setup_logger(name='Yandex', level=LOG_LEVEL)


class Yandex:
    base_url = 'https://yandex.com'

    def __init__(self):
        self.query = {}
        self.user_agent = None
        self.filtering = True

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
        referrer = self.base_url
        page = 1
        while True:
            logger.info('Page: %d' % page)
            html = fetch_url(url, headers={'Referer': referrer})
            links = self.get_links(html)

            if links:
                duplicate = True
                for link in links:
                    if self.filtering:
                        if is_blacklisted(link):
                            continue

                    if link not in result:
                        duplicate = False
                        logger.info(link)
                        result.append(link)
                if duplicate:
                    duplicate_page += 1

            if duplicate_page >= 3:
                break

            next_page = self.get_next_page(html)
            if next_page:
                referrer = url
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
            html = fetch_url(self.base_url, delete_cookie=True)

        patern_captcha = r'\/support\/smart-captcha|\/checkcaptcha'

        if re.search(patern_captcha, html, re.I):
            logger.error('Error captcha')
            return search_url

        _parser = NativeHTMLParser()
        _parser.feed(html)
        _parser.close()

        if _parser.root is None:
            return search_url

        form_search = _parser.root.find('.//form[@role="search"]')

        if form_search:
            search_url = form_search.get('action')
            inputs = form_search.findall('.//input[@type="hidden"]')
            for inp in inputs:
                _name = inp.get('name')
                _value = inp.get('value')
                if not _name:
                    continue

                if _name != 'text':
                    self.query.update({_name: _value or ''})

        if search_url:
            self.query.update({'text': str(keyword)})
            search_url = f'{search_url}?{urlencode(self.query)}'

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

        patern_captcha = r'\/support\/smart-captcha|\/checkcaptcha'

        if re.search(patern_captcha, html, re.I):
            logger.error('Error captcha')
            return result

        search_result = _parser.root.find('.//ul[@id="search-result"]')
        if not search_result:
            return result

        links = search_result.findall('li[@class="serp-item"]//h2/a')

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

        patern_captcha = r'\/support\/smart-captcha|\/checkcaptcha'

        if re.search(patern_captcha, html, re.I):
            logger.error('Error captcha')
            return next_page

        _parser = NativeHTMLParser()
        _parser.feed(html)
        _parser.close()

        if _parser.root is None:
            return next_page

        page_items = _parser.root.find('.//div[@class="pager__items"]')
        if not page_items:
            return next_page

        page_links = page_items.findall('a')
        for link in page_links:
            _class = link.get('class')
            _href = link.get('href')
            if _class and re.search(r'pager__item_kind_next', _class, re.I):
                next_page = validate_url(urljoin(self.base_url, _href))
                if next_page:
                    break

        if not next_page:
            logger.debug(page_items)
            logger.debug(page_links)

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
