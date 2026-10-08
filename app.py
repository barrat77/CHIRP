"""Run with: python -m streamlit run app.py"""
import csv
import hashlib
from pathlib import Path
import pandas as pd
import streamlit as st
from channels import DEFAULTS, read_csv, export_csv, validate

EXAMPLE = Path(__file__).parent / 'examples' / 'channels.csv'
st.set_page_config(page_title='CHIRP | Channel workshop', page_icon='📻', layout='wide')
st.title('📻 CHIRP')
st.caption('Your local channel workshop · Example CSV → Edit channels → Download')
with st.sidebar:
    st.header('Start with an example')
    upload = st.file_uploader('CHIRP-exported CSV', type=['csv'])
    demo = st.checkbox('Use demo channels', value=upload is None)
    st.caption('Uploads stay in this local session. They are not added to GitHub.')
    st.download_button('Download example CSV', EXAMPLE.read_bytes(),
                       'example.csv', 'text/csv')

data = upload.getvalue() if upload else (EXAMPLE.read_bytes() if demo else None)
if data is None:
    st.info('Upload an example exported from CHIRP, or use the demo to explore.')
    st.stop()
try:
    headers, rows = read_csv(data)
except (ValueError, csv.Error) as exc:
    st.error(str(exc))
    st.stop()
fingerprint = hashlib.sha256(data).hexdigest()
if st.session_state.get('source') != fingerprint:
    st.session_state.source = fingerprint
    st.session_state.channels = rows
    st.session_state.revision = 0

left, middle, right = st.columns(3)
left.metric('Example channels', len(rows))
middle.metric('Columns preserved', len(headers))
right.metric('Source', upload.name if upload else 'Demo CSV')
st.subheader('Build your channel list')
st.write('Edit cells, add rows at the bottom, or select rows to delete them. Frequencies and offsets use MHz.')
edited = st.data_editor(pd.DataFrame(st.session_state.channels, columns=headers).fillna(''),
                        num_rows='dynamic', hide_index=True, use_container_width=True,
                        key=f'editor-{fingerprint}-{st.session_state.revision}')
current = [{field: '' if pd.isna(value) else str(value) for field, value in row.items()}
           for row in edited.to_dict('records')]
with st.expander('Add a simplex or repeater channel'):
    with st.form('new_channel'):
        a, b, c = st.columns(3)
        name = a.text_input('Channel name')
        freq = b.number_input('Receive frequency (MHz)', value=146.52, min_value=0.000001, format='%.6f')
        duplex = c.selectbox('Duplex', ['', '-', '+', 'split', 'off'])
        offset = a.number_input('Offset (MHz) / split transmit frequency', min_value=0.0, value=0.0, format='%.6f')
        tone_mode = b.selectbox('Tone mode', ['', 'Tone', 'TSQL'])
        tone = c.number_input('CTCSS tone (Hz)', min_value=60.0, max_value=260.0, value=88.5, step=0.1)
        comment = st.text_input('Comment')
        add = st.form_submit_button('Add channel')
    if add:
        locations = [int(row['Location']) for row in current if str(row.get('Location', '')).isdigit()]
        new = {field: DEFAULTS.get(field, '') for field in headers}
        settings = dict(Location=str(max(locations, default=0) + 1), Name=name,
                        Frequency=f'{freq:.6f}', Duplex=duplex, Offset=f'{offset:.6f}',
                        Tone=tone_mode, rToneFreq=f'{tone:.1f}', cToneFreq=f'{tone:.1f}', Comment=comment)
        new.update({k: v for k, v in settings.items() if k in headers})
        st.session_state.channels = current + [new]
        st.session_state.revision += 1
        st.rerun()

st.subheader('Choose channels to export')
query = st.text_input('Filter by name or comment', placeholder='Search your channel list')
selected = [r for r in current if not query or query.casefold() in
            (r.get('Name', '') + ' ' + r.get('Comment', '')).casefold()]
renumber = st.checkbox('Renumber exported channels consecutively')
start = st.number_input('First channel number', min_value=0, value=1, step=1, disabled=not renumber)
selected = [dict(row) for row in selected]
if renumber:
    for i, row in enumerate(selected, int(start)):
        row['Location'] = str(i)
st.dataframe(pd.DataFrame(selected, columns=headers), hide_index=True, use_container_width=True)
errors = validate(selected)
if errors:
    st.error('\n'.join(errors))
if selected and not errors:
    st.download_button(f'Download {len(selected)} channels', export_csv(headers, selected),
                       'chirp_channels.csv', 'text/csv', type='primary')
elif not selected:
    st.info('Add a channel or clear the filter to enable export.')
st.caption('Open the exported CSV in CHIRP and copy channels into a download from your radio. '
           'Check radio-specific limits, tones, power, and channel settings in CHIRP before uploading.')
