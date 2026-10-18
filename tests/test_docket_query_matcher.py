#!/usr/bin/env python3
import unittest
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class TestDocketQueryMatching(unittest.TestCase):
    def setUp(self):
        with open(BASE_DIR / "site" / "api" / "v1" / "feed.json") as f:
            self.feed = json.load(f)
        self.records = self.feed["records"]

    def clean_id(self, s):
        if not s:
            return ""
        s = re.sub(r"^(parcel|case|apn|docket|matter|file|tax\s*deed)\s+", "", str(s), flags=re.I)
        return re.sub(r"[^a-z0-9]", "", s.lower())

    def match_record(self, raw_docket, raw_county="", raw_state=""):
        norm_q = str(raw_docket).lower().strip()
        clean_q = self.clean_id(raw_docket)

        # 1. Exact match
        for r in self.records:
            if ((r.get("docket_id") and r["docket_id"].lower() == norm_q) or
                (r.get("Case_or_TaxDeed_No") and r["Case_or_TaxDeed_No"].lower() == norm_q) or
                (r.get("Parcel_ID") and r["Parcel_ID"].lower() == norm_q) or
                (r.get("parcel_id_raw") and r["parcel_id_raw"].lower() == norm_q)):
                return r, "exact"

        # 2. Clean alphanumeric match
        if clean_q:
            for r in self.records:
                c_dock = self.clean_id(r.get("docket_id"))
                c_case = self.clean_id(r.get("Case_or_TaxDeed_No"))
                c_par = self.clean_id(r.get("Parcel_ID"))
                c_raw = self.clean_id(r.get("parcel_id_raw"))
                if (c_dock and (c_dock == clean_q or c_dock in clean_q or clean_q in c_dock)) or \
                   (c_case and (c_case == clean_q or c_case in clean_q or clean_q in c_case)) or \
                   (c_par and (c_par == clean_q or c_par in clean_q or clean_q in c_par)) or \
                   (c_raw and (c_raw == clean_q or c_raw in clean_q or clean_q in c_raw)):
                    return r, "clean_id"

        # 3. Substring match
        for r in self.records:
            parts = [r.get("docket_id", ""), r.get("Case_or_TaxDeed_No", ""), r.get("Parcel_ID", ""), r.get("parcel_id_raw", "")]
            full = " ".join(parts).lower()
            if norm_q in full or (r.get("docket_id") and r["docket_id"].lower() in norm_q):
                return r, "substring"

        # 4. County/State fallback
        if raw_county or raw_state:
            for r in self.records:
                c_match = not raw_county or raw_county.lower() in (r.get("County", "")).lower()
                s_match = not raw_state or raw_state.upper() == (r.get("State", "")).upper()
                if c_match and s_match:
                    return r, "county_state"

        return None, "none"

    def test_query_variations(self):
        test_cases = [
            "R7233 032",
            "R7233-032",
            "Parcel R7233 032",
            "Parcel R7233-032",
            "360-150-12-00",
            "Parcel 360-150-12-00",
            "3601501200",
            "22-CA-008975",
            "Case 22-CA-008975",
            "24-DCV-312823",
            "105-152-16",
            "24-0388-I",
        ]
        for tc in test_cases:
            rec, mtype = self.match_record(tc)
            self.assertIsNotNone(rec, f"Failed to match query: {tc}")
            self.assertIn(mtype, ["exact", "clean_id", "substring"])

if __name__ == "__main__":
    unittest.main()
