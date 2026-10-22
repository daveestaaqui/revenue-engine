#!/usr/bin/env python3
"""
Updates San Diego APN 360-150-12-00 with ground-truth financial reconciliation
across CSV feeds, feed.json, and encrypted vault.json.
"""
import csv
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from scrapers.sources.ca import SAN_DIEGO_APN_METADATA
from portal.vault_security import encrypt_docket_payload, get_current_vault_key

apn = '360-150-12-00'
meta = SAN_DIEGO_APN_METADATA[apn]

# 1. Update CSVs
csv_files = [
    BASE_DIR / 'data' / 'raw_ca_feed.csv',
    BASE_DIR / 'exports' / 'California_Surplus_Feed.csv',
    BASE_DIR / 'exports' / 'Master_Surplus_Lead_Feed.csv'
]
gross_str = f"${meta['Gross_Sale_Price_USD']:,.2f}"
deduct_str = f"${meta['County_Deductions_USD']:,.2f}"
net_str = f"${meta['Net_Excess_Proceeds_USD']:,.2f}"
new_verify_note = (
    f"Listed on San Diego County TTC Final Report of Sale PA-7102 PDF — Item 0263, APN {apn} "
    f"(Official Sale Price: {gross_str} less {deduct_str} statutory deductions = {net_str} net excess proceeds)"
)

for fpath in csv_files:
    if not fpath.exists():
        continue
    rows = []
    with open(fpath, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for r in reader:
            if r.get('Parcel_ID') == apn or apn in str(r.get('Case_or_TaxDeed_No', '')):
                r['Verify_Note'] = new_verify_note
                r['Property_Address'] = meta['Property_Address']
                r['Surplus_Balance_USD'] = f"{meta['Gross_Sale_Price_USD']:.2f}"
                if 'Est_Finder_Fee_USD' in r:
                    r['Est_Finder_Fee_USD'] = f"{meta['Counsel_Fee_Benchmark_USD']:.2f}"
            rows.append(r)
    with open(fpath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f'Updated {fpath.name}')

# 2. Update site/api/v1/feed.json
feed_file = BASE_DIR / 'site' / 'api' / 'v1' / 'feed.json'
with open(feed_file, 'r', encoding='utf-8') as f:
    feed = json.load(f)
for rec in feed['records']:
    if rec.get('Parcel_ID') == apn or rec.get('docket_id') == apn:
        rec['Verify_Note'] = new_verify_note
        rec['Property_Address'] = '4850 Jennifer [REDACTED — SUBSCRIBER ACCESS ONLY]'
        rec['Surplus_Balance_USD'] = meta['Gross_Sale_Price_USD']
        rec['Est_Finder_Fee_USD'] = meta['Counsel_Fee_Benchmark_USD']
        rec['Gross_Sale_Price_USD'] = meta['Gross_Sale_Price_USD']
        rec['Net_Excess_Proceeds_USD'] = meta['Net_Excess_Proceeds_USD']
        rec['County_Deductions_USD'] = meta['County_Deductions_USD']
        rec['Financial_Reconciliation'] = meta

with open(feed_file, 'w', encoding='utf-8') as f:
    json.dump(feed, f, indent=2)
print('Updated feed.json')

# 3. Update site/api/v1/vault.json
vault_key = get_current_vault_key()
vault_file = BASE_DIR / 'site' / 'api' / 'v1' / 'vault.json'
with open(vault_file, 'r', encoding='utf-8') as f:
    vault = json.load(f)

target_lead = None
for rec in feed['records']:
    if rec.get('Parcel_ID') == apn or rec.get('docket_id') == apn:
        target_lead = dict(rec)
        target_lead['Owner_Name'] = 'DISE LEONARD L 1999 TRUST ET AL'
        target_lead['Property_Address'] = meta['Property_Address']
        target_lead['Verify_Note'] = new_verify_note
        target_lead['Surplus_Balance_USD'] = meta['Gross_Sale_Price_USD']
        target_lead['Gross_Sale_Price_USD'] = meta['Gross_Sale_Price_USD']
        target_lead['Net_Excess_Proceeds_USD'] = meta['Net_Excess_Proceeds_USD']
        target_lead['County_Deductions_USD'] = meta['County_Deductions_USD']
        target_lead['Financial_Reconciliation'] = meta
        break

if target_lead:
    new_cipher = encrypt_docket_payload(target_lead, vault_key)
    entry = vault['dockets'].get(apn, {})
    entry['docket_id'] = apn
    entry['State'] = 'CA'
    entry['County'] = 'San Diego'
    entry['Surplus_Balance_USD'] = meta['Gross_Sale_Price_USD']
    entry['Gross_Sale_Price_USD'] = meta['Gross_Sale_Price_USD']
    entry['Net_Excess_Proceeds_USD'] = meta['Net_Excess_Proceeds_USD']
    entry['County_Deductions_USD'] = meta['County_Deductions_USD']
    entry['Financial_Reconciliation'] = meta
    entry['cipher'] = new_cipher
    vault['dockets'][apn] = entry
    with open(vault_file, 'w', encoding='utf-8') as f:
        json.dump(vault, f, indent=2)
    print('Updated vault.json with encrypted unredacted payload and reconciliation metadata!')
