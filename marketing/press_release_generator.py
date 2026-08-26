#!/usr/bin/env python3
"""
Surplus Docket — Autonomous Press Release & Media Syndication Engine
Maintains the official /press/ Newsroom, generates Google News-ready RSS/Atom feeds,
and automatically dispatches webhook notifications for zero-touch media broadcast.

Strategic Cadence: Bi-Weekly / Monthly Milestones (High Authority, Non-Spammy).
"""

import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
from compliance.content_fact_checker import verify_content_integrity, generate_fact_check_badge_html

SITE_DIR = ROOT_DIR / "site"
PRESS_DIR = SITE_DIR / "press"
RELEASES_DIR = PRESS_DIR / "releases"
SYNDICATE_DIR = ROOT_DIR / "marketing" / "syndicate" / "press_releases"

PRESS_DIR.mkdir(parents=True, exist_ok=True)
RELEASES_DIR.mkdir(parents=True, exist_ok=True)
SYNDICATE_DIR.mkdir(parents=True, exist_ok=True)

PRESS_RELEASES = [
    {
        "slug": "surplus-docket-unveils-rest-api-for-law-practice-management",
        "date": "August 23, 2026",
        "iso_date": "2026-08-23T07:00:00-04:00",
        "rfc822_date": "Sun, 23 Aug 2026 07:00:00 -0400",
        "headline": "Surplus Docket Unveils Programmatic REST JSON API for Law Firm Practice Management and AI Intake Automation",
        "subheadline": "Enterprise API tier enables direct ingestion into Clio, MyCase, Airtable, and custom legal-tech pipelines with priority 6:00 AM dispatch.",
        "location": "ATLANTA, Ga.",
        "summary": "Surplus Docket introduced its programmatic REST JSON API endpoint (/api/v1/feed.json), allowing legal-tech practices to stream live court surplus records directly into their CRM intake pipelines without manual data entry.",
        "body_paragraphs": [
            "Surplus Docket today expanded its enterprise offerings with the release of its developer-first REST JSON API endpoint (`/api/v1/feed.json`), designed to power automated client intake and workflow management for modern asset recovery practices.",
            "As legal practices increasingly adopt workflow automation tools such as Zapier, Make, Clio, and custom AI agents, the need for clean, machine-readable court docket streams has accelerated. Surplus Docket's REST API delivers standardized JSON schemas containing official case docket numbers, verified surplus balances, parcel identification numbers, property situs addresses, and calculated statutory filing deadlines.",
            "Subscribers to the National Feed + API tier receive priority 6:00 AM EST data dispatch, custom county ingestion support, and webhook notifications whenever new high-value excess proceeds cases are confirmed in monitored court registries.",
            "\"Legal practitioners should not have to manually re-type county clerk records into their practice management systems,\" stated Surplus Docket. \"Our REST API allows firms to connect ground-truth public records directly into their client outreach workflows in under ten minutes.\"",
            "Complete interactive documentation, sample cURL requests, Python SDK scripts, and JSON response schemas are publicly accessible in the Surplus Docket Developer Documentation portal at surplusdocket.com/api-documentation.html."
        ]
    },
    {
        "slug": "surplus-docket-launches-autonomous-legal-intelligence-platform",
        "date": "August 18, 2026",
        "iso_date": "2026-08-18T07:00:00-04:00",
        "rfc822_date": "Tue, 18 Aug 2026 07:00:00 -0400",
        "headline": "Surplus Docket Launches Autonomous Public Records Intelligence Platform for Asset Recovery Counsel Across Florida, Texas, and Georgia",
        "subheadline": "New legal-tech data pipeline eliminates dead bank leads with automated institutional lien pre-filtering and daily 7:00 AM court registry feeds.",
        "location": "WEST PALM BEACH, Fla. & HOUSTON, Tex.",
        "summary": "Surplus Docket officially announced the launch of its autonomous public records intelligence platform, providing structured, case-verified tax deed surplus and excess proceeds data to asset recovery attorneys, title counsel, and real estate practitioners.",
        "body_paragraphs": [
            "Surplus Docket today announced the public launch of its autonomous legal data intelligence platform, engineered specifically for law firms, title searchers, and asset recovery practitioners specializing in county tax deed surplus and court excess proceeds retrieval.",
            "Across the United States, hundreds of millions of dollars in excess auction proceeds remain unclaimed in county clerk and district court registries following tax deed foreclosure sales. However, legal practitioners have historically faced significant operational friction, spending hours manually scraping fragmented county clerk portals only to encounter records encumbered by senior mortgage liens and institutional bank claims.",
            "Surplus Docket solves this industry bottleneck by deploying an automated data pipeline that scrubs institutional bank liens, junior mortgage servicers, and HOA encumbrances from raw clerk lists. The platform delivers pure, case-verified individual and estate heir claims directly to subscribers every morning at 7:00 AM EST in CSV, XLSX, and programmatic REST JSON formats.",
            "\"Our mission is to bring institutional data cleanliness to the asset recovery legal sector,\" said the Product Architecture Team at Surplus Docket. \"By replacing unscrubbed PDF lists with case-verifiable court docket metadata and automated statutory deadline tracking, we allow recovery counsel to file petitions within days of auction confirmation instead of weeks.\"",
            "The platform launches with comprehensive monitoring across 12 high-volume judicial circuits in Florida (under Fla. Stat. § 197.582), Texas (under Tex. Tax Code § 34.04), and Georgia (under O.C.G.A. § 48-4-5), representing over 92% of total statewide surplus proceeds volume in those jurisdictions.",
            "In addition to daily automated feeds, Surplus Docket provides all subscribers with a complete Asset Recovery Practitioner Toolkit featuring court-ready petition templates, client retainer agreements, statutory fee calculators, and a self-service Stripe billing portal."
        ]
    }
]

