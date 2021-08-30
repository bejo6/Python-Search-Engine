import re
from urllib.parse import urljoin, urlencode
from blacklist import is_blacklisted
from helper import fetch_url, clean_url, valid_url, setup_logger
from html_parser import NativeHTMLParser
from config import LOG_LEVEL


logger = setup_logger(name='Gigablast', level=LOG_LEVEL)


class Gigablast:
    base_url = 'https://www.gigablast.com'

    def __init__(self) -> None:
        self.query = {}
        self.user_agent = None
        self.referer = self.base_url
        self.filtering = True

    def search(self, keyword: str):
        self.query.update({'q': keyword})
        search_url = self.build_query(keyword=keyword)
        if search_url:
            search_url = urljoin(self.base_url, search_url)

        return self.search_run(search_url)

    def search_run(self, url: str) -> list:
        result = []
        if not url:
            return result

        duplicate_page = 0
        headers = {'Referer': self.base_url}
        page = 1
        while True:
            logger.info(f'Page: {page}')
            html = fetch_url(url, headers=headers)
            html_link = self.get_html_link(html, url)
            links = self.get_links(html_link)

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

            next_page = self.get_next_page(html_link)
            if next_page:
                headers.update({'Referer': url})
                url = next_page
            else:
                break
            page += 1

        result = list(dict.fromkeys(result))
        logger.info(f'Total links: {len(result)}')

        return result

    def build_query(self, keyword: str, html: str = None) -> str:
        search_url = ''
        if not html:
            html = fetch_url(self.base_url, delete_cookie=True)

        _parser = NativeHTMLParser()
        root = _parser.feed(html)
        _parser.close()

        form_search = root.find('.//form[@id="mainform"]')

        if form_search:
            action = form_search.get('action')
            if action:
                search_url = urljoin(self.base_url, action)

            inputs = form_search.findall('.//input')
            for inp in inputs:
                _name = inp.get('name')
                _value = inp.get('value')

                if not _name:
                    continue

                if _name != 'q':
                    self.query.update({_name: _value or ''})
                else:
                    self.query.update({_name: keyword})

        if search_url:
            search_url = f'{search_url}?{urlencode(self.query)}'

        return search_url

    @staticmethod
    def get_links(html: str = None) -> list:
        result = []
        if not html:
            return result

        _parser = NativeHTMLParser()
        root = _parser.feed(html)
        _parser.close()

        link_ads = root.findall('.//font[@size]')
        for ads in link_ads:
            link = ads.find('.//a')
            if link is not None:
                _href = link.get('href')
                url = valid_url(_href)
                if url:
                    result.append(url)

        table_results = root.findall('.//table[@class="result"]')
        for res in table_results:
            link = res.find('.//a[@class="title"]')
            if link is not None:
                _href = link.get('href')
                url = valid_url(_href)
                if url:
                    result.append(url)

        if result:
            result = list(dict.fromkeys(result))

        return result

    def get_html_link(self, html: str = None, referer: str = None) -> str:
        search_link = ''
        patern_uxrl = r'uxrl[\s=]+(uxrl\+)?((?:")(.*?)(?:")|(?:\')(.*?)(?:\'));'
        if html is not None:
            uxrl = re.findall(patern_uxrl, html, re.I)
            if uxrl:
                search_path = ''
                for u in uxrl:
                    search_path += u[-1]

                if search_path:
                    search_link = urljoin(self.base_url, search_path)

        if search_link:
            html = fetch_url(search_link, headers={'Referer': referer})
        return html

    def get_next_page(self, html: str = None) -> str:
        next_page = ''
        if not html:
            return next_page

        _parser = NativeHTMLParser()
        root = _parser.feed(html)
        _parser.close()

        list_links = root.findall('.//center//a')

        for link in list_links:
            if link is not None:
                _href = link.get('href')
                _font = link.find('.//font[@size]')

                if _font is None or _href is None:
                    continue

                _text = _font.text
                if re.search(r'next[\s\d]+results', _text, re.I):
                    next_page = clean_url(urljoin(self.base_url, _href))
                    if next_page:
                        break

        return next_page
