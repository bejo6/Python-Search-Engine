import re
from logging import DEBUG
from urllib.parse import urljoin, urlencode, unquote
from utils.blacklist import is_blacklisted
from utils.helper import setup_logger, validate_url
from libs.fetch import FetchRequest

logger = setup_logger(name='Yahoo')


class Yahoo:
    base_url = 'https://search.yahoo.com'

    def __init__(self, debug=False):
        self.debug = debug
        self.fetch = FetchRequest()
        self.query = {}
        self.filtering = True

        if self.debug:
            logger.setLevel(DEBUG)

    def search(self, keyword: str) -> list:
        self.query.update({'p': keyword})
        search_url = self.build_query()
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

    def build_query(self, html=None):
        patern_form = r'(?:<form[^>]+role[\s=]+((?:")search(?:")|(?:\')search(?:\'))[^>]+>)[\s\S]+<\/form>'
        patern_action = r'action[\s=]+((?:")(.*?)(?:")|(?:\')(.*?)(?:\'))'
        patern_input = r'(?:<input[^>]+/?>)'
        patern_name = r'name[\s=]+((?:")(.*?)(?:")|(?:\')(.*?)(?:\'))'
        patern_value = r'value[\s=]+((?:")(.*?)(?:")|(?:\')(.*?)(?:\'))'

        if not html:
            html = self.fetch.get(self.base_url)

        search_url = ''
        if html:
            get_form = re.search(patern_form, str(html), re.M | re.I)
            if get_form:
                form_str = get_form.group(0)
                action_val = re.search(patern_action, form_str, re.I)
                if action_val and len(action_val.groups()) >= 3:
                    search_url = action_val.group(3) or action_val.group(2)
                inputs = re.findall(patern_input, form_str, re.I)
                for _input in inputs:
                    name = None
                    value = None
                    get_name = re.search(patern_name, _input, re.I)
                    get_value = re.search(patern_value, _input, re.I)
                    if get_name and len(get_name.groups()) >= 3:
                        name = get_name.group(3) or get_name.group(2)
                    if get_value and len(get_value.groups()) >= 3:
                        value = get_value.group(3) or get_value.group(2)

                    if name and name != 'p':
                        self.query.update({name: value or ''})

        if search_url:
            search_url = '%s?%s' % (search_url, urlencode(self.query))

        return search_url

    @staticmethod
    def get_links(html):
        result = []
        if not html:
            return result

        patern_links = r'(?:<a[^>]+referrerpolicy[\s=]+[\'"]origin[\'"][^>]+>)'
        patern_href = r'href[\s=]+((?:")(.*?)(?:")|(?:\')(.*?)(?:\'))'
        patern_url = r'\/RU=(.*?)\/RK='

        matches = re.findall(patern_links, html, re.M | re.I)
        for match in matches:
            href = re.search(patern_href, match, re.I)

            if href and len(href.groups()) >= 3:
                temp_link = validate_url(href.group(3) or href.group(2))
                web_url = re.search(patern_url, temp_link, re.I)
                if web_url:
                    try:
                        link = validate_url(unquote(web_url.group(1)))
                        if link:
                            result.append(link)
                    except IndexError:
                        pass

        if result:
            result = list(dict.fromkeys(result))

        return result

    def get_next_page(self, html):
        next_page = ''
        if not html:
            return next_page

        patern_next = r'(?:<a[^>]+class[\s=]+((?:")next(?:")|(?:\')next(?:\'))[^>]+>)'
        patern_href = r'href[\s=]+((?:")(.*?)(?:")|(?:\')(.*?)(?:\'))'

        matches = re.search(patern_next, html, re.M | re.I)
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
                            help='Output results (default yahoo_results.txt)',
                            default='yahoo_results.txt',
                            action='store')

        args = parser.parse_args()
        if not args.keyword:
            parser.print_help()
            sys.exit('[!] Keyword required')

        eng = Yahoo()
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
