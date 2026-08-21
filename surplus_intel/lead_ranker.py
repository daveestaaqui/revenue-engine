#!/usr/bin/env python3
"""
Surplus Lead Scoring and Opportunity Ranker
Scores records based on payout size, entity vs individual probability, and actionable equity spread.
"""

import json
import pandas as pd

def score_leads(processed_records, min_surplus=5000.0):
    scored = []
    for r in processed_records:
        amt = r["surplus_amount"]
        if amt < min_surplus:
            continue

        is_individual = r["owner_type"] == "Individual / Estate"
        
        # Priority Grade
        if amt >= 25000 and is_individual:
            grade = "Tier 1: High Priority (Fee > $5,000)"
            action = "Immediate Skip-Trace & Direct Outreach"
        elif amt >= 10000 and is_individual:
            grade = "Tier 2: Medium Priority (Fee $2,000 - $5,000)"
            action = "Standard Claim Packet Delivery"
        elif is_individual:
            grade = "Tier 3: Low Priority (Fee $1,000 - $2,000)"
            action = "Batch Mailer / Aggregated Wholesaler Lead List"
        else:
            grade = "Tier 4: Institutional / Corporate"
            action = "Corporate Legal Dept Outreach"

        scored_item = {**r, "tier": grade, "recommended_action": action}
        scored.append(scored_item)

    return scored

def export_summary(scored_leads, output_csv="surplus_leads_ranked.csv"):
    if not scored_leads:
        print("No leads matched the threshold.")
        return
    df = pd.DataFrame(scored_leads)
    df.to_csv(output_csv, index=False)
    print(f"✅ Exported {len(scored_leads)} ranked surplus opportunities to {output_csv}")
