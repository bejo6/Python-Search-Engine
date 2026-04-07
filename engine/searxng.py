import json
import os
import re
from logging import DEBUG
from urllib.parse import urljoin, urlencode
from utils.blacklist import is_blacklisted
from utils.helper import setup_logger, validate_url
from libs.fetch import FetchRequest

logger = setup_logger(name='SearXNG')

# Environment variables for private instance (optional)
SEARXNG_PRIVATE_HOST = os.environ.get('SEARXNG_HOST', '')
SEARXNG_API_KEY = os.environ.get('SEARXNG_API_KEY', '')

# Healthy public SearXNG instances from https://searx.space/ (verified 2026-04-08)
# Fallback: used only when no private host is configured
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

    Modes:
    1. Private host (no rate limits, full control):
       - Set via constructor:  Searxng(host=..., api_key=...)
       - Or env vars:          SEARXNG_HOST + SEARXNG_API_KEY
       - Or pyse.py args:      --searxng-host <url> --searxng-key <key>

    2. Public fallback (rate limited, shared instances):
       - Auto-fallback across 20 healthy hosts from searx.space
       - If one host fails (429, 503, timeout), tries next host

    Each SearXNG instance internally aggregates 50+ search engines
    (Google, Bing, DuckDuckGo, Yahoo, Startpage, etc.)
    """
    base_url = 'https://searx.space'
    search_path = '/search'

    def __init__(self, debug=False, host=None, api_key=None):
        self.debug = debug
        self.fetch = FetchRequest()
        self.filtering = True
        self._host_index = 0
        self._broken_hosts = set()

        # Private host settings (constructor > env vars > None)
        self.private_host = host or SEARXNG_PRIVATE_HOST or ''
        self.api_key = api_key or SEARXNG_API_KEY or ''

        # Determine host pool
        if self.private_host:
            self.hosts = [self.private_host.rstrip('/')]
            if self.debug:
                logger.debug('Using private SearXNG host: %s' % self.private_host)
        else:
            self.hosts = list(SEARXNG_HOSTS)
            if self.debug:
                logger.debug('Using %d public SearXNG hosts (fallback)' % len(self.hosts))

        if self.debug:
            logger.setLevel(DEBUG)

    def _get_headers(self, extra=None):
        """Build request headers with optional API key auth."""
        headers = {
            'User-Agent': self.fetch.user_agent,
            'Accept': 'application/json, text/html',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        if self.api_key:
            headers['X-API-Key'] = self.api_key
        if extra:
            headers.update(extra)
        return headers

    def _get_host(self):
        """Get next available host. Returns None if all exhausted."""
        for i in range(len(self.hosts)):
            idx = (self._host_index + i) % len(self.hosts)
            host = self.hosts[idx]
            if host not in self._broken_hosts:
                return host
        return None

    def search(self, keyword):
        """
        Search with auto-fallback across host pool.
        Private host (if set) is tried first, then public fallbacks.
        """
        keyword = str(keyword)
        tried_hosts = []

        # Build hosts list: private host first (if different from public list)
        if self.private_host:
            host_pool = [self.private_host.rstrip('/')] + [
                h for h in SEARXNG_HOSTS if h.rstrip('/') != self.private_host.rstrip('/')
            ]
        else:
            host_pool = list(SEARXNG_HOSTS)

        while True:
            # Get next untried host
            host = None
            for h in host_pool:
                if h not in self._broken_hosts:
                    host = h
                    break
            if host is None:
                logger.error('All SearXNG hosts failed (tried: %d)' % len(tried_hosts))
                return []

            search_url = '%s%s?%s' % (
                host,
                self.search_path,
                urlencode({'q': keyword, 'format': 'json', 'categories': 'general'}),
            )

            if self.debug:
                logger.debug('Trying host: %s' % host)
            logger.info('SearXNG host: %s' % host.split('/')[2])

            try:
                headers = self._get_headers()
                html = self.fetch.get(search_url, headers=headers)
                if not html:
                    self._broken_hosts.add(host)
                    tried_hosts.append(host)
                    continue

                # SearXNG returns JSON for format=json
                results = self._parse_json_results(html, host)
                if results:
                    if self.debug:
                        logger.debug('Success on host: %s (results: %d)' % (host, len(results)))
                    return results
                else:
                    self._broken_hosts.add(host)
                    tried_hosts.append(host)

            except Exception as e:
                if self.debug:
                    logger.debug('Host %s failed: %s' % (host, e))
                self._broken_hosts.add(host)
                tried_hosts.append(host)

        return []

    def _parse_json_results(self, data, host):
        """Parse SearXNG JSON API response."""
        result = []
        try:
            parsed = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return self._parse_html_fallback(data, host)

        # Check for error response
        if not isinstance(parsed, dict):
            return []
        if parsed.get('error'):
            logger.debug('SearXNG error: %s' % parsed.get('error'))
            return []

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

        logger.info('Total links: %d (host: %s)' % (len(result), host.split('/')[2]))
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
            logger.info('Total links: %d (host: %s, HTML fallback)' % (
                len(result), host.split('/')[2]))

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
        parser.add_argument('--host',
                            dest='host',
                            default=SEARXNG_PRIVATE_HOST,
                            help='Private SearXNG host URL',
                            action='store')
        parser.add_argument('--key',
                            dest='api_key',
                            default=SEARXNG_API_KEY,
                            help='API key for private host (X-API-Key header)',
                            action='store')

        args = parser.parse_args()
        if not args.keyword:
            parser.print_help()
            sys.exit('[!] Keyword required')

        eng = Searxng(debug=args.debug_mode, host=args.host, api_key=args.api_key)
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
