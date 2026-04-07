import re
from logging import DEBUG
from urllib.parse import urljoin, urlencode, urlparse, parse_qs
from utils.blacklist import is_blacklisted
from utils.helper import setup_logger, validate_url
from libs.html_parser import NativeHTMLParser
from libs.fetch import FetchRequest

logger = setup_logger(name='Ecosia')


class Ecosia:
    base_url = 'https://www.ecosia.org'
    search_url = 'https://www.ecosia.org/search'

    def __init__(self, debug=False):
        self.debug = debug
        self.fetch = FetchRequest()
        self.query = {}
        self.filtering = True

        if self.debug:
            logger.setLevel(DEBUG)

    def search(self, keyword):
        self.query.update({'q': str(keyword), 'method': 'index'})
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
        search_url = ''
        self.query.update({'q': str(keyword), 'method': 'index'})
        search_url = '%s?%s' % ('/search', urlencode(self.query))

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

        # Ecosia result links: class="result__link" or class="_2sFQ_"
        links = _parser.root.findall('.//a[@class="result__link"]')
        for link in links:
            _href = link.get('href')
            if _href and _href.startswith('/search/redirect?'):
                # Ecosia uses redirect URLs, extract target
                parsed = urlparse(_href)
                params = parse_qs(parsed.query)
                if 'url' in params:
                    _href = params['url'][0]
            valid_url = validate_url(_href)
            if valid_url:
                result.append(valid_url)

        # Fallback: try generic result link patterns
        if not result:
            all_links = _parser.root.findall('.//a')
            for link in all_links:
                _class = link.get('class', '')
                _href = link.get('href')
                if not _href:
                    continue

                # Look for result-related classes
                if any(x in _class for x in ['result', 'mainline', 'title', 'heading']):
                    # Skip internal ecosia links
                    if _href.startswith('http') and 'ecosia.org' not in _href:
                        valid_url = validate_url(_href)
                        if valid_url:
                            result.append(valid_url)
                    elif _href.startswith('/search/redirect'):
                        parsed = urlparse(_href)
                        params = parse_qs(parsed.query)
                        if 'url' in params:
                            valid_url = validate_url(params['url'][0])
                            if valid_url:
                                result.append(valid_url)

        # Final fallback: extract from __NEXT_DATA__ or embedded JSON
        if not result:
            result.extend(Ecosia._extract_from_json(html))

        if result:
            result = list(dict.fromkeys(result))

        return result

    @staticmethod
    def _extract_from_json(html):
        """Extract result URLs from Ecosia embedded JSON data."""
        links = []
        try:
            # Try to find result URLs in embedded JSON/script data
            for m in re.finditer(r'"url"\s*:\s*"(https?://[^"]+)"', html):
                url = m.group(1).replace('\\u0026', '&').replace('\\/', '/')
                valid_url = validate_url(url)
                if valid_url and 'ecosia.org' not in valid_url:
                    links.append(valid_url)
        except Exception:
            pass
        return links

    def get_next_page(self, html):
        next_page = ''
        if not html:
            return next_page

        _parser = NativeHTMLParser()
        _parser.feed(str(html))
        _parser.close()

        if _parser.root is None:
            return next_page

        # Look for pagination / "Next" button
        pagination_links = _parser.root.findall('.//a')
        for _link in pagination_links:
            _href = _link.get('href')
            _text = _link.text
            if not _href:
                continue

            if _text and re.search(r'next|more|further', _text, re.I):
                next_page = validate_url(urljoin(self.base_url, _href))
                if next_page:
                    break

        # Fallback: check for 'next' or 'page' parameter in embedded data
        if not next_page:
            match = re.search(r'"page"\s*:\s*(\d+)', html)
            if match:
                current_page = int(match.group(1))
                next_page_num = current_page + 1
                # Reconstruct URL with next page
                parsed = urlparse('https://www.ecosia.org/search')
                params = parse_qs(parsed.query)
                params.update(self.query)
                params['p'] = str(next_page_num)
                next_page = '%s?%s' % ('/search', urlencode(params))
                if next_page:
                    next_page = validate_url(urljoin(self.base_url, next_page))

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
                            help='Output results (default ecosia_results.txt)',
                            default='ecosia_results.txt',
                            action='store')

        args = parser.parse_args()
        if not args.keyword:
            parser.print_help()
            sys.exit('[!] Keyword required')

        eng = Ecosia()
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
