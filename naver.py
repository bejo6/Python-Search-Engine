from urllib.parse import urljoin, urlencode
from blacklist import is_blacklisted
from helper import fetch_url, setup_logger, validate_url
from html_parser import NativeHTMLParser
from config import LOG_LEVEL


logger = setup_logger(name='Naver', level=LOG_LEVEL)


class Naver:
    base_url = 'https://www.naver.com'
    search_url = 'https://search.naver.com/search.naver'

    def __init__(self):
        self.query = {}
        self.user_agent = None
        self.filtering = True

    def search(self, keyword):
        search_url = self.build_query(keyword=str(keyword))
        if search_url:
            search_url = urljoin(self.search_url, search_url)

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

        _parser = NativeHTMLParser()
        _parser.feed(str(html))
        _parser.close()

        if _parser.root is None:
            return search_url

        form_search = _parser.root.find('.//form[@id="sform"]')

        if form_search:
            search_url = form_search.get('action')

            self.query.update({'where': 'web'})

            inputs = form_search.findall('.//input[@type="hidden"]')

            for inp in inputs:
                _name = inp.get('name')
                _value = inp.get('value')
                _disabled = inp.get('disabled')
                if not _name:
                    continue

                if _disabled:
                    continue

                if _name != 'query':
                    self.query.update({_name: _value or ''})

        if search_url:
            self.query.update({'query': keyword})
            search_url = '%s?%s' % (search_url, urlencode(self.query))

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

        search_result = _parser.root.find('.//ul[@class="lst_total"]')
        if not search_result:
            return result

        links = search_result.findall('li//a[@class="link_tit"]')

        for link in links:
            _href = link.get('href')
            valid_url = validate_url(_href)
            if valid_url:
                result.append(valid_url)

        if result:
            result = list(dict.fromkeys(result))

        return result

    def get_next_page(self, html):
        next_page = ''
        if not html:
            return next_page

        _parser = NativeHTMLParser()
        _parser.feed(html)
        _parser.close()

        if _parser.root is None:
            return next_page

        page_items = _parser.root.find('.//div[@class="sc_page"]')
        if not page_items:
            return next_page

        btn_next = page_items.find('a[@class="btn_next"]')
        _href = btn_next.get('href')
        if _href:
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
                            help='Output results (default naver_results.txt)',
                            default='naver_results.txt',
                            action='store')

        args = parser.parse_args()
        if not args.keyword:
            parser.print_help()
            sys.exit('[!] Keyword required')

        eng = Naver()
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
