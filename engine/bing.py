import re
from logging import DEBUG
from urllib.parse import urljoin, urlencode
from utils.blacklist import is_blacklisted
from utils.helper import setup_logger, validate_url
from libs.fetch import FetchRequest

logger = setup_logger(name='Bing')


class Bing:
    base_url = 'https://www.bing.com'

    def __init__(self, debug=False):
        self.debug = debug
        self.fetch = FetchRequest()
        self.query = {}
        self.filtering = True

        if self.debug:
            logger.setLevel(DEBUG)

    def search(self, keyword: str) -> list:
        self.query.update({'q': keyword})
        self.build_query()

        search_url = urljoin(self.base_url, '/search')
        url = '%s?%s' % (search_url, urlencode(self.query))

        return self.search_run(url)

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

    def build_query(self):
        html = self.fetch.get(self.base_url)

        if html:
            self.query.update({'sp': -1})
            self.query.update({'qs': 'n'})
            self.query.update({'sk': ''})

            form_value = self.get_query_form_value(html)
            if form_value:
                self.query.update({'form': form_value})

            cvid = self.get_query_cvid(html)
            if cvid:
                self.query.update({'cvid': cvid})

    def get_query_form_value(self, html=None):
        form_value = ''
        if not html:
            html = self.fetch.get(self.base_url)

        patern_input = r'<[\s]?input\s+(.*?)[\s]?\/>'
        patern_input_form = r'name[\s=]+((?:")form(?:")|(?:\')form(?:\'))'
        patern_input_value = r'value[\s=]+(?:\'|")(.*?)(?:\'|")'

        inputs = re.findall(patern_input, str(html), re.I)
        for _input in inputs:
            if re.search(patern_input_form, _input, re.I):
                get_value = re.search(patern_input_value, _input, re.I)
                if get_value:
                    form_value = get_value.group(1)
                    break

        return form_value

    def get_query_cvid(self, html=None):
        cvid = ''
        if not html:
            html = self.fetch.get(self.base_url)

        patern_ig = r'IG[\s:]+(?:")([A-F0-9]+)(?:")|(?:\')([A-F0-9]+)(?:\')'

        get_ig = re.search(patern_ig, str(html), re.I)
        if get_ig:
            for ig in get_ig.groups():
                if ig:
                    cvid = ig
                    break

        return cvid

    @staticmethod
    def get_links(html):
        result = []
        if not html:
            return result

        patern_links = r'<(\s+)?(li|div)\s+class[\s=]+((?:")b_algo(?:")|(?:\')b_algo(?:\'))(\s+)?>(\s+)?<(\s+)?(h2|p)(\s+)?>(\s+)?<(\s+)?a\s+(.*?)>'
        patern_href = r'href[\s=]+((?:")(.*?)(?:")|(?:\')(.*?)(?:\'))'

        matches = re.findall(patern_links, str(html), re.M | re.I)
        for match in matches:
            href = re.search(patern_href, match[-1], re.I)
            if href and len(href.groups()) >= 3:
                valid_url = validate_url(href.group(3) or href.group(2))
                if valid_url:
                    result.append(valid_url)

        if result:
            result = list(dict.fromkeys(result))

        return result

    def get_next_page(self, html=None):
        next_page = ''
        if not html:
            return next_page

        patern_sbpagn = r'(?:<a[^>]+(sb_pagN(_bp)?)+[^>]+>)'
        patern_href = r'href[\s=]+((?:")(.*?)(?:")|(?:\')(.*?)(?:\'))'

        matches = re.search(patern_sbpagn, str(html), re.M | re.I)
        if matches:
            href = re.search(patern_href, matches.group(0), re.I)

            if href and len(href.groups()) >= 3:
                path = href.group(3) or href.group(2)
                next_page = validate_url(urljoin(self.base_url, path))

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
                            help='Output results (default bing_results.txt)',
                            default='bing_results.txt',
                            action='store')

        args = parser.parse_args()
        if not args.keyword:
            parser.print_help()
            sys.exit('[!] Keyword required')

        eng = Bing()
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
