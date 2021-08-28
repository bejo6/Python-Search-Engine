import re
from urllib.parse import urljoin, urlencode
from blacklist import is_blacklisted
from helper import fetch_url, clean_url, valid_url, setup_logger
from html_parser import NativeHTMLParser
from config import LOG_LEVEL


logger = setup_logger(name='Yandex', level=LOG_LEVEL)


class Yandex:
    base_url = 'https://yandex.com'

    def __init__(self) -> None:
        self.query = {}
        self.user_agent = None
        self.filtering = True

    def search(self, keyword: str):
        search_url = self.build_query(keyword=keyword)
        if search_url:
            search_url = urljoin(self.base_url, search_url)

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

        patern_captcha = r'\/support\/smart-captcha|\/checkcaptcha'

        if re.search(patern_captcha, html, re.I):
            logger.error('Error captcha')
            return search_url

        _parser = NativeHTMLParser()
        root = _parser.feed(html)
        _parser.close()
        form_search = root.find('.//form[@role="search"]')

        if form_search:
            search_url = form_search.get('action')
            inputs = form_search.findall('.//input[@type="hidden"]')
            for inp in inputs:
                _name = inp.get('name')
                _value = inp.get('value')
                if not _name:
                    continue

                if _name != 'text':
                    self.query.update({_name: _value or ''})

        if search_url:
            self.query.update({'text': keyword})
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

        # links = root.findall('.//ul[@id="search-result"]//li[@class="serp-item"]//h2/a[@data-log-node]')
        # links = root.findall('.//ul[@id="search-result"]/li[@class="serp-item"]//h2/a[@data-log-node]')
        # links = root.findall('.//ul[@id="search-result"]/li[@class="serp-item"]//h2/a')
        search_result = root.find('.//ul[@id="search-result"]')
        if not search_result:
            return result
        # //li[@class="serp-item"]//h2/a[@]
        links = search_result.findall('li[@class="serp-item"]//h2/a')
        # print(links)
        # print(len(links))
        for link in links:
            _class = link.get('class')
            _href = link.get('href')
            _data_event = link.get('data-event-required')
            if _data_event:
                continue

            if _class and re.search(r'organic__url', _class, re.I):
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

        page_items = root.find('.//div[@class="pager__items"]')
        if not page_items:
            return next_page

        page_links = page_items.findall('a')
        for link in page_links:
            _class = link.get('class')
            _href = link.get('href')
            if _class and re.search(r'pager__item_kind_next', _class, re.I):
                next_page = clean_url(urljoin(self.base_url, _href))
                if next_page:
                    break

        if not next_page:
            logger.debug(page_items)
            logger.debug(page_links)

        return next_page
