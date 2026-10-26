"""Phase 2 AP-3: Provider Registry with ResolvedProvider dataclass."""
from __future__ import annotations
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

log = logging.getLogger("provider_registry")

class UnknownProviderError(ValueError):
    pass

class CapabilityMismatchError(ValueError):
    pass

@dataclass(frozen=True)
class ResolvedProvider:
    canonical: str
    family: str
    context_limit: int
    reasoning: bool
    quota_bucket: str

class ProviderRegistry:
    DEFAULT_PATH = Path("/opt/jarvis/config/provider_registry.yaml")
    PHASE1_MAPPING = {
        "kimi_pro": "kimi-pro",
        "nexum": "nexum-v1",
        "local": "sonnet",
        "claude": "claude",
        "helper": "helper",
    }

    def __init__(self, registry_path: Optional[Path] = None):
        self._path = registry_path or self.DEFAULT_PATH
        self._providers: dict[str, dict] = {}
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        if not self._path.exists():
            raise FileNotFoundError(f"Provider registry not found: {self._path}")
        try:
            import yaml
        except ImportError as e:
            raise ImportError("PyYAML required") from e
        with open(self._path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict) or "providers" not in data:
            raise ValueError(f"Registry must contain providers key: {self._path}")
        providers_raw = data["providers"]
        for key, val in providers_raw.items():
            if not isinstance(val, dict):
                continue
            self._providers[key] = {
                "canonical": str(val["canonical"]),
                "family": str(val["family"]),
                "context_limit": int(val["context_limit"]),
                "reasoning": bool(val.get("reasoning", False)),
                "quota_bucket": str(val.get("quota_bucket", key)),
            }
        self._loaded = True

    def resolve(self, provider: str, *, require_reasoning: bool = False, fallback: Optional[str] = None) -> ResolvedProvider:
        self.load()
        canonical = self.PHASE1_MAPPING.get(provider, provider)
        entry = self._providers.get(canonical)
        if entry is None and fallback is not None:
            fallback_canonical = self.PHASE1_MAPPING.get(fallback, fallback)
            entry = self._providers.get(fallback_canonical)
            if entry is not None:
                canonical = fallback_canonical
        if entry is None:
            raise UnknownProviderError(f"Unknown provider {provider!r} (canonical: {canonical!r}). Known: {sorted(self._providers.keys())}")
        resolved = ResolvedProvider(
            canonical=entry["canonical"],
            family=entry["family"],
            context_limit=entry["context_limit"],
            reasoning=entry["reasoning"],
            quota_bucket=entry["quota_bucket"],
        )
        if require_reasoning and not resolved.reasoning:
            raise CapabilityMismatchError(f"Provider {resolved.canonical!r} does not support reasoning")
        return resolved

    def known_providers(self) -> list[str]:
        self.load()
        return sorted(self._providers.keys())

_default_registry: Optional[ProviderRegistry] = None

def get_registry(path: Optional[Path] = None) -> ProviderRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = ProviderRegistry(path)
    return _default_registry

def resolve(provider: str, *, require_reasoning: bool = False, fallback: Optional[str] = None) -> ResolvedProvider:
    return get_registry().resolve(provider, require_reasoning=require_reasoning, fallback=fallback)
