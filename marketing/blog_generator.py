#!/usr/bin/env python3
"""
Surplus Docket - Autonomous Legal Blog & Market Intelligence Engine
===================================================================
1. Programmatically analyzes newly indexed tax deed dockets and state statutes.
2. Generates comprehensive, SEO-optimized legal articles in site/blog/posts/.
3. Updates site/blog/index.html with the latest research articles.
4. Injects Schema.org Article JSON-LD, canonical tags, and Stripe CTAs.
"""

import os
import sys
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
from compliance.content_fact_checker import verify_content_integrity, generate_fact_check_badge_html

SITE_DIR = BASE_DIR / "site"
BLOG_DIR = SITE_DIR / "blog"
POSTS_DIR = BLOG_DIR / "posts"
EXPORTS_DIR = BASE_DIR / "exports"

POSTS_DIR.mkdir(parents=True, exist_ok=True)

# Master Blog Post Registry / Archive
ARTICLES = [
    {
        "slug": "florida-tax-deed-surplus-guide-fl-197-582",
        "title": "Florida Tax Deed Surplus Recovery: A Practical Guide to Fla. Stat. § 197.582",
        "excerpt": "An in-depth legal analysis of the 120-day claim window, clerk notice procedures, statutory priority of liens, and the 20% representative fee cap under Florida law.",
        "category": "Florida Legal Framework",
        "date": "2026-08-22",
        "read_time": "6 min read",
        "keywords": "Florida tax deed surplus, Fla. Stat. 197.582, clerk of court surplus funds, Florida excess proceeds attorney",
        "content_html": """
        <p class="text-base text-slate-700 leading-relaxed mb-6">
            In Florida tax deed sales conducted by county clerks of court, when competitive bidding drives the final purchase price above the opening statutory bid, the excess balance is retained by the Clerk of the Circuit Court as <strong>tax deed surplus funds</strong> pursuant to <strong>Florida Statute § 197.582</strong>.
        </p>

        <h2 class="text-2xl font-heading font-black text-brand-navy mt-8 mb-4">1. The Statutory Framework and Clerk Notice</h2>
        <p class="text-base text-slate-700 leading-relaxed mb-6">
            Under Fla. Stat. § 197.582(2), within 90 days following the payment of surplus funds from a tax deed sale, the clerk of court must issue formal notice to all persons who held an interest of record on the date of the sale. This notice is mailed to the addresses listed in the tax collector's statement.
        </p>

        <div class="bg-brand-canvas border-l-4 border-brand-green p-6 my-6 rounded-r-xl">
            <p class="text-sm font-semibold text-brand-navy mb-1">Critical 120-Day Claim Window:</p>
            <p class="text-xs text-slate-600">
                Lienholders and property owners must file a notarized claim with the clerk of court within 120 days from the date of the clerk's statutory notice. Failure to timely file may result in the forfeiture of priority or remission to the Florida Department of Financial Services.
            </p>
        </div>

        <h2 class="text-2xl font-heading font-black text-brand-navy mt-8 mb-4">2. Order of Lien Seniority</h2>
        <p class="text-base text-slate-700 leading-relaxed mb-6">
            Florida law strictly dictates the order in which surplus funds are disbursed:
        </p>
        <ul class="list-disc list-inside space-y-2 text-sm text-slate-700 mb-6">
            <li><strong>First Priority:</strong> Governmental liens (municipal code enforcement, federal tax liens, state tax warrants).</li>
            <li><strong>Second Priority:</strong> Senior recorded mortgagees and judgment creditors based on recording priority (first in time, first in right).</li>
            <li><strong>Third Priority:</strong> Junior encumbrances and HOA/condo assessment liens.</li>
            <li><strong>Residual Estate:</strong> The former titled record owner or their legal estate heirs.</li>
        </ul>

        <h2 class="text-2xl font-heading font-black text-brand-navy mt-8 mb-4">3. Third-Party Representation & Fee Caps</h2>
        <p class="text-base text-slate-700 leading-relaxed mb-6">
            Florida Statute § 197.582 establishes strict consumer protections regarding third-party surplus finders and non-attorney representatives. Agreements to assist an owner in recovering surplus funds are capped at <strong>20% of the total amount recovered</strong>, and must contain explicit statutory disclosures.
        </p>

        <div class="bg-brand-navy text-white rounded-2xl p-8 my-10 shadow-xl text-center">
            <h3 class="text-2xl font-heading font-black mb-2">Automate Your Florida Surplus Docket Pipeline</h3>
            <p class="text-slate-300 text-sm max-w-xl mx-auto mb-6">
                Receive fresh, case-verified tax deed surplus dockets across Orange, Palm Beach, Miami-Dade, and Hillsborough counties every business morning at 7:00 AM EST.
            </p>
            <a href="https://buy.stripe.com/bJe9AT15Yazp2Dz7O60ZW1X" target="_blank" rel="noopener noreferrer" class="inline-block px-8 py-3.5 bg-brand-green hover:bg-brand-greenDark text-white font-heading font-bold rounded-lg shadow-lg transition-all">
                Subscribe to Multi-State Feed (FL, TX, GA) — $249/mo
            </a>
        </div>
        """
    },
    {
        "slug": "texas-tax-sale-excess-proceeds-court-registry-guide",
        "title": "Texas Tax Sale Excess Proceeds: Filing Petitions under Tex. Tax Code § 34.04",
        "excerpt": "How excess funds from Texas tax warrant and judicial foreclosure sales are deposited into district court registries, with procedural rules for formal judicial petitions.",
        "category": "Texas Legal Framework",
        "date": "2026-08-22",
        "read_time": "5 min read",
        "keywords": "Texas tax sale excess proceeds, Texas Tax Code 34.04, Harris County excess funds, Dallas district clerk excess proceeds",
        "content_html": """
        <p class="text-base text-slate-700 leading-relaxed mb-6">
            Unlike states with administrative clerk claim systems, Texas handles tax sale overages through formal judicial mechanisms. Under <strong>Texas Tax Code § 34.04</strong>, proceeds from a sheriff or constable tax foreclosure sale that exceed delinquent taxes, penalties, interest, and court costs must be remitted into the <strong>registry of the court</strong> that issued the order of sale.
        </p>

        <h2 class="text-2xl font-heading font-black text-brand-navy mt-8 mb-4">1. The Two-Year Statute of Limitations</h2>
        <p class="text-base text-slate-700 leading-relaxed mb-6">
            Under Tex. Tax Code § 34.04(a), a person claiming an interest in excess proceeds must file a formal petition in the district court within <strong>two (2) years from the date of the sale</strong>. If no petition is adjudicated within this 2-year window, the court clerk transfers the unclaimed balance to the county general fund.
        </p>

        <h2 class="text-2xl font-heading font-black text-brand-navy mt-8 mb-4">2. Procedural Petition Requirements</h2>
        <p class="text-base text-slate-700 leading-relaxed mb-6">
            A proper Texas excess proceeds petition must be filed in the original tax suit cause number and must include:
        </p>
        <ul class="list-disc list-inside space-y-2 text-sm text-slate-700 mb-6">
            <li>Formal service of citation on the taxing units and all parties to the underlying judgment.</li>
            <li>Proof of title or lien seniority as of the date of the judgment.</li>
            <li>A certified copy of the deed, probate letters of administration, or recorded assignment.</li>
        </ul>

        <div class="bg-brand-navy text-white rounded-2xl p-8 my-10 shadow-xl text-center">
            <h3 class="text-2xl font-heading font-black mb-2">Track Texas District Court Registries Daily</h3>
            <p class="text-slate-300 text-sm max-w-xl mx-auto mb-6">
                Never miss newly deposited excess funds in Harris County (Houston), Dallas County, and major Texas district courts.
            </p>
            <a href="https://buy.stripe.com/bJe9AT15Yazp2Dz7O60ZW1X" target="_blank" rel="noopener noreferrer" class="inline-block px-8 py-3.5 bg-brand-green hover:bg-brand-greenDark text-white font-heading font-bold rounded-lg shadow-lg transition-all">
                Subscribe to Multi-State Feed (FL, TX, GA) — $249/mo
            </a>
        </div>
        """
    },
    {
        "slug": "institutional-lien-filtering-asset-recovery",
        "title": "Why Institutional Lien Pre-Filtering Multiplies Recovery Law Firm ROI",
        "excerpt": "How raw county clerk lists waste hundreds of billable hours on mortgage servicers and bank liens, and how automated pre-filtering isolates recoverable owner equity.",
        "category": "Data Intelligence & Workflow",
        "date": "2026-08-22",
        "read_time": "4 min read",
        "keywords": "surplus fund filtering, tax deed lead scrubbing, asset recovery automation, legal CRM surplus feeds",
        "content_html": """
        <p class="text-base text-slate-700 leading-relaxed mb-6">
            Law firms and asset recovery specialists entering the tax deed surplus market quickly encounter a major bottleneck: <strong>raw public clerk lists are cluttered with dead-end institutional records</strong>.
        </p>

        <h2 class="text-2xl font-heading font-black text-brand-navy mt-8 mb-4">The Institutional Encumbrance Problem</h2>
        <p class="text-base text-slate-700 leading-relaxed mb-6">
            When a residential or commercial property sells at tax auction, institutional first mortgagees (e.g. Wells Fargo, Bank of America, Fannie Mae) often hold superior recorded liens that consume 100% of the surplus balance. Reaching out to former owners on cases with massive unsatisfied senior mortgages results in wasted title fees, uncollectible retainers, and lost attorney hours.
        </p>

        <h2 class="text-2xl font-heading font-black text-brand-navy mt-8 mb-4">How Automated Algorithmic Filtering Works</h2>
        <p class="text-base text-slate-700 leading-relaxed mb-6">
            Surplus Docket's data engine normalizes public county filings and filters out recognized banking institutions, servicers, and secondary lienholders. The result is a clean, prioritized data feed consisting of:
        </p>
        <ul class="list-disc list-inside space-y-2 text-sm text-slate-700 mb-6">
            <li>Direct individual property owners with substantial equity balances.</li>
            <li>Estate and probate heir situations where title had passed to heirs prior to sale.</li>
            <li>Clear case docket numbers, parcel situs addresses, and statutory fee calculation benchmarks.</li>
        </ul>

        <div class="bg-brand-navy text-white rounded-2xl p-8 my-10 shadow-xl text-center">
            <h3 class="text-2xl font-heading font-black mb-2">Get Pre-Filtered Clean Feeds Every Morning</h3>
            <p class="text-slate-300 text-sm max-w-xl mx-auto mb-6">
                Receive standardized CSV and Excel feeds ready for instant import into your firm's CRM.
            </p>
            <a href="https://buy.stripe.com/bJe9AT15Yazp2Dz7O60ZW1X" target="_blank" rel="noopener noreferrer" class="inline-block px-8 py-3.5 bg-brand-green hover:bg-brand-greenDark text-white font-heading font-bold rounded-lg shadow-lg transition-all">
                Subscribe to Multi-State Feed (FL, TX, GA) — $249/mo
            </a>
        </div>
        """
    }
]


