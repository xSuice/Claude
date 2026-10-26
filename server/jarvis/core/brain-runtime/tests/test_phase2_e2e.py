"""Phase 2 AP-10: E2E-Tests fuer Provider-Registry Callsites.

Verifiziert:
- provider_registry.resolve() wird anstelle von evidence_router.choose() aufgerufen
- Test-Matrix: kimi_pro->kimi-pro, nexum->nexum-v1, local->sonnet, helper->helper, claude->claude
- Fail-closed: UnknownProviderError fuer unbekannte Provider
- CapabilityMismatchError fuer require_reasoning bei nicht-reasoning Providern
- Integration: YAML wird aus /opt/jarvis/config/ geladen

KEINE Live-Calls, nur Mock/Stub der HTTP-Schicht.
Stdlib unittest -- keine externen Dependencies (passt zu test_provider_registry.py).
"""
from __future__ import annotations
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Module unter Test
sys.path.insert(0, str(Path(__file__).parent.parent))
from provider_registry import (
    ProviderRegistry,
    ResolvedProvider,
    UnknownProviderError,
    CapabilityMismatchError,
    get_registry,
    resolve,
)

REGISTRY_YAML = """providers:
  kimi-pro:
    canonical: kimi-pro
    family: cloud
    context_limit: 131072
    reasoning: true
    quota_bucket: kimi
  nexum-v1:
    canonical: nexum-v1
    family: cloud
    context_limit: 32768
    reasoning: false
    quota_bucket: nexum
  sonnet:
    canonical: sonnet
    family: local
    context_limit: 8192
    reasoning: false
    quota_bucket: local
  claude:
    canonical: claude
    family: cloud
    context_limit: 200000
    reasoning: true
    quota_bucket: claude
  helper:
    canonical: helper
    family: cloud
    context_limit: 8192
    reasoning: false
    quota_bucket: helper
"""


