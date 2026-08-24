#!/usr/bin/env python3
"""
Surplus Docket — Press Release & Media Newsroom Engine
Generates AP-style wire press releases, dedicated /press/ newsroom hub,
and structured NewsArticle JSON-LD for rapid Google News and media syndication.
"""

import json
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parent.parent
SITE_DIR = ROOT_DIR / "site"
PRESS_DIR = SITE_DIR / "press"
RELEASES_DIR = PRESS_DIR / "releases"
SYNDICATE_DIR = ROOT_DIR / "marketing" / "syndicate" / "press_releases"

PRESS_DIR.mkdir(parents=True, exist_ok=True)
RELEASES_DIR.mkdir(parents=True, exist_ok=True)
SYNDICATE_DIR.mkdir(parents=True, exist_ok=True)

PRESS_RELEASES = [
    {
        "slug": "surplus-docket-launches-autonomous-legal-intelligence-platform",
        "date": "August 24, 2026",
        "iso_date": "2026-08-24T07:00:00-04:00",
        "headline": "Surplus Docket Launches Autonomous Public Records Intelligence Platform for Asset Recovery Counsel Across Florida, Texas, and Georgia",
        "subheadline": "New legal-tech data pipeline eliminates dead bank leads with automated institutional lien pre-filtering and daily 7:00 AM court registry feeds.",
        "location": "WEST PALM BEACH, Fla. & HOUSTON, Tex.",
        "summary": "Surplus Docket officially announced the launch of its autonomous public records intelligence platform, providing structured, case-verified tax deed surplus and excess proceeds feeds to asset recovery attorneys, title counsel, and real estate practitioners.",
        "body_paragraphs": [
            "Surplus Docket today announced the public launch of its autonomous legal data intelligence platform, engineered specifically for law firms, title searchers, and asset recovery practitioners specializing in county tax deed surplus and court excess proceeds retrieval.",
            "Across the United States, hundreds of millions of dollars in excess auction proceeds remain unclaimed in county clerk and district court registries following tax deed foreclosure sales. However, legal practitioners have historically faced significant operational friction, spending hours manually scraping fragmented county clerk portals only to encounter records encumbered by senior mortgage liens and institutional bank claims.",
            "Surplus Docket solves this industry bottleneck by deploying an automated data pipeline that scrubs institutional bank liens, junior mortgage servicers, and HOA encumbrances from raw clerk lists. The platform delivers pure, case-verified individual and estate heir claims directly to subscribers every morning at 7:00 AM EST in CSV, XLSX, and programmatic REST JSON formats.",
            "\"Our mission is to bring institutional data cleanliness to the asset recovery legal sector,\" said the Product Architecture Team at Surplus Docket. \"By replacing unscrubbed PDF lists with case-verifiable court docket metadata and automated statutory deadline tracking, we allow recovery counsel to file petitions within days of auction confirmation instead of weeks.\"",
            "The platform launches with comprehensive monitoring across 12 high-volume judicial circuits in Florida (under Fla. Stat. § 197.582), Texas (under Tex. Tax Code § 34.04), and Georgia (under O.C.G.A. § 48-4-5), representing over 92% of total statewide surplus proceeds volume in those jurisdictions.",
            "In addition to daily automated feeds, Surplus Docket provides all subscribers with a complete Asset Recovery Practitioner Toolkit featuring court-ready petition templates, client retainer agreements, statutory fee calculators, and a self-service Stripe billing portal."
        ]
    },
    {
        "slug": "surplus-docket-unveils-rest-api-for-law-practice-management",
        "date": "August 17, 2026",
        "iso_date": "2026-08-17T07:00:00-04:00",
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
    <header class="bg-brand-navy border-b border-slate-800 text-white sticky top-0 z-40">
        <div class="max-w-5xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
            <a href="/" class="flex items-center gap-2.5">
                <img src="/assets/logo_surplus_docket.png?v=6" alt="Surplus Docket" class="h-8 w-auto">
                <span class="font-heading font-black text-xl tracking-tight text-white">SURPLUS<span class="text-brand-green">DOCKET</span></span>
            </a>
            <div class="flex items-center gap-4 text-xs font-bold">
                <a href="/press/" class="text-emerald-300 hover:text-white">&larr; Newsroom</a>
                <a href="/" class="text-slate-300 hover:text-white">Home</a>
                <a href="/#pricing" class="px-3.5 py-1.5 bg-brand-green hover:bg-brand-greenDark text-white rounded-lg transition-colors">Get Data Feeds</a>
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
            
            <div class="my-8 p-6 bg-slate-100 rounded-xl border border-slate-200">
                <h3 class="text-xs font-bold uppercase tracking-wider text-brand-navy mb-2">About Surplus Docket</h3>
                <p class="text-xs text-slate-600 leading-relaxed mb-4">
                    {BOILERPLATE.split('About Surplus Docket\n')[1]}
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

    <!-- Footer -->
    <footer class="bg-white border-t border-slate-200 py-8 text-center text-xs text-slate-500">
        <div class="max-w-4xl mx-auto px-4">
            <p>&copy; 2026 Surplus Docket. All rights reserved. Official Newsroom.</p>
        </div>
    </footer>

</body>
</html>"""
    
    file_path = RELEASES_DIR / f"{pr['slug']}.html"
    file_path.write_text(html, encoding="utf-8")
    print(f"  ✓ Generated Press Release: {file_path.name}")
    
    # Also write plain text / Markdown wire draft in syndicate
    text_path = SYNDICATE_DIR / f"{pr['slug']}.txt"
    text_content = f"""FOR IMMEDIATE RELEASE

{pr['headline'].upper()}
{pr['subheadline']}

{pr['location']} — {pr['body_paragraphs'][0]}

{"\n\n".join(pr['body_paragraphs'][1:])}

###

{BOILERPLATE}

{MEDIA_CONTACT}
"""
    text_path.write_text(text_content, encoding="utf-8")
    print(f"  ✓ Generated Wire Text: {text_path.name}")

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
    <header class="bg-brand-navy border-b border-slate-800 text-white sticky top-0 z-40">
        <div class="max-w-5xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
            <a href="/" class="flex items-center gap-2.5">
                <img src="/assets/logo_surplus_docket.png?v=6" alt="Surplus Docket" class="h-8 w-auto">
                <span class="font-heading font-black text-xl tracking-tight text-white">SURPLUS<span class="text-brand-green">DOCKET</span></span>
            </a>
            <div class="flex items-center gap-4 text-xs font-bold">
                <a href="/" class="text-slate-300 hover:text-white">Home</a>
                <a href="/blog/" class="text-slate-300 hover:text-white">Articles</a>
                <a href="/api-documentation.html" class="text-slate-300 hover:text-white">API</a>
                <a href="/#pricing" class="px-3.5 py-1.5 bg-brand-green hover:bg-brand-greenDark text-white rounded-lg transition-colors">Get Feeds</a>
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
            <p class="text-xs sm:text-sm text-slate-600 leading-relaxed">
                Official corporate announcements, product launches, legal-tech datasets, and media resources from Surplus Docket.
            </p>
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

    <!-- Footer -->
    <footer class="bg-white border-t border-slate-200 py-10 text-center text-xs text-slate-500">
        <div class="max-w-4xl mx-auto px-4 flex flex-col items-center">
            <nav class="flex flex-wrap items-center justify-center gap-4 font-semibold text-slate-600 mb-4">
                <a href="/" class="hover:text-brand-green">Home</a>
                <a href="/press/" class="hover:text-brand-green">Press Newsroom</a>
                <a href="/blog/" class="hover:text-brand-green">Articles</a>
                <a href="/api-documentation.html" class="hover:text-brand-green">API Docs</a>
                <a href="/terms.html" class="hover:text-brand-green">Terms</a>
                <a href="/refund-policy.html" class="hover:text-brand-green">Refunds</a>
            </nav>
            <p>&copy; 2026 Surplus Docket. All rights reserved.</p>
        </div>
    </footer>

</body>
</html>"""

    newsroom_path = PRESS_DIR / "index.html"
    newsroom_path.write_text(html, encoding="utf-8")
    print(f"✓ Generated Press Newsroom: {newsroom_path}")

def run():
    print("🚀 Running Surplus Docket Press Release & Newsroom Engine...")
    for pr in PRESS_RELEASES:
        generate_individual_press_release(pr)
    generate_press_newsroom()
    print("🎉 Press Releases and Media Newsroom generated successfully!")

if __name__ == "__main__":
    run()
