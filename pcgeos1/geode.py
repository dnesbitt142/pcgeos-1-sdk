#!/usr/bin/env python3
"""Bounds-checked reader for the 1.x/2.x executable layouts in these uploads.

Not a GEOS loader or an ABI converter. All resource and export IDs are zero-based.
"""
from __future__ import annotations
import hashlib
import struct
from pathlib import Path


class GeodeError(ValueError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def u16(data: bytes, offset: int) -> int:
    if not 0 <= offset <= len(data) - 2:
        raise GeodeError(f"16-bit read outside input at {offset:#x}")
    return struct.unpack_from('<H', data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    if not 0 <= offset <= len(data) - 4:
        raise GeodeError(f"32-bit read outside input at {offset:#x}")
    return struct.unpack_from('<I', data, offset)[0]


def align16(n: int) -> int:
    return (n + 15) & ~15


def parse(data: bytes, label: str = '<bytes>') -> dict:
    if data[:4] == bytes.fromhex('c745cf53'):
        version, h, la, ra, pa = 1, 200, 32, 8, 16
    elif data[:4] == bytes.fromhex('c745c153'):
        version, h, la, ra, pa = 2, 256, 4, 44, 52
    else:
        raise GeodeError(f'{label}: unsupported signature')
    if len(data) < h + 88:
        raise GeodeError(f'{label}: truncated header')
    count, lib_count, export_count = struct.unpack_from('<3H', data, h + 8)
    tail = h + 24
    import_at = h + 88
    export_at = import_at + lib_count * 14
    resource_at = export_at + export_count * 4
    table_end = resource_at + count * 10
    if not count or table_end > len(data):
        raise GeodeError(f'{label}: truncated or invalid tables')
    for at, expected in ((tail + 50, export_count), (tail + 52, lib_count),
                         (tail + 56, count), (tail + 2, u16(data, h)),
                         (tail + 4, u16(data, h + 2))):
        if u16(data, at) != expected:
            raise GeodeError(f'{label}: inconsistent duplicate header fields')
    imports = []
    for i in range(lib_count):
        at = import_at + i * 14
        imports.append(dict(index=i, name=data[at:at + 8].decode('ascii').strip(),
                            attributes=u16(data, at + 8),
                            protocol=[u16(data, at + 10), u16(data, at + 12)]))
    exports = [dict(ordinal=i, offset=u16(data, export_at + i * 4),
                    resource=u16(data, export_at + i * 4 + 2))
               for i in range(export_count)]
    resources, relocations, spans = [], [], []
    for i in range(count):
        size = u16(data, resource_at + 2 * i)
        position = u32(data, resource_at + count * 2 + i * 4)
        offset = position + (256 if version == 2 else 0)
        rb = u16(data, resource_at + count * 6 + i * 2)
        flags = u16(data, resource_at + count * 8 + i * 2)
        reloc_at = offset + align16(size)
        if rb % 4:
            raise GeodeError(f'{label}: unaligned relocation table R{i}')
        if size or rb:
            if offset < table_end or reloc_at + rb > len(data):
                raise GeodeError(f'{label}: resource R{i} outside payload')
            spans.append((offset, reloc_at + rb, i))
        resources.append(dict(id=i, size=size, file_offset=offset,
                              relocation_offset=reloc_at, relocation_bytes=rb, flags=flags))
        for j in range(rb // 4):
            at = reloc_at + 4 * j
            info, extra, target = struct.unpack_from('<BBH', data, at)
            source, kind = info >> 4, info & 15
            if target + 2 > size or source not in (0, 1, 2) or kind > 5:
                raise GeodeError(f'{label}: invalid relocation R{i}:{target:04x}')
            if source == 1 and extra >= lib_count:
                raise GeodeError(f'{label}: invalid import index in relocation')
            relocations.append(dict(resource=i, offset=target, file_offset=offset + target,
                                    record_file_offset=at, info=info, source=source,
                                    type=kind, extra=extra, value=u16(data, offset + target)))
    spans.sort()
    if any(a[1] > b[0] for a, b in zip(spans, spans[1:])):
        raise GeodeError(f'{label}: overlapping resources')
    for export in exports:
        if export['resource'] >= count:
            raise GeodeError(f'{label}: invalid export resource')
    return dict(label=label, size=len(data), sha256=sha256(data), format_version=version,
                long_name=data[la:la + 36].split(b'\0')[0].decode('latin1'),
                release=list(struct.unpack_from('<4H', data, ra)),
                protocol=list(struct.unpack_from('<2H', data, pa)),
                permanent_name=data[tail + 20:tail + 28].decode('ascii').strip(),
                permanent_extension=data[tail + 28:tail + 32].decode('ascii').strip(),
                kernel_protocol=list(struct.unpack_from('<2H', data, h + 4))
                                if version == 1 else None,
                header_at=h, table_end=table_end, resource_table_at=resource_at,
                imports=imports, exports=exports, resources=resources, relocations=relocations,
                library_entry=dict(offset=u16(data, tail + 44), resource=u16(data, tail + 46)))


def resource_bytes(data: bytes, info: dict, rid: int) -> bytes:
    r = info['resources'][rid]
    return data[r['file_offset']:r['file_offset'] + r['size']]


def relocation_bytes(data: bytes, info: dict, rid: int) -> bytes:
    r = info['resources'][rid]
    return data[r['relocation_offset']:r['relocation_offset'] + r['relocation_bytes']]
