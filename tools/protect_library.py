"""Anonymize COFF file metadata and archive members, retaining link symbols."""

import argparse
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile


def anonymize_coff(data):
    data = bytearray(data)
    machine, sections, _, symbols, count, optional, _ = struct.unpack_from("<HHIIIHH", data)
    if machine != 0x8664 or optional:
        raise RuntimeError("Expected a regular x64 MSVC COFF object")
    for index in range(sections):
        header = 20 + index*40
        name = bytes(data[header:header+8]).rstrip(b"\0")
        size, offset = struct.unpack_from("<II", data, header+16)
        if name != b".debug$S" or not size:
            continue
        if struct.unpack_from("<I", data, offset)[0] != 4:
            raise RuntimeError("Expected CodeView C13 debug metadata")
        pos, end = offset+4, offset+size
        while pos < end:
            kind, length = struct.unpack_from("<II", data, pos)
            start, stop = pos+8, pos+8+length
            if stop > end:
                raise RuntimeError("Invalid CodeView subsection size")
            if kind == 0xF1:  # DEBUG_S_SYMBOLS
                record = start
                while record < stop:
                    length, symbol_kind = struct.unpack_from("<HH", data, record)
                    next_record = record+2+length
                    if length < 2 or next_record > stop:
                        raise RuntimeError("Invalid CodeView symbol size")
                    if symbol_kind == 0x1101:  # S_OBJNAME: signature followed by filename
                        data[record+8:next_record] = bytes(next_record-record-8)
                    record = next_record
            elif kind == 0xF3:  # DEBUG_S_STRINGTABLE: filenames used by line/checksum records
                data[start:stop] = bytes(length)
            pos = offset + ((stop-offset+3) & ~3)
    index = 0
    while index < count:
        record = symbols+index*18
        storage, auxiliaries = struct.unpack_from("BB", data, record+16)
        if storage == 103:  # IMAGE_SYM_CLASS_FILE: auxiliary records contain the filename
            start = record+18
            data[start:start+auxiliaries*18] = bytes(auxiliaries*18)
        index += 1+auxiliaries
    return data


def verify(library, source_dir):
    data = library.read_bytes()
    names = [p.name.encode("ascii") for p in source_dir.iterdir()
             if p.suffix in (".c", ".h")]
    for name in names:
        if name in data or name.decode("ascii").encode("utf-16le") in data:
            raise RuntimeError("Source filename remains in protected library")
    strings = re.findall(rb"[\x20-\x7e]{5,}", data)
    strings += [s.replace(b"\0", b"") for s in
                re.findall(rb"(?:[\x20-\x7e]\0){5,}", data)]
    for value in strings:
        if re.search(rb"[A-Za-z]:[\\/]|[\\/][\w.-]+[\\/]|\.(?:obj|pdb)\b", value):
            raise RuntimeError("Build path or object/debug filename remains in protected library")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", required=True, type=Path)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--ar")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    library = args.library.resolve()
    if args.verify_only:
        verify(library, args.source_dir)
        print("Protection verified: no source/build names or paths")
        return
    if not args.ar:
        parser.error("--ar is required unless --verify-only is used")

    # Rebuild the archive index with anonymous members; never edit relocation tables.
    members = subprocess.check_output([args.ar, "t", str(library)]).decode("utf-8").splitlines()
    if not members or len(set(members)) != len(members):
        raise RuntimeError("Expected a nonempty archive with unique object members")
    try:
        with tempfile.TemporaryDirectory(prefix="gslib-protect-", dir=library.parent) as temp:
            temp = Path(temp)
            objects = []
            for index, member in enumerate(members):
                name = str(index)
                obj = temp / name
                obj.write_bytes(anonymize_coff(
                    subprocess.check_output([args.ar, "p", str(library), member])))
                objects.append(name)
            result = temp / "protected"
            subprocess.run([args.ar, "rcsD", str(result), *objects], cwd=temp, check=True)
            verify(result, args.source_dir)
            os.replace(result, library)
    except Exception:
        library.unlink(missing_ok=True)
        raise
    print("Protection verified: no source/build names or paths")


if __name__ == "__main__":
    main()
