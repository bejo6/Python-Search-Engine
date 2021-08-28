import re
from urllib.parse import urljoin, urlencode, urlparse, parse_qs
from blacklist import is_blacklisted
from helper import fetch_url, valid_url, setup_logger
from html_parser import NativeHTMLParser
from config import LOG_LEVEL


logger = setup_logger(name='Lycos', level=LOG_LEVEL)


class Lycos:
    base_url = 'https://www.lycos.com'
    search_url = 'https://search.lycos.com/web'

    def __init__(self) -> None:
        self.query = {}
        self.user_agent = None
        self.filtering = True

    def search(self, keyword: str):
        search_url = self.build_query(keyword=keyword)
        return self.search_run(search_url)

    def search_run(self, url: str) -> list:
        result = []
        if not url:
            return result

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
        logger.info(f'Total links: {len(result)}')

        return result

    def build_query(self, keyword: str, html: str = None) -> str:
        search_url = ''
        if not html:
            html = fetch_url(self.base_url, delete_cookie=True)

        # patern_keyvol = r'\#keyvol.*val[^\w]+([a-f0-9]+)[^\w]+'
        patern_keyvol = r'\#keyvol[.)"\'\s]+val[("\'\s]+([a-f0-9]+)[)"\'\s]+;'
        match_keyvol = re.search(patern_keyvol, html, re.I)
        if match_keyvol:
            try:
                self.query.update({
                    'q': keyword,
                    'keyvol': match_keyvol.group(1)
                })
            except IndexError:
                pass

        _parser = NativeHTMLParser()
        root = _parser.feed(html)
        _parser.close()

        form_search = root.find('.//form[@id="form_query"]')

        if form_search:
            search_url = form_search.get('action')
            _input = form_search.find('.//input[@id="keyvol"]')
            if _input:
                _name = _input.get('name')
                _value = _input.get('value')
                if _name == 'keyvol':
                    if 'keyvol' not in self.query:
                        self.query.update({
                            'q': keyword,
                            'keyvol': _value
                        })

        if search_url and self.query:
            self.search_url = search_url
            search_url = f'{search_url}?{urlencode(self.query)}'
        elif self.query:
            search_url = f'{self.search_url}?{urlencode(self.query)}'

        return search_url

    @staticmethod
    def get_links(html: str = None) -> list:
        result = []
        if not html:
            return result

        _parser = NativeHTMLParser()
        root = _parser.feed(html)
        _parser.close()

        links = root.findall('.//li//a[@class="result-link"]')

        for link in links:
            _href = link.get('href')
            _urlparse = urlparse(_href)
            if _urlparse:
                _query = _urlparse.query
                if not _query:
                    continue

                _parse_qs = parse_qs(_query)
                if not isinstance(_parse_qs, dict):
                    continue

                urls = _parse_qs.get('as')
                if not isinstance(urls, (list, tuple)):
                    continue

                url = valid_url(urls[0])
                if url:
                    if '..' in url:
                        p = urlparse(url)
                        url = f'{p.scheme}://{p.netloc}'

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

        page_items = root.find('.//ul[@class="pagination"]')
        if not page_items:
            return next_page

        links = page_items.findall('li//a')
        for link in links:
            _href = link.get('href')
            _title = link.get('title')
            if re.search(r'next', _title, re.I):
                next_page = urljoin(self.search_url, _href)

        return next_page
