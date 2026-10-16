"""North Carolina tax foreclosure surplus scraper (N.C.G.S. § 105-374 / § 45-21.31).

Checked official portals for Mecklenburg (mecknc.gov), Wake (wake.gov / nccourts.gov),
Guilford (guilfordcountync.gov), Forsyth (forsyth.cc), and Durham (dconc.gov).
In North Carolina, tax foreclosure and mortgage foreclosure surplus proceeds are deposited
with the County Clerk of Superior Court (Special Proceedings Division) within individual
case files rather than published as a consolidated public machine-readable surplus balance
spreadsheet. Per the scraper contract, this module returns [] rather than fabricating data.
"""

from __future__ import annotations


def fetch() -> list[dict]:
    """Return current public machine-readable NC county surplus records (none published online)."""
    return []
