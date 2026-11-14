"""Tests of the data side of Quick notes (no GUI): python3 -m unittest discover -s tests   (from apps/quick-notes)"""
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import notes as N


class NotesTest(unittest.TestCase):
    def test_add_puts_the_newest_first_and_squeezes_blanks(self):
        a = N.add([], "  buy   milk ", now=100)
        b = N.add(a, "call Alex", now=200)
        self.assertEqual([n["text"] for n in b], ["call Alex", "buy milk"])
        self.assertEqual(b[0]["ts"], 200)

    def test_blank_text_adds_nothing(self):
        self.assertEqual(N.add([], "   \n "), [])

    def test_remove_in_and_out_of_range(self):
        n = N.add(N.add([], "a", 1), "b", 2)
        self.assertEqual([x["text"] for x in N.remove(n, 0)], ["a"])
        self.assertEqual(N.remove(n, 5), n)
        self.assertEqual(N.remove(n, -1), n)

    def test_save_and_load_keep_unicode(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "n.json")
            N.save(N.add([], "žluťoučký kůň", 5), p)
            self.assertEqual(N.load(p)[0]["text"], "žluťoučký kůň")
            self.assertFalse(os.path.exists(p + ".new"))

    def test_a_missing_or_broken_file_is_an_empty_list(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(N.load(os.path.join(d, "none.json")), [])
            p = os.path.join(d, "bad.json")
            open(p, "w").write("{not json")
            self.assertEqual(N.load(p), [])

    def test_when_and_summary(self):
        now = time.time()
        self.assertRegex(N.when(now, now), r"^\d\d:\d\d$")
        self.assertRegex(N.when(now - 86400 * 3, now), r"^\d+\.\d+\.$")
        self.assertEqual([N.summary([]), N.summary([1]), N.summary([1, 2])], ["no notes", "1 note", "2 notes"])


if __name__ == "__main__":
    unittest.main()
