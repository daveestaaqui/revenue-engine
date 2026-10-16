# Real county surplus sources

Each module `scrapers/sources/<state>.py` (fl, tx, ga, nc, tn, ca) exposes:

```python
def fetch() -> list[dict]:
    """Download the CURRENT official public surplus/excess-proceeds list(s) at runtime and parse them."""
```

## Hard rules
- Records MUST come from an official government source fetched at runtime. Never hardcode, invent,
  or "fill in" records, amounts, owners, case numbers, dates, or URLs.
- If a county publishes nothing machine-readable/public (login, captcha, paid portal), skip it and log why.
  Do not bypass captchas or logins.
- Each county fetch must be isolated: one county failing must not break the others
  (catch exceptions, `print` a warning, continue).
- Use `requests` with a normal browser User-Agent and a timeout (30s). `pypdf`, `bs4`, `pandas`, `openpyxl`,
  and `playwright` are available in `.venv`.

## Record schema (one dict per surplus matter)

| key | type | notes |
|---|---|---|
| `State` | str | `FL`, `TX`, ... |
| `County` | str | e.g. `Palm Beach` (no "County" suffix) |
| `Case_or_TaxDeed_No` | str | exactly as published by the county; `""` if not published |
| `Parcel_ID` | str | as published; `""` if none |
| `Owner_Name` | str | former owner / defendant as published; `""` if none |
| `Property_Address` | str | as published; `""` if none |
| `Surplus_Balance_USD` | float | as published |
| `Sale_Date` | str | `YYYY-MM-DD` or `""` |
| `Record_Type` | str | `TAX_DEED`, `TAX_FORECLOSURE`, `FORECLOSURE`, or `EXCESS_PROCEEDS` |
| `Source_URL` | str | the exact official document/page the record was parsed from |
| `Verify_URL` | str | direct per-case URL **only if** the official portal supports a plain GET deep link that was tested to load that case; otherwise the same as `Source_URL` |
| `Verify_Note` | str | short human instruction, e.g. `"Listed on Harris County excess proceeds PDF"` or `"Search case # on clerk portal"` |
| `Retrieved_At` | str | ISO timestamp of fetch |
