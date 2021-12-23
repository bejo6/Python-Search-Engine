import re
from urllib.parse import urljoin, urlencode
from blacklist import is_blacklisted
from helper import fetch_url, setup_logger, validate_url
from config import LOG_LEVEL


logger = setup_logger(name='Ask', level=LOG_LEVEL)


class Ask:
    base_url = 'https://www.ask.com'

    def __init__(self):
        self.query = {}
        self.user_agent = None
        self.filtering = True

    def search(self, keyword):
        search_url = self.build_query(str(keyword))
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
            logger.info('Page: %d %s' % (page, url))
            html = fetch_url(url, headers=headers)
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
                            continue

                    if link not in result:
                        duplicate = False
                        logger.info(link)
                        result.append(link)
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
        search_url = urljoin(self.base_url, '/web')
        self.query.update({
            'q': str(keyword),
            'ad': 'dirN',
            'qo': 'homepageSearchBox',
        })
        url = '%s?%s' % (search_url, urlencode(self.query))

        return url

    @staticmethod
    def get_links(html):
        result = []
        if not html:
            return result

        patern_links = r'(?:<a[^>]+result-link[^>]+>)'
        patern_href = r'href[\s=]+((?:")(.*?)(?:")|(?:\')(.*?)(?:\'))'
        patern_utm = r'\?utm_content.+$'

        matches = re.findall(patern_links, str(html), re.M | re.I)
        for match in matches:
            href = re.search(patern_href, match, re.I)

            if href and len(href.groups()) >= 3:
                try:
                    valid_url = validate_url(href.group(3) or href.group(2))
                    valid_url = re.sub(patern_utm, '', valid_url)
                    if valid_url:
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

        patern_next = r'(?:<li[^>]+PartialWebPagination-next[^>]+>)(\s+)?(?:<a[^>]+>)'
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
                            help='Output results (default ask_results.txt)',
                            default='ask_results.txt',
                            action='store')

        args = parser.parse_args()
        if not args.keyword:
            parser.print_help()
            sys.exit('[!] Keyword required')

        eng = Ask()
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
