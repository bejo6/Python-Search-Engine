import json
import re
from logging import DEBUG
from urllib.parse import urljoin, urlencode
from utils.blacklist import is_blacklisted
from utils.helper import setup_logger, validate_url
from libs.fetch import FetchRequest

logger = setup_logger(name='SearXNG')

# Healthy SearXNG instances from https://searx.space/ (verified 2026-04-08)
# Sorted by search_success %, TLS grade, HTTP grade
SEARXNG_HOSTS = [
    "https://opnxng.com",
    "https://priv.au",
    "https://search.2b9t.xyz",
    "https://search.abohiccups.com",
    "https://search.einfachzocken.eu",
    "https://search.femboy.ad",
    "https://search.freestater.org",
    "https://search.minus27315.dev",
    "https://search.rhscz.eu",
    "https://searx.oloke.xyz",
    "https://searx.rhscz.eu",
    "https://searx.ro",
    "https://searxng.canine.tools",
    "https://searxng.shreven.org",
    "https://searxng.site",
    "https://searxng.website",
    "https://searxng.cups.moe",
    "https://search.datenkrake.ch",
    "https://search.catboy.house",
    "https://searx.tiekoetter.com",
]


class Searxng:
    """
    SearXNG meta-search engine with auto-fallback.
    Queries a pool of healthy instances from searx.space.
    If one host fails, automatically falls back to the next.
    Each SearXNG instance internally aggregates 50+ search engines
    (Google, Bing, DuckDuckGo, Yahoo, Startpage, etc.)
    """
    base_url = 'https://searx.space'
    # JSON API endpoint (no JS needed, returns structured data)
    search_path = '/search'

    def __init__(self, debug=False):
        self.debug = debug
        self.fetch = FetchRequest()
        self.filtering = True
        # Working host index (start from 0, increment on failure)
        self._host_index = 0
        # Track broken hosts for this session
        self._broken_hosts = set()

        if self.debug:
            logger.setLevel(DEBUG)

    def _get_host(self):
        """Get next available host. Returns None if all exhausted."""
        for i in range(len(SEARXNG_HOSTS)):
            idx = (self._host_index + i) % len(SEARXNG_HOSTS)
            host = SEARXNG_HOSTS[idx]
            if host not in self._broken_hosts:
                return host
        return None

    def search(self, keyword):
        """
        Search across SearXNG instance pool with auto-fallback.
        Tries each host until one returns results.
        """
        keyword = str(keyword)
        tried_hosts = []

        while True:
            host = self._get_host()
            if host is None:
                logger.error('All SearXNG hosts failed')
                return []

            search_url = f'{host}{self.search_path}?{urlencode({"q": keyword, "format": "json", "categories": "general"})}'

            if self.debug:
                logger.debug(f'Trying host: {host}')
            logger.info(f'SearXNG host: {host}')

            try:
                html = self.fetch.get(search_url)
                if not html:
                    self._broken_hosts.add(host)
                    self._host_index = (self._host_index + 1) % len(SEARXNG_HOSTS)
                    tried_hosts.append(host)
                    continue

                # SearXNG returns JSON, not HTML
                results = self._parse_json_results(html, host)
                if results:
                    self._host_index = SEARXNG_HOSTS.index(host) if host in SEARXNG_HOSTS else 0
                    return results
                else:
                    self._broken_hosts.add(host)
                    self._host_index = (self._host_index + 1) % len(SEARXNG_HOSTS)
                    tried_hosts.append(host)

            except Exception as e:
                if self.debug:
                    logger.debug(f'Host {host} failed: {e}')
                self._broken_hosts.add(host)
                self._host_index = (self._host_index + 1) % len(SEARXNG_HOSTS)
                tried_hosts.append(host)

        return []

    def _parse_json_results(self, data, host):
        """Parse SearXNG JSON API response."""
        result = []
        try:
            parsed = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            # Not JSON, probably error page - fallback
            return self._parse_html_fallback(data, host)

        results = parsed.get('results', [])
        if not results:
            return []

        for item in results:
            url = item.get('url', '')
            if not url:
                continue

            if self.filtering and is_blacklisted(url):
                logger.debug('[BLACKLIST] %s' % url)
                continue

            valid_url = validate_url(url)
            if valid_url:
                logger.info(valid_url)
                result.append(valid_url)

        if result:
            result = list(dict.fromkeys(result))

        logger.info('Total links: %d (host: %s)' % (len(result), host))
        return result

    def _parse_html_fallback(self, html, host):
        """Fallback: parse HTML if JSON API fails."""
        result = []
        if not html:
            return result

        # Extract URLs from SearXNG results
        raw_urls = re.findall(r'<a[^>]+class="[^"]*result-header[^"]*"[^>]+href="([^"]+)"', str(html), re.I)
        if not raw_urls:
            raw_urls = re.findall(r'<article[^>]+data-url="([^"]+)"', str(html), re.I)
        if not raw_urls:
            raw_urls = re.findall(r'<a[^>]+href="(/redirect[^"]*url=([^&"]+))', str(html), re.I)

        for url in raw_urls:
            valid_url = validate_url(url)
            if valid_url and not is_blacklisted(valid_url):
                result.append(valid_url)

        if result:
            result = list(dict.fromkeys(result))
            logger.info('Total links: %d (host: %s, HTML fallback)' % (len(result), host))

        return result

    # Unused methods to maintain interface compatibility
    @staticmethod
    def search_run(url):
        return []

    @staticmethod
    def get_links(html):
        return []

    @staticmethod
    def get_next_page(html):
        return ''


if __name__ == '__main__':
    import sys
    import argparse
    import json as json_mod
    try:
        parser = argparse.ArgumentParser(usage='%(prog)s [options]')
        parser._optionals.title = 'Options'
        parser.add_argument('-k', '--keyword',
                            dest='keyword',
                            help='Keyword to search',
                            action='store')
        parser.add_argument('-s', '--save',
                            dest='save_output',
                            help='Save Output results',
                            action='store_true')
        parser.add_argument('-o', '--output',
                            dest='output_file',
                            help='Output results (default searxng_results.txt)',
                            default='searxng_results.txt',
                            action='store')
        parser.add_argument('-d', '--debug',
                            dest='debug_mode',
                            help='Set DEBUG mode',
                            action='store_true')

        args = parser.parse_args()
        if not args.keyword:
            parser.print_help()
            sys.exit('[!] Keyword required')

        eng = Searxng(debug=args.debug_mode)
        res = eng.search(args.keyword)

        if args.save_output:
            if res:
                for rlink in res:
                    with open(args.output_file, 'a', encoding='utf-8', errors='replace') as f:
                        try:
                            f.write('%s\n' % rlink)
                        except UnicodeEncodeError:
                            logger.error(rlink)
        else:
            print(json_mod.dumps(res, indent=2, default=str))
    except KeyboardInterrupt:
        sys.exit('KeyboardInterrupt')