BOILERPLATE = """About Surplus Docket
Surplus Docket is an autonomous public records intelligence and legal data compiler that aggregates, case-verifies, and standardizes tax deed surplus and excess proceeds records across judicial registries in Florida, Texas, and Georgia. Purpose-built for asset recovery attorneys, title searchers, and probate investors, Surplus Docket delivers clean, institutional-lien-scrubbed datasets via daily automated CSV/Excel exports and programmatic REST APIs. For more information, visit https://surplusdocket.com."""

MEDIA_CONTACT = """Media Relations:
Surplus Docket Press Office
Email: press@surplusdocket.com
Website: https://surplusdocket.com/press/
Digital Media Kit: https://surplusdocket.com/press/"""

def generate_individual_press_release(pr):
    paragraphs_html = "".join(f'<p class="mb-4 sm:mb-5 leading-relaxed text-slate-700">{p}</p>' for p in pr["body_paragraphs"])
    about_text = BOILERPLATE.replace("About Surplus Docket\n", "").strip()
    
    # Pre-publication editorial & statutory fact-check sentinel
    fact_check_cert = verify_content_integrity(
        title=pr['headline'],
        content_text=" ".join(pr['body_paragraphs']),
        pub_date_str=pr['iso_date'],
        category="Press Release"
    )
    fact_check_badge = generate_fact_check_badge_html(fact_check_cert)
    
    html = f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{pr['headline']} | Surplus Docket Newsroom</title>
    <meta name="description" content="{pr['summary']}">
    <link rel="canonical" href="https://surplusdocket.com/press/releases/{pr['slug']}.html">
    <link rel="icon" type="image/x-icon" href="/assets/favicon.ico">
    <meta name="robots" content="index, follow">
    
    <!-- Open Graph -->
    <meta property="og:type" content="article">
    <meta property="og:site_name" content="Surplus Docket">
    <meta property="og:title" content="{pr['headline']}">
    <meta property="og:description" content="{pr['summary']}">
    <meta property="og:url" content="https://surplusdocket.com/press/releases/{pr['slug']}.html">
    <meta property="og:image" content="https://surplusdocket.com/assets/logo_surplus_docket.png">
    
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    colors: {{
                        brand: {{
                            navy: '#0f172a',
                            navyLight: '#1e293b',
                            green: '#059669',
                            greenDark: '#047857',
                            greenSoft: '#d1fae5',
                            canvas: '#f8fafc'
                        }}
                    }},
                    fontFamily: {{
                        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
                        heading: ['Cabinet Grotesk', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
                        mono: ['JetBrains Mono', 'Menlo', 'monospace']
                    }}
                }}
            }}
        }}
    </script>
    
    <!-- NewsArticle JSON-LD Structured Data -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": "{pr['headline']}",
        "description": "{pr['summary']}",
        "datePublished": "{pr['iso_date']}",
        "dateModified": "{pr['iso_date']}",
        "mainEntityOfPage": {{
            "@type": "WebPage",
            "@id": "https://surplusdocket.com/press/releases/{pr['slug']}.html"
        }},
        "author": {{
            "@type": "Organization",
            "name": "Surplus Docket Newsroom",
            "url": "https://surplusdocket.com"
        }},
        "publisher": {{
            "@type": "Organization",
            "name": "Surplus Docket",
            "logo": {{
                "@type": "ImageObject",
                "url": "https://surplusdocket.com/assets/logo_surplus_docket.png"
            }}
        }}
    }}
    </script>
