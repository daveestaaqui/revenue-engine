#!/usr/bin/env python3
"""
Master Public Record Surplus & Excess Funds Pipeline
Parses raw county tax sale records, extracts individual homeowner overages, and generates claim packets.
"""

import sys
import os

from surplus_intel.surplus_extractor import parse_tabular_surplus_data, process_raw_records
from surplus_intel.lead_ranker import score_leads, export_summary
from surplus_intel.packet_generator import generate_claim_packet

def run_pipeline(input_file, state="FL", min_surplus=5000.0, output_dir="/Users/davidmahler/revenue-engine/output"):
    print(f"[*] Ingesting: {input_file} (Jurisdiction: {state})")
    raw_records = parse_tabular_surplus_data(input_file)
    print(f"[*] Raw Records Ingested: {len(raw_records)}")

    processed = process_raw_records(raw_records, state=state, default_fee_rate=0.20)
    print(f"[*] Processed Records with Surplus >= $1k: {len(processed)}")

    scored = score_leads(processed, min_surplus=min_surplus)
    print(f"[*] Filtered High-Yield Opportunities: {len(scored)}")

    output_csv = os.path.join(output_dir, "ranked_surplus_opportunities.csv")
    export_summary(scored, output_csv=output_csv)

    print("\n=======================================================")
    print(" 🎯 TOP SURPLUS RECOVERY OPPORTUNITIES (INDIVIDUAL/ESTATE)")
    print("=======================================================")
    
    total_potential_fees = 0.0
    generated_packets = []

    for idx, lead in enumerate(scored, 1):
        if lead["owner_type"] == "Individual / Estate":
            total_potential_fees += lead["estimated_finder_fee"]
            packet_path = generate_claim_packet(lead, out_dir=output_dir)
            generated_packets.append(packet_path)
            print(f"[{idx}] {lead['owner_name']}")
            print(f"    - Surplus Balance:    ${lead['surplus_amount']:,.2f}")
            print(f"    - Est. Finder Fee:    ${lead['estimated_finder_fee']:,.2f} ({lead['statutory_fee_rate']})")
            print(f"    - Property Address:   {lead['property_address']}")
            print(f"    - Case/Deed No:       {lead['parcel_or_case']}")
            print(f"    - Generated Packet:   {os.path.basename(packet_path)}")
            print("-" * 55)

    print(f"\n💰 Total Potential Finder Fees in this batch: ${total_potential_fees:,.2f}")
    print(f"📁 Claim packets generated in: {output_dir}")

if __name__ == "__main__":
    data_file = sys.argv[1] if len(sys.argv) > 1 else "/Users/davidmahler/revenue-engine/data/sample_florida_tax_deed_surplus.csv"
    run_pipeline(data_file)
