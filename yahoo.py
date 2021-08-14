import re
from urllib.parse import urljoin, urlencode, unquote
from helper import fetch_url, clean_url, is_blacklisted


class Yahoo:
    base_url = 'https://search.yahoo.com'

    def __init__(self) -> None:
        self.query = {}
        self.filtering = True

    def search(self, keyword: str) -> list:
        # https://search.yahoo.com/search;_ylt=Awr9CKwV6hZhSEIAcfdDDWVH?p=TRANSMISSION&fr=sfp&fr2=p%3As%2Cv%3Asfp%2Cm%3Asb-top&iscqry=
        self.query.update({'p': keyword})
        search_url = self.build_query()
        if search_url:
            search_url = urljoin(self.base_url, search_url)

        return self.search_run(search_url)

    def search_run(self, url: str) -> list:
        result = []
        if not url:
            return result

        duplicate_page = 0
        referrer = self.base_url
        while True:
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
                        print('[Yahoo]', link)
                        result.append(link)
                if duplicate:
                    duplicate_page += 1

            if duplicate_page >= 3:
                # print('duplicate_page:', duplicate_page)
                # print('last count link:', len(links))
                break

            next = self.get_next_page(html)
            if next:
                referrer = url
                url = next
            else:
                break

        result = list(dict.fromkeys(result))
        return result

    def build_query(self, html: str=None) -> str:
        patern_form = r'(?:<form[^>]+role[\s=]+((?:")search(?:")|(?:\')search(?:\'))[^>]+>)[\s\S]+<\/form>'
        patern_action = r'action[\s=]+((?:")(.*?)(?:")|(?:\')(.*?)(?:\'))'
        patern_input = r'(?:<input[^>]+/?>)'
        patern_name = r'name[\s=]+((?:")(.*?)(?:")|(?:\')(.*?)(?:\'))'
        patern_value = r'value[\s=]+((?:")(.*?)(?:")|(?:\')(.*?)(?:\'))'

        if not html:
            html = fetch_url(self.base_url, delete_cookie=True)

        search_url = ''
        if html:
            get_form = re.search(patern_form, html, re.M | re.I)
            if get_form:
                form_str = get_form.group(0)
                action_val = re.search(patern_action, form_str, re.I)
                if action_val and len(action_val.groups()) >= 3:
                    search_url = action_val.group(3) or action_val.group(2)
                inputs = re.findall(patern_input, form_str, re.I)
                for input in inputs:
                    name = None
                    value = None
                    get_name = re.search(patern_name, input, re.I)
                    get_value = re.search(patern_value, input, re.I)
                    if get_name and len(get_name.groups()) >= 3:
                        name = get_name.group(3) or get_name.group(2)
                    if get_value and len(get_value.groups()) >= 3:
                        value = get_value.group(3) or get_value.group(2)

                    if name and name != 'p':
                        self.query.update({name: value or ''})

        if search_url:
            search_url = f'{search_url}?{urlencode(self.query)}'

        return search_url

    def get_links(self, html: str=None) -> list:
        result = []
        if not html:
            return result

        patern_links = r'(?:<a[^>]+referrerpolicy[\s=]+[\'"]origin[\'"][^>]+>)'
        patern_href = r'href[\s=]+((?:")(.*?)(?:")|(?:\')(.*?)(?:\'))'
        patern_url = r'\/RU=(.*?)\/RK='

        matches = re.findall(patern_links, html, re.M | re.I)
        for match in matches:
            href = re.search(patern_href, match, re.I)
            
            if href and len(href.groups()) >= 3:
                temp_link = clean_url(href.group(3) or href.group(2))
                web_url = re.search(patern_url, temp_link, re.I)
                if web_url:
                    try:
                        link = clean_url(unquote(web_url.group(1)))
                        if link:
                            result.append(link)
                    except IndexError:
                        pass

        if result:
            result = list(dict.fromkeys(result))

        return result

    def get_next_page(self, html: str=None) -> str:
        next = ''
        if not html:
            return next

        patern_next = r'(?:<a[^>]+class[\s=]+((?:")next(?:")|(?:\')next(?:\'))[^>]+>)'
        patern_href = r'href[\s=]+((?:")(.*?)(?:")|(?:\')(.*?)(?:\'))'

        matches = re.search(patern_next, html, re.M | re.I)
        if matches:
            href = re.search(patern_href, matches.group(0), re.I)
            if href and len(href.groups()) >= 3:
                path = href.group(3) or href.group(2)
                next = clean_url(urljoin(self.base_url, path))

        return next
