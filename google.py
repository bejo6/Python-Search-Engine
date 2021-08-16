import random
import re
from urllib.parse import urljoin, urlencode
from helper import fetch_url, clean_url, is_blacklisted, valid_url


class Google:
    base_url = 'https://www.google.com'

    def __init__(self) -> None:
        self.query = {}
        self.user_agent = None
        self.filtering = True

    def search(self, keyword: str):
        search_url = self.build_query(keyword)
        return self.search_run(search_url)

    def search_run(self, url: str) -> list:
        result = []
        if not url:
            return result

        duplicate_page = 0
        headers = {'User-Agent': self.user_agent}
        while True:
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
                        print('[Google]', link)
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

        result = list(dict.fromkeys(result))
        return result

    def build_query(self, keyword: str = None) -> str:
        self.build_clients(keyword)
        search_url = urljoin(self.base_url, '/search')
        url = f'{search_url}?{urlencode(self.query)}'

        return url

    def build_clients(self, keyword: str = None):
        RAND_MS = random.randint(1552, 2568)
        client_brave = {
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36',
            'params': {
                'q': keyword,
                'oq': keyword,
                'aqs': f'chrome..69i57.{RAND_MS}j0j1',
                'sourceid': 'chrome',
                'ie': 'UTF-8',
            }
        }
        client_edge = {
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36 Edg/92.0.902.73',
            'params': {
                'q': keyword,
                'oq': keyword,
                'aqs': f'edge..69i57.{RAND_MS}j0j1',
                'sourceid': 'chrome',
                'ie': 'UTF-8',
            }
        }
        client_opera = {
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36 OPR/77.0.4054.277',
            'params': {
                'client': 'opera',
                'q': keyword,
                'sourceid': 'opera',
                'ie': 'UTF-8',
                'oe': 'UTF-8',
            }
        }
        client_firefox = {
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'params': {
                'client': 'firefox-b-d',
                'q': keyword,
            }
        }
        clients = [
            client_brave,
            client_edge,
            client_opera,
            client_firefox,
        ]
        client = random.choice(clients)
        # client = client_firefox
        self.query = client.get('params')
        self.user_agent = client.get('user_agent')

    @staticmethod
    def get_links(html: str = None) -> list:
        result = []
        if not html:
            return result

        patern_links = r'(?:<a[^>]+data-ved[\s=]+[^>]+>)'
        patern_href = r'href[\s=]+((?:")(.*?)(?:")|(?:\')(.*?)(?:\'))'

        matches = re.findall(patern_links, html, re.M | re.I)
        for match in matches:
            href = re.search(patern_href, match, re.I)

            if href and len(href.groups()) >= 3:
                try:
                    link = valid_url(href.group(3) or href.group(2))
                    if link:
                        # result.append(unquote(link))
                        result.append(link)
                except IndexError:
                    pass

        if result:
            result = list(dict.fromkeys(result))

        return result

    def get_next_page(self, html: str = None) -> str:
        next_page = ''
        if not html:
            return next_page

        patern_next = r'(?:<a[^>]+id[\s=]+((?:")pnnext(?:")|(?:\')pnnext(?:\'))[^>]+>)'
        patern_href = r'href[\s=]+((?:")(.*?)(?:")|(?:\')(.*?)(?:\'))'

        matches = re.search(patern_next, html, re.M | re.I)
        if matches:
            href = re.search(patern_href, matches.group(0), re.I)
            if href and len(href.groups()) >= 3:
                path = href.group(3) or href.group(2)
                next_page = clean_url(urljoin(self.base_url, path))

        return next_page
