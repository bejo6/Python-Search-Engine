# Engine Health Check Report

**Date**: 2026-04-07  
**Tool**: `check_engines.py` (custom health check script)  
**Status**: Complete

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total Engines | 13 |
| Alive | 12 (92.3%) |
| Dead | 1 (7.7%) |
| Degraded | 0 |

---

## Results Overview

| # | Engine | Status | HTTP | Response Size | Response Time | Notes |
|---|--------|--------|------|---------------|---------------|-------|
| 1 | **Google** | ALIVE | 200 | 88.9 KB | 0.10s | Fast, reliable |
| 2 | **Bing** | ALIVE | 200 | 67.8 KB | 0.20s | Good response |
| 3 | **Yahoo** | ALIVE | 200 | 190.0 KB | 0.24s | Heavy page but working |
| 4 | **Yandex** | ALIVE | 200 | 39.4 KB | 2.31s | Slower, potential captcha risk |
| 5 | **AOL** | ALIVE | 200 | 127.6 KB | 0.30s | Powered by Bing/Google |
| 6 | **Ask** | ALIVE | 200 | 112.6 KB | 0.40s | Working normally |
| 7 | **Gigablast** | **DEAD** | - | 0 | - | DNS resolution failure (`Name or service not known`) |
| 8 | **Lycos** | ALIVE | 200 | 9.4 KB | 3.38s | Slow but working |
| 9 | **MetaGer** | ALIVE | 200 | 21.8 KB | 1.18s | German meta-search, working |
| 10 | **Mojeek** | ALIVE | 200 | 20.5 KB | 1.05s | Independent crawler, working |
| 11 | **Naver** | ALIVE | 200 | 230.3 KB | 0.48s | Korean, very heavy page |
| 12 | **Seznam** | ALIVE | 200 | 183.3 KB | 0.59s | Czech search, working |
| 13 | **GetSearchInfo** | ALIVE | 200 | 113.1 KB | 1.24s | Legacy, working |

---

## Dead Engines (Action Required)

### 1. Gigablast (`engine/gigablast.py`)

- **Base URL**: `https://www.gigablast.com`
- **Error**: DNS resolution failure — `[Errno -2] Name or service not known`
- **Root Cause**: Domain `gigablast.com` no longer resolves via DNS. The service appears to have been shut down or the domain has expired.
- **Recommendation**: 
  - Mark engine as deprecated in the codebase
  - Consider removing from `pyse.py` engine list
  - Add a fallback or replacement engine if needed

**Code impact**: 
- Remove `Gigablast` from imports in `pyse.py`
- Remove `Gigablast(debug=debug_mode)` from the engines list
- Optionally deprecate `engine/gigablast.py`

---

## Alive Engines (Verified Working)

### Tier 1: Major Search Engines

- **Google** — `https://www.google.com/search?q=KEYWORD`
- **Bing** — `https://www.bing.com/search?q=KEYWORD`
- **Yahoo** — `https://search.yahoo.com/search?p=KEYWORD`
- **Yandex** — `https://yandex.com/search/?text=KEYWORD` (note: uses `text` param, captcha-sensitive)

### Tier 2: Secondary/Regional Engines

- **AOL** — `https://search.aol.com/aol/search?q=KEYWORD`
- **Ask** — `https://www.ask.com/web?q=KEYWORD`
- **Mojeek** — `https://www.mojeek.com/search?q=KEYWORD` (independent crawler)
- **Seznam** — `https://search.seznam.cz/?q=KEYWORD` (Czech)
- **Naver** — `https://search.naver.com/search.naver?query=KEYWORD&where=web` (Korean)

### Tier 3: Niche/Meta Engines

- **Lycos** — `https://search.lycos.com/web/?q=KEYWORD` (slow but functional)
- **MetaGer** — `https://metager.org/meta/meta.ger3?eingabe=KEYWORD` (German meta-search, uses `eingabe` param)
- **GetSearchInfo** — `https://www.getsearchinfo.com/search?q=KEYWORD` (legacy engine)

---

## Architecture Notes

### Engine Pattern

All 13 engines follow the same design pattern:
1. **Class structure**: Each engine is a standalone class in `engine/<name>.py`
2. **Constructor**: `__init__(self, debug=False)` — initializes `FetchRequest`, query dict, filtering flag
3. **`.search(keyword)`** — Main entry point, builds query URL
4. **`.search_run(url)`** — Paginated search loop (collects links, handles next page)
5. **`.build_query(keyword)`** — Parses search form from homepage to get hidden form fields
6. **`.get_links(html)`** — Extracts result links using regex or HTML parser
7. **`.get_next_page(html)`** — Finds next page URL for pagination

### Shared Components (in `libs/` and `utils/`)

- **`libs/fetch.py`** — `FetchRequest` class: HTTP GET/POST with cookie management, gzip handling
- **`libs/html_parser.py`** — `NativeHTMLParser`: Custom HTML parser with ElementTree support
- **`utils/helper.py`** — URL validation, domain validation, charset decoding, random user agents
- **`utils/blacklist.py`** — Domain filtering (excludes major platforms like reddit, github, etc.)
- **`utils/static.py`** — Static data (TLDs, user agents, charset list)

### Main Entry Point (`pyse.py`)

```
Usage: python3 pyse.py -k "keyword" [-o output.txt] [-d]
       python3 pyse.py -l keywords.txt [-o output.txt] [-d]
```

- Runs all engines in **parallel threads** (13 threads for 13 engines)
- Results saved to `results.txt` (deduplicated)
- Flag `-d` enables DEBUG mode

---

## Known Issues (Post-2022)

1. **Gigablast domain down** — DNS no longer resolves (confirmed dead)
2. **CAPTCHA risk** — Yandex, Google, and Bing may present CAPTCHAs for automated requests
3. **HTML structure drift** — Since 2022, many search engines have updated their HTML layouts. The regex/XPath selectors used by engines may no longer match current page structures. Live testing of actual search results is recommended for each engine.
4. **No DuckDuckGo** — Notable absence of DuckDuckGo engine (2022 decision, may have been intentional)
5. **User agent strings outdated** — All engines use Chrome 92/Edge 92 user agents (mid-2021 versions)

---

## Recommended Next Steps

1. [ ] Remove Gigablast from engine list
2. [ ] Update user agent strings to current browser versions
3. [ ] Test actual search results (not just connectivity) for each engine
4. [ ] Consider adding a CAPTCHA detection mechanism
5. [ ] Update outdated Python dependencies
6. [ ] Add error handling improvements (current engines swallow some exceptions silently)
