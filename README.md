# CHIRP — Local Repeater Generator

A local Python/Streamlit channel workshop. Start with a CHIRP-exported CSV, preserve its columns and values, edit/add/filter channels, and download a new CSV.

## Run on Windows

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Run these commands from the CHIRP folder. Open the localhost URL printed by Streamlit.

## Example files

Export a CSV from CHIRP and upload it in the sidebar. UTF-8 files up to 5 MB are supported. Location must be the first column, and Frequency must be present. Existing values (including leading zeroes in DTCS codes) and extra columns are preserved. CSV comment lines starting with # are omitted. Uploaded files remain in memory and are not committed to GitHub. Radio .img files are not supported in this first version.

The included demo is illustrative, not a live repeater directory. You can edit channels in the table or add simplex/repeater channels using the form. The filter controls which channels appear in the exported CSV. Renumbering affects only the export.

Validation currently checks unique channel numbers, MHz numbers, and basic mode fields. It is not a full radio compatibility validator. Open the result in CHIRP and verify all settings against your radio. CSV files cannot be uploaded directly to a radio: open your radio image/download in CHIRP and copy the channels into it. See [CHIRP CSV documentation](https://chirpmyradio.com/projects/chirp/wiki/CSV_HowTo).

## Local and GitHub copies

This folder is an independent Git repository linked to https://github.com/barrat77/CHIRP.

```powershell
git add app.py channels.py requirements.txt README.md tests examples .gitignore
git commit -m "Update CHIRP app"
git push origin main
```

## Next features

- Import repeater data from a selected source and filter by location/radius.
- Radio-specific profiles and compatibility validation after confirming radio models.
- Mapping other CSV column formats to CHIRP fields.

## Tests

```powershell
python -m unittest discover -s tests
```
