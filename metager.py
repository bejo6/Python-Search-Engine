import re
import base64
from urllib.parse import urljoin, urlencode, urlparse, unquote, parse_qs
from blacklist import is_blacklisted
from helper import fetch_url, valid_url, setup_logger, decode_bytes
from html_parser import NativeHTMLParser
from config import LOG_LEVEL


logger = setup_logger(name='metaGer', level=LOG_LEVEL)


class MetaGer:
    base_url = 'https://metager.org'
    next_page = ''

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
            logger.info(f'Page: {page} {url}')
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

            if self.next_page:
                referrer = url
                url = self.next_page
            else:
                break
            page += 1

        result = list(dict.fromkeys(result))
        return result

    def build_query(self, keyword: str, html: str = None) -> str:
        search_url = ''
        if not html:
            html = fetch_url(self.base_url, delete_cookie=True)

        _parser = NativeHTMLParser()
        root = _parser.feed(html)
        _parser.close()

        form_search = root.find('.//form[@id="searchForm"]')

        if form_search:
            action = form_search.get('action')
            if action:
                search_url = action.strip()

            inputs = form_search.findall('.//input')
            for inp in inputs:
                _name = inp.get('name')
                _value = inp.get('value')

                if not _name:
                    continue

                if _name != 'eingabe':
                    self.query.update({_name: _value or ''})
                else:
                    self.query.update({_name: keyword})

        if search_url:
            search_url = f'{search_url}?{urlencode(self.query)}'

        return search_url

    def get_links(self, html: str = None) -> list:
        result = []
        if not html:
            return result

        _parser = NativeHTMLParser()
        root = _parser.feed(html)
        _parser.close()

        iframe = root.find('.//iframe[@id="mg-framed"]')
        links = root.findall('.//a[@class="result-link"]')

        if not links and iframe is not None:
            iframe_src = iframe.get('src')
            iframe_url = valid_url(iframe_src)
            if iframe_url:
                iframe_html = fetch_url(iframe_url)
                return self.get_links(iframe_html)

        for link in links:
            _href = link.get('href')
            url = valid_url(_href)

            patern_metager = r'\/r\/metager\/'
            patern_redirect = r'\/redir\/clickGate'
            if re.search(patern_metager, url, re.I):
                url = self.get_url_base64(url)
            elif re.search(patern_redirect, url, re.I):
                url = self.get_redirect_url(url)

            if url:
                result.append(url)

        self.get_next_page(root)

        if result:
            result = list(dict.fromkeys(result))

        return result

    def get_next_page(self, root):
        self.next_page = ''
        next_search_link = root.find('.//div[@id="next-search-link"]')
        if next_search_link is None:
            return

        _next = next_search_link.find('a')
        if _next is not None:
            _href = _next.get('href')
            if _href:
                self.next_page = urljoin(self.base_url, _href)

    @staticmethod
    def get_url_base64(url: str) -> str:
        _url = ''
        _parse = urlparse(url)
        _split = _parse.path.split('/', maxsplit=5)
        if len(_split) >= 6:
            _urlbase64 = unquote(_split[-1])
            _urlbase64 = re.sub(r'<+slash>+', '/', _urlbase64, flags=re.I)
            _decode = base64.urlsafe_b64decode(_urlbase64)
            _url, _ = decode_bytes(_decode)

        return _url

    @staticmethod
    def get_redirect_url(url: str) -> str:
        _url = ''
        _parse = urlparse(url)
        _query = _parse.query
        _parse_qs = parse_qs(_query)

        urls = _parse_qs.get('url')
        if not isinstance(urls, (list, tuple)):
            return _url

        first_url = valid_url(urls[0])
        if first_url:
            if '..' in first_url:
                p = urlparse(url)
                first_url = f'{p.scheme}://{p.netloc}'

            _url = first_url

        return _url