def render_article_page(article):
    """Renders a standalone SEO-optimized article page with JSON-LD Schema after passing fact-check audit."""
    post_file = POSTS_DIR / f"{article['slug']}.html"
    
    # Pre-publication editorial & statutory fact-check sentinel
    fact_check_cert = verify_content_integrity(
        title=article['title'],
        content_text=article['content_html'],
        pub_date_str=article['date'],
        category=article['category']
    )
    fact_check_badge = generate_fact_check_badge_html(fact_check_cert)
    
    html = f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{article['title']} | Surplus Docket Legal Insights</title>
    <meta name="description" content="{article['excerpt']}">
    <link rel="canonical" href="https://surplusdocket.com/blog/posts/{article['slug']}.html">
    <meta name="keywords" content="{article['keywords']}">
    <link rel="icon" type="image/png" href="/assets/favicon.png">
    
    <!-- OpenGraph & Twitter Cards -->
    <meta property="og:title" content="{article['title']}">
    <meta property="og:description" content="{article['excerpt']}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="https://surplusdocket.com/blog/posts/{article['slug']}.html">
    <meta property="article:published_time" content="{article['date']}">
    
    <!-- JSON-LD Article Schema -->
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "Article",
      "headline": "{article['title']}",
      "description": "{article['excerpt']}",
      "datePublished": "{article['date']}",
      "author": {{
        "@type": "Organization",
        "name": "Surplus Docket Research Team",
        "url": "https://surplusdocket.com/"
      }},
      "publisher": {{
        "@type": "Organization",
        "name": "Surplus Docket",
        "logo": {{
          "@type": "ImageObject",
          "url": "https://surplusdocket.com/assets/favicon.png"
        }}
      }}
    }}
    </script>
    
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800;900&display=swap" rel="stylesheet">
    
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    fontFamily: {{
                        sans: ['Inter', 'sans-serif'],
                        heading: ['Plus Jakarta Sans', 'sans-serif'],
                    }},
                    colors: {{
                        brand: {{
                            green: '#4c6d48',
                            greenDark: '#365134',
                            greenSoft: '#edf3ec',
                            navy: '#1b365d',
                            navyDark: '#102238',
                            canvas: '#f8f8f4',
                        }}
                    }}
                }}
            }}
        }}
    </script>
    <style>
        h1, h2, h3, h4, h5 {{
            text-wrap: balance;
            letter-spacing: -0.015em;
        }}
        p, li {{
            text-wrap: pretty;
        }}
    </style>
