from urllib.parse import urljoin, urlencode
from blacklist import is_blacklisted
from helper import fetch_url, clean_url, valid_url, setup_logger
from html_parser import NativeHTMLParser
from config import LOG_LEVEL


logger = setup_logger(name='Naver', level=LOG_LEVEL)


class Naver:
    base_url = 'https://www.naver.com'
    search_url = 'https://search.naver.com/search.naver'

    def __init__(self) -> None:
        self.query = {}
        self.user_agent = None
        self.filtering = True

    def search(self, keyword: str):
        search_url = self.build_query(keyword=keyword)
        if search_url:
            search_url = urljoin(self.search_url, search_url)

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

        _parser = NativeHTMLParser()
        root = _parser.feed(html)
        _parser.close()
        form_search = root.find('.//form[@id="sform"]')

        if form_search:
            search_url = form_search.get('action')

            self.query.update({'where': 'web'})

            inputs = form_search.findall('.//input[@type="hidden"]')

            for inp in inputs:
                _name = inp.get('name')
                _value = inp.get('value')
                _disabled = inp.get('disabled')
                if not _name:
                    continue

                if _disabled:
                    continue

                if _name != 'query':
                    self.query.update({_name: _value or ''})

        if search_url:
            self.query.update({'query': keyword})
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

        search_result = root.find('.//ul[@class="lst_total"]')
        if not search_result:
            return result

        links = search_result.findall('li//a[@class="link_tit"]')

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

        page_items = root.find('.//div[@class="sc_page"]')
        if not page_items:
            return next_page

        btn_next = page_items.find('a[@class="btn_next"]')
        _href = btn_next.get('href')
        if _href:
            next_page = clean_url(urljoin(self.search_url, _href))

        return next_page
