"""Tests for provider_registry.py - Phase 2 AP-3 (stdlib unittest, no pytest)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from provider_registry import (
    ResolvedProvider, ProviderRegistry, UnknownProviderError,
    CapabilityMismatchError,
)

YAML_CONTENT = (
    "providers:\n"
    "  kimi-pro:\n"
    "    canonical: kimi-pro\n"
    "    family: cloud\n"
    "    context_limit: 131072\n"
    "    reasoning: true\n"
    "    quota_bucket: kimi\n"
    "  nexum-v1:\n"
    "    canonical: nexum-v1\n"
    "    family: cloud\n"
    "    context_limit: 32768\n"
    "    reasoning: false\n"
    "    quota_bucket: nexum\n"
    "  sonnet:\n"
    "    canonical: sonnet\n"
    "    family: local\n"
    "    context_limit: 8192\n"
    "    reasoning: false\n"
    "    quota_bucket: local\n"
    "  claude:\n"
    "    canonical: claude\n"
    "    family: cloud\n"
    "    context_limit: 200000\n"
    "    reasoning: true\n"
    "    quota_bucket: claude\n"
    "  helper:\n"
    "    canonical: helper\n"
    "    family: cloud\n"
    "    context_limit: 8192\n"
    "    reasoning: false\n"
    "    quota_bucket: helper\n"
)


class _RegistryTestBase(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.yaml_path = Path(self._tmpdir.name) / "provider_registry.yaml"
        self.yaml_path.write_text(YAML_CONTENT, encoding="utf-8")
        self.registry = ProviderRegistry(self.yaml_path)

    def tearDown(self):
        self._tmpdir.cleanup()


class TestResolveKnown(_RegistryTestBase):
    def test_kimi_pro(self):
        r = self.registry.resolve("kimi_pro")
        self.assertIsInstance(r, ResolvedProvider)
        self.assertEqual(r.canonical, "kimi-pro")
        self.assertEqual(r.family, "cloud")
        self.assertEqual(r.context_limit, 131072)
        self.assertTrue(r.reasoning)
        self.assertEqual(r.quota_bucket, "kimi")

    def test_nexum(self):
        r = self.registry.resolve("nexum")
        self.assertEqual(r.canonical, "nexum-v1")
        self.assertFalse(r.reasoning)

    def test_local(self):
        r = self.registry.resolve("local")
        self.assertEqual(r.canonical, "sonnet")
        self.assertEqual(r.family, "local")

    def test_claude(self):
        self.assertTrue(self.registry.resolve("claude").reasoning)

    def test_helper(self):
        self.assertEqual(self.registry.resolve("helper").canonical, "helper")

    def test_direct_canonical(self):
        self.assertEqual(self.registry.resolve("kimi-pro").canonical, "kimi-pro")


class TestResolveUnknown(_RegistryTestBase):
    def test_raises(self):
        with self.assertRaises(UnknownProviderError):
            self.registry.resolve("unknown_provider")

    def test_error_lists_known(self):
        try:
            self.registry.resolve("bogus")
            self.fail("expected UnknownProviderError")
        except UnknownProviderError as e:
            self.assertIn("claude", str(e))
            self.assertIn("kimi-pro", str(e))


class TestFallback(_RegistryTestBase):
    def test_fallback_used(self):
        r = self.registry.resolve("unknown", fallback="claude")
        self.assertEqual(r.canonical, "claude")

    def test_fallback_unknown_raises(self):
        with self.assertRaises(UnknownProviderError):
            self.registry.resolve("unknown", fallback="also_unknown")


class TestRequireReasoning(_RegistryTestBase):
    def test_ok(self):
        r = self.registry.resolve("kimi_pro", require_reasoning=True)
        self.assertTrue(r.reasoning)

    def test_fails(self):
        with self.assertRaises(CapabilityMismatchError):
            self.registry.resolve("nexum", require_reasoning=True)


class TestYamlLoad(_RegistryTestBase):
    def test_known(self):
        known = self.registry.known_providers()
        for p in ("kimi-pro", "nexum-v1", "sonnet", "claude", "helper"):
            self.assertIn(p, known)

    def test_missing_raises(self):
        reg = ProviderRegistry(Path("/nonexistent/x.yaml"))
        with self.assertRaises(FileNotFoundError):
            reg.resolve("kimi_pro")

    def test_idempotent(self):
        self.registry.load()
        n1 = len(self.registry.known_providers())
        self.registry.load()
        self.assertEqual(n1, len(self.registry.known_providers()))


class TestFields(_RegistryTestBase):
    def test_frozen(self):
        r = self.registry.resolve("kimi_pro")
        with self.assertRaises(AttributeError):
            r.canonical = "x"

    def test_all_fields(self):
        r = self.registry.resolve("kimi_pro")
        for f in ("canonical", "family", "context_limit", "reasoning", "quota_bucket"):
            self.assertTrue(hasattr(r, f), f"missing field {f}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
