import re
import json
import base64
from logging import DEBUG
from urllib.parse import urljoin, urlencode, urlparse, parse_qs
from utils.blacklist import is_blacklisted
from utils.helper import setup_logger, validate_url
from libs.html_parser import NativeHTMLParser
from libs.fetch import FetchRequest

logger = setup_logger(name='Startpage')


class Startpage:
    base_url = 'https://www.startpage.com'
    search_url = 'https://www.startpage.com/do/search'

    def __init__(self, debug=False):
        self.debug = debug
        self.fetch = FetchRequest()
        self.query = {}
        self.filtering = True

        if self.debug:
            logger.setLevel(DEBUG)

    def search(self, keyword):
        self.query.update({'query': str(keyword)})
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
        self.query.update({'query': str(keyword), 'language': 'english'})
        search_url = '%s?%s' % ('/do/search', urlencode(self.query))

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

        # Primary: class="result-title result-link" on <a> tags
        links = _parser.root.findall('.//a[@class="result-title result-link css-1bggj8v"]')

        for link in links:
            _href = link.get('href')
            valid_url = validate_url(_href)
            if valid_url:
                result.append(valid_url)

        # Fallback: find all result-title links with generic selector
        if not result:
            links = _parser.root.findall('.//a')
            for link in links:
                _class = link.get('class', '')
                _href = link.get('href')
                if 'result-link' in _class or 'result-title' in _class:
                    valid_url = validate_url(_href)
                    if valid_url:
                        result.append(valid_url)

        # Also extract from wgl-site-title and wgl-display-url classes (display URL links)
        if not result:
            display_links = _parser.root.findall('.//a[@class="wgl-site-title css-1d1wvpc"]')
            for link in display_links:
                _href = link.get('href')
                valid_url = validate_url(_href)
                if valid_url:
                    result.append(valid_url)

            display_links2 = _parser.root.findall('.//a[@class="wgl-display-url css-u4i8t0"]')
            for link in display_links2:
                _href = link.get('href')
                valid_url = validate_url(_href)
                if valid_url:
                    result.append(valid_url)

        # Final fallback: try to parse embedded JSON data containing clickUrl fields
        if not result:
            result.extend(Startpage._extract_from_json(html))

        if result:
            result = list(dict.fromkeys(result))

        return result

    @staticmethod
    def _extract_from_json(html):
        """Extract clickUrl from embedded React data JSON in Startpage HTML."""
        links = []
        try:
            # Startpage embeds result data in a React.createElement call
            match = re.search(r'React\.createElement\(UIStartpage\.AppSerpWeb,\s*(\{.*?"web-google".*?\})\s*\)', html, re.DOTALL)
            if not match:
                # Try simpler pattern for the pagination block
                match = re.search(r'React\.createElement\(UIStartpage\.AppSerpWeb,\s*(\{.*\})\)\s*\)', html, re.DOTALL)

            if match:
                json_str = match.group(1)
                # Find all "clickUrl":"..." patterns
                for m in re.finditer(r'"clickUrl"\s*:\s*"([^"]+)"', json_str):
                    url = m.group(1)
                    valid_url = validate_url(url)
                    if valid_url and not valid_url.startswith('/'):
                        links.append(valid_url)

                # If no clickUrl found, try "url" in result arrays
                if not links:
                    for m in re.finditer(r'"url"\s*:\s*"([^"]+)"', json_str):
                        url = m.group(1)
                        valid_url = validate_url(url)
                        if valid_url:
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

        # Check pagination links: look for "Next" text in pagination area
        pagination_links = _parser.root.findall('.//a')
        for _link in pagination_links:
            _href = _link.get('href')
            _text = _link.text
            if not _href:
                # Check for text inside span
                spans = _link.findall('.//span')
                for span in spans:
                    span_text = span.text
                    if span_text and re.search(r'next', span_text, re.I):
                        # Look for Next URL from embedded JSON
                        next_page = self._get_next_from_json(html)
                        if next_page:
                            return next_page

            if _text and re.search(r'next', _text, re.I):
                next_page = validate_url(urljoin(self.base_url, _href))
                if next_page:
                    break

        # Fallback: extract next page URL from embedded JSON pagination data
        if not next_page:
            next_page = self._get_next_from_json(html)

        return next_page

    @staticmethod
    def _get_next_from_json(html):
        """Extract next page URL from Startpage JSON data."""
        try:
            # Find pagination Next URL in embedded JSON
            match = re.search(r'"Next".*?"url"\s*:\s*"([^"]+)"', html)
            if match:
                next_url = match.group(1)
                return validate_url(urljoin('https://www.startpage.com', next_url))

            # Alternative: find all page URLs and take the highest numbered one
            pages = re.findall(r'"/serp\?q=([^&]*)&page=(\d+)[^"]*"', html)
            if pages:
                max_page = max(pages, key=lambda x: int(x[1]))
                return validate_url('https://www.startpage.com/serp?q=%s&page=%s' % (max_page[0], int(max_page[1]) + 1))
        except Exception:
            pass

        return ''


if __name__ == '__main__':
    import sys
    import argparse
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
                            help='Output results (default startpage_results.txt)',
                            default='startpage_results.txt',
                            action='store')

        args = parser.parse_args()
        if not args.keyword:
            parser.print_help()
            sys.exit('[!] Keyword required')

        eng = Startpage()
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