</head>
<body class="antialiased min-h-screen flex flex-col font-sans bg-brand-canvas text-slate-700">

    <!-- Header -->
    <header class="w-full border-b border-slate-200 bg-white/95 backdrop-blur-md sticky top-0 z-50 shadow-sm">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 py-3 flex items-center justify-between">
            <a href="/" class="flex items-center gap-3 group">
                <img src="/assets/logo_surplus_docket.png?v=6" alt="Surplus Docket" class="h-8 sm:h-10 w-auto object-contain transition-transform group-hover:scale-105 shrink-0">
                <div class="flex items-baseline gap-1.5 leading-none">
                    <span class="font-heading font-black text-xl text-brand-green">SURPLUS</span>
                    <span class="font-heading font-black text-xl text-brand-navy">DOCKET</span>
                </div>
            </a>
            <div class="flex items-center gap-2.5 sm:gap-4">
                <a href="/blog/" class="text-xs sm:text-sm font-semibold text-slate-600 hover:text-brand-green transition-colors">All Articles</a>
                <a href="https://billing.stripe.com/p/login/bJe28r4iagXN4LHb0i0ZW00" target="_blank" rel="noopener noreferrer" class="hidden sm:inline-flex text-xs font-heading font-bold text-slate-600 hover:text-brand-navy border border-slate-300 bg-white px-3 py-2 rounded-lg transition-all shadow-sm">Billing Portal</a>
                <a href="https://buy.stripe.com/bJe9AT15Yazp2Dz7O60ZW1X" target="_blank" rel="noopener noreferrer" class="text-xs sm:text-sm font-heading font-bold bg-brand-green hover:bg-brand-greenDark text-white px-4 sm:px-5 py-2.5 rounded-lg shadow-sm transition-all">
                    Subscribe
                </a>
            </div>
        </div>
    </header>

    <main class="flex-grow max-w-4xl mx-auto px-4 py-16 w-full">
        <div class="mb-8">
            <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-brand-green/30 bg-brand-greenSoft text-brand-greenDark text-xs font-bold uppercase tracking-wider mb-4">
                {article['category']}
            </div>
            <h1 class="text-3xl md:text-5xl font-heading font-black text-brand-navy mb-4 leading-tight">
                {article['title']}
            </h1>
            <div class="flex items-center gap-4 text-xs font-semibold text-slate-500 border-b border-slate-200 pb-6">
                <span>Published: {article['date']}</span>
                <span>•</span>
                <span>{article['read_time']}</span>
                <span>•</span>
                <span>Surplus Docket Research Team</span>
            </div>
        </div>

        <article class="bg-white border border-slate-200 rounded-2xl p-8 md:p-12 shadow-sm">
            {article['content_html']}
            {fact_check_badge}
        </article>

        <div class="mt-8 text-center">
            <a href="/blog/" class="text-sm font-bold text-brand-green hover:underline">&larr; Back to All Legal Articles & Guides</a>
        </div>
    </main>

    <!-- Footer -->
    <footer class="bg-white border-t border-slate-200 py-12 text-center px-4">
        <div class="max-w-4xl mx-auto flex flex-col items-center">
            <!-- Centered Brand Lockup -->
            <a href="/" class="flex items-center gap-3 mb-6 group">
                <img src="/assets/logo_surplus_docket.png?v=6" alt="Surplus Docket" class="h-8 sm:h-10 w-auto object-contain transition-transform group-hover:scale-105 shrink-0">
                <div class="flex items-baseline gap-1.5 leading-none">
                    <span class="font-heading font-black text-lg sm:text-2xl text-brand-green">SURPLUS</span>
                    <span class="font-heading font-black text-lg sm:text-2xl text-brand-navy">DOCKET</span>
                </div>
            </a>
            
            <!-- Simple, Clean Centered Navigation Bar -->
                        <!-- Condensed & Responsive Footer Navigation -->
            <nav class="flex flex-wrap items-center justify-center gap-x-3 sm:gap-x-5 gap-y-2 text-xs sm:text-xs font-semibold text-slate-600 mb-6 max-w-2xl px-2">
                <a href="/florida-tax-deed-surplus.html" class="hover:text-brand-green transition-colors">FL Feed</a>
                <span class="text-slate-300 hidden sm:inline">•</span>
                <a href="/texas-tax-sale-excess-proceeds.html" class="hover:text-brand-green transition-colors">TX Feed</a>
                <span class="text-slate-300 hidden sm:inline">•</span>
                <a href="/georgia-tax-sale-excess-funds.html" class="hover:text-brand-green transition-colors">GA Feed</a>
                <span class="text-slate-300 hidden sm:inline">•</span>
                <a href="/practitioner-toolkit.html" class="hover:text-brand-green transition-colors">Toolkit</a>
                <span class="text-slate-300 hidden sm:inline">•</span>
                <a href="/comparison.html" class="hover:text-brand-green transition-colors">Comparison</a>
                <span class="text-slate-300 hidden sm:inline">•</span>
                <a href="/methodology.html" class="hover:text-brand-green transition-colors">Methodology</a>
                <span class="text-slate-300 hidden sm:inline">•</span>
                <a href="/api-documentation.html" class="hover:text-brand-green transition-colors">API</a>
                <span class="text-slate-300 hidden sm:inline">•</span>
                <a href="/blog/" class="hover:text-brand-green transition-colors">Articles</a>
                <span class="text-slate-300 hidden sm:inline">•</span>
                <a href="/press/" class="hover:text-brand-green transition-colors">Press</a>
                <span class="text-slate-300 hidden sm:inline">•</span>
                <a href="/#pricing" class="hover:text-brand-green transition-colors">Pricing</a>
                <span class="text-slate-300 hidden sm:inline">•</span>
                <a href="/terms.html" class="hover:text-brand-green transition-colors">Terms</a>
                <span class="text-slate-300 hidden sm:inline">•</span>
                <a href="/refund-policy.html" class="hover:text-brand-green transition-colors">Refunds</a>
                <span class="text-slate-300 hidden sm:inline">•</span>
                <a href="https://billing.stripe.com/p/login/bJe28r4iagXN4LHb0i0ZW00" target="_blank" rel="noopener noreferrer" class="hover:text-brand-green transition-colors font-bold text-brand-navy">Customer Portal</a>
            </nav>
            
                        <div class="text-center text-xs text-slate-400 w-full pt-6 border-t border-slate-200">
                <p>&copy; 2026 Surplus Docket. All rights reserved.</p>
            </div>
        </div>
    </footer>

    

    <script>
        
        
        
    </script>
