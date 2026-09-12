"""Dependency-free site, internal link and sitemap checks; live mode is GET-only."""
import argparse
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1] / 'site'
ORIGIN = 'https://surplusdocket.com'


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        self.links.extend(value for key, value in attrs if key in ('href', 'src') and value)


def exists(url):
    target = ROOT / unquote(urlsplit(url).path).lstrip('/')
    if target.is_dir():
        return (target / 'index.html').is_file()
    return target.is_file() or (not target.suffix and target.with_suffix('.html').is_file())


def check(live=False):
    errors, checked = [], 0
    for page in ROOT.rglob('*.html'):
        parser = Links()
        parser.feed(page.read_text(errors='replace'))
        base = ORIGIN + '/' + page.relative_to(ROOT).as_posix()
        for link in parser.links:
            url = urljoin(base, link)
            if urlsplit(url).netloc == 'surplusdocket.com' and not exists(url):
                errors.append(f'{page.relative_to(ROOT)}: missing {urlsplit(url).path}')
        checked += 1
    try:
        urls = [node.text for node in ET.parse(ROOT / 'sitemap.xml').findall('.//{*}loc')]
        for url in urls:
            if not url or urlsplit(url).netloc != 'surplusdocket.com' or not exists(url):
                errors.append(f'Invalid sitemap target: {url}')
        if ORIGIN + '/sitemap.xml' not in (ROOT / 'robots.txt').read_text():
            errors.append('robots.txt does not advertise the sitemap')
    except (OSError, ET.ParseError) as exc:
        errors.append(str(exc))
    live_results = {}
    if live:
        for path in ('/', '/robots.txt', '/sitemap.xml'):
            try:
                request = Request(ORIGIN + path, headers={'User-Agent': 'SurplusDocket-HealthCheck/1.0'})
                with urlopen(request, timeout=20) as response:
                    body = response.read().decode('utf-8')
                    live_results[path] = response.status
                    if path == '/sitemap.xml':
                        ET.fromstring(body)
                    if path == '/robots.txt' and ORIGIN + '/sitemap.xml' not in body:
                        errors.append('Live robots.txt lacks sitemap discovery')
                    if path == '/' and ('Surplus Docket' not in body or 'buy.stripe.com' not in body):
                        errors.append('Live homepage lacks branding or checkout link')
            except Exception as exc:
                errors.append(f'{path}: {type(exc).__name__}: {exc}')
    return {'html_pages_checked': checked, 'live_get_checks': live_results, 'errors': sorted(set(errors)), 'ok': not errors}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    report = check(args.live)
    Path('site-health.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['ok'] else 1)
