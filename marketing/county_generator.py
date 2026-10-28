#!/usr/bin/env python3
"""
Autonomous County Programmatic SEO Generator
Generates laser-focused, hyper-targeted County Landing Pages for top tax deed & excess proceeds jurisdictions.
"""

import os
import html
import json
import urllib.parse
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
SITE_DIR = BASE_DIR / 'site'
FEED_JSON_PATH = SITE_DIR / 'api' / 'v1' / 'feed.json'

COUNTIES = [
    {
        'slug': 'palm-beach-tax-deed-surplus.html',
        'county': 'Palm Beach County',
        'state': 'FL',
        'state_full': 'Florida',
        'city': 'West Palm Beach',
        'statute': 'Fla. Stat. § 197.582',
        'deadline': '120 Days from Clerk Notice',
        'fee_cap': '20% statutory limit for non-attorney filers',
        'clerk_name': 'Palm Beach County Clerk & Comptroller (Joseph Abruzzo)',
        'clerk_url': 'https://www.mypalmbeachclerk.com/',
        'description': 'Daily automated Palm Beach County tax deed surplus lead feed. Pre-filtered individual surplus claims and court registry intelligence for Florida recovery practitioners.'
    },
    {
        'slug': 'broward-county-tax-deed-surplus.html',
        'county': 'Broward County',
        'state': 'FL',
        'state_full': 'Florida',
        'city': 'Fort Lauderdale',
        'statute': 'Fla. Stat. § 197.582',
        'deadline': '120 Days from Clerk Notice',
        'fee_cap': '20% statutory limit under Florida law',
        'clerk_name': 'Broward County Clerk of the Circuit Court',
        'clerk_url': 'https://www.browardclerk.org/',
        'description': 'Daily automated Broward County / Fort Lauderdale tax deed surplus data feed. Verified clerk dockets and institutional entity filtering for recovery attorneys.'
    },
    {
        'slug': 'harris-county-excess-proceeds.html',
        'county': 'Harris County',
        'state': 'TX',
        'state_full': 'Texas',
        'city': 'Houston',
        'statute': 'Tex. Tax Code § 34.04',
        'deadline': '2 Years from Date of Tax Sale',
        'fee_cap': '25% statutory cap on recovery contingency',
        'clerk_name': 'Harris County District Clerk (Court Registry Division)',
        'clerk_url': 'https://www.hcdistrictclerk.com/',
        'description': 'Daily automated Harris County / Houston excess proceeds feed. Scrubbed court registry tax sale excess proceeds data for Texas recovery attorneys.'
    },
    {
        'slug': 'miami-dade-tax-deed-surplus.html',
        'county': 'Miami-Dade County',
        'state': 'FL',
        'state_full': 'Florida',
        'city': 'Miami',
        'statute': 'Fla. Stat. § 197.582',
        'deadline': '120 Days from Clerk Notice',
        'fee_cap': '20% statutory limit under Florida law',
        'clerk_name': 'Miami-Dade County Clerk of Courts (Tax Deed Unit)',
        'clerk_url': 'https://www.miamidadeclerk.gov/',
        'description': 'Daily automated Miami-Dade County tax deed surplus data feed. Filtered individual surplus equity with verified docket IDs for asset recovery lawyers.'
    },
    {
        'slug': 'orange-county-tax-deed-surplus.html',
        'county': 'Orange County',
        'state': 'FL',
        'state_full': 'Florida',
        'city': 'Orlando',
        'statute': 'Fla. Stat. § 197.582',
        'deadline': '120 Days from Clerk Notice',
        'fee_cap': '20% statutory recovery limit',
        'clerk_name': 'Orange County Comptroller (Tax Deed Administration)',
        'clerk_url': 'https://www.myorangeclerk.com/',
        'description': 'Daily Orange County / Orlando tax deed surplus leads. Case-verified dockets, statutory equity calculations, and filtered individual owner records.'
    },
    {
        'slug': 'hillsborough-tax-deed-surplus.html',
        'county': 'Hillsborough County',
        'state': 'FL',
        'state_full': 'Florida',
        'city': 'Tampa',
        'statute': 'Fla. Stat. § 197.582',
        'deadline': '120 Days from Clerk Notice',
        'fee_cap': '20% statutory limit under Florida law',
        'clerk_name': 'Hillsborough County Clerk of Court & Comptroller',
        'clerk_url': 'https://www.hillsclerk.com/',
        'description': 'Daily automated Hillsborough County / Tampa tax deed surplus feed. Instant CSV/Excel delivery of verified overage leads for asset recovery practitioners.'
    },
    {
        'slug': 'dallas-county-excess-proceeds.html',
        'county': 'Dallas County',
        'state': 'TX',
        'state_full': 'Texas',
        'city': 'Dallas',
        'statute': 'Tex. Tax Code § 34.04',
        'deadline': '2 Years from Date of Tax Sale',
        'fee_cap': '25% statutory cap on recovery fee',
        'clerk_name': 'Dallas County District Clerk (Civil Court Registry)',
        'clerk_url': 'https://www.dallascounty.org/',
        'description': 'Daily Dallas County tax sale excess proceeds records. Filtered court registry deposits, verified docket numbers, and statutory claim data.'
    },
    {
        'slug': 'tarrant-county-excess-proceeds.html',
        'county': 'Tarrant County',
        'state': 'TX',
        'state_full': 'Texas',
        'city': 'Fort Worth',
        'statute': 'Tex. Tax Code § 34.04',
        'deadline': '2 Years from Date of Tax Sale',
        'fee_cap': '25% statutory cap on recovery fee',
        'clerk_name': 'Tarrant County District Clerk (Civil Registry)',
        'clerk_url': 'https://www.tarrantcountytx.gov/',
        'description': 'Daily Tarrant County / Fort Worth tax sale excess proceeds feed. Pre-filtered court registry intelligence and statutory recovery data.'
    },
    {
        'slug': 'travis-county-excess-proceeds.html',
        'county': 'Travis County',
        'state': 'TX',
        'state_full': 'Texas',
        'city': 'Austin',
        'statute': 'Tex. Tax Code § 34.04',
        'deadline': '2 Years from Date of Tax Sale',
        'fee_cap': '25% statutory cap on recovery fee',
        'clerk_name': 'Travis County District Clerk (Civil Trust Division)',
        'clerk_url': 'https://www.traviscountytx.gov/',
        'description': 'Daily Travis County / Austin excess proceeds leads. Filtered district court tax foreclosure registry surplus intelligence.'
    },
    {
        'slug': 'fulton-county-excess-funds.html',
        'county': 'Fulton County',
        'state': 'GA',
        'state_full': 'Georgia',
        'city': 'Atlanta',
        'statute': 'O.C.G.A. § 48-4-5',
        'deadline': '5 Years from Date of Tax Sale',
        'fee_cap': 'Statutory claim priority & non-contingent fee models',
        'clerk_name': 'Fulton County Tax Commissioner (Excess Funds Division)',
        'clerk_url': 'https://www.fultonclerk.org/',
        'description': 'Daily Fulton County / Atlanta tax sale excess funds leads. Pre-filtered sheriff tax sale surplus intelligence for Georgia recovery attorneys.'
    },
    {
        'slug': 'cobb-county-excess-funds.html',
        'county': 'Cobb County',
        'state': 'GA',
        'state_full': 'Georgia',
        'city': 'Marietta',
        'statute': 'O.C.G.A. § 48-4-5',
        'deadline': '5 Years from Date of Tax Sale',
        'fee_cap': 'Statutory claim distribution rules',
        'clerk_name': 'Cobb County Sheriff & Superior Court Clerk',
        'clerk_url': 'https://www.cobbsheriff.org/',
        'description': 'Daily Cobb County / Marietta tax sale excess funds data feed. Clean individual surplus claims delivered in CSV/Excel every morning by 7:30 AM EST.'
    },
    {
        'slug': 'dekalb-county-excess-funds.html',
        'county': 'DeKalb County',
        'state': 'GA',
        'state_full': 'Georgia',
        'city': 'Decatur',
        'statute': 'O.C.G.A. § 48-4-5',
        'deadline': '5 Years from Date of Tax Sale',
        'fee_cap': 'Statutory claim distribution rules',
        'clerk_name': 'DeKalb County Tax Commissioner (Delinquent Tax Division)',
        'clerk_url': 'https://www.dekalbcountytax.org/',
        'description': 'Daily DeKalb County excess funds data feed. Clean, case-verified tax auction overages delivered in CSV/Excel every morning by 7:30 AM EST.'
    },
    {
        'slug': 'gwinnett-county-excess-funds.html',
        'county': 'Gwinnett County',
        'state': 'GA',
        'state_full': 'Georgia',
        'city': 'Lawrenceville',
        'statute': 'O.C.G.A. § 48-4-5',
        'deadline': '5 Years from Date of Tax Sale',
        'fee_cap': '20% statutory recovery benchmark',
        'clerk_name': 'Gwinnett County Tax Commissioner (Delinquent Tax & Excess Funds)',
        'clerk_url': 'https://www.gwinnetttaxcommissioner.com/property-tax-delinquent-tax-excess-funds',
        'description': 'Daily Gwinnett County / Lawrenceville tax sale excess funds feed. Verified parcel IDs, record owners, and official Tax Commissioner excess funds ledger intelligence.'
    },
    {
        'slug': 'san-diego-county-excess-proceeds.html',
        'county': 'San Diego County',
        'state': 'CA',
        'state_full': 'California',
        'city': 'San Diego',
        'statute': 'Cal. Rev. & Tax Code § 4675',
        'deadline': '1 Year from Tax Deed Recordation',
        'fee_cap': '20% practitioner fee benchmark',
        'clerk_name': 'San Diego County Treasurer-Tax Collector',
        'clerk_url': 'https://www.sdttc.com/content/ttc/en/tax-collection/Avail_Excess_Proceeds.html',
        'description': 'Daily San Diego County Chapter 7 tax sale excess proceeds feed. Verified Assessor Parcel Numbers (APNs), deed recordation windows, and excess proceeds pools.'
    },
    {
        'slug': 'los-angeles-county-excess-proceeds.html',
        'county': 'Los Angeles County',
        'state': 'CA',
        'state_full': 'California',
        'city': 'Los Angeles',
        'statute': 'Cal. Rev. & Tax Code § 4675',
        'deadline': '1 Year from Tax Deed Recordation',
        'fee_cap': '20% practitioner fee benchmark',
        'clerk_name': 'Los Angeles County Treasurer and Tax Collector',
        'clerk_url': 'https://ttc.lacounty.gov/public-auction-excess-proceeds/',
        'description': 'Daily Los Angeles County tax-defaulted auction excess proceeds feed. Verified APNs, statutory claim deadlines under RTC § 4675, and filtered individual records.'
    },
    {
        'slug': 'orange-county-ca-excess-proceeds.html',
        'county': 'Orange County',
        'state': 'CA',
        'state_full': 'California',
        'city': 'Santa Ana',
        'statute': 'Cal. Rev. & Tax Code § 4675',
        'deadline': '1 Year from Tax Deed Recordation',
        'fee_cap': '20% practitioner fee benchmark',
        'clerk_name': 'Orange County Treasurer-Tax Collector (Santa Ana, CA)',
        'clerk_url': 'https://www.octreasurer.gov/tax-auction-results',
        'description': 'Daily Orange County, California tax auction excess proceeds feed. Verified APNs and statutory claim windows under California Revenue & Taxation Code § 4675.'
    },
    {
        'slug': 'fort-bend-county-excess-proceeds.html',
        'county': 'Fort Bend County',
        'state': 'TX',
        'state_full': 'Texas',
        'city': 'Richmond',
        'statute': 'Tex. Tax Code § 34.04',
        'deadline': '2 Years from Date of Tax Sale',
        'fee_cap': '25% statutory cap (Tex. Tax Code § 34.04(i))',
        'clerk_name': 'Fort Bend County District Clerk (Trust & Excess Proceeds Registry)',
        'clerk_url': 'https://www.fortbendcountytx.gov/government/departments/district-clerk',
        'description': 'Daily Fort Bend County / Richmond Texas district court excess proceeds feed. Verified DCV cause numbers, registry balances, and 2-year statutory claim windows.'
    },
    {
        'slug': 'davidson-county-excess-proceeds.html',
        'county': 'Davidson County',
        'state': 'TN',
        'state_full': 'Tennessee',
        'city': 'Nashville',
        'statute': 'T.C.A. § 67-5-2501 & § 67-5-2702',
        'deadline': '1 Year Redemption / Chancery Court Registry Window',
        'fee_cap': '10% statutory finder cap / Attorney fee schedule',
        'clerk_name': 'Metropolitan Nashville & Davidson County Chancery Court Clerk & Master',
        'clerk_url': 'https://chanceryclerkandmaster.nashville.gov/delinquent-taxes/excess-proceeds/',
        'description': 'Daily Nashville / Davidson County Chancery Court tax sale excess proceeds feed. Verified Chancery Court docket numbers, parcels, and registry balances.'
    },
    {
        'slug': 'mecklenburg-county-tax-foreclosure-surplus.html',
        'county': 'Mecklenburg County',
        'state': 'NC',
        'state_full': 'North Carolina',
        'city': 'Charlotte',
        'statute': 'N.C.G.S. § 105-374(q) & § 1-339.71',
        'deadline': '10-Day Upset Bid + Special Proceeding Window',
        'fee_cap': 'Statutory attorney special proceeding schedule',
        'clerk_name': 'Mecklenburg County Clerk of Superior Court (Special Proceedings)',
        'clerk_url': 'https://www.nccourts.gov/locations/mecklenburg-county',
        'description': 'Daily Mecklenburg County / Charlotte judicial tax foreclosure surplus and special proceeding registry intelligence under N.C.G.S. § 105-374(q).'
    }
]

