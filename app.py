"""Run with: python -m streamlit run app.py"""
import csv
import hashlib
from pathlib import Path
import pandas as pd
import streamlit as st
from channels import DEFAULTS, read_csv, export_csv, validate, append_channels
from repeaters import STATES, fetch_repeaters, read_listings, convert_results

ROOT = Path(__file__).parent
BASE_FILE = ROOT / 'local_data' / 'default_52.csv'
EXAMPLE = ROOT / 'examples' / 'channels.csv'
st.set_page_config(page_title='CHIRP | Channel workshop', page_icon='📻', layout='wide')
st.title('📻 CHIRP')
st.caption('52 default channels + local GMRS repeaters → Your radio channel file')
with st.sidebar:
    st.header('Start with an example')
    upload = st.file_uploader('CHIRP-exported CSV', type=['csv'])
    st.caption('A valid 52-channel upload is saved as your local default. Uploads are excluded from GitHub.')
    if upload is not None:
        try:
            uploaded_headers, uploaded_rows = read_csv(upload.getvalue())
            problems = validate(uploaded_rows)
            if len(uploaded_rows) != 52:
                st.error(f'The default file needs 52 channels; this file has {len(uploaded_rows)}.')
            elif problems:
                st.error('\n'.join(problems))
            else:
                BASE_FILE.parent.mkdir(exist_ok=True)
                if not BASE_FILE.exists() or BASE_FILE.read_bytes() != upload.getvalue():
                    BASE_FILE.write_bytes(upload.getvalue())
                st.success('52 default channels saved in your project folder.')
        except (ValueError, csv.Error, OSError) as exc:
            st.error(str(exc))
    if BASE_FILE.exists():
        st.caption(str(BASE_FILE))
        st.download_button('Download saved defaults', BASE_FILE.read_bytes(), 'default_52.csv', 'text/csv')

if not BASE_FILE.exists():
    st.info('Upload your 52-channel example CSV once. It will be saved locally and included in every generated file.')
    st.stop()
try:
    base_bytes = BASE_FILE.read_bytes()
    headers, base = read_csv(base_bytes)
    if len(base) != 52 or validate(base):
        raise ValueError('The saved default must contain 52 valid channels. Upload the example again.')
except (ValueError, csv.Error, OSError) as exc:
    st.error(str(exc))
    st.stop()
# Include settings needed for new repeaters even if the example omitted optional columns.
for field in DEFAULTS:
    if field not in headers:
        headers.append(field)
        for row in base:
            row[field] = DEFAULTS[field]
fingerprint = hashlib.sha256(base_bytes).hexdigest()
if st.session_state.get('source') != fingerprint:
    st.session_state.source = fingerprint
    st.session_state.additions = []
    st.session_state.revision = 0
    st.session_state.pop('found', None)
st.session_state.setdefault('additions', [])
st.session_state.setdefault('revision', 0)

left, middle, right = st.columns(3)
left.metric('Default channels', 52)
middle.metric('Additional channels', len(st.session_state.additions))
right.metric('Total channels', len(append_channels(base, st.session_state.additions, headers)))
with st.expander('Your 52 default channels', expanded=False):
    st.caption('These channels are always included first. Editing/filtering additional channels does not remove them.')
    st.dataframe(pd.DataFrame(base, columns=headers), hide_index=True, width='stretch')

st.subheader('Find GMRS repeaters')
a, b = st.columns(2)
state = a.selectbox('State', list(STATES), index=list(STATES).index('Virginia'))
county = b.text_input('County', placeholder='e.g. Loudoun')
source = st.radio('Listings source', ['RepeaterBook online', 'Import listings file'], horizontal=True)
if source == 'RepeaterBook online':
    with st.expander('Connect RepeaterBook'):
        st.write('Online lookup requires RepeaterBook approval for this CHIRP app and your own app-bound token.')
        st.link_button('RepeaterBook app access setup', 'https://www.repeaterbook.com/wiki/doku.php?id=api')
        token = st.text_input('App-bound user token', type='password')
        user_agent = st.text_input('Approved User-Agent (including contact email)',
                                   placeholder='CHIRP-Workshop/1.0 (+https://github.com/barrat77/CHIRP; your@email.com)')
        st.caption('Credentials stay in this session and are not saved to files or GitHub.')
    search = st.button('Find county repeaters', type='primary')
    if search:
        try:
            with st.spinner('Searching GMRS listings…'):
                records = fetch_repeaters(state, county, token.strip(), user_agent.strip())
            found, skipped = convert_results(records, state, county)
            st.session_state.found = (state, county.strip(), found, skipped, 'RepeaterBook')
        except ValueError as exc:
            st.session_state.pop('found', None)
            st.error(str(exc))
    st.caption('Data courtesy of RepeaterBook.com. Coverage depends on published listings; unlisted private systems cannot be discovered.')