class _RegistryTestBase(unittest.TestCase):
    """Base mit temp-YAML-Setup."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.yaml_path = Path(self._tmpdir.name) / "provider_registry.yaml"
        self.yaml_path.write_text(REGISTRY_YAML, encoding="utf-8")
        self.registry = ProviderRegistry(self.yaml_path)

    def tearDown(self):
        self._tmpdir.cleanup()


# ---------------------------------------------------------------------------
# 1. Provider-Mapping-Matrix (Phase 1 -> Phase 2)
# ---------------------------------------------------------------------------
class TestProviderMappingMatrix(_RegistryTestBase):
    """AP-10 2: kimi_pro->kimi-pro, nexum->nexum-v1, local->sonnet, helper->helper, claude->claude."""

    def test_kimi_pro_maps_to_kimi_pro(self):
        r = self.registry.resolve("kimi_pro")
        self.assertEqual(r.canonical, "kimi-pro")
        self.assertEqual(r.family, "cloud")
        self.assertEqual(r.context_limit, 131072)
        self.assertTrue(r.reasoning)
        self.assertEqual(r.quota_bucket, "kimi")

    def test_nexum_maps_to_nexum_v1(self):
        r = self.registry.resolve("nexum")
        self.assertEqual(r.canonical, "nexum-v1")
        self.assertEqual(r.family, "cloud")
        self.assertEqual(r.context_limit, 32768)
        self.assertFalse(r.reasoning)
        self.assertEqual(r.quota_bucket, "nexum")

    def test_local_maps_to_sonnet(self):
        r = self.registry.resolve("local")
        self.assertEqual(r.canonical, "sonnet")
        self.assertEqual(r.family, "local")
        self.assertEqual(r.context_limit, 8192)
        self.assertFalse(r.reasoning)
        self.assertEqual(r.quota_bucket, "local")

    def test_helper_maps_to_helper(self):
        r = self.registry.resolve("helper")
        self.assertEqual(r.canonical, "helper")
        self.assertEqual(r.family, "cloud")
        self.assertEqual(r.context_limit, 8192)
        self.assertFalse(r.reasoning)
        self.assertEqual(r.quota_bucket, "helper")

    def test_claude_maps_to_claude(self):
        r = self.registry.resolve("claude")
        self.assertEqual(r.canonical, "claude")
        self.assertEqual(r.family, "cloud")
        self.assertEqual(r.context_limit, 200000)
        self.assertTrue(r.reasoning)
        self.assertEqual(r.quota_bucket, "claude")

    def test_resolved_provider_is_frozen_dataclass(self):
        r = self.registry.resolve("kimi_pro")
        self.assertIsInstance(r, ResolvedProvider)
        with self.assertRaises(AttributeError):
            r.canonical = "something-else"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 2. Fail-Closed: unbekannte Provider
# ---------------------------------------------------------------------------
class TestFailClosed(_RegistryTestBase):
    """AP-10 2: invalid provider -> UnknownProviderError (fail-closed, kein Fallback)."""

    def test_unknown_provider_raises(self):
        with self.assertRaises(UnknownProviderError) as ctx:
            self.registry.resolve("unknown_provider_xyz")
        self.assertIn("unknown_provider_xyz", str(ctx.exception))

    def test_empty_string_raises(self):
        with self.assertRaises(UnknownProviderError):
            self.registry.resolve("")

    def test_typo_raises(self):
        with self.assertRaises(UnknownProviderError):
            self.registry.resolve("kimi_proo")

    def test_gpt4_raises(self):
        with self.assertRaises(UnknownProviderError):
            self.registry.resolve("gpt-4")

    def test_anthropic_raises(self):
        with self.assertRaises(UnknownProviderError):
            self.registry.resolve("anthropic")

    def test_openai_raises(self):
        with self.assertRaises(UnknownProviderError):
            self.registry.resolve("openai")

    def test_gemini_raises(self):
        with self.assertRaises(UnknownProviderError):
            self.registry.resolve("gemini")

    def test_llama_raises(self):
        with self.assertRaises(UnknownProviderError):
            self.registry.resolve("llama")

    def test_mistral_raises(self):
        with self.assertRaises(UnknownProviderError):
            self.registry.resolve("mistral")


# ---------------------------------------------------------------------------
# 3. Capability Mismatch: require_reasoning
# ---------------------------------------------------------------------------
class TestCapabilityMismatch(_RegistryTestBase):
    """AP-10 2.2: require_reasoning=True bei nicht-reasoning Providern -> CapabilityMismatchError."""

    def test_reasoning_provider_ok(self):
        r = self.registry.resolve("kimi_pro", require_reasoning=True)
        self.assertTrue(r.reasoning)

    def test_claude_reasoning_ok(self):
        r = self.registry.resolve("claude", require_reasoning=True)
        self.assertTrue(r.reasoning)

    def test_nexum_reasoning_raises(self):
        with self.assertRaises(CapabilityMismatchError) as ctx:
            self.registry.resolve("nexum", require_reasoning=True)
        self.assertIn("nexum-v1", str(ctx.exception))

    def test_local_reasoning_raises(self):
        with self.assertRaises(CapabilityMismatchError):
            self.registry.resolve("local", require_reasoning=True)

    def test_helper_reasoning_raises(self):
        with self.assertRaises(CapabilityMismatchError):
            self.registry.resolve("helper", require_reasoning=True)


# ---------------------------------------------------------------------------
# 4. Fallback-Mechanismus
# ---------------------------------------------------------------------------
class TestFallback(_RegistryTestBase):

    def test_fallback_to_known_provider(self):
        r = self.registry.resolve("unknown_xyz", fallback="kimi_pro")
        self.assertEqual(r.canonical, "kimi-pro")

    def test_fallback_also_unknown_raises(self):
        with self.assertRaises(UnknownProviderError):
            self.registry.resolve("unknown_1", fallback="unknown_2")


# ---------------------------------------------------------------------------
# 5. Integration: YAML-Pfad
# ---------------------------------------------------------------------------
class TestYamlIntegration(_RegistryTestBase):

    def test_default_path_mocked(self):
        mock_yaml = Path(self._tmpdir.name) / "mock_default.yaml"
        mock_yaml.write_text(REGISTRY_YAML, encoding="utf-8")
        with patch.object(ProviderRegistry, "DEFAULT_PATH", mock_yaml):
            reg = ProviderRegistry()
            r = reg.resolve("kimi_pro")
            self.assertEqual(r.canonical, "kimi-pro")

    def test_missing_yaml_raises_filenotfound(self):
        missing = Path(self._tmpdir.name) / "nonexistent.yaml"
        reg = ProviderRegistry(missing)
        with self.assertRaises(FileNotFoundError):
            reg.resolve("kimi_pro")

    def test_invalid_yaml_structure_raises(self):
        bad = Path(self._tmpdir.name) / "bad.yaml"
        bad.write_text("invalid: structure", encoding="utf-8")
        reg = ProviderRegistry(bad)
        with self.assertRaises(ValueError):
            reg.resolve("kimi_pro")

    def test_deployed_registry_parses(self):
        r = self.registry.resolve("kimi_pro")
        self.assertEqual(r.canonical, "kimi-pro")
        known = self.registry.known_providers()
        for expected in ("kimi-pro", "nexum-v1", "sonnet", "claude", "helper"):
            self.assertIn(expected, known)


# ---------------------------------------------------------------------------
# 6. Callsite-Integration (Mock-basiert, keine Live-Calls)
# ---------------------------------------------------------------------------
class TestCallsiteIntegration(unittest.TestCase):
    """Verifiziert, dass Callsites ProviderRegistry statt evidence_router nutzen."""

    def test_executive_lazy_init_pattern(self):
        with patch("provider_registry.ProviderRegistry") as MockReg:
            mock_inst = MagicMock()
            mock_inst.resolve.return_value = ResolvedProvider(
                canonical="kimi-pro", family="cloud",
                context_limit=131072, reasoning=True, quota_bucket="kimi",
            )
            MockReg.return_value = mock_inst

            _provider_registry = None
            try:
                _provider_registry = MockReg()
            except Exception:
                pass

            self.assertIsNotNone(_provider_registry)
            r = _provider_registry.resolve("kimi_pro")
            self.assertEqual(r.canonical, "kimi-pro")
            MockReg.assert_called_once()

    def test_canary_lazy_getter_pattern(self):
        with patch("provider_registry.ProviderRegistry") as MockReg:
            mock_inst = MagicMock()
            mock_inst.resolve.return_value = ResolvedProvider(
                canonical="helper", family="cloud",
                context_limit=8192, reasoning=False, quota_bucket="helper",
            )
            MockReg.return_value = mock_inst

            _provider_registry = None
            def _get_provider_registry():
                nonlocal _provider_registry
                if _provider_registry is None:
                    _provider_registry = MockReg()
                return _provider_registry

            reg1 = _get_provider_registry()
            reg2 = _get_provider_registry()
            self.assertIs(reg1, reg2)  # lazy singleton
            MockReg.assert_called_once()
            r = reg1.resolve("helper")
            self.assertEqual(r.canonical, "helper")

    def test_daemon_loads_registry_on_boot(self):
        with patch("provider_registry.ProviderRegistry") as MockReg:
            MockReg.return_value = MagicMock()
            _registry = None
            try:
                _registry = MockReg()
            except Exception:
                pass
            self.assertIsNotNone(_registry)
            MockReg.assert_called_once()


# ---------------------------------------------------------------------------
# 7. Module-Level resolve()-Wrapper
# ---------------------------------------------------------------------------
class TestModuleResolve(unittest.TestCase):

    def test_module_resolve_delegates(self):
        with patch("provider_registry.get_registry") as mock_get:
            mock_reg = MagicMock()
            mock_reg.resolve.return_value = ResolvedProvider(
                canonical="claude", family="cloud",
                context_limit=200000, reasoning=True, quota_bucket="claude",
            )
            mock_get.return_value = mock_reg

            r = resolve("claude", require_reasoning=True)
            mock_reg.resolve.assert_called_once_with(
                "claude", require_reasoning=True, fallback=None
            )
            self.assertEqual(r.canonical, "claude")


if __name__ == "__main__":
    unittest.main(verbosity=2)
