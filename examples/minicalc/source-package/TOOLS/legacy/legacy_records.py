#!/usr/bin/env python3
"""Read-only diagnostic record reader for the uploaded viewer's WQ1/WK1 formats.

This is development groundwork, not a GEOS application, formula evaluator,
workbook editor, complete import filter, or format-preserving Save command.
Unknown records and all formula bytes are retained rather than discarded.
Supported BOF versions: WQ1 0x5120 and WK1 0x0406 (the viewer's own check).
WQ1 field boundaries are cross-checked against libwps QuattroSpreadsheet.cpp;
see SOURCES.md. No text encoding is guessed: labels are exposed as raw bytes.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_RECORDS = 200_000
CELL_TYPES = {0x0C: 'blank', 0x0D: 'integer', 0x0E: 'number',
              0x0F: 'label', 0x10: 'formula'}


class RecordError(ValueError):
    """Input does not match the deliberately narrow diagnostic format."""


@dataclass(frozen=True)
class Record:
    offset: int
    opcode: int
    payload: bytes

    def raw_bytes(self) -> bytes:
        """Reconstruct an unchanged record for preservation tests, in memory."""
        return struct.pack('<HH', self.opcode, len(self.payload)) + self.payload


@dataclass(frozen=True)
class WorkbookRecords:
    version: int
    records: tuple[Record, ...]
    sha256: str
    file_bytes: int

    @property
    def format_name(self) -> str:
        return 'WQ1' if self.version == 0x5120 else 'WK1'


def parse_records(data: bytes) -> WorkbookRecords:
    if not 6 <= len(data) <= MAX_FILE_BYTES:
        raise RecordError('Input length is outside the supported diagnostic bounds')
    records = []
    at = 0
    saw_eof = False
    while at < len(data):
        if len(records) >= MAX_RECORDS:
            raise RecordError('Too many records')
        if at + 4 > len(data):
            raise RecordError(f'Truncated record header at {at:#x}')
        opcode, length = struct.unpack_from('<HH', data, at)
        end = at + 4 + length
        if end > len(data):
            raise RecordError(f'Truncated record payload at {at:#x}')
        record = Record(at, opcode, data[at + 4:end])
        records.append(record)
        at = end
        if opcode == 1:
            if length != 0:
                raise RecordError('Non-empty EOF record')
            if at != len(data):
                raise RecordError('Trailing data after EOF is outside this reader\'s scope')
            saw_eof = True
            break
    first = records[0]
    if first.opcode != 0 or len(first.payload) != 2:
        raise RecordError('Expected a two-byte BOF version record')
    version = struct.unpack('<H', first.payload)[0]
    if version not in (0x5120, 0x0406):
        raise RecordError(f'Unsupported BOF version {version:#06x}')
    if not saw_eof:
        raise RecordError('Missing EOF record')
    if any(r.opcode == 0 for r in records[1:]):
        raise RecordError('Multiple BOF records are outside this reader\'s scope')
    return WorkbookRecords(version, tuple(records), hashlib.sha256(data).hexdigest(), len(data))


def cell_address(col: int, row: int) -> str:
    if not (0 <= col < 256 and 0 <= row < 8192):
        raise RecordError(f'Unsupported cell coordinate ({col}, {row})')
    n, letters = col + 1, ''
    while n:
        n, digit = divmod(n - 1, 26)
        letters = chr(65 + digit) + letters
    return f'{letters}{row + 1}'


def read_cell(record: Record, version: int) -> dict | None:
    if record.opcode not in CELL_TYPES:
        return None
    p = record.payload
    if len(p) < 5:
        raise RecordError(f'Truncated cell header at {record.offset:#x}')
    col, row = struct.unpack_from('<HH', p, 1)
    cell = dict(address=cell_address(col, row), column=col, row=row,
                kind=CELL_TYPES[record.opcode], format_byte=p[0],
                record_offset=record.offset, record_length=len(p),
                raw_payload_hex=p.hex())
    if record.opcode == 0x0C:
        cell['uninterpreted_tail_hex'] = p[5:].hex()
    elif record.opcode == 0x0D:
        if len(p) < 7:
            raise RecordError('Truncated integer cell')
        cell['value'] = struct.unpack_from('<h', p, 5)[0]
        cell['uninterpreted_tail_hex'] = p[7:].hex()
    elif record.opcode in (0x0E, 0x10):
        if len(p) < 13:
            raise RecordError('Truncated floating-point cell')
        number = struct.unpack_from('<d', p, 5)[0]
        cell['cached_ieee64_hex'] = p[5:13].hex()
        # Keep special NaN/error payloads raw; do not invent a semantic value.
        cell['cached_value' if record.opcode == 0x10 else 'value'] = (
            number if math.isfinite(number) else None)
        cell['non_finite_raw_value'] = not math.isfinite(number)
        if record.opcode == 0x10:
            minimum = 19 if version == 0x5120 else 15
            if len(p) < minimum:
                raise RecordError('Truncated formula header')
            total = struct.unpack_from('<H', p, 13)[0]
            if total != len(p) - 15:
                raise RecordError('Formula declared length does not match record payload')
            cell['formula_bytes_hex'] = p[13:].hex()
            if version == 0x5120:
                boundary0, boundary1 = struct.unpack_from('<HH', p, 15)
                if not 4 <= boundary0 <= boundary1 <= total:
                    raise RecordError('Invalid WQ1 formula field boundaries')
                cell['formula_declared_size'] = total
                cell['formula_field_boundaries'] = [boundary0, boundary1]
                cell['expression_bytes_hex'] = p[19:15 + boundary0].hex()
                cell['reference_area_hex'] = p[15 + boundary0:].hex()
            else:
                cell['expression_bytes_hex'] = p[15:].hex()
            cell['formula_evaluated'] = False
        else:
            cell['uninterpreted_tail_hex'] = p[13:].hex()
    else:
        if len(p) < 6:
            raise RecordError('Truncated label cell')
        cell['alignment_byte'] = p[5]
        if version == 0x5120:
            if len(p) < 7 or 7 + p[6] > len(p):
                raise RecordError('Truncated length-prefixed WQ1 label')
            end = 7 + p[6]
            label = p[7:end]
        else:
            end = p.find(b'\0', 6)
            if end < 0:
                raise RecordError('Unterminated WK1 label')
            label = p[6:end]
            end += 1
        cell['label_bytes_hex'] = label.hex()
        cell['ascii_preview'] = ''.join(chr(x) if 32 <= x < 127 else f'\\x{x:02x}'
                                        for x in label)
        cell['uninterpreted_tail_hex'] = p[end:].hex()
    return cell


def summarize(data: bytes, label: str) -> dict:
    workbook = parse_records(data)
    cells = [cell for r in workbook.records
             if (cell := read_cell(r, workbook.version)) is not None]
    counts = collections.Counter(c['kind'] for c in cells)
    locations = collections.Counter(c['address'] for c in cells)
    return dict(label=label, file_bytes=len(data), sha256=workbook.sha256,
                format=workbook.format_name, version_hex=f'{workbook.version:#06x}',
                record_count=len(workbook.records), cell_record_count=len(cells),
                cell_type_counts=dict(sorted(counts.items())),
                duplicate_cell_record_addresses=sorted(k for k, n in locations.items() if n > 1),
                formula_evaluation_performed=False,
                scope='Read-only record inventory; raw formula bytes preserved, not evaluated',
                record_inventory=[dict(offset=r.offset, opcode=f'{r.opcode:#06x}',
                                       payload_length=len(r.payload),
                                       payload_sha256=hashlib.sha256(r.payload).hexdigest())
                                  for r in workbook.records], cells=cells)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--json', type=Path, help='NEW JSON report file; input is never modified')
    args = parser.parse_args()
    try:
        if args.input.stat().st_size > MAX_FILE_BYTES:
            raise RecordError('File exceeds diagnostic size limit')
        report = summarize(args.input.read_bytes(), args.input.name)
        text = json.dumps(report, indent=2, allow_nan=False) + '\n'
        if args.json:
            with args.json.open('x', encoding='utf-8') as f:
                f.write(text)
        else:
            print(text, end='')
    except (OSError, ValueError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
