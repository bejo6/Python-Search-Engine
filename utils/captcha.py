#!/usr/bin/env python3
"""
Captcha detection utilities for search engines.
Detects common bot-blocking patterns in search engine responses.
"""

import re

# Common captcha/bot-blocking indicators in HTML
CAPTCHA_INDICATORS = [
    # Google reCAPTCHA
    r'recaptcha',
    r'grecaptcha',
    r'google.com/recaptcha',

    # Generic captcha terms
    r'captcha',
    r'human verification',
    r'verify you are human',
    r'prove you\'re human',
    r'are you a robot',
    r'i\'m not a robot',
    r'robot check',
    r'bot protection',

    # Cloudflare
    r'cf-chl-bypass',
    r'cf_captcha_kind',
    r'cloudflare.*captcha',
    r'checking your browser',
    r'verifying you are not a robot',
    r'just a moment to check your browser',
    r'ddos protection by cloudflare',

    # Specific search engines
    r'checkcaptcha',
    r'smart-captcha',
    r'enter the text you see below',
    r'enter both characters and digits',

    # Access denied / blocked
    r'access denied',
    r'automated access',
    r'automated queries',
    r'rate limit',
    r'too many requests',
    r'you have been blocked',
    r'abuse detected',
    r'unusual traffic',
    r'suspicious activity',
]

# Compile once for performance
_COMPILED = [re.compile(p, re.I) for p in CAPTCHA_INDICATORS]


def is_captcha(html, known_patterns=None):
    """
    Check if the given HTML content indicates a captcha/bot-block page.
    
    Args:
        html: HTML string to check
        known_patterns: Optional list of engine-specific regex patterns
    
    Returns:
        dict with keys: detected (bool), reason (str), indicators (list of matched patterns)
    """
    if not html or len(html) < 100:
        return {"detected": False, "reason": "Content too short", "indicators": []}

    results = {
        "detected": False,
        "reason": "",
        "indicators": [],
    }
    
    all_patterns = _COMPILED[:]
    
    # Add engine-specific patterns
    if known_patterns:
        for p in known_patterns:
            if isinstance(p, str):
                all_patterns.append(re.compile(p, re.I))
            elif hasattr(p, 'search'):
                all_patterns.append(p)
    
    for pattern in all_patterns:
        if pattern.search(html):
            results["detected"] = True
            results["indicators"].append(pattern.pattern)
            results["reason"] = f"Captcha/block indicator found: {pattern.pattern}"
    
    return results


# Engine-specific captcha indicators
ENGINE_CAPTCHA_PATTERNS = {
    "Google": [
        r'consent.google',
        r'consent\.googleusercontent',
        r'our systems have detected unusual traffic',
        r'automated requests',
    ],
    "Bing": [
        r'are you a robot',
        r'bk.*captcha',
        r'bing.com/secure',
    ],
    "Yandex": [
        r'/support/smart-captcha',
        r'/checkcaptcha',
    ],
    "Yahoo": [
        r'login.yahoo',
        r'captcha.yimg',
    ],
    "DuckDuckGo": [
        r'DuckDuckGo will use',
        r'unusual behavior',
    ],
}


def check_engine_captcha(html, engine_name):
    """
    Check for captcha using both generic and engine-specific patterns.
    """
    patterns = ENGINE_CAPTCHA_PATTERNS.get(engine_name, [])
    return is_captcha(html, known_patterns=patterns)
