"""User-triggered, authenticated GMRS directory lookup and conversion."""
import csv
import io
import json
from decimal import Decimal, InvalidOperation
import requests
from channels import DEFAULTS

STATES = dict(line.split('|') for line in '''Alabama|01
Alaska|02
Arizona|04
Arkansas|05
California|06
Colorado|08
Connecticut|09
Delaware|10
District of Columbia|11
Florida|12
Georgia|13
Hawaii|15
Idaho|16
Illinois|17
Indiana|18
Iowa|19
Kansas|20
Kentucky|21
Louisiana|22
Maine|23
Maryland|24
Massachusetts|25
Michigan|26
Minnesota|27
Mississippi|28
Missouri|29
Montana|30
Nebraska|31
Nevada|32
New Hampshire|33
New Jersey|34
New Mexico|35
New York|36
North Carolina|37
North Dakota|38
Ohio|39
Oklahoma|40
Oregon|41
Pennsylvania|42
Rhode Island|44
South Carolina|45
South Dakota|46
Tennessee|47
Texas|48
Utah|49
Vermont|50
Virginia|51
Washington|53
West Virginia|54
Wisconsin|55
Wyoming|56'''.splitlines())
GMRS_OUTPUTS = {Decimal('462.550') + Decimal('.025') * i for i in range(8)}


def county_key(value):
    value = str(value).strip().casefold()
    return value.removesuffix(' county').strip()


def fetch_repeaters(state, county, token, user_agent):
    if state not in STATES or not county.strip():
        raise ValueError('Choose a state and enter a county.')
    if not token.startswith('rbuapp_') or '@' not in user_agent:
        raise ValueError('Configure an approved app-bound user token and User-Agent with contact email.')
    try:
        response = requests.get('https://www.repeaterbook.com/api/export.php',
                                params={'state_id': STATES[state], 'county': county_key(county),
                                        'stype': 'gmrs'},
                                headers={'X-RB-App-Token': token, 'User-Agent': user_agent},
                                timeout=(5, 25), allow_redirects=False)
    except requests.RequestException as exc:
        raise ValueError('RepeaterBook could not be reached. Please try later.') from exc
    if response.status_code in (401, 403):
        raise ValueError('RepeaterBook denied access. Check CHIRP app approval, token, and approved User-Agent.')
    if response.status_code == 429:
        raise ValueError('RepeaterBook rate limit reached. Wait before searching again.')
    if response.status_code != 200:
        raise ValueError(f'RepeaterBook returned HTTP {response.status_code}. No channels were added.')
    try:
        payload = response.json()
        results = payload['results']
        if not isinstance(results, list) or not all(isinstance(r, dict) for r in results):
            raise ValueError()
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError('RepeaterBook returned an unexpected response. No channels were added.') from exc
    return results


def read_listings(data, filename):
    if len(data) > 5_000_000:
        raise ValueError('Listings file must be smaller than 5 MB.')
    try:
        text = data.decode('utf-8-sig')
        if filename.lower().endswith('.json'):
            payload = json.loads(text)
            records = payload.get('results') if isinstance(payload, dict) else payload
        else:
            records = list(csv.DictReader(io.StringIO(text)))
        if not isinstance(records, list) or not all(isinstance(r, dict) for r in records):
            raise ValueError()
        return records
    except (ValueError, UnicodeError, csv.Error) as exc:
        raise ValueError('Choose a UTF-8 listings CSV or JSON results file.') from exc


def parse_tone(value):
    value = str(value or '').strip()
    if value.upper() in ('', 'CSQ', 'NONE', 'OPEN'):
        return '', ''
    if value.upper().startswith('D') and value[1:].isdigit() and len(value[1:]) <= 3:
        return 'DTCS', value[1:].zfill(3)
    try:
        tone = Decimal(value)
        if tone.is_finite() and Decimal('60') <= tone <= Decimal('260'):
            return 'Tone', str(tone)
    except InvalidOperation:
        pass
    raise ValueError('Tone is unavailable or unsupported; confirm it with the repeater owner.')


def convert_listing(item, state, county):
    if county_key(item.get('County', '')) != county_key(county):
        return None
    if str(item.get('State', '')).strip().casefold() != state.casefold():
        return None
    status = str(item.get('Operational Status', 'Unknown'))
    if status.casefold() not in ('on-air', 'unknown', ''):
        return None
    try:
        receive = Decimal(str(item.get('Frequency', '')))
        transmit = Decimal(str(item.get('Input Freq', '')))
    except InvalidOperation as exc:
        raise ValueError('Missing receive or input frequency.') from exc
    if receive not in GMRS_OUTPUTS or transmit != receive + Decimal('5'):
        raise ValueError('Not a recognized GMRS repeater pair.')
    txmode, tx = parse_tone(item.get('PL'))
    rxmode, rx = parse_tone(item.get('TSQ'))
    row = dict(DEFAULTS)
    row.update(Frequency=f'{receive:.6f}', Duplex='+', Offset='5.000000', Mode='FM',
               Name=str(item.get('Landmark') or item.get('Callsign') or item.get('Nearest City') or 'GMRS'))
    if txmode == 'Tone':
        row['rToneFreq'] = tx
    if rxmode == 'Tone':
        row['cToneFreq'] = rx
    if txmode == 'DTCS':
        row['DtcsCode'] = tx
    if rxmode == 'DTCS':
        row['RxDtcsCode'] = rx
    if txmode and not rxmode:
        row['Tone'] = 'Tone' if txmode == 'Tone' else 'Cross'
        row['CrossMode'] = f'{txmode}->'
    elif txmode == rxmode == 'Tone' and tx == rx:
        row['Tone'] = 'TSQL'
    elif txmode == rxmode == 'DTCS':
        row['Tone'] = 'DTCS'
    elif txmode or rxmode:
        row['Tone'] = 'Cross'
        row['CrossMode'] = f'{txmode}->{rxmode}'
    access = str(item.get('Use') or 'Unknown')
    row['Comment'] = f"{county}, {state}; Access: {access}; Status: {status}; " + str(item.get('Notes') or '')
    return row


def convert_results(records, state, county):
    channels, skipped = [], []
    for i, item in enumerate(records, 1):
        try:
            row = convert_listing(item, state, county)
            if row:
                channels.append(row)
        except ValueError as exc:
            skipped.append(f'Listing {i}: {exc}')
    return channels, skipped
