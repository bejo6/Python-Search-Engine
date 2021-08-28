import re
from urllib.parse import urljoin, urlencode
from blacklist import is_blacklisted
from helper import fetch_url, clean_url, setup_logger
from config import LOG_LEVEL


logger = setup_logger(name='Bing', level=LOG_LEVEL)


class Bing:
    base_url = 'https://www.bing.com'

    def __init__(self) -> None:
        self.query = {}
        self.filtering = True

    def search(self, keyword: str) -> list:
        self.query.update({'q': keyword})
        self.build_query()

        search_url = urljoin(self.base_url, '/search')
        url = f'{search_url}?{urlencode(self.query)}'

        return self.search_run(url)

    def search_run(self, url: str) -> list:
        result = []
        duplicate_page = 0
        referrer = self.base_url
        page = 1
        while True:
            logger.info(f'Page: {page}')
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
        return result

    def build_query(self):
        html = fetch_url(self.base_url, delete_cookie=True)
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

    def get_query_form_value(self, html: str = None) -> str:
        form_value = ''
        if not html:
            html = fetch_url(self.base_url, delete_cookie=True)

        patern_input = r'<[\s]?input\s+(.*?)[\s]?\/>'
        patern_input_form = r'name[\s=]+((?:")form(?:")|(?:\')form(?:\'))'
        patern_input_value = r'value[\s=]+(?:\'|")(.*?)(?:\'|")'

        inputs = re.findall(patern_input, html, re.I)
        for _input in inputs:
            if re.search(patern_input_form, _input, re.I):
                get_value = re.search(patern_input_value, _input, re.I)
                if get_value:
                    form_value = get_value.group(1)
                    break

        return form_value

    def get_query_cvid(self, html: str = None) -> str:
        cvid = ''
        if not html:
            html = fetch_url(self.base_url, delete_cookie=True)

        patern_ig = r'IG[\s:]+(?:")([A-F0-9]+)(?:")|(?:\')([A-F0-9]+)(?:\')'

        get_ig = re.search(patern_ig, html, re.I)
        if get_ig:
            for ig in get_ig.groups():
                if ig:
                    cvid = ig
                    break

        return cvid

    @staticmethod
    def get_links(html: str = None) -> list:
        result = []
        if not html:
            return result

        patern_links = r'<(\s+)?(li|div)\s+class[\s=]+((?:")b_algo(?:")|(?:\')b_algo(?:\'))(\s+)?>(\s+)?<(\s+)?(h2|p)(\s+)?>(\s+)?<(\s+)?a\s+(.*?)>'
        patern_href = r'href[\s=]+((?:")(.*?)(?:")|(?:\')(.*?)(?:\'))'

        matches = re.findall(patern_links, html, re.M | re.I)
        for match in matches:
            href = re.search(patern_href, match[-1], re.I)
            if href and len(href.groups()) >= 3:
                link = clean_url(href.group(3) or href.group(2))
                if link:
                    result.append(link)

        if result:
            result = list(dict.fromkeys(result))

        return result

    def get_next_page(self, html: str = None) -> str:
        next_page = ''
        if not html:
            return next_page

        patern_sbpagn = r'(?:<a[^>]+(sb_pagN(_bp)?)+[^>]+>)'
        patern_href = r'href[\s=]+((?:")(.*?)(?:")|(?:\')(.*?)(?:\'))'

        matches = re.search(patern_sbpagn, html, re.M | re.I)
        if matches:
            href = re.search(patern_href, matches.group(0), re.I)

            if href and len(href.groups()) >= 3:
                path = href.group(3) or href.group(2)
                next_page = clean_url(urljoin(self.base_url, path))

        return next_page