</head>
<body class="bg-brand-canvas text-slate-800 font-sans antialiased min-h-screen flex flex-col justify-between">

    <!-- Header Navigation -->
    <header class="w-full border-b border-slate-200 bg-white/95 backdrop-blur-md sticky top-0 z-50 shadow-sm">
        <div class="max-w-5xl mx-auto px-4 sm:px-6 h-16 sm:h-20 flex items-center justify-between gap-3">
            <a href="/" class="flex items-center gap-2.5 sm:gap-3 group shrink-0 min-w-0">
                <img src="/assets/logo_surplus_docket.png?v=6" alt="Surplus Docket" class="h-8 sm:h-10 w-auto object-contain transition-transform group-hover:scale-105 shrink-0">
                <div class="flex flex-col sm:flex-row sm:items-baseline sm:gap-1.5 leading-none shrink-0">
                    <span class="font-heading font-black text-sm sm:text-2xl tracking-tight text-brand-green">SURPLUS</span>
                    <span class="font-heading font-black text-sm sm:text-2xl tracking-tight text-brand-navy">DOCKET</span>
                </div>
            </a>
            <div class="flex items-center gap-3 sm:gap-4 text-xs sm:text-sm font-semibold text-slate-600">
                <a href="/press/" class="text-brand-green hover:text-brand-greenDark font-bold flex items-center gap-1">&larr; Newsroom</a>
                <a href="/" class="hover:text-brand-green transition-colors">Home</a>
                <a href="/#pricing" class="px-3.5 py-2 bg-brand-green hover:bg-brand-greenDark text-white font-heading font-bold text-xs sm:text-sm rounded-lg transition-all shadow-sm">Get Feeds</a>
            </div>
        </div>
    </header>

    <main class="py-12 sm:py-16 px-4 sm:px-6 max-w-4xl mx-auto flex-grow">
        <!-- Press Release Header -->
        <div class="mb-8 border-b border-slate-200 pb-8">
            <div class="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
                <span class="text-brand-green">FOR IMMEDIATE RELEASE</span>
                <span>•</span>
                <span>{pr['date']}</span>
            </div>
            <h1 class="text-2xl sm:text-4xl font-heading font-black text-brand-navy leading-tight mb-4">
                {pr['headline']}
            </h1>
            <p class="text-base sm:text-lg text-slate-600 font-medium leading-relaxed">
                {pr['subheadline']}
            </p>
        </div>

        <!-- Press Release Body -->
        <article class="text-sm sm:text-base text-slate-700 leading-relaxed max-w-none">
            <p class="font-bold text-slate-900 mb-4 sm:mb-5">
                <strong>{pr['location']}</strong> — {pr['body_paragraphs'][0]}
            </p>
            {paragraphs_html}
            
            {fact_check_badge}
            
            <div class="my-8 p-6 bg-slate-100 rounded-xl border border-slate-200">
                <h3 class="text-xs font-bold uppercase tracking-wider text-brand-navy mb-2">About Surplus Docket</h3>
                <p class="text-xs text-slate-600 leading-relaxed mb-4">
                    {about_text}
                </p>
                <div class="pt-4 border-t border-slate-200 text-xs text-slate-600">
                    <p class="font-bold text-brand-navy mb-1">Media Contact:</p>
                    <p>Surplus Docket Press Relations</p>
                    <p>Email: <a href="mailto:press@surplusdocket.com" class="text-brand-green hover:underline">press@surplusdocket.com</a></p>
                    <p>Website: <a href="https://surplusdocket.com" class="text-brand-green hover:underline">https://surplusdocket.com</a></p>
                </div>
            </div>
        </article>

        <!-- Back to Newsroom -->
        <div class="mt-8 pt-6 border-t border-slate-200 flex justify-between items-center text-xs font-bold">
            <a href="/press/" class="text-brand-green hover:underline">&larr; Back to All Press Releases</a>
            <a href="/" class="text-slate-500 hover:text-brand-navy">Surplus Docket Platform &rarr;</a>
        </div>
    </main>

    <!-- Footer (Institutional Multi-Column Grid) -->
    <footer class="bg-white border-t border-slate-200 pt-16 pb-12 px-4 sm:px-6 lg:px-8 text-slate-600">
        <div class="max-w-7xl mx-auto">
            <!-- Main Grid -->
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-8 lg:gap-10 pb-12 border-b border-slate-200 text-left">
                <!-- Col 1: Brand & Overview (Spans 2 cols on lg) -->
                <div class="lg:col-span-2 space-y-4">
                    <a href="/" class="flex items-center gap-3 group shrink-0">
                        <img src="/assets/logo_surplus_docket.png?v=6" alt="Surplus Docket" class="h-9 sm:h-10 w-auto object-contain transition-transform group-hover:scale-105">
                        <div class="flex flex-col sm:flex-row sm:items-baseline sm:gap-1.5 leading-none">
                            <span class="font-heading font-black text-sm sm:text-2xl tracking-tight text-brand-green">SURPLUS</span>
                            <span class="font-heading font-black text-sm sm:text-2xl tracking-tight text-brand-navy">DOCKET</span>
                        </div>
                    </a>
                    <p class="text-xs sm:text-sm text-slate-500 leading-relaxed max-w-sm">
                        Structured daily public records intelligence indexing tax deed surplus and excess proceeds filings across county court registries for asset recovery law practices.
                    </p>
                    <div class="flex flex-wrap items-center gap-2 pt-1 text-xs">
                        <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-brand-greenSoft text-brand-greenDark font-mono font-bold text-[11px]">
                            <span class="w-1.5 h-1.5 rounded-full bg-brand-green animate-pulse"></span>
                            Daily 7:00 AM EST Dispatch
                        </span>
                        <a href="/api-documentation.html" class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-mono text-[11px] font-semibold transition-colors">
                            REST API v1
                        </a>
                    </div>
                </div>

                <!-- Col 2: Jurisdictions & Feeds -->
                <div class="space-y-3">
                    <p class="text-xs font-bold uppercase tracking-wider text-brand-navy font-heading">Jurisdiction Feeds</p>
                    <ul class="space-y-2 text-xs font-medium">
                        <li><a href="/florida-tax-deed-surplus.html" class="hover:text-brand-green transition-colors flex items-center justify-between"><span>Florida Feed</span> <span class="text-[10px] text-brand-green font-mono">FL § 197</span></a></li>
                        <li><a href="/texas-tax-sale-excess-proceeds.html" class="hover:text-brand-green transition-colors flex items-center justify-between"><span>Texas Feed</span> <span class="text-[10px] text-brand-green font-mono">TX § 34</span></a></li>
                        <li><a href="/georgia-tax-sale-excess-funds.html" class="hover:text-brand-green transition-colors flex items-center justify-between"><span>Georgia Feed</span> <span class="text-[10px] text-brand-green font-mono">GA § 48</span></a></li>
                        <li><a href="/north-carolina-tax-foreclosure-surplus.html" class="hover:text-brand-green transition-colors flex items-center justify-between"><span>North Carolina</span> <span class="text-[10px] text-slate-400 font-mono">NC § 105</span></a></li>
                        <li><a href="/tennessee-tax-sale-excess-proceeds.html" class="hover:text-brand-green transition-colors flex items-center justify-between"><span>Tennessee</span> <span class="text-[10px] text-slate-400 font-mono">TN § 67</span></a></li>
                        <li><a href="/california-tax-defaulted-excess-proceeds.html" class="hover:text-brand-green transition-colors flex items-center justify-between"><span>California</span> <span class="text-[10px] text-slate-400 font-mono">CA § 4675</span></a></li>
                    </ul>
                </div>

                <!-- Col 3: Legal Tech & Tools -->
                <div class="space-y-3">
                    <p class="text-xs font-bold uppercase tracking-wider text-brand-navy font-heading">Practitioner Tools</p>
                    <ul class="space-y-2 text-xs font-medium">
                        <li><a href="/practitioner-toolkit.html" class="hover:text-brand-green transition-colors">1-Click Petition Builder</a></li>
                        <li><a href="/#calculator" class="hover:text-brand-green transition-colors">Statutory Cap Calculator</a></li>
                        <li><a href="/methodology.html" class="hover:text-brand-green transition-colors">Lien Scrubbing Methodology</a></li>
                        <li><a href="/comparison.html" class="hover:text-brand-green transition-colors">Provider Comparison Matrix</a></li>
                        <li><a href="/api-documentation.html" class="hover:text-brand-green transition-colors">Programmatic REST API</a></li>
                        <li><a href="/assets/sample_surplus_docket_feed.csv" download class="hover:text-brand-green transition-colors">Sample Data Export (.csv)</a></li>
                    </ul>
                </div>

                <!-- Col 4: Account & Compliance -->
                <div class="space-y-3">
                    <p class="text-xs font-bold uppercase tracking-wider text-brand-navy font-heading">Company & Legal</p>
                    <ul class="space-y-2 text-xs font-medium">
                        <li><a href="/#pricing" class="hover:text-brand-green transition-colors">Subscription Pricing</a></li>
                        <li><a href="https://billing.stripe.com/p/login/bJe28r4iagXN4LHb0i0ZW00" target="_blank" rel="noopener noreferrer" class="text-brand-navy font-bold hover:text-brand-green transition-colors flex items-center gap-1"><span>Customer Portal</span> <span class="text-slate-400">&rarr;</span></a></li>
                        <li><a href="/blog/" class="hover:text-brand-green transition-colors">Legal Research Articles</a></li>
                        <li><a href="/press/" class="hover:text-brand-green transition-colors">Press & Newsroom</a></li>
                        <li><a href="/terms.html" class="hover:text-brand-green transition-colors">Commercial Data Terms</a></li>
                        <li><a href="/refund-policy.html" class="hover:text-brand-green transition-colors">14-Day Refund Guarantee</a></li>
                    </ul>
                </div>
            </div>

            <!-- Bottom Sub-Bar -->
            <div class="pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-400">
                <p>&copy; 2026 Surplus Docket. All rights reserved.</p>
                <p class="text-center sm:text-right text-[11px] text-slate-400 max-w-md">
                    Surplus Docket is a public records data compiler, not a law firm or Consumer Reporting Agency (15 U.S.C. § 1681).
                </p>
            </div>
        </div>
    </footer>

