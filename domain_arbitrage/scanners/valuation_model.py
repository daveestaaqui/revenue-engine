#!/usr/bin/env python3
"""
Algorithmic Domain Valuation & Commercial Demand Scoring Model
Evaluates dropping and expired domains for instant resale liquidity on GoDaddy/Afternic.
"""

import re

HIGH_VALUE_KEYWORDS = {
    # Tech / AI / FinTech
    "ai": 25, "cloud": 15, "data": 15, "crypto": 12, "pay": 20, "flow": 15, "stack": 12,
    "chain": 12, "vault": 18, "labs": 14, "app": 14, "tech": 10, "meta": 10, "smart": 12,
    # Real Estate & Finance
    "capital": 22, "fund": 20, "equity": 22, "loan": 20, "asset": 18, "invest": 18,
    "realty": 18, "property": 16, "estate": 15, "wealth": 18, "credit": 15,
    # Health & Commerce
    "health": 15, "care": 12, "shop": 10, "direct": 12, "prime": 14, "group": 12
}

TRADEMARK_BLACKLIST = [
    "google", "apple", "microsoft", "amazon", "facebook", "meta", "instagram",
    "tiktok", "twitter", "uber", "airbnb", "netflix", "walmart", "tesla", "nike",
    "paypal", "chase", "disney", "coca", "pepsi"
]

def score_domain(domain_name):
    clean = domain_name.lower().strip()
    if not ("." in clean):
        return None

    name, tld = clean.rsplit(".", 1)
    
    # Must be .com, .org, .net, or .io for maximum resale liquidity
    if tld not in ["com", "org", "net", "io", "ai"]:
        return None

    # Filter out numbers and hyphens (kill resale value)
    if "-" in name or any(char.isdigit() for char in name):
        return None

    # Filter out trademark conflicts
    if any(tm in name for tm in TRADEMARK_BLACKLIST):
        return None

    # Length criteria (ideal: 4 to 12 characters)
    length = len(name)
    if length < 4 or length > 16:
        return None

    score = 0

    # Keyword match scoring
    matched_keywords = []
    for kw, weight in HIGH_VALUE_KEYWORDS.items():
        if kw in name:
            score += weight
            matched_keywords.append(kw)

    # Length bonuses
    if length <= 6:
        score += 30
    elif length <= 8:
        score += 20
    elif length <= 10:
        score += 10

    # .com premium
    if tld == "com":
        score += 25
    elif tld in ["ai", "io"]:
        score += 15

    # Determine suggested resale price
    if score >= 65:
        resale_val = 899.0
        tier = "Tier 1: High Liquidity ($799 - $1,299)"
    elif score >= 45:
        resale_val = 499.0
        tier = "Tier 2: Medium Liquidity ($399 - $699)"
    elif score >= 30:
        resale_val = 299.0
        tier = "Tier 3: Standard Resale ($199 - $399)"
    else:
        return None

    wholesale_cost = 10.50 # Namecheap/Cloudflare base reg fee
    net_profit = resale_val * 0.80 - wholesale_cost # After standard 20% Afternic commission

    return {
        "domain": clean,
        "name": name,
        "tld": tld,
        "length": length,
        "score": score,
        "keywords_matched": matched_keywords,
        "tier": tier,
        "wholesale_cost_usd": wholesale_cost,
        "suggested_buy_it_now_usd": resale_val,
        "estimated_net_profit_usd": round(net_profit, 2)
    }
