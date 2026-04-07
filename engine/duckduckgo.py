import re
from logging import DEBUG
from urllib.parse import urljoin, urlencode, urlparse, parse_qs
from utils.blacklist import is_blacklisted
from utils.helper import setup_logger, validate_url
from libs.html_parser import NativeHTMLParser
from libs.fetch import FetchRequest

logger = setup_logger(name='Duckduckgo')


class Duckduckgo:
    base_url = 'https://html.duckduckgo.com'
    search_url = 'https://html.duckduckgo.com/html/'

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
        self.query.update({'q': str(keyword)})
        search_url = '%s?%s' % ('/html/', urlencode(self.query))

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

        # DuckDuckGo HTML lite uses a.result__url for display links with href="/l/?uddg=..."
        # The actual target URL is embedded in the "uddg" query parameter
        links = _parser.root.findall('.//a[@class="result__url"]')

        for link in links:
            _href = link.get('href')
            if _href:
                # Extract actual URL from /l/?uddg=ENCODED_URL format
                parsed = urlparse(_href)
                params = parse_qs(parsed.query)
                if 'uddg' in params:
                    _href = params['uddg'][0]
                valid_url = validate_url(_href)
                if valid_url:
                    result.append(valid_url)

        # Fallback: also try result__a (title links) which also have /l/?uddg= format
        if not result:
            links = _parser.root.findall('.//a[@class="result__a"]')
            for link in links:
                _href = link.get('href')
                if _href:
                    parsed = urlparse(_href)
                    params = parse_qs(parsed.query)
                    if 'uddg' in params:
                        _href = params['uddg'][0]
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
        _parser.feed(str(html))
        _parser.close()

        if _parser.root is None:
            return next_page

        # DuckDuckGo HTML pagination: form with next button or link with class 'result-more'
        more_links = _parser.root.findall('.//a')
        for _link in more_links:
            _href = _link.get('href')
            _text = _link.text
            _class = _link.get('class', '')
            if not _href:
                continue

            # Look for "Next" link
            if _text and re.search(r'next|more', _text, re.I):
                if 'uddg' not in _href:  # Not a result link
                    next_page = validate_url(urljoin(self.base_url, _href))
                    if next_page:
                        break

            # Also check for data-suggestion-label or pagination forms
            if 'next' in _class.lower() or ('next' in _href.lower() and '/l/' not in _href):
                next_page = validate_url(urljoin(self.base_url, _href))
                if next_page:
                    break

        # Fallback: check for form with 's' (start) parameter
        if not next_page:
            forms = _parser.root.findall('.//form')
            for form in forms:
                action = form.get('action', '')
                if 'next' in action.lower() or ('s=' in action and '/html/' in action):
                    next_page = validate_url(urljoin(self.base_url, action))
                    if next_page:
                        break

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
                            help='Output results (default duckduckgo_results.txt)',
                            default='duckduckgo_results.txt',
                            action='store')

        args = parser.parse_args()
        if not args.keyword:
            parser.print_help()
            sys.exit('[!] Keyword required')

        eng = Duckduckgo()
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