STATE_HUBS = {
    'FL': '/florida-tax-deed-surplus.html',
    'TX': '/texas-tax-sale-excess-proceeds.html',
    'GA': '/georgia-tax-sale-excess-funds.html',
    'NC': '/north-carolina-tax-foreclosure-surplus.html',
    'TN': '/tennessee-tax-sale-excess-proceeds.html',
    'CA': '/california-tax-defaulted-excess-proceeds.html',
}

STATE_BLOG_GUIDES = {
    'FL': ('Florida § 197.582 & § 45.032 Statutory Guide', '/blog/posts/florida-tax-deed-surplus-guide-fl-197-582.html'),
    'TX': ('Texas Tax Code § 34.04 District Court Guide', '/blog/posts/texas-tax-sale-excess-proceeds-court-registry-guide.html'),
    'GA': ('Georgia O.C.G.A. § 48-4-5 Excess Funds Guide', '/blog/posts/georgia-tax-sale-excess-funds-guide-ocga-48-4-5.html'),
    'NC': ('North Carolina N.C.G.S. § 105-374 Surplus Guide', '/blog/posts/north-carolina-tax-foreclosure-surplus-guide-ncgs-105-374.html'),
    'TN': ('Tennessee T.C.A. § 67-5-2501 Chancery Guide', '/blog/posts/tennessee-delinquent-tax-sale-surplus-guide-tca-67-5-2501.html'),
    'CA': ('California RTC § 4675 Excess Proceeds Guide', '/blog/posts/california-tax-defaulted-excess-proceeds-guide-rtc-4675.html'),
}


