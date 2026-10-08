# CHIRP — Local Repeater Generator

A local Python/Streamlit channel workshop. Preserve your 52 default channels, find county GMRS repeaters, append/edit/filter additional channels, and download a combined CHIRP CSV.

## Run on Windows

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Run these commands from the CHIRP folder. Open the localhost URL printed by Streamlit.

## Example files

Upload your exact 52-channel CHIRP CSV once. A valid upload is saved verbatim as `local_data/default_52.csv` inside this project folder, excluded from GitHub. A different valid 52-channel upload replaces that local default. Every export keeps all 52 default rows first, preserves their locations and settings, and numbers additional channels after the highest default location. Filtering affects additions only. Optional CHIRP columns missing from the example are added with standard defaults for repeater programming. Radio .img files are not supported.

UTF-8 files up to 5 MB are supported. Location must be the first column, and Frequency must be present. Existing values (including leading zeroes in DTCS codes) and extra columns are preserved. CSV comment lines starting with # are omitted on export. The demo under examples is illustrative and is not used as the 52-channel default.

## County GMRS repeater search

Select a US state and enter your county. RepeaterBook online lookup requires **approval for this application** and an app-bound `rbuapp_` user token plus the approved User-Agent with contact email. An existing token for another application does not approve this app. See [RepeaterBook API access setup](https://www.repeaterbook.com/wiki/doku.php?id=api). Requests are user-triggered, county/state scoped, and do not retry denials or rate limits. Credentials and results stay in the local session. Live integration cannot work until approved credentials are supplied.

Alternatively import a CSV or JSON file you have permission to use. JSON may be a list or an object containing a `results` list. Field names: `State`, `County`, `Frequency`, `Input Freq`; optional `PL`, `TSQ`, `Use`, `Operational Status`, `Callsign`, `Landmark`, `Nearest City`, `Notes`. State must be its full name; frequencies use MHz. Only standard 462/467 MHz GMRS repeater pairs are accepted. Closed/private listings are shown with access status. Restricted or unrecognized tone data is skipped for manual review, rather than guessed. Offline listings are excluded. Missing status/access are labeled unknown.

Select discovered repeaters and append them. Exact channel duplicates are skipped; different names/tone settings sharing a frequency are retained. County filtering concerns listed repeater location, not guaranteed radio coverage. National GMRS simplex channels do not vary by county; your provided default list supplies your baseline channels. Unlisted private systems and private settings are not discoverable. Finding a private listing does not grant permission to transmit.

Validation currently checks unique channel numbers, MHz numbers, and basic mode fields. It is not a full radio compatibility validator. Open the result in CHIRP and verify all settings against your radio. CSV files cannot be uploaded directly to a radio: open your radio image/download in CHIRP and copy the channels into it. See [CHIRP CSV documentation](https://chirpmyradio.com/projects/chirp/wiki/CSV_HowTo).

## Local and GitHub copies

This folder is an independent Git repository linked to https://github.com/barrat77/CHIRP.

```powershell
git add app.py channels.py requirements.txt README.md tests examples .gitignore
git commit -m "Update CHIRP app"
git push origin main
```

## Next features

- Additional directory integrations and radius filtering.
- Radio-specific profiles and compatibility validation after confirming radio models.
- Mapping other CSV column formats to CHIRP fields.

## Tests

```powershell
python -m unittest discover -s tests
```
