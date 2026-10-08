"""CHIRP CSV import/export without changing uploaded radio settings."""
import csv
import io
from decimal import Decimal, InvalidOperation

FIELDS = ['Location', 'Name', 'Frequency', 'Duplex', 'Offset', 'Tone',
          'rToneFreq', 'cToneFreq', 'DtcsCode', 'DtcsPolarity', 'RxDtcsCode',
          'CrossMode', 'Mode', 'TStep', 'Skip', 'Power', 'Comment']
DEFAULTS = dict(zip(FIELDS, ['1', '', '146.520000', '', '0.000000', '',
                           '88.5', '88.5', '023', 'NN', '023', 'Tone->Tone',
                           'FM', '5.00', '', '', '']))


def read_csv(data):
    if len(data) > 5_000_000:
        raise ValueError('Please choose a CSV smaller than 5 MB.')
    try:
        text = data.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise ValueError('Save your example as a UTF-8 CSV file.') from exc
    lines = list(csv.reader(io.StringIO(text, newline=''), strict=True))
    lines = [line for line in lines if line and not line[0].startswith('#')]
    if not lines:
        raise ValueError('The file is empty.')
    headers = lines[0]
    if headers[0] != 'Location' or 'Frequency' not in headers:
        raise ValueError('Choose a CHIRP-exported CSV with Location first and a Frequency column.')
    if len(headers) != len(set(headers)):
        raise ValueError('Duplicate column names are not supported.')
    rows = []
    for number, values in enumerate(lines[1:], 2):
        if len(values) != len(headers):
            raise ValueError(f'Row {number} has {len(values)} cells; expected {len(headers)}.')
        rows.append(dict(zip(headers, values)))
    if not rows:
        raise ValueError('The example contains no channels.')
    return headers, rows


def validate(rows):
    errors, used = [], set()
    for i, row in enumerate(rows, 1):
        try:
            location = int(row.get('Location', ''))
            if location < 0 or location in used:
                raise ValueError()
            used.add(location)
        except (ValueError, TypeError):
            errors.append(f'Row {i}: Location must be a unique nonnegative integer.')
        for field in ('Frequency', 'Offset'):
            if field not in row:
                continue
            try:
                value = Decimal(str(row[field]))
                if not value.is_finite() or value < 0 or (field == 'Frequency' and value == 0):
                    raise InvalidOperation()
            except (InvalidOperation, ValueError):
                errors.append(f'Row {i}: {field} must be a valid MHz value.')
        for field, choices in [('Duplex', ('', '+', '-', 'split', 'off')),
                               ('Tone', ('', 'Tone', 'TSQL', 'DTCS', 'DTCS-R', 'TSQL-R', 'Cross')),
                               ('Mode', ('FM', 'NFM', 'AM', 'WFM', 'USB', 'LSB', 'CW', 'RTTY', 'DIG', 'PKT', 'NCW', 'NCWR', 'CWR', 'P25', 'DV', 'DMR', 'DN')),
                               ('Skip', ('', 'S'))]:
            if field in row and row[field] not in choices:
                errors.append(f'Row {i}: unsupported {field} value {row[field]!r}.')
    return errors


def export_csv(headers, rows):
    errors = validate(rows)
    if errors:
        raise ValueError('\n'.join(errors))
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode('utf-8')


def append_channels(base, additions, headers):
    """Keep every base row unchanged; append unique additions after its last slot."""
    result = [dict(row) for row in base]
    next_location = max(int(row['Location']) for row in base) + 1
    def identity(row):
        return tuple(str(row.get(k, '')) for k in
                     ('Name', 'Frequency', 'Duplex', 'Offset', 'Tone', 'rToneFreq',
                      'cToneFreq', 'DtcsCode', 'RxDtcsCode', 'CrossMode'))
    seen = {identity(row) for row in result}
    for row in additions:
        if identity(row) in seen:
            continue
        seen.add(identity(row))
        new = {field: str(row.get(field, DEFAULTS.get(field, ''))) for field in headers}
        new['Location'] = str(next_location)
        result.append(new)
        next_location += 1
    return result