def load_live_feed_records():
    if not FEED_JSON_PATH.exists():
        return []
    try:
        data = json.loads(FEED_JSON_PATH.read_text(encoding='utf-8'))
        return data.get('records', [])
    except Exception:
        return []


def render_county_live_table(c, all_records):
    county_short = c['county'].replace(' County', '').strip().lower()
    state_code = c['state'].upper()
    matches = [
        r for r in all_records
        if str(r.get('State', '')).upper() == state_code
        and county_short in str(r.get('County', '')).lower()
    ]
    is_state_fallback = False
    if not matches:
        matches = [r for r in all_records if str(r.get('State', '')).upper() == state_code]
        is_state_fallback = True

    if not matches:
        return ""

    matches = sorted(matches, key=lambda r: float(r.get('Surplus_Balance_USD', 0) or 0), reverse=True)[:8]
    heading_label = (
        f"Verified {c['county']} Registry Filings (Live Sample)"
        if not is_state_fallback
        else f"Verified {c['state_full']} Statewide Registry Filings (Live Sample)"
    )

    rows_html = ""
    for r in matches:
        docket_id = str(r.get('docket_id') or r.get('Case_or_TaxDeed_No') or '').strip()
        display_case = html.escape(str(r.get('Case_or_TaxDeed_No') or docket_id))
        owner_redacted = html.escape(str(r.get('Owner_Name') or 'Redacted Owner'))
        county_name = html.escape(str(r.get('County') or county_short.title()))
        bal = float(r.get('Surplus_Balance_USD', 0) or 0)
        fee = float(r.get('Est_Finder_Fee_USD', 0) or (bal * (0.25 if state_code == 'TX' else 0.20)))
        docket_href = f"/docket.html?docket={urllib.parse.quote(docket_id)}"

        rows_html += f"""
                    <tr class="border-b border-slate-100 hover:bg-slate-50/80 transition-colors">
                        <td class="py-3 px-4 font-mono text-xs font-bold text-brand-navy">
                            <a href="{docket_href}" class="hover:text-brand-green underline">{display_case}</a>
                        </td>
                        <td class="py-3 px-4 text-xs text-slate-600">{county_name} Co., {state_code}</td>
                        <td class="py-3 px-4 text-xs text-slate-600 font-mono">{owner_redacted}</td>
                        <td class="py-3 px-4 text-xs font-mono font-bold text-emerald-700 text-right">${bal:,.2f}</td>
                        <td class="py-3 px-4 text-xs font-mono text-slate-600 text-right">${fee:,.2f}</td>
                        <td class="py-3 px-4 text-right">
                            <a href="{docket_href}" class="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-brand-navy hover:bg-brand-green text-white text-[11px] font-bold transition-colors">
                                View Dossier &rarr;
                            </a>
                        </td>
                    </tr>"""

    return f"""
        <!-- Live Verified County Docket Table -->
        <div class="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden mb-10">
            <div class="p-5 sm:p-6 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-slate-50">
                <div>
                    <span class="text-[11px] font-mono font-bold uppercase tracking-wider text-brand-green">Ground-Truth Verified Records</span>
                    <h2 class="font-heading font-bold text-base sm:text-lg text-brand-navy">{heading_label}</h2>
                </div>
                <a href="/#live-docket" class="text-xs font-bold text-brand-green hover:underline">
                    Browse All 170+ Verified Dockets &rarr;
                </a>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse">
                    <thead>
                        <tr class="border-b border-slate-200 bg-slate-100/70 text-[11px] font-mono uppercase text-slate-500">
                            <th class="py-2.5 px-4">Docket / Parcel ID</th>
                            <th class="py-2.5 px-4">Jurisdiction</th>
                            <th class="py-2.5 px-4">Record Titleholder</th>
                            <th class="py-2.5 px-4 text-right">Surplus Pool</th>
                            <th class="py-2.5 px-4 text-right">Fee Benchmark</th>
                            <th class="py-2.5 px-4 text-right">Dossier</th>
                        </tr>
                    </thead>
                    <tbody>{rows_html}
                    </tbody>
                </table>
            </div>
        </div>
"""