</body>
</html>"""
    
    file_path = RELEASES_DIR / f"{pr['slug']}.html"
    file_path.write_text(html, encoding="utf-8")
    print(f"  ✓ Generated Press Release: {file_path.name}")
    
    # Also write plain text / Markdown wire draft in syndicate
    text_path = SYNDICATE_DIR / f"{pr['slug']}.txt"
    body_rest = "\n\n".join(pr['body_paragraphs'][1:])
    headline_upper = pr['headline'].upper()
    subheadline = pr['subheadline']
    location = pr['location']
    first_p = pr['body_paragraphs'][0]
    
    text_content = f"""FOR IMMEDIATE RELEASE

{headline_upper}
{subheadline}

{location} — {first_p}

{body_rest}

###

{BOILERPLATE}

{MEDIA_CONTACT}
"""
    text_path.write_text(text_content, encoding="utf-8")

def generate_press_newsroom():
    cards_html = ""
    for pr in PRESS_RELEASES:
        cards_html += f"""
        <div class="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-sm hover:shadow-md transition-all">
            <div class="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                <span class="text-brand-green">Press Release</span>
                <span>•</span>
                <span>{pr['date']}</span>
            </div>
            <h2 class="text-xl sm:text-2xl font-heading font-black text-brand-navy mb-2.5">
                <a href="/press/releases/{pr['slug']}.html" class="hover:text-brand-green transition-colors">
                    {pr['headline']}
                </a>
            </h2>
            <p class="text-xs sm:text-sm text-slate-600 leading-relaxed mb-4">
                {pr['summary']}
            </p>
            <a href="/press/releases/{pr['slug']}.html" class="text-xs font-bold text-brand-green hover:text-brand-greenDark inline-flex items-center gap-1">
                Read Full Release &rarr;
            </a>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Press &amp; Media Newsroom | Surplus Docket</title>
    <meta name="description" content="Official press releases, announcements, and media resources for Surplus Docket, the autonomous public records intelligence platform.">
    <link rel="canonical" href="https://surplusdocket.com/press/">
    <link rel="alternate" type="application/rss+xml" title="Surplus Docket Press Feed" href="https://surplusdocket.com/press/feed.xml">
    <link rel="icon" type="image/x-icon" href="/assets/favicon.ico">
    <meta name="robots" content="index, follow">
    
    <!-- Open Graph -->
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="Surplus Docket">
    <meta property="og:title" content="Press &amp; Media Newsroom | Surplus Docket">
    <meta property="og:description" content="Official press releases, media kits, and corporate announcements from Surplus Docket.">
    <meta property="og:url" content="https://surplusdocket.com/press/">
    <meta property="og:image" content="https://surplusdocket.com/assets/logo_surplus_docket.png">
    
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    colors: {{
                        brand: {{
                            navy: '#0f172a',
                            navyLight: '#1e293b',
                            green: '#059669',
                            greenDark: '#047857',
                            greenSoft: '#d1fae5',
                            canvas: '#f8fafc'
                        }}
                    }},
                    fontFamily: {{
                        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
                        heading: ['Cabinet Grotesk', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
                        mono: ['JetBrains Mono', 'Menlo', 'monospace']
                    }}
                }}
            }}
        }}
    </script>
