"""Retrieve regional candidates from a known public forum page."""
import re
from decimal import Decimal
from html.parser import HTMLParser
import requests
from channels import DEFAULTS
from repeaters import GMRS_OUTPUTS, county_key

SOURCE = 'https://forums.mygmrs.com/forum/27-area-repeaters/'
COUNTIES = {'loudoun', 'fairfax', 'arlington', 'prince william', 'clarke',
            'warren', 'frederick', 'shenandoah', 'page', 'rockingham',
            'augusta', 'culpeper', 'stafford'}


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        if tag in ('p', 'br', 'div', 'li'):
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)
        if tag in ('p', 'div', 'li'):
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def parse_candidates(html, county):
    parser = VisibleText()
    parser.feed(html)
    text = ''.join(parser.parts)
    rows = []
    seen = set()
    pattern = r'(?P<name>[A-Z][A-Z0-9 ()-]*?\s\d{3})\s*[-–]\s*(?P<coverage>[^\n]*?)rx\s*(?P<rx>462\.\d+)\s*[/\\]\s*tx\s*(?P<tx>467\.\d+)'
    for match in re.finditer(pattern, text):
        rx, tx = Decimal(match['rx']), Decimal(match['tx'])
        if rx not in GMRS_OUTPUTS or tx - rx != Decimal('5'):
            continue
        name = match['name'].strip()
        identity = (name, rx)
        if identity in seen:
            continue
        seen.add(identity)
        row = dict(DEFAULTS)
        row.update(Name=name, Frequency=f'{rx:.6f}', Duplex='off', Offset='0.000000',
                   Tone='', Comment=f'Regional candidate for {county}, Virginia; receive only: tones/access unconfirmed; '
                   f'listed TX {tx:.6f} MHz; {match["coverage"].strip()}; Source: {SOURCE}')
        rows.append(row)
    return rows


def quick_local_search(state, county):
    if state != 'Virginia' or county_key(county) not in COUNTIES:
        raise ValueError('Quick forum lookup currently supports Northern Virginia counties only. Use the Google search link for other locations.')
    try:
        response = requests.get(SOURCE, timeout=(5, 25), allow_redirects=False,
                                headers={'User-Agent': 'CHIRP-Workshop/1.0 (+https://github.com/barrat77/CHIRP)'})
    except requests.RequestException as exc:
        raise ValueError('The forum could not be reached. No channels were added.') from exc
    if response.status_code != 200:
        raise ValueError(f'Forum returned HTTP {response.status_code}. No channels were added.')
    rows = parse_candidates(response.text, county.strip())
    if not rows:
        raise ValueError('No recognizable listings found. The forum format may have changed; no channels were added.')
    return rows