def generate_county_page(c, all_records=None):
    state_hub_url = STATE_HUBS.get(c['state'], '/')
    guide_title, guide_url = STATE_BLOG_GUIDES.get(c['state'], ('Statutory Surplus Practice Guide', '/blog/'))
    live_table_html = render_county_live_table(c, all_records or [])
    return f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Surplus Docket — {c['county']} Tax Deed Surplus &amp; Excess Proceeds</title>
    <meta name="description" content="{c['description']}">
    <link rel="canonical" href="https://surplusdocket.com/{c['slug']}">
    <link rel="icon" type="image/png" href="/assets/favicon.png">
    <link rel="icon" type="image/x-icon" href="/favicon.ico">

    <!-- Open Graph / SEO -->
    <meta property="og:type" content="website">
    <meta property="og:title" content="Surplus Docket — {c['county']} Tax Deed Surplus &amp; Excess Proceeds">
    <meta property="og:description" content="{c['description']}">
    <meta property="og:url" content="https://surplusdocket.com/{c['slug']}">
    <meta property="og:image" content="https://surplusdocket.com/assets/og_image.png">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:image" content="https://surplusdocket.com/assets/og_image.png">

    <!-- Schema.org JSON-LD -->
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@graph": [
        {{
          "@type": "Dataset",
          "name": "{c['county']} Tax Deed Surplus & Excess Proceeds Feed",
          "description": "{c['description']}",
          "spatialCoverage": "{c['county']}, {c['state_full']}",
          "license": "https://surplusdocket.com/terms.html",
          "creator": {{
            "@type": "Organization",
            "name": "Surplus Docket",
            "url": "https://surplusdocket.com"
          }}
        }},
        {{
          "@type": "BreadcrumbList",
          "itemListElement": [
            {{
              "@type": "ListItem",
              "position": 1,
              "name": "Home",
              "item": "https://surplusdocket.com/"
            }},
            {{
              "@type": "ListItem",
              "position": 2,
              "name": "{c['state_full']}",
              "item": "https://surplusdocket.com{state_hub_url}"
            }},
            {{
              "@type": "ListItem",
              "position": 3,
              "name": "{c['county']}",
              "item": "https://surplusdocket.com/{c['slug']}"
            }}
          ]
        }},
        {{
          "@type": "FAQPage",
          "mainEntity": [
            {{
              "@type": "Question",
              "name": "What statute governs tax sale surplus in {c['county']}?",
              "acceptedAnswer": {{
                "@type": "Answer",
                "text": "Surplus funds in {c['county']} are governed by {c['statute']}. Claimants have a statutory deadline of {c['deadline']}."
              }}
            }},
            {{
              "@type": "Question",
              "name": "Where are tax deed excess proceeds deposited in {c['county']}?",
              "acceptedAnswer": {{
                "@type": "Answer",
                "text": "Excess auction proceeds are deposited directly with the {c['clerk_name']} registry pending petition disbursement."
              }}
            }}
          ]
        }},
        {{
          "@type": "GovernmentService",
          "name": "{c['county']} Court Registry Surplus Fund Administration",
          "serviceType": "Tax Deed Surplus Recovery",
          "provider": {{
            "@type": "GovernmentOrganization",
            "name": "{c['clerk_name']}",
            "url": "{c['clerk_url']}"
          }},
          "areaServed": {{
            "@type": "AdministrativeArea",
            "name": "{c['county']}, {c['state_full']}"
          }}
        }}
      ]
    }}
    </script>

    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700;800;900&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    fontFamily: {{
                        sans: ['"Plus Jakarta Sans"', 'sans-serif'],
                        heading: ['Cinzel', 'serif'],
                        mono: ['"JetBrains Mono"', 'monospace'],
                    }},
                    colors: {{
                        brand: {{
                            green: '#4c6d48',
                            greenDark: '#365134',
                            greenSoft: '#edf3ec',
                            navy: '#1b365d',
                            navyDark: '#102238',
                            canvas: '#f8f8f4',
                            slateText: '#334155',
                        }}
                    }}
                }}
            }}
        }}
    </script>
    <!-- Plausible Analytics (Privacy-First) -->
    <script defer data-domain="surplusdocket.com" src="https://plausible.io/js/script.outbound-links.file-downloads.tagged-events.js"></script>
    <style>
        h1, h2, h3 {{ text-wrap: balance; }}
        p {{ text-wrap: pretty; }}
    </style>
