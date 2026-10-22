import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest


spec = importlib.util.spec_from_file_location(
    "protect_library", Path(__file__).resolve().parents[1] / "tools/protect_library.py")
protect = importlib.util.module_from_spec(spec)
spec.loader.exec_module(protect)


class ProtectionMetadataTest(unittest.TestCase):
    def test_codeview_keeps_layout_and_other_records(self):
        name = b"C:\\private\\unit.obj\0"
        objname = struct.pack("<HHI", 6+len(name), 0x1101, 0) + name
        compile_record = struct.pack("<HH", 6, 0x113C) + b"keep"
        payload = objname + compile_record
        subsection = struct.pack("<II", 0xF1, len(payload)) + payload
        subsection += bytes(-len(subsection) % 4)
        strings = b"\0C:\\private\\unit.c\0"
        subsection += struct.pack("<II", 0xF3, len(strings)) + strings
        subsection += bytes(-len(subsection) % 4)
        debug = struct.pack("<I", 4) + subsection
        # Raw sections need not start at a four-byte file offset.
        header = struct.pack("<HHIIIHH", 0x8664, 1, 0, 0, 0, 0, 0)
        section = b".debug$S" + struct.pack("<IIIIIIHHI", 0, 0, len(debug), 61, 0, 0, 0, 0, 0)
        original = header + section + b"!" + debug
        result = protect.anonymize_coff(original)
        self.assertEqual(len(original), len(result))
        self.assertEqual(original[:61], result[:61])
        self.assertIn(compile_record, result)
        self.assertNotIn(b"private", result)
        self.assertNotIn(b"unit.", result)

    def test_file_symbol_auxiliaries_are_anonymized(self):
        header = struct.pack("<HHIIIHH", 0x8664, 0, 0, 20, 3, 0, 0)
        symbol = b".file\0\0\0" + struct.pack("<IhHBB", 0, -2, 0, 103, 2)
        original = header + symbol + b"C:\\private\\unit.c\0".ljust(36, b"\0")
        result = protect.anonymize_coff(original)
        self.assertEqual(original[:38], result[:38])
        self.assertEqual(bytes(36), result[38:])

    def test_other_coff_formats_fail(self):
        with self.assertRaises(RuntimeError):
            protect.anonymize_coff(struct.pack("<HHIIIHH", 0x14C, 0, 0, 0, 0, 0, 0))

    def test_verification_rejects_paths_and_source_names(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "unit.c").touch()
            library = root / "library"
            for data in (b"unit.c", "unit.c".encode("utf-16le"),
                         b"C:\\private\\build", b"/private/build/unit", b"unit.obj", b"unit.pdb"):
                with self.subTest(data=data):
                    library.write_bytes(data)
                    with self.assertRaises(RuntimeError):
                        protect.verify(library, root)
            library.write_bytes(b"gslib_gs_setup\0/DEFAULTLIB:MSVCRT\0")
            protect.verify(library, root)


if __name__ == "__main__":
    unittest.main()
