"""
Simple alias registry for Libra v2.0 Phase 2.
"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Optional

from utils.alias_generator import generate_alias, validate_alias

class AliasRecord:
    def __init__(self, alias: str, onion: str, public_key: str, is_public: bool):
        self.alias = alias
        self.onion = onion
        self.public_key = public_key
        self.is_public = is_public
        self.created_at = datetime.utcnow()
        self.last_seen = self.created_at
        self.metadata: Dict[str, str] = {}

    def update_last_seen(self):
        self.last_seen = datetime.utcnow()

class AliasRegistry:
    def __init__(self):
        self._public_registry: Dict[str, AliasRecord] = {}
        self._private_registry: Dict[str, AliasRecord] = {}

    def publish_alias(self, onion: str, public_key: str, alias: Optional[str] = None, is_public: bool = True):
        alias = alias or generate_alias(seed=public_key)
        if not validate_alias(alias):
            raise ValueError("Alias must be a three-word phrase from the approved lists")

        registry = self._public_registry if is_public else self._private_registry
        record = AliasRecord(alias=alias, onion=onion, public_key=public_key, is_public=is_public)
        registry[alias] = record
        return record

    def lookup_alias(self, alias: str, include_private: bool = False) -> Optional[AliasRecord]:
        record = self._public_registry.get(alias)
        if record:
            record.update_last_seen()
            return record
        if include_private:
            record = self._private_registry.get(alias)
            if record:
                record.update_last_seen()
            return record
        return None

    def remove_alias(self, alias: str, include_private: bool = True):
        removed = self._public_registry.pop(alias, None)
        if not removed and include_private:
            removed = self._private_registry.pop(alias, None)
        return removed

    def purge_stale(self, threshold_minutes: int = 60):
        now = datetime.utcnow()
        def _purge(registry):
            stale = [alias for alias, record in registry.items()
                     if now - record.last_seen > timedelta(minutes=threshold_minutes)]
            for alias in stale:
                registry.pop(alias, None)
        _purge(self._public_registry)
        _purge(self._private_registry)
