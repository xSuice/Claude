#!/usr/bin/env python3
"""S11-Regression: Inhalts-Secret-Scan in vault-to-server.py::scan()/contains_secret().

Reale Dateien in einem Scratch-Vault, kein Mock -- stellt sicher, dass eine
Notiz mit einem eingefuegten Secret NICHT im Rueckgabedict von scan() landet,
unabhaengig vom Dateinamen (das ist genau die S11-Luecke: alter Filter prueft
nur den Namen).
"""
import importlib.util
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = importlib.util.spec_from_file_location("vault_to_server", os.path.join(HERE, "vault-to-server.py"))
vts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vts)


class ContentSecretScanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="s11-vault-")
        self._orig_vault = vts.VAULT
        vts.VAULT = self.tmp

    def tearDown(self):
        vts.VAULT = self._orig_vault

    def _write(self, name, content):
        p = os.path.join(self.tmp, name)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(content)
        return p

    def test_harmless_note_is_included(self):
        self._write("Meeting.md", "# Meeting\nAgenda: nichts Geheimes hier.\n")
        out = vts.scan()
        self.assertIn("Meeting.md", out)

    def test_openai_style_key_in_innocuous_filename_is_blocked(self):
        self._write("Meeting.md", "Notiz: sk-" + "a" * 32 + " nicht committen\n")
        out = vts.scan()
        self.assertNotIn("Meeting.md", out)

    def test_private_key_block_is_blocked(self):
        self._write("Server-Setup.md", "-----BEGIN OPENSSH PRIVATE KEY-----\nabc\n-----END OPENSSH PRIVATE KEY-----\n")
        out = vts.scan()
        self.assertNotIn("Server-Setup.md", out)

    def test_github_token_is_blocked(self):
        self._write("Links.md", "ghp_" + "b" * 36 + "\n")
        out = vts.scan()
        self.assertNotIn("Links.md", out)

    def test_aws_key_is_blocked(self):
        self._write("Infra.md", "AKIA" + "C" * 16 + "\n")
        out = vts.scan()
        self.assertNotIn("Infra.md", out)

    def test_inline_apikey_assignment_is_blocked(self):
        self._write("Projekt.md", 'api_key = "abcdefgh12345678"\n')
        out = vts.scan()
        self.assertNotIn("Projekt.md", out)

    def test_attachment_content_is_never_scanned(self):
        # ATT-Dateien (Bilder) sind binaer -- contains_secret() darf dort nie
        # aufgerufen werden (scan() filtert per 'low.endswith(EXT)').
        p = os.path.join(self.tmp, "Bild.png")
        with open(p, "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\nsk-" + b"a" * 32)
        out = vts.scan()
        self.assertIn("Bild.png", out)  # Attachment wird NICHT wegen Inhalt blockiert

    def test_contains_secret_read_error_does_not_raise(self):
        self.assertFalse(vts.contains_secret(os.path.join(self.tmp, "nicht-vorhanden.md")))


if __name__ == "__main__":
    unittest.main()
