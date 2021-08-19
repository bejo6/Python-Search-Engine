import re
from urllib.parse import urljoin, urlencode
from helper import fetch_url, clean_url, is_blacklisted, valid_url


class Ask:
    base_url = 'https://www.ask.com'

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
        empty_page = 0
        headers = {'Referer': self.base_url}
        page = 1
        while True:
            html = fetch_url(url, headers=headers)
            links = self.get_links(html)

            if not links:
                empty_page += 1
                if page > 1:
                    break
            else:
                duplicate = True
                for link in links:
                    if self.filtering:
                        if is_blacklisted(link):
                            continue

                    if link not in result:
                        duplicate = False
                        print('[Ask]', link)
                        result.append(link)
                if duplicate:
                    duplicate_page += 1

            if duplicate_page >= 3:
                break

            if empty_page >= 2:
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

    def build_query(self, keyword: str = None) -> str:
        search_url = urljoin(self.base_url, '/web')
        self.query.update({
            'q': keyword,
            'ad': 'dirN',
            'qo': 'homepageSearchBox',
        })
        url = f'{search_url}?{urlencode(self.query)}'

        return url

    @staticmethod
    def get_links(html: str = None) -> list:
        result = []
        if not html:
            return result

        patern_links = r'(?:<a[^>]+result-link[^>]+>)'
        patern_href = r'href[\s=]+((?:")(.*?)(?:")|(?:\')(.*?)(?:\'))'
        patern_utm = r'\?utm_content.+$'

        matches = re.findall(patern_links, html, re.M | re.I)
        for match in matches:
            href = re.search(patern_href, match, re.I)

            if href and len(href.groups()) >= 3:
                try:
                    link = valid_url(href.group(3) or href.group(2))
                    link = re.sub(patern_utm, '', link)
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

        patern_next = r'(?:<li[^>]+PartialWebPagination-next[^>]+>)(\s+)?(?:<a[^>]+>)'
        patern_href = r'href[\s=]+((?:")(.*?)(?:")|(?:\')(.*?)(?:\'))'

        matches = re.search(patern_next, html, re.M | re.I)
        if matches:
            href = re.search(patern_href, matches.group(0), re.I)
            if href and len(href.groups()) >= 3:
                path = href.group(3) or href.group(2)
                next_page = clean_url(urljoin(self.base_url, path))

        return next_page
