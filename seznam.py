import re
from urllib.parse import urljoin, urlencode
from helper import fetch_url, clean_url, is_blacklisted, valid_url, setup_logger
from html_parser import NativeHTMLParser
from config import LOG_LEVEL


logger = setup_logger(name='Seznam', level=LOG_LEVEL)


class Seznam:
    base_url = 'https://www.seznam.cz'
    search_url = 'https://search.seznam.cz'

    def __init__(self) -> None:
        self.query = {}
        self.user_agent = None
        self.filtering = True

    def search(self, keyword: str):
        self.query.update({'q': keyword})
        search_url = self.build_query()
        if search_url:
            search_url = urljoin(self.search_url, search_url)

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
                headers.update({'Referer': url})
                url = next_page
            else:
                break
            page += 1

        result = list(dict.fromkeys(result))
        return result

    def build_query(self, html: str = None) -> str:
        search_url = ''
        if not html:
            html = fetch_url(self.base_url, delete_cookie=True)

        _parser = NativeHTMLParser()
        root = _parser.feed(html)
        _parser.close()
        form_search = root.find('.//form[@class="sticky-header-search__form"]')

        if form_search:
            search_url = form_search.get('action')
            inputs = form_search.findall('.//input[@type="hidden"]')

            for inp in inputs:
                _name = inp.get('name')
                _value = inp.get('value')
                if not _name:
                    continue

                if _name != 'q':
                    self.query.update({_name: _value or ''})

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

        search_result = root.find('.//div[@data-dot="results"]')
        if not search_result:
            return result

        links = search_result.findall('.//a[@data-l-id]')

        for link in links:
            _href = link.get('href')
            url = valid_url(_href)
            if url:
                result.append(url)

        if result:
            result = list(dict.fromkeys(result))

        return result

    def get_next_page(self, html: str = None) -> str:
        next_page = ''
        if not html:
            return next_page

        _parser = NativeHTMLParser()
        root = _parser.feed(html)
        _parser.close()

        page_items = root.find('.//ul[@id="paging"]')
        if not page_items:
            return next_page

        list_element = page_items.findall('li')
        for li in list_element:
            _class = li.get('class')
            if _class and re.search(r'Paging-item--next', _class, re.I):
                _href = li.find('a').get('href')
                next_page = clean_url(urljoin(self.search_url, _href))
                if next_page:
                    break

        return next_page