</body>
</html>"""
    post_file.write_text(html.strip(), encoding="utf-8")
    print(f"  [✓] Generated Article: {post_file.name}")


def render_blog_index():
    """Renders the main blog directory hub at site/blog/index.html."""
    index_file = BLOG_DIR / "index.html"
    
    cards_html = ""
    for art in ARTICLES:
        cards_html += f"""
        <div class="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm hover:shadow-md transition-all flex flex-col justify-between">
            <div>
                <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-brand-green/30 bg-brand-greenSoft text-brand-greenDark text-xs font-bold uppercase tracking-wider mb-4">
                    {art['category']}
                </div>
                <h2 class="text-2xl font-heading font-bold text-brand-navy mb-3 hover:text-brand-green transition-colors">
                    <a href="/blog/posts/{art['slug']}.html">{art['title']}</a>
                </h2>
                <p class="text-sm text-slate-600 leading-relaxed mb-6">
                    {art['excerpt']}
                </p>
            </div>
            <div class="flex items-center justify-between pt-4 border-t border-slate-100 text-xs font-semibold text-slate-500">
                <span>{art['date']} • {art['read_time']}</span>
                <a href="/blog/posts/{art['slug']}.html" class="text-brand-green font-bold hover:underline">Read Analysis &rarr;</a>
            </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Legal Insights & Statutory Guides | Surplus Docket</title>
    <meta name="description" content="Expert legal breakdowns, statutory guides, and public records analysis on Florida and Texas tax deed surplus funds and court registry excess proceeds.">
    <link rel="canonical" href="https://surplusdocket.com/blog/">
    <link rel="icon" type="image/png" href="/assets/favicon.png">
    
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800;900&display=swap" rel="stylesheet">
    
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    fontFamily: {{
                        sans: ['Inter', 'sans-serif'],
                        heading: ['Plus Jakarta Sans', 'sans-serif'],
                    }},
                    colors: {{
                        brand: {{
                            green: '#4c6d48',
                            greenDark: '#365134',
                            greenSoft: '#edf3ec',
                            navy: '#1b365d',
                            canvas: '#f8f8f4',
                        }}
                    }}
                }}
            }}
        }}
    </script>
    <style>
        h1, h2, h3, h4, h5 {{
            text-wrap: balance;
            letter-spacing: -0.015em;
        }}
        p, li {{
            text-wrap: pretty;
        }}
    </style>
