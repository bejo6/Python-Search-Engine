import re
from urllib.parse import urljoin, urlencode, unquote
from helper import fetch_url, clean_url, is_blacklisted, valid_url, setup_logger
from html_parser import NativeHTMLParser
from config import LOG_LEVEL


logger = setup_logger(name='Aol', level=LOG_LEVEL)


class Aol:
    base_url = 'https://search.aol.com'

    def __init__(self) -> None:
        self.query = {}
        self.user_agent = None
        self.filtering = True

    def search(self, keyword: str):
        self.query.update({'q': keyword})
        search_url = self.build_query()
        if search_url:
            search_url = urljoin(self.base_url, search_url)

        return self.search_run(search_url)

    def search_run(self, url: str) -> list:
        result = []
        if not url:
            return result

        duplicate_page = 0
        referrer = 'https://www.aol.com'
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

    def build_query(self, html: str = None) -> str:
        if not html:
            html = fetch_url('https://www.aol.com', delete_cookie=True)

        _parser = NativeHTMLParser()
        root = _parser.feed(html)
        _parser.close()
        form_header = root.find('.//form[@id="header-form"]')

        search_url = ''
        if form_header:
            search_url = form_header.get('action')
            inputs = form_header.findall('.//input[@type="hidden"]')
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

        patern_url = r'\/RU=(.*?)\/RK='

        _parser = NativeHTMLParser()
        root = _parser.feed(html)
        _parser.close()

        links = root.findall('.//a[@referrerpolicy="origin"]')

        for link in links:
            _class = link.get('class')
            _href = link.get('href')
            if _class and re.search(r'ac-algo', _class, re.I):
                temp_url = _href
                web_url = re.search(patern_url, temp_url, re.I)
                if web_url:
                    try:
                        url = valid_url(unquote(web_url.group(1)))
                        if url:
                            result.append(url)
                    except IndexError:
                        pass

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

        find_next_page = root.find('.//a[@class="next"]')
        if find_next_page is not None:
            _href = find_next_page.get('href')
            if _href:
                next_page = clean_url(urljoin(self.base_url, _href))

        return next_page