</head>
<body class="bg-brand-canvas text-slate-800 font-sans antialiased min-h-screen flex flex-col justify-between">

    <!-- Header Navigation -->
    <header class="w-full border-b border-slate-200 bg-white/95 backdrop-blur-md sticky top-0 z-50 shadow-sm">
        <div class="max-w-6xl mx-auto px-4 sm:px-6 h-16 sm:h-20 flex items-center justify-between gap-3">
            <a href="/" class="flex items-center gap-2.5 sm:gap-3 group shrink-0 min-w-0">
                <img src="/assets/logo_surplus_docket.png?v=6" alt="Surplus Docket" class="h-8 sm:h-10 w-auto object-contain transition-transform group-hover:scale-105 shrink-0">
                <div class="flex flex-col sm:flex-row sm:items-baseline sm:gap-1.5 leading-none shrink-0">
                    <span class="font-heading font-black text-sm sm:text-2xl tracking-tight text-brand-green">SURPLUS</span>
                    <span class="font-heading font-black text-sm sm:text-2xl tracking-tight text-brand-navy">DOCKET</span>
                </div>
            </a>
            <div class="flex items-center gap-3 sm:gap-5 text-xs sm:text-sm font-semibold text-slate-600">
                <a href="/" class="hover:text-brand-green transition-colors">Home</a>
                <a href="/press/" class="text-brand-navy font-bold hover:text-brand-green transition-colors">Newsroom</a>
                <a href="/blog/" class="hover:text-brand-green transition-colors hidden sm:inline">Articles</a>
                <a href="/api-documentation.html" class="hover:text-brand-green transition-colors hidden sm:inline">API</a>
                <a href="/#pricing" class="px-3.5 py-2 bg-brand-green hover:bg-brand-greenDark text-white font-heading font-bold text-xs sm:text-sm rounded-lg transition-all shadow-sm">Get Feeds</a>
            </div>
        </div>
    </header>

    <main class="py-12 sm:py-16 px-4 sm:px-6 max-w-5xl mx-auto flex-grow">
        <!-- Hero Section -->
        <div class="text-center max-w-2xl mx-auto mb-12">
            <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-brand-green/30 bg-brand-greenSoft text-brand-greenDark text-xs font-bold uppercase tracking-wider mb-3">
                Newsroom &amp; Media Relations
            </div>
            <h1 class="text-3xl sm:text-4xl font-heading font-black text-brand-navy mb-3">
                Official Press Releases &amp; Media Hub
            </h1>
            <p class="text-xs sm:text-sm text-slate-600 leading-relaxed mb-4">
                Official corporate announcements, product releases, legal-tech datasets, and media resources from Surplus Docket.
            </p>
            <div class="flex items-center justify-center gap-3 text-xs">
                <a href="/press/feed.xml" class="inline-flex items-center gap-1.5 font-bold text-amber-600 bg-amber-50 border border-amber-200 px-3 py-1 rounded-full hover:bg-amber-100 transition-colors">
                    <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><path d="M6.18 15.64a2.18 2.18 0 0 1 2.18 2.18C8.36 19 7.38 20 6.18 20C5 20 4 19 4 17.82a2.18 2.18 0 0 1 2.18-2.18M4 4.44A15.56 15.56 0 0 1 19.56 20h-2.83A12.73 12.73 0 0 0 4 7.27V4.44m0 5.66a9.9 9.9 0 0 1 9.9 9.9h-2.83A7.07 7.07 0 0 0 4 12.93V10.1z"/></svg>
                    Press RSS Feed
                </a>
            </div>
        </div>

        <!-- Press Releases List -->
        <div class="space-y-6 mb-16">
            {cards_html}
        </div>

        <!-- Media Kit & Press Inquiries Card -->
        <div class="bg-brand-navy text-white rounded-2xl p-6 sm:p-8 shadow-xl border border-slate-700 grid md:grid-cols-2 gap-6 items-center">
            <div>
                <div class="text-xs uppercase font-bold text-emerald-300 tracking-wider mb-1">Journalist &amp; Media Inquiries</div>
                <h3 class="text-xl font-heading font-bold text-white mb-2">Covering Surplus Docket?</h3>
                <p class="text-xs text-slate-300 leading-relaxed mb-4">
                    Our team provides journalists, legal analysts, and real estate publications with ground-truth court registry data, county surplus statistics, and expert commentary on statutory excess proceeds.
                </p>
                <a href="mailto:press@surplusdocket.com" class="inline-flex items-center gap-2 px-4 py-2 bg-brand-green hover:bg-brand-greenDark text-white font-heading font-bold text-xs rounded-lg transition-colors shadow">
                    Contact Press Office &rarr;
                </a>
            </div>
            <div class="bg-slate-800/80 p-5 rounded-xl border border-slate-700 text-xs space-y-2">
                <div class="font-bold text-emerald-300 uppercase tracking-wider">Fast Facts &amp; Boilerplate:</div>
                <p class="text-slate-300 leading-relaxed">
                    <strong>Founded:</strong> 2026<br>
                    <strong>Primary Coverage:</strong> Florida (§ 197.582), Texas (§ 34.04), Georgia (§ 48-4-5)<br>
                    <strong>Platform:</strong> Automated daily public records feeds &amp; REST JSON API<br>
                    <strong>Press Contact:</strong> press@surplusdocket.com
                </p>
            </div>
        </div>
    </main>

    <!-- Footer (Institutional Multi-Column Grid) -->
    <footer class="bg-white border-t border-slate-200 pt-16 pb-12 px-4 sm:px-6 lg:px-8 text-slate-600">
        <div class="max-w-7xl mx-auto">
            <!-- Main Grid -->
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-8 lg:gap-10 pb-12 border-b border-slate-200 text-left">
                <!-- Col 1: Brand & Overview (Spans 2 cols on lg) -->
                <div class="lg:col-span-2 space-y-4">
                    <a href="/" class="flex items-center gap-3 group shrink-0">
                        <img src="/assets/logo_surplus_docket.png?v=6" alt="Surplus Docket" class="h-9 sm:h-10 w-auto object-contain transition-transform group-hover:scale-105">
                        <div class="flex flex-col sm:flex-row sm:items-baseline sm:gap-1.5 leading-none">
                            <span class="font-heading font-black text-sm sm:text-2xl tracking-tight text-brand-green">SURPLUS</span>
                            <span class="font-heading font-black text-sm sm:text-2xl tracking-tight text-brand-navy">DOCKET</span>
                        </div>
                    </a>
                    <p class="text-xs sm:text-sm text-slate-500 leading-relaxed max-w-sm">
                        Structured daily public records intelligence indexing tax deed surplus and excess proceeds filings across county court registries for asset recovery law practices.
                    </p>
                    <div class="flex flex-wrap items-center gap-2 pt-1 text-xs">
                        <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-brand-greenSoft text-brand-greenDark font-mono font-bold text-[11px]">
                            <span class="w-1.5 h-1.5 rounded-full bg-brand-green animate-pulse"></span>
                            Daily 7:00 AM EST Dispatch
                        </span>
                        <a href="/api-documentation.html" class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-mono text-[11px] font-semibold transition-colors">
                            REST API v1
                        </a>
                    </div>
                </div>

                <!-- Col 2: Jurisdictions & Feeds -->
                <div class="space-y-3">
                    <p class="text-xs font-bold uppercase tracking-wider text-brand-navy font-heading">Jurisdiction Feeds</p>
                    <ul class="space-y-2 text-xs font-medium">
                        <li><a href="/florida-tax-deed-surplus.html" class="hover:text-brand-green transition-colors flex items-center justify-between"><span>Florida Feed</span> <span class="text-[10px] text-brand-green font-mono">FL § 197</span></a></li>
                        <li><a href="/texas-tax-sale-excess-proceeds.html" class="hover:text-brand-green transition-colors flex items-center justify-between"><span>Texas Feed</span> <span class="text-[10px] text-brand-green font-mono">TX § 34</span></a></li>
                        <li><a href="/georgia-tax-sale-excess-funds.html" class="hover:text-brand-green transition-colors flex items-center justify-between"><span>Georgia Feed</span> <span class="text-[10px] text-brand-green font-mono">GA § 48</span></a></li>
                        <li><a href="/north-carolina-tax-foreclosure-surplus.html" class="hover:text-brand-green transition-colors flex items-center justify-between"><span>North Carolina</span> <span class="text-[10px] text-slate-400 font-mono">NC § 105</span></a></li>
                        <li><a href="/tennessee-tax-sale-excess-proceeds.html" class="hover:text-brand-green transition-colors flex items-center justify-between"><span>Tennessee</span> <span class="text-[10px] text-slate-400 font-mono">TN § 67</span></a></li>
                        <li><a href="/california-tax-defaulted-excess-proceeds.html" class="hover:text-brand-green transition-colors flex items-center justify-between"><span>California</span> <span class="text-[10px] text-slate-400 font-mono">CA § 4675</span></a></li>
                    </ul>
                </div>

                <!-- Col 3: Legal Tech & Tools -->
                <div class="space-y-3">
                    <p class="text-xs font-bold uppercase tracking-wider text-brand-navy font-heading">Practitioner Tools</p>
                    <ul class="space-y-2 text-xs font-medium">
                        <li><a href="/practitioner-toolkit.html" class="hover:text-brand-green transition-colors">1-Click Petition Builder</a></li>
                        <li><a href="/#calculator" class="hover:text-brand-green transition-colors">Statutory Cap Calculator</a></li>
                        <li><a href="/methodology.html" class="hover:text-brand-green transition-colors">Lien Scrubbing Methodology</a></li>
                        <li><a href="/comparison.html" class="hover:text-brand-green transition-colors">Provider Comparison Matrix</a></li>
                        <li><a href="/api-documentation.html" class="hover:text-brand-green transition-colors">Programmatic REST API</a></li>
                        <li><a href="/assets/sample_surplus_docket_feed.csv" download class="hover:text-brand-green transition-colors">Sample Data Export (.csv)</a></li>
                    </ul>
                </div>

                <!-- Col 4: Account & Compliance -->
                <div class="space-y-3">
                    <p class="text-xs font-bold uppercase tracking-wider text-brand-navy font-heading">Company & Legal</p>
                    <ul class="space-y-2 text-xs font-medium">
                        <li><a href="/#pricing" class="hover:text-brand-green transition-colors">Subscription Pricing</a></li>
                        <li><a href="https://billing.stripe.com/p/login/bJe28r4iagXN4LHb0i0ZW00" target="_blank" rel="noopener noreferrer" class="text-brand-navy font-bold hover:text-brand-green transition-colors flex items-center gap-1"><span>Customer Portal</span> <span class="text-slate-400">&rarr;</span></a></li>
                        <li><a href="/blog/" class="hover:text-brand-green transition-colors">Legal Research Articles</a></li>
                        <li><a href="/press/" class="hover:text-brand-green transition-colors">Press & Newsroom</a></li>
                        <li><a href="/terms.html" class="hover:text-brand-green transition-colors">Commercial Data Terms</a></li>
                        <li><a href="/refund-policy.html" class="hover:text-brand-green transition-colors">14-Day Refund Guarantee</a></li>
                    </ul>
                </div>
            </div>

            <!-- Bottom Sub-Bar -->
            <div class="pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-400">
                <p>&copy; 2026 Surplus Docket. All rights reserved.</p>
                <p class="text-center sm:text-right text-[11px] text-slate-400 max-w-md">
                    Surplus Docket is a public records data compiler, not a law firm or Consumer Reporting Agency (15 U.S.C. § 1681).
                </p>
            </div>
        </div>
    </footer>