</head>
<body class="antialiased min-h-screen flex flex-col font-sans bg-brand-canvas text-slate-700">

    <!-- Header -->
    <header class="w-full border-b border-slate-200 bg-white/95 backdrop-blur-md sticky top-0 z-50 shadow-sm">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 py-3 flex items-center justify-between">
            <a href="/" class="flex items-center gap-3 group">
                <img src="/assets/logo_surplus_docket.png?v=6" alt="Surplus Docket" class="h-8 sm:h-10 w-auto object-contain transition-transform group-hover:scale-105 shrink-0">
                <div class="flex items-baseline gap-1.5 leading-none">
                    <span class="font-heading font-black text-xl text-brand-green">SURPLUS</span>
                    <span class="font-heading font-black text-xl text-brand-navy">DOCKET</span>
                </div>
            </a>
            <div class="flex items-center gap-2.5 sm:gap-4">
                <a href="/" class="text-xs sm:text-sm font-semibold text-slate-600 hover:text-brand-green transition-colors">Main Hub</a>
                <a href="/api-documentation.html" class="hidden md:inline-block text-xs sm:text-sm font-semibold text-slate-600 hover:text-brand-green transition-colors">API Docs</a>
                <a href="https://billing.stripe.com/p/login/bJe28r4iagXN4LHb0i0ZW00" target="_blank" rel="noopener noreferrer" class="hidden sm:inline-flex text-xs font-heading font-bold text-slate-600 hover:text-brand-navy border border-slate-300 bg-white px-3 py-2 rounded-lg transition-all shadow-sm">Billing Portal</a>
                <a href="https://buy.stripe.com/bJe9AT15Yazp2Dz7O60ZW1X" target="_blank" rel="noopener noreferrer" class="text-xs sm:text-sm font-heading font-bold bg-brand-green hover:bg-brand-greenDark text-white px-4 sm:px-5 py-2.5 rounded-lg shadow-sm transition-all">
                    Subscribe
                </a>
            </div>
        </div>
    </header>

    <main class="flex-grow max-w-6xl mx-auto px-4 py-16 w-full">
        <div class="text-center mb-16 max-w-3xl mx-auto">
            <div class="inline-flex items-center gap-2 px-3.5 py-1 rounded-full border border-brand-green/30 bg-brand-greenSoft text-brand-greenDark text-xs font-bold uppercase tracking-wider mb-4">
                Public Records Research & Law Guides
            </div>
            <h1 class="text-4xl md:text-5xl font-heading font-black text-brand-navy mb-4">
                Legal Intelligence & Statutory Guides
            </h1>
            <p class="text-slate-600 text-base md:text-lg">
                Practical analysis, statutory timelines, and court registry procedures for asset recovery law firms and property researchers.
            </p>
        </div>

        <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {cards_html}
        </div>
    </main>

    <!-- Footer -->
    <footer class="bg-white border-t border-slate-200 py-12 text-center px-4">
        <div class="max-w-4xl mx-auto flex flex-col items-center">
            <!-- Centered Brand Lockup -->
            <a href="/" class="flex items-center gap-3 mb-6 group">
                <img src="/assets/logo_surplus_docket.png?v=6" alt="Surplus Docket" class="h-8 sm:h-10 w-auto object-contain transition-transform group-hover:scale-105 shrink-0">
                <div class="flex items-baseline gap-1.5 leading-none">
                    <span class="font-heading font-black text-lg sm:text-2xl text-brand-green">SURPLUS</span>
                    <span class="font-heading font-black text-lg sm:text-2xl text-brand-navy">DOCKET</span>
                </div>
            </a>
            
            <!-- Simple, Clean Centered Navigation Bar -->
                        <!-- Condensed & Responsive Footer Navigation -->
            <nav class="flex flex-wrap items-center justify-center gap-x-3 sm:gap-x-5 gap-y-2 text-xs sm:text-xs font-semibold text-slate-600 mb-6 max-w-2xl px-2">
                <a href="/florida-tax-deed-surplus.html" class="hover:text-brand-green transition-colors">FL Feed</a>
                <span class="text-slate-300 hidden sm:inline">•</span>
                <a href="/texas-tax-sale-excess-proceeds.html" class="hover:text-brand-green transition-colors">TX Feed</a>
                <span class="text-slate-300 hidden sm:inline">•</span>
                <a href="/georgia-tax-sale-excess-funds.html" class="hover:text-brand-green transition-colors">GA Feed</a>
                <span class="text-slate-300 hidden sm:inline">•</span>
                <a href="/practitioner-toolkit.html" class="hover:text-brand-green transition-colors">Toolkit</a>
                <span class="text-slate-300 hidden sm:inline">•</span>
                <a href="/comparison.html" class="hover:text-brand-green transition-colors">Comparison</a>
                <span class="text-slate-300 hidden sm:inline">•</span>
                <a href="/methodology.html" class="hover:text-brand-green transition-colors">Methodology</a>
                <span class="text-slate-300 hidden sm:inline">•</span>
                <a href="/api-documentation.html" class="hover:text-brand-green transition-colors">API</a>
                <span class="text-slate-300 hidden sm:inline">•</span>
                <a href="/blog/" class="hover:text-brand-green transition-colors">Articles</a>
                <span class="text-slate-300 hidden sm:inline">•</span>
                <a href="/press/" class="hover:text-brand-green transition-colors">Press</a>
                <span class="text-slate-300 hidden sm:inline">•</span>
                <a href="/#pricing" class="hover:text-brand-green transition-colors">Pricing</a>
                <span class="text-slate-300 hidden sm:inline">•</span>
                <a href="/terms.html" class="hover:text-brand-green transition-colors">Terms</a>
                <span class="text-slate-300 hidden sm:inline">•</span>
                <a href="/refund-policy.html" class="hover:text-brand-green transition-colors">Refunds</a>
                <span class="text-slate-300 hidden sm:inline">•</span>
                <a href="https://billing.stripe.com/p/login/bJe28r4iagXN4LHb0i0ZW00" target="_blank" rel="noopener noreferrer" class="hover:text-brand-green transition-colors font-bold text-brand-navy">Customer Portal</a>
            </nav>
            
                        <div class="text-center text-xs text-slate-400 w-full pt-6 border-t border-slate-200">
                <p>&copy; 2026 Surplus Docket. All rights reserved.</p>
            </div>
        </div>
    </footer>

    

    <script>
        
        
        
    </script>
</body>
</html>"""
    index_file.write_text(html.strip(), encoding="utf-8")
    print(f"  [✓] Generated Blog Index Hub: {index_file.name}")


def main():
    print("=" * 60)
    print(" 📚 SURPLUS DOCKET — AUTONOMOUS BLOG & CONTENT ENGINE")
    print("=" * 60)
    for art in ARTICLES:
        render_article_page(art)
    render_blog_index()
    print("=" * 60)


if __name__ == "__main__":
    main()