else:
    listing_file = st.file_uploader('Repeater listings CSV or JSON', type=['csv', 'json'])
    st.caption('Required fields: State, County, Frequency, Input Freq. Optional: PL, TSQ, Use, Operational Status, Callsign, Landmark, Notes. Frequencies use MHz.')
    if st.button('Find county repeaters in file'):
        try:
            if listing_file is None or not county.strip():
                raise ValueError('Choose a listings file and enter your county.')
            records = read_listings(listing_file.getvalue(), listing_file.name)
            found, skipped = convert_results(records, state, county)
            st.session_state.found = (state, county.strip(), found, skipped, 'Imported listings')
        except ValueError as exc:
            st.session_state.pop('found', None)
            st.error(str(exc))

if 'found' in st.session_state:
    found_state, found_county, found, skipped, found_source = st.session_state.found
    if found_state == state and found_county.casefold() == county.strip().casefold() and (
            (found_source == 'RepeaterBook') == (source == 'RepeaterBook online')):
        st.write(f'{len(found)} usable GMRS listings in {found_county}, {found_state}.')
        if skipped:
            with st.expander(f'{len(skipped)} listings need manual review'):
                st.write('\n'.join(skipped))
        if found:
            preview = pd.DataFrame(found).drop(columns=['Location'])
            preview.insert(0, 'Add', True)
            choices = st.data_editor(preview, hide_index=True, width='stretch',
                                     disabled=[c for c in preview.columns if c != 'Add'],
                                     key='found-' + hashlib.sha256(str(st.session_state.found).encode()).hexdigest())
            st.caption('OPEN indicates public access. Private, closed, or unknown access requires checking with the owner. Access status is included in channel comments.')
            if st.button('Append selected repeaters after defaults'):
                picked = [found[i] for i, include in enumerate(choices['Add']) if include]
                merged = append_channels(base, st.session_state.additions + picked, headers)
                added = len(merged) - 52 - len(st.session_state.additions)
                st.session_state.additions = merged[52:]
                st.session_state.revision += 1
                st.session_state.notice = f'Added {added} channels; exact duplicates were skipped.'
                st.rerun()
if st.session_state.get('notice'):
    st.success(st.session_state.pop('notice'))

st.subheader('Additional channels')
st.caption('Edit or delete additions here. Default channels stay intact.')
edited = st.data_editor(pd.DataFrame(st.session_state.additions, columns=headers).fillna(''),
                        num_rows='dynamic', hide_index=True, width='stretch',
                        key=f'editor-{fingerprint}-{st.session_state.revision}')
current = [{field: '' if pd.isna(value) else str(value) for field, value in row.items()}
           for row in edited.to_dict('records')]
# Persist edits before later search/append actions rerun the interface.
st.session_state.additions = current
with st.expander('Add a channel manually'):
    with st.form('new_channel'):
        a, b, c = st.columns(3)
        name = a.text_input('Channel name')
        freq = b.number_input('Receive frequency (MHz)', value=462.55, min_value=0.000001, format='%.6f')
        duplex = c.selectbox('Duplex', ['', '-', '+', 'split', 'off'])
        offset = a.number_input('Offset (MHz) / split transmit frequency', min_value=0.0, value=5.0, format='%.6f')
        tone_mode = b.selectbox('Tone mode', ['', 'Tone', 'TSQL'])
        tone = c.number_input('CTCSS tone (Hz)', min_value=60.0, max_value=260.0, value=88.5, step=0.1)
        comment = st.text_input('Comment')
        add = st.form_submit_button('Add channel')
    if add:
        new = {field: DEFAULTS.get(field, '') for field in headers}
        new.update(Name=name, Frequency=f'{freq:.6f}', Duplex=duplex, Offset=f'{offset:.6f}',
                   Tone=tone_mode, rToneFreq=f'{tone:.1f}', cToneFreq=f'{tone:.1f}', Comment=comment)
        st.session_state.additions = current + [new]
        st.session_state.revision += 1
        st.rerun()

st.subheader('Generate channel file')
query = st.text_input('Filter additional channels by name or comment', placeholder='Defaults are always included')
selected = [r for r in current if not query or query.casefold() in
            (r.get('Name', '') + ' ' + r.get('Comment', '')).casefold()]
combined = append_channels(base, selected, headers)
st.dataframe(pd.DataFrame(combined, columns=headers), hide_index=True, width='stretch')
errors = validate(combined)
if errors:
    st.error('\n'.join(errors))
else:
    st.download_button(f'Download {len(combined)} channels (52 defaults + {len(combined)-52} additions)',
                       export_csv(headers, combined), 'chirp_channels.csv', 'text/csv', type='primary')
st.caption('Open the CSV in CHIRP and copy channels into a download from your radio. Check tones, access permissions, power, and radio channel capacity before uploading.')
