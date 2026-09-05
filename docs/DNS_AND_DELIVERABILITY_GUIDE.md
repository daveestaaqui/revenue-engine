# Surplus Docket — DNS, Email Deliverability & Routing Guide

This guide details the exact DNS settings required in Cloudflare for `surplusdocket.com` to guarantee 100% email deliverability, eliminate spoofing warnings, pass enterprise law firm spam filters (Mimecast, Barracuda, Proofpoint), and ensure all inbound inquiries reach your Gmail inbox.

---

## 1. SPF (Sender Policy Framework) Record

When Elena Brooks sends emails via Gmail SMTP (`smtp.gmail.com:587`) using `elena.brooks@surplusdocket.com`, receiving mail servers check `surplusdocket.com`'s SPF record. If Google is missing, the email is flagged as unauthorized or soft-fails.

In **Cloudflare DNS** for `surplusdocket.com`:
* **Type:** `TXT`
* **Name:** `@` (or `surplusdocket.com`)
* **Content:**
  ```text
  v=spf1 include:_spf.google.com include:_spf.mx.cloudflare.net ~all
  ```
* **TTL:** `Auto`

> **Note:** If an existing SPF TXT record already exists (e.g. only with Cloudflare), **update** it to merge both into the single record above. Never have two SPF TXT records on the root domain.

---

## 2. DMARC Record

DMARC tells recipient mail systems how to treat mail claiming to come from `surplusdocket.com`.

In **Cloudflare DNS**:
* **Type:** `TXT`
* **Name:** `_dmarc`
* **Content:**
  ```text
  v=DMARC1; p=none; sp=none; pct=100;
  ```
* **TTL:** `Auto`

`p=none` allows email delivery while establishing policy legitimacy across law firm mail servers.

---

## 3. Cloudflare Email Routing Rules

To ensure no emails sent to David or Elena bounce:

Go to **Cloudflare Dashboard -> surplusdocket.com -> Email -> Email Routing -> Routing Rules**:

| Rule Type | Match | Action | Destination |
| :--- | :--- | :--- | :--- |
| **Catch-all** | Any address (`*@surplusdocket.com`) | Forward | `sandwichfitness@gmail.com` |
| **Custom Address** | `elena.brooks@surplusdocket.com` | Forward | `sandwichfitness@gmail.com` |
| **Custom Address** | `david@surplusdocket.com` | Forward | `sandwichfitness@gmail.com` |

> **Catch-all Protection:** The Catch-all rule is essential. It guarantees that inquiries sent via the website form to `david@surplusdocket.com`, direct replies to `elena.brooks@`, or legal inquiries to `legal@` or `support@` will all land in your inbox.

---

## 4. Gmail "Send Mail As" Configuration

For outgoing emails to appear seamlessly from Elena Brooks:
1. Open **Gmail -> Settings (Gear) -> See all settings -> Accounts and Import**.
2. Under **Send mail as**:
   * Verify that `Elena Brooks <elena.brooks@surplusdocket.com>` is added.
   * SMTP Server: `smtp.gmail.com`
   * Port: `587` (TLS)
   * Username: `sandwichfitness@gmail.com`
   * Password: Your Google App Password (16 characters)
3. Check **"Reply from the same address the message was sent to"** so when a prospect replies to Elena, hitting "Reply" automatically replies as Elena.
