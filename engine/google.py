import re
import random
from logging import DEBUG
from urllib.parse import urljoin, urlencode
from utils.blacklist import is_blacklisted
from utils.helper import setup_logger, validate_url, random_agent
from libs.fetch import FetchRequest

logger = setup_logger(name='Google')


class Google:
    base_url = 'https://www.google.com'

    def __init__(self, debug=False):
        self.debug = debug
        self.fetch = FetchRequest()
        self.query = {}
        self.filtering = True
        self.user_agent = random_agent()

        if self.debug:
            logger.setLevel(DEBUG)

    def search(self, keyword):
        search_url = self.build_query(str(keyword))
        return self.search_run(search_url)

    def search_run(self, url):
        result = []
        if not url:
            return result

        duplicate_page = 0
        empty_page = 0
        headers = {'Referer': self.base_url, 'User-Agent': self.user_agent}
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

    def build_query(self, keyword):
        self.build_clients(keyword)
        search_url = urljoin(self.base_url, '/search')
        url = '%s?%s' % (search_url, urlencode(self.query))

        return url

    def build_clients(self, keyword):
        RAND_MS = random.randint(1552, 2568)
        client_brave = {
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36',
            'params': {
                'q': keyword,
                'oq': keyword,
                'aqs': 'chrome..69i57.%dj0j1' % RAND_MS,
                'sourceid': 'chrome',
                'ie': 'UTF-8',
            }
        }
        client_edge = {
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36 Edg/92.0.902.73',
            'params': {
                'q': keyword,
                'oq': keyword,
                'aqs': 'edge..69i57.%dj0j1' % RAND_MS,
                'sourceid': 'chrome',
                'ie': 'UTF-8',
            }
        }
        client_opera = {
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36 OPR/78.0.4093.147',
            'params': {
                'client': 'opera',
                'q': keyword,
                'sourceid': 'opera',
                'ie': 'UTF-8',
                'oe': 'UTF-8',
            }
        }
        client_firefox = {
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0',
            'params': {
                'client': 'firefox-b-d',
                'q': keyword,
            }
        }
        clients = [
            client_brave,
            client_edge,
            client_opera,
            client_firefox,
        ]
        client = random.choice(clients)
        self.query = client.get('params')
        self.user_agent = client.get('user_agent')

    @staticmethod
    def get_links(html):
        result = []
        if not html:
            return result

        patern_links = r'(?:<a[^>]+data-ved[\s=]+[^>]+>)'
        patern_href = r'href[\s=]+((?:")(.*?)(?:")|(?:\')(.*?)(?:\'))'
        patern_google_cache = r'(https?://)webcache\.googleusercontent\.[^\/]+/search\?q=cache:[^:]+:' \
                              r'(https?://)?(.+?)(\+?(&cd=[^&]+)(&hl=[^&]+)?(&ct=[^&]+)?(&gl=[^&]+)?.*)'

        matches = re.findall(patern_links, str(html), re.M | re.I)
        for match in matches:
            href = re.search(patern_href, match, re.I)

            if href and len(href.groups()) >= 3:
                try:
                    valid_url = validate_url(href.group(3) or href.group(2))
                    if valid_url:
                        cache_link = re.search(patern_google_cache, valid_url, re.I)
                        if cache_link:
                            result.append('%s%s' % (cache_link.group(1), cache_link.group(3)))
                        else:
                            result.append(valid_url)
                except IndexError:
                    pass

        if result:
            result = list(dict.fromkeys(result))

        return result

    def get_next_page(self, html):
        next_page = ''
        if not html:
            return next_page

        patern_next = r'(?:<a[^>]+id[\s=]+((?:")pnnext(?:")|(?:\')pnnext(?:\'))[^>]+>)'
        patern_href = r'href[\s=]+((?:")(.*?)(?:")|(?:\')(.*?)(?:\'))'

        matches = re.search(patern_next, str(html), re.M | re.I)
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
                            help='Output results (default google_results.txt)',
                            default='google_results.txt',
                            action='store')

        args = parser.parse_args()
        if not args.keyword:
            parser.print_help()
            sys.exit('[!] Keyword required')

        eng = Google()
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
