"""Unit tests for tools/measure_code.py.

Run with:
  python3 -m unittest discover -s tools/code_match -p 'test_*.py'
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import measure_code as mc  # noqa: E402


IL_SAMPLE = """\
	.method private hidebysig 
		instance void Foo () cil managed 
	{
		// Method begins at RVA 0x1234
		// Header size: 1
		// Code size: 12 (0xc)
		.maxstack 8

		IL_0000: ldarg.0
		IL_0001: ldc.i4.0
		IL_0002: bne.un.s IL_0007
		IL_0004: nop
		IL_0005: br.s IL_0009
		IL_0007: nop
		IL_0008: ret
	} // end of method Foo
"""


class NormalizeBodyTests(unittest.TestCase):
    def test_strips_comments_and_maxstack(self):
        body = mc.normalize_body(IL_SAMPLE.splitlines())
        self.assertNotIn("//", body)
        self.assertNotIn("maxstack", body)
        self.assertNotIn("RVA", body)

    def test_renumbers_labels_by_first_appearance(self):
        body = mc.normalize_body(IL_SAMPLE.splitlines())
        self.assertIn("IL_0000: ldarg.0", body)
        # labels are remapped in order of appearance, not by original address
        self.assertIn("IL_0002: bne.un.s IL_0003", body)
        self.assertIn("IL_0003: nop", body)

    def test_ignores_absolute_addresses(self):
        a = mc.normalize_body(IL_SAMPLE.replace("0x1234", "0x9999").splitlines())
        b = mc.normalize_body(IL_SAMPLE.splitlines())
        self.assertEqual(a, b)

    def test_collapses_whitespace(self):
        body = mc.normalize_body(["  IL_0000:   call   void  Foo::Bar()  "])
        self.assertEqual(body, "IL_0000: call void Foo::Bar()")


class GeneratedClassifierTests(unittest.TestCase):
    def test_flags_compiler_generated(self):
        for key in ("'<>c'::'<Foo>b__1_0'",
                    "'<>c__DisplayClass3_0'::.ctor",
                    "'<DoThing>d__12'::MoveNext"):
            self.assertTrue(mc.is_generated(key), key)

    def test_accepts_hand_authored(self):
        for key in ("Animal::Update", "MainMenu::OnQuitButtonClicked"):
            self.assertFalse(mc.is_generated(key), key)


class ParseBodiesTests(unittest.TestCase):
    def test_extracts_key_and_code_size(self):
        bodies = mc.parse_bodies(IL_SAMPLE)
        self.assertIn("Foo", bodies)
        self.assertEqual(bodies["Foo"].code_bytes, 12)

    def test_disambiguates_overloads(self):
        text = IL_SAMPLE + IL_SAMPLE.replace("void Foo", "void Foo", 1)
        bodies = mc.parse_bodies(text)
        self.assertEqual(len(bodies), 2)
        self.assertIn("Foo", bodies)
        self.assertTrue(any(k.startswith("Foo#") for k in bodies))


class CompareTests(unittest.TestCase):
    @staticmethod
    def _bodies(items):
        return {k: mc.Body(k, size, norm) for k, size, norm in items}

    def test_missing_body_keeps_denominator_weight(self):
        orig = mc.Assembly("o", Path("o"), "x", self._bodies([("A", 10, "x"), ("B", 30, "y")]))
        new = mc.Assembly("n", Path("n"), "y", self._bodies([("A", 10, "x")]))
        s = mc.compare(orig, new, lambda _k: True)
        self.assertEqual(s["code_bytes"], 40)
        self.assertEqual(s["code_bytes_matched"], 10)
        self.assertEqual(s["bodies_missing"], 1)

    def test_extra_body_earns_no_credit(self):
        orig = mc.Assembly("o", Path("o"), "x", self._bodies([("A", 10, "x")]))
        new = mc.Assembly("n", Path("n"), "y", self._bodies([("A", 10, "x"), ("Z", 99, "q")]))
        s = mc.compare(orig, new, lambda _k: True)
        self.assertEqual(s["code_bytes"], 10)
        self.assertEqual(s["code_bytes_matched"], 10)
        self.assertEqual(s["code_matched"], 1.0)
        self.assertEqual(s["bodies_extra"], 1)

    def test_differing_body_earns_no_credit(self):
        orig = mc.Assembly("o", Path("o"), "x", self._bodies([("A", 10, "x")]))
        new = mc.Assembly("n", Path("n"), "y", self._bodies([("A", 10, "z")]))
        s = mc.compare(orig, new, lambda _k: True)
        self.assertEqual(s["code_bytes_matched"], 0)
        self.assertEqual(s["bodies_differing"], 1)

    def test_empty_scope_is_fully_matched(self):
        empty = mc.Assembly("o", Path("o"), "x", {})
        s = mc.compare(empty, empty, lambda _k: True)
        self.assertEqual(s["code_matched"], 1.0)


if __name__ == "__main__":
    unittest.main()
