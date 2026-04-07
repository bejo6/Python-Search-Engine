#!/usr/bin/env python3
"""
Test script to validate each alive search engine's actual search patterns.
This uses real engine classes and checks if they can find links.
Includes captcha detection.
"""

import sys
import os
import time
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.helper import setup_logger

TEST_KEYWORD = "python programming"

# All engines: (label, module_name, class_name)
engines_to_test = [
    ("Google", "engine.google", "Google"),
    ("Bing", "engine.bing", "Bing"),
    ("Yahoo", "engine.yahoo", "Yahoo"),
    ("Yandex", "engine.yandex", "Yandex"),
    ("AOL", "engine.aol", "Aol"),
    ("Ask", "engine.ask", "Ask"),
    ("Lycos", "engine.lycos", "Lycos"),
    ("MetaGer", "engine.metager", "MetaGer"),
    ("Mojeek", "engine.mojeek", "Mojeek"),
    ("Naver", "engine.naver", "Naver"),
    ("Seznam", "engine.seznam", "Seznam"),
    ("GetSearchInfo", "engine.getsearchinfo", "GetSearchInfo"),
    ("DuckDuckGo", "engine.duckduckgo", "Duckduckgo"),
    ("Startpage", "engine.startpage", "Startpage"),
    ("Ecosia", "engine.ecosia", "Ecosia"),
]

try:
    from utils.captcha import check_engine_captcha
    HAS_CAPTCHA = True
except ImportError:
    HAS_CAPTCHA = False


def test_engine(label, module_name, class_name):
    """Test a single engine and return results dict."""
    result = {
        "name": label,
        "status": "UNKNOWN",
        "links_found": 0,
        "links": [],
        "error": None,
        "time_seconds": None,
        "captcha_detected": False,
        "captcha_reason": "",
    }
    
    try:
        mod = __import__(module_name, fromlist=[class_name])
        EngineClass = getattr(mod, class_name)
        engine = EngineClass(debug=False)
        
        start = time.time()
        links = engine.search(TEST_KEYWORD)
        elapsed = time.time() - start
        
        result["time_seconds"] = round(elapsed, 2)
        result["links"] = links if isinstance(links, list) else []
        result["links_found"] = len(result["links"])
        
        if links and len(links) > 0:
            result["status"] = "OK"
            result["sample_links"] = links[:3]
        elif links is not None and len(links) == 0:
            # Check if captcha was the reason
            if HAS_CAPTCHA:
                # Re-fetch to check captcha
                try:
                    base_url = getattr(EngineClass, 'base_url', '')
                    search_url = getattr(EngineClass, 'search_url', '') + '/search?q=test'
                    from libs.fetch import FetchRequest
                    fetch = FetchRequest()
                    html = fetch.get(base_url or search_url)
                    if html:
                        cap = check_engine_captcha(html, label)
                        if cap["detected"]:
                            result["captcha_detected"] = True
                            result["captcha_reason"] = cap["reason"]
                except Exception:
                    pass
            result["status"] = "NO_LINKS"
        else:
            result["status"] = "ERROR"
            result["error"] = "returned None"
    except Exception as e:
        result["status"] = "EXCEPTION"
        result["error"] = f"{type(e).__name__}: {str(e)}"
    
    return result


def main():
    print("=" * 80)
    print("Search Engine Pattern Validation Test")
    print(f"Keyword: '{TEST_KEYWORD}'")
    print(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    results = []
    for label, module, cls in engines_to_test:
        print(f"Testing {label}...", end=" ", flush=True)
        r = test_engine(label, module, cls)
        results.append(r)
        status_icon = {
            "OK": "[PASS]",
            "NO_LINKS": "[WARN]",
            "ERROR": "[FAIL]",
            "EXCEPTION": "[ERR ]",
        }.get(r["status"], "[????]")
        
        extra = ""
        if r["captcha_detected"]:
            extra = f" [CAPTCHA: {r['captcha_reason']}]"
        err_msg = f" -- {r['error']}" if r.get('error') else ""
        samples = ' | '.join(r.get('sample_links', [])[:2]) if r.get('status') == 'OK' else ''
        
        print(f"{status_icon} {r['status']}" 
              f" (links: {r['links_found']}, time: {r['time_seconds']}s){extra}{err_msg}")
        if samples:
            print(f"          Sample: {samples}")
        time.sleep(1)
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    ok_count = sum(1 for r in results if r["status"] == "OK")
    no_links = sum(1 for r in results if r["status"] == "NO_LINKS")
    captcha_count = sum(1 for r in results if r.get("captcha_detected"))
    failed = sum(1 for r in results if r["status"] in ("ERROR", "EXCEPTION"))
    
    print(f"Total tested: {len(results)}")
    print(f"  PASS (links found):   {ok_count}")
    print(f"  WARN (no links):      {no_links}")
    print(f"  CAPTCHA detected:     {captcha_count}")
    print(f"  FAIL (error/except):  {failed}")
    print()
    
    print(f"{'Engine':<20} {'Status':<12} {'Links':>5} {'Time (s)':>9} {'Captcha'}")
    print("-" * 80)
    for r in results:
        cap = "YES" if r.get("captcha_detected") else "-"
        print(f"{r['name']:<20} {r['status']:<12} {r['links_found']:>5} {r['time_seconds']:>9.2f} {cap}")
    
    print()
    print("=" * 80)
    print("WORKING ENGINES (links returned)")
    print("=" * 80)
    for r in results:
        if r["status"] == "OK":
            print(f"  [OK] {r['name']} ({r['links_found']} links, {r['time_seconds']}s)")
            for link in r.get('sample_links', []):
                print(f"    -> {link}")
    
    print()
    print("=" * 80)
    print("FAILED ENGINES")
    print("=" * 80)
    for r in results:
        if r["status"] != "OK":
            reasons = []
            if r.get("captcha_detected"):
                reasons.append(f"Captcha/Blocked: {r['captcha_reason']}")
            if r.get("error"):
                reasons.append(r["error"])
            reason_str = "; ".join(reasons) if reasons else "No links extracted (pattern may not match)"
            print(f"  [FAIL] {r['name']} -- {reason_str}")
    
    # Save to JSON
    save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_results.json")
    with open(save_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to: {save_path}")


if __name__ == "__main__":
    main()
