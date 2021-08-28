import re
from urllib.parse import urljoin, urlencode
from blacklist import is_blacklisted
from helper import fetch_url, clean_url, valid_url, setup_logger
from html_parser import NativeHTMLParser
from config import LOG_LEVEL


logger = setup_logger(name='Mojeek', level=LOG_LEVEL)


class Mojeek:
    base_url = 'https://www.mojeek.com'

    def __init__(self) -> None:
        self.query = {}
        self.user_agent = None
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
        logger.info(f'Total links: {len(result)}')

        return result

    def build_query(self, keyword: str, html: str = None) -> str:
        if not html:
            html = fetch_url(self.base_url, delete_cookie=True)

        _parser = NativeHTMLParser()
        root = _parser.feed(html)
        _parser.close()

        form_search = root.find('.//form[@action="/search"]')

        if form_search:
            action = form_search.get('action')
            search_url = urljoin(self.base_url, action)
        else:
            search_url = urljoin(self.base_url, '/search')

        if search_url:
            self.query.update({'q': keyword})
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

        links = root.findall('.//a[@class="ob"]')

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

        pagination = root.find('.//div[@class="pagination"]')
        if not pagination:
            return next_page

        list_pagination = pagination.findall('.//li')
        for li in list_pagination:
            _link = li.find('.//a')
            if _link is not None:
                _href = _link.get('href')
                _text = _link.text
                if _text is None or _href is None:
                    continue

                if re.search(r'next', _text, re.I):
                    next_page = clean_url(urljoin(self.base_url, _href))
                    if next_page:
                        break

        return next_page
