import re
from logging import DEBUG
from urllib.parse import urljoin, urlencode
from utils.blacklist import is_blacklisted
from utils.helper import setup_logger, validate_url
from libs.html_parser import NativeHTMLParser
from libs.fetch import FetchRequest

logger = setup_logger(name='Gigablast')


class Gigablast:
    base_url = 'https://www.gigablast.com'

    def __init__(self, debug=False):
        self.debug = debug
        self.fetch = FetchRequest()
        self.query = {}
        self.filtering = True

        if self.debug:
            logger.setLevel(DEBUG)

    def search(self, keyword):
        self.query.update({'q': str(keyword)})
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
            html_link = self.get_html_link(html, url)
            links = self.get_links(html_link)

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

            next_page = self.get_next_page(html_link)
            if next_page and next_page != url:
                headers.update({'Referer': url})
                url = next_page
            else:
                break
            page += 1

        result = list(dict.fromkeys(result))
        logger.info('Total links: %d' % len(result))

        return result

    def build_query(self, keyword):
        search_url = ''
        html = self.fetch.get(self.base_url)

        _parser = NativeHTMLParser()
        _parser.feed(str(html))
        _parser.close()

        if _parser.root is None:
            return search_url

        query = dict(self.query)

        mainform = _parser.root.find('.//form[@action="search"]')
        if mainform:
            action = mainform.get('action')
            if action:
                search_url = urljoin(self.base_url, action)

            inputs = mainform.findall('.//input[@type="hidden"]')
            for inp in inputs:
                _name = inp.get('name')
                _value = inp.get('value')

                if not _name:
                    continue

                if _name != 'q':
                    query.update({_name: _value or ''})
                else:
                    query.update({_name: keyword})

        if search_url:
            search_url = '%s?%s' % (search_url, urlencode(query))

        return search_url

    def get_links(self, html=None):
        result = []
        if not html:
            return result

        html = self.get_html_link(html)

        _parser = NativeHTMLParser()
        _parser.feed(str(html))
        _parser.close()

        if _parser.root is None:
            return result

        links = _parser.root.findall('.//font//a')

        for link in links:
            if link is not None:
                _href = link.get('href')
                valid_url = validate_url(_href)
                if valid_url:
                    if not re.search(r'^(.*\.)?gigablast\.com', valid_url, re.I):
                        result.append(valid_url)

        if result:
            result = list(dict.fromkeys(result))

        return result

    def get_html_link(self, html=None, referer=None):
        search_link = ''
        patern_uxrl = r'uxrl[\s=]+(uxrl\+)?((?:")(.*?)(?:")|(?:\')(.*?)(?:\'));'
        if html is not None:
            uxrl = re.findall(patern_uxrl, str(html), re.I)
            if uxrl:
                search_path = ''
                for u in uxrl:
                    search_path += u[-1]

                if search_path:
                    search_link = urljoin(self.base_url, search_path)

        if search_link:
            html = self.fetch.get(search_link, headers={'Referer': referer})
        return html

    def get_next_page(self, html, recheck=False):
        next_page = ''
        if not html:
            return next_page

        _parser = NativeHTMLParser()
        _parser.feed(str(html))
        _parser.close()

        if _parser.root is None:
            return next_page

        div_box = _parser.root.find('.//div[@id="box"]')
        if div_box:
            center_tags = div_box.findall('.//center/a')

            if center_tags:
                start_page = 0
                next_path = ''
                for clink in center_tags:
                    next_href = clink.get('href')
                    m_start_page = re.match(r'.*&?s=(\d+)', next_href, re.I)
                    if m_start_page:
                        spage = int(m_start_page.group(1))
                        if spage >= start_page:
                            start_page = spage
                            next_path = next_href

                if next_path:
                    next_page = validate_url(urljoin(self.base_url, next_path))

        else:
            if not recheck:
                html_link = self.get_html_link(html)
                return self.get_next_page(html_link, recheck=True)

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
                            help='Output results (default gigablast_results.txt)',
                            default='gigablast_results.txt',
                            action='store')

        args = parser.parse_args()
        if not args.keyword:
            parser.print_help()
            sys.exit('[!] Keyword required')

        eng = Gigablast()
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