</body>
</html>"""

    newsroom_path = PRESS_DIR / "index.html"
    newsroom_path.write_text(html, encoding="utf-8")
    print(f"✓ Generated Press Newsroom: {newsroom_path}")

def generate_press_rss():
    feed_path = PRESS_DIR / "feed.xml"
    now_rfc822 = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    
    items_xml = ""
    for pr in PRESS_RELEASES:
        items_xml += f"""    <item>
      <title><![CDATA[{pr['headline']}]]></title>
      <link>https://surplusdocket.com/press/releases/{pr['slug']}.html</link>
      <guid isPermaLink="true">https://surplusdocket.com/press/releases/{pr['slug']}.html</guid>
      <pubDate>{pr['rfc822_date']}</pubDate>
      <description><![CDATA[{pr['summary']}]]></description>
      <author>press@surplusdocket.com (Surplus Docket Newsroom)</author>
      <category>Legal Technology / Public Records</category>
    </item>
"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Surplus Docket™ Press Releases &amp; Newsroom</title>
    <link>https://surplusdocket.com/press/</link>
    <description>Official press releases and legal intelligence announcements from Surplus Docket.</description>
    <language>en-us</language>
    <lastBuildDate>{now_rfc822}</lastBuildDate>
    <atom:link href="https://surplusdocket.com/press/feed.xml" rel="self" type="application/rss+xml"/>
{items_xml}  </channel>
</rss>
"""
    feed_path.write_text(rss_xml.strip() + "\n", encoding="utf-8")
    print(f"✓ Generated Press RSS Feed: {feed_path}")

def dispatch_webhook():
    webhook_url = os.getenv("PR_WEBHOOK_URL")
    if not webhook_url:
        print("• Notice: PR_WEBHOOK_URL not configured. Skipping external webhook broadcast.")
        return
        
    latest_pr = PRESS_RELEASES[0]
    payload = {
        "content": f"📢 **New Press Release on Surplus Docket Newsroom**\n\n**{latest_pr['headline']}**\n{latest_pr['summary']}\n\n🔗 Read Full Release: https://surplusdocket.com/press/releases/{latest_pr['slug']}.html",
        "username": "Surplus Docket Wire Bot"
    }
    
    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "SurplusDocket-PR-Bot/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"✓ Webhook broadcast dispatched (HTTP {resp.status})")
    except Exception as e:
        print(f"⚠️ Webhook dispatch note: {e}")

def run():
    print("🚀 Running Surplus Docket Press Release & Newsroom Engine...")
    for pr in PRESS_RELEASES:
        generate_individual_press_release(pr)
    generate_press_newsroom()
    generate_press_rss()
    dispatch_webhook()
    print("🎉 Press Releases, Newsroom, and RSS Syndication complete!")

if __name__ == "__main__":
    run()