</head>
<body class="antialiased min-h-screen flex flex-col font-sans bg-brand-canvas text-brand-slateText">

    <!-- Top Header -->
    <header class="w-full border-b border-brand-navy bg-white/95 backdrop-blur-md sticky top-0 z-50 shadow-sm">
        <div class="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 h-16 sm:h-20 flex items-center justify-between gap-2">
            <a href="/" class="flex items-center gap-2.5 sm:gap-3 group shrink-0 min-w-0">
                <img src="/assets/logo_surplus_docket.png?v=6" alt="Surplus Docket" class="h-8 sm:h-10 w-auto object-contain transition-transform group-hover:scale-105 shrink-0">
                <div class="flex flex-col sm:flex-row sm:items-baseline sm:gap-1.5 leading-none shrink-0">
                    <span class="font-heading font-black text-sm sm:text-2xl tracking-tight text-brand-green">SURPLUS</span>
                    <span class="font-heading font-black text-sm sm:text-2xl tracking-tight text-brand-navy">DOCKET</span>
                </div>
            </a>
            <div class="flex items-center gap-1.5 sm:gap-3 shrink-0">
                <a href="/" class="hidden sm:inline-flex text-xs font-semibold text-slate-600 hover:text-brand-green transition-colors px-2 py-1">Main Hub</a>
                <a href="https://billing.stripe.com/p/login/bJe28r4iagXN4LHb0i0ZW00" target="_blank" rel="noopener noreferrer" class="hidden md:inline-flex text-xs font-heading font-bold text-slate-600 hover:text-brand-navy border border-slate-300 bg-white px-3 py-2 rounded-lg transition-all shadow-sm">Billing Portal</a>
                <a href="https://buy.stripe.com/4gM14n8yq9vl0vrb0i0ZW21" target="_blank" rel="noopener noreferrer" class="text-xs sm:text-sm font-heading font-bold bg-brand-green hover:bg-brand-greenDark text-white px-3 sm:px-5 py-2 sm:py-2.5 rounded-lg transition-all shadow-md shrink-0">
                    Start 7-Day Trial
                </a>
            </div>
        </div>
    </header>

    <!-- Main County Content -->
    <main class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-14 flex-grow">
        <!-- Breadcrumb -->
        <nav class="text-xs text-slate-400 mb-6 flex items-center gap-2">
            <a href="/" class="hover:text-brand-green">Home</a>
            <span>&gt;</span>
            <a href="{state_hub_url}" class="hover:text-brand-green">{c['state_full']}</a>
            <span>&gt;</span>
            <span class="text-brand-navy font-semibold">{c['county']}</span>
        </nav>

        <!-- County Title Badge & Hero -->
        <div class="mb-8">
            <span class="text-xs font-mono font-bold text-brand-green uppercase tracking-widest bg-brand-greenSoft px-3 py-1 rounded-full border border-brand-green/30">
                {c['statute']} • {c['county']}
            </span>
            <h1 class="text-3xl sm:text-4xl md:text-5xl font-heading font-black text-brand-navy mt-4 mb-3 tracking-tight">
                {c['county']} Tax Deed Surplus & Excess Proceeds Feed
            </h1>
            <p class="text-sm sm:text-base text-slate-600 leading-relaxed max-w-3xl">
                Automated daily intelligence for {c['county']} ({c['city']}, {c['state']}). Our pipeline ingests official filings from the {c['clerk_name']}, filters out institutional entities, and delivers verified individual owner surplus claims every morning by 7:30 AM EST.
            </p>
        </div>

        <!-- Statutory Metrics Grid -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10">
            <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
                <span class="text-xs font-mono text-slate-500 uppercase tracking-wider block mb-1">Governing Statute</span>
                <span class="font-heading font-bold text-sm text-brand-navy">{c['statute']}</span>
            </div>
            <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
                <span class="text-xs font-mono text-slate-500 uppercase tracking-wider block mb-1">Claim Window</span>
                <span class="font-heading font-bold text-sm text-brand-green">{c['deadline']}</span>
            </div>
            <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
                <span class="text-xs font-mono text-slate-500 uppercase tracking-wider block mb-1">Statutory Benchmark</span>
                <span class="font-heading font-bold text-sm text-slate-700">{c['fee_cap']}</span>
            </div>
        </div>

        <!-- Official County Verification & Directory Card -->
        <div class="bg-white border-2 border-brand-green rounded-3xl p-5 sm:p-8 shadow-xl mb-10">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-4 border-b border-slate-100">
                <div>
                    <span class="text-xs font-mono font-bold text-brand-green bg-brand-greenSoft px-2.5 py-1 rounded">OFFICIAL COUNTY SOURCE DIRECTORY</span>
                    <h3 class="font-heading font-bold text-base sm:text-lg text-brand-navy mt-1">{c['county']} Official Records</h3>
                </div>
                <div class="text-left sm:text-right">
                    <span class="text-[11px] sm:text-xs text-slate-400 block uppercase font-bold tracking-wider">County Registry</span>
                    <span class="font-heading font-bold text-sm sm:text-base text-brand-navy">{c['city']}, {c['state']}</span>
                </div>
            </div>
            
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs mb-6">
                <div>
                    <span class="text-slate-400 block mb-0.5 font-medium">Registry Authority</span>
                    <span class="font-semibold text-slate-800">{c['clerk_name']}</span>
                </div>
                <div>
                    <span class="text-slate-400 block mb-0.5 font-medium">Governing Statute</span>
                    <span class="font-semibold text-slate-800">{c['statute']}</span>
                </div>
                <div>
                    <span class="text-slate-400 block mb-0.5 font-medium">Statutory Claim Window</span>
                    <span class="font-semibold text-slate-800">{c['deadline']}</span>
                </div>
                <div>
                    <span class="text-slate-400 block mb-0.5 font-medium">Official Portal Link</span>
                    <a href="{c['clerk_url']}" target="_blank" rel="noopener noreferrer" class="text-brand-navy hover:text-brand-green underline font-semibold">
                        {c['clerk_name']} Portal &rarr;
                    </a>
                </div>
            </div>

            <a href="https://buy.stripe.com/4gM14n8yq9vl0vrb0i0ZW21" target="_blank" rel="noopener noreferrer" class="block w-full text-center py-3.5 bg-brand-green hover:bg-brand-greenDark text-white font-heading font-bold text-sm rounded-xl shadow-md transition-all">
                Unlock Full {c['county']} Daily Lead Feed — $249/mo
            </a>
        </div>
{live_table_html}
        <!-- County Procedural Notes -->
        <div class="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 mb-10 shadow-sm space-y-4 text-xs sm:text-sm text-slate-600 leading-relaxed">
            <h3 class="font-heading font-bold text-base text-brand-navy">{c['county']} Recovery Procedure & Verification</h3>
            <p>
                When a tax deed auction or sheriff's tax sale closes above the upset bid in {c['county']}, the clerk deposits excess funds into the statutory court registry. Under {c['statute']}, junior lienholders have initial notice priority, after which remaining funds belong to the record titleholder or heirs.
            </p>
            <p>
                Surplus Docket's automated crawler monitors {c['county']} filings daily, excludes institutional and bank-owned records, flags estates for heir search, and formats an actionable CSV and Excel feed ready for practitioner due diligence (lien examination remains firm responsibility).
            </p>
            <div class="pt-3 border-t border-slate-100 flex flex-wrap items-center gap-4 text-xs font-bold">
                <a href="{guide_url}" class="text-brand-green hover:underline">Read {guide_title} &rarr;</a>
                <a href="/tools.html" class="text-brand-navy hover:text-brand-green hover:underline">Open Statutory Deadline Calculator &amp; Clio/Filevine Tools &rarr;</a>
                <a href="/sdk/" class="text-brand-navy hover:text-brand-green hover:underline">OpenSurplus SDK &amp; Python CLI &rarr;</a>
            </div>
        </div>

        <!-- Cross-Jurisdiction Matrix Links -->
        <div class="bg-brand-canvas border border-slate-300 rounded-2xl p-6 text-center text-xs text-slate-600">
            <p class="font-bold text-brand-navy mb-3">Explore Monitored Jurisdictions &amp; Resources</p>
            <div class="flex flex-wrap items-center justify-center gap-2 font-semibold mb-3">
                <a href="/palm-beach-tax-deed-surplus.html" class="px-2.5 py-1 bg-white rounded-lg border border-slate-200 hover:border-brand-green hover:text-brand-green">Palm Beach, FL</a>
                <a href="/broward-county-tax-deed-surplus.html" class="px-2.5 py-1 bg-white rounded-lg border border-slate-200 hover:border-brand-green hover:text-brand-green">Broward, FL</a>
                <a href="/miami-dade-tax-deed-surplus.html" class="px-2.5 py-1 bg-white rounded-lg border border-slate-200 hover:border-brand-green hover:text-brand-green">Miami-Dade, FL</a>
                <a href="/orange-county-tax-deed-surplus.html" class="px-2.5 py-1 bg-white rounded-lg border border-slate-200 hover:border-brand-green hover:text-brand-green">Orange, FL</a>
                <a href="/hillsborough-tax-deed-surplus.html" class="px-2.5 py-1 bg-white rounded-lg border border-slate-200 hover:border-brand-green hover:text-brand-green">Hillsborough, FL</a>
                <a href="/harris-county-excess-proceeds.html" class="px-2.5 py-1 bg-white rounded-lg border border-slate-200 hover:border-brand-green hover:text-brand-green">Harris, TX</a>
                <a href="/dallas-county-excess-proceeds.html" class="px-2.5 py-1 bg-white rounded-lg border border-slate-200 hover:border-brand-green hover:text-brand-green">Dallas, TX</a>
                <a href="/fort-bend-county-excess-proceeds.html" class="px-2.5 py-1 bg-white rounded-lg border border-slate-200 hover:border-brand-green hover:text-brand-green">Fort Bend, TX</a>
                <a href="/tarrant-county-excess-proceeds.html" class="px-2.5 py-1 bg-white rounded-lg border border-slate-200 hover:border-brand-green hover:text-brand-green">Tarrant, TX</a>
                <a href="/travis-county-excess-proceeds.html" class="px-2.5 py-1 bg-white rounded-lg border border-slate-200 hover:border-brand-green hover:text-brand-green">Travis, TX</a>
                <a href="/gwinnett-county-excess-funds.html" class="px-2.5 py-1 bg-white rounded-lg border border-slate-200 hover:border-brand-green hover:text-brand-green">Gwinnett, GA</a>
                <a href="/fulton-county-excess-funds.html" class="px-2.5 py-1 bg-white rounded-lg border border-slate-200 hover:border-brand-green hover:text-brand-green">Fulton, GA</a>
                <a href="/dekalb-county-excess-funds.html" class="px-2.5 py-1 bg-white rounded-lg border border-slate-200 hover:border-brand-green hover:text-brand-green">DeKalb, GA</a>
                <a href="/cobb-county-excess-funds.html" class="px-2.5 py-1 bg-white rounded-lg border border-slate-200 hover:border-brand-green hover:text-brand-green">Cobb, GA</a>
                <a href="/san-diego-county-excess-proceeds.html" class="px-2.5 py-1 bg-white rounded-lg border border-slate-200 hover:border-brand-green hover:text-brand-green">San Diego, CA</a>
                <a href="/los-angeles-county-excess-proceeds.html" class="px-2.5 py-1 bg-white rounded-lg border border-slate-200 hover:border-brand-green hover:text-brand-green">Los Angeles, CA</a>
                <a href="/orange-county-ca-excess-proceeds.html" class="px-2.5 py-1 bg-white rounded-lg border border-slate-200 hover:border-brand-green hover:text-brand-green">Orange, CA</a>
                <a href="/davidson-county-excess-proceeds.html" class="px-2.5 py-1 bg-white rounded-lg border border-slate-200 hover:border-brand-green hover:text-brand-green">Davidson, TN</a>
                <a href="/mecklenburg-county-tax-foreclosure-surplus.html" class="px-2.5 py-1 bg-white rounded-lg border border-slate-200 hover:border-brand-green hover:text-brand-green">Mecklenburg, NC</a>
            </div>
            <div class="flex flex-wrap items-center justify-center gap-2 pt-2 border-t border-slate-200/60 font-semibold">
                <a href="{state_hub_url}" class="px-3 py-1 bg-brand-greenSoft text-brand-greenDark rounded-lg border border-brand-green/30 hover:bg-brand-green hover:text-white transition-all">{c['state_full']} Statewide Registry &rarr;</a>
                <a href="/practitioner-toolkit.html" class="px-3 py-1 bg-brand-greenSoft text-brand-greenDark rounded-lg border border-brand-green/30 hover:bg-brand-green hover:text-white transition-all">Practitioner Toolkit &rarr;</a>
                <a href="/tools.html" class="px-3 py-1 bg-brand-greenSoft text-brand-greenDark rounded-lg border border-brand-green/30 hover:bg-brand-green hover:text-white transition-all">Free Practice Tools &rarr;</a>
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
                            Daily by 7:30 AM EST Delivery
                        </span>
                        <a href="/api-documentation.html" class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-mono text-[11px] font-semibold transition-colors">
                            REST API v1
                        </a>
                    </div>
                </div>

                <!-- Col 2: Jurisdictions & State Coverage -->
                <div class="space-y-3">
                    <p class="text-xs font-bold uppercase tracking-wider text-brand-navy font-heading">State Coverage</p>
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
                        <li><a href="/tools.html" class="text-brand-green font-bold hover:underline transition-colors">Free Tools Hub</a></li>
                        <li><a href="/sdk/" class="hover:text-brand-green transition-colors">OpenSurplus SDK &amp; Python CLI</a></li>
                        <li><a href="/practitioner-toolkit.html" class="hover:text-brand-green transition-colors">1-Click Petition Builder</a></li>
                        <li><a href="/#calculator" class="hover:text-brand-green transition-colors">Statutory Cap Calculator</a></li>
                        <li><a href="/methodology.html" class="hover:text-brand-green transition-colors">Lien Scrubbing Methodology</a></li>
                        <li><a href="/comparison.html" class="hover:text-brand-green transition-colors">Provider Comparison Matrix</a></li>
                        <li><a href="/api-documentation.html" class="hover:text-brand-green transition-colors">Programmatic REST API</a></li>
                        <li><a href="/openapi.json" class="hover:text-brand-green transition-colors">OpenAPI 3.1.0 Spec (.json)</a></li>
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
                        <li><a href="/privacy.html" class="hover:text-brand-green transition-colors">Privacy Policy</a></li>
                        <li><a href="/refund-policy.html" class="hover:text-brand-green transition-colors">14-Day Refund Guarantee</a></li>
                    </ul>
                </div>
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

def run():
    print("============================================================")
    print(" 🏛️ GENERATING PROGRAMMATIC COUNTY SEO HUBS")
    print("============================================================")
    all_records = load_live_feed_records()
    for c in COUNTIES:
        out_path = SITE_DIR / c['slug']
        out_path.write_text(generate_county_page(c, all_records), encoding='utf-8')
        print(f"  [✓] Generated County Hub: {c['slug']}")
    print("============================================================")

if __name__ == '__main__':
    run()
