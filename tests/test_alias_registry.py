import os
import sys
import unittest

# ensure repo root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.alias_generator import generate_alias, validate_alias, alias_from_onion
from utils.alias_registry import AliasRegistry

class AliasGeneratorTests(unittest.TestCase):
    def test_generate_alias_random(self):
        alias = generate_alias()
        self.assertTrue(validate_alias(alias))

    def test_alias_from_onion_is_deterministic(self):
        onion = "abcdefg1234567890.onion"
        alias_a = alias_from_onion(onion)
        alias_b = alias_from_onion(onion)
        self.assertEqual(alias_a, alias_b)
        self.assertTrue(validate_alias(alias_a))

class AliasRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = AliasRegistry()
        self.onion = "exampleonionaddress123.onion"
        self.public_key = "pubkey"

    def test_publish_and_lookup_public_alias(self):
        record = self.registry.publish_alias(onion=self.onion, public_key=self.public_key)
        self.assertEqual(record.onion, self.onion)
        found = self.registry.lookup_alias(record.alias)
        self.assertIsNotNone(found)
        self.assertEqual(found.onion, self.onion)

    def test_publish_private_and_lookup(self):
        record = self.registry.publish_alias(onion=self.onion, public_key=self.public_key, is_public=False)
        self.assertIsNone(self.registry.lookup_alias(record.alias))
        found = self.registry.lookup_alias(record.alias, include_private=True)
        self.assertEqual(found.onion, self.onion)

    def test_remove_alias(self):
        record = self.registry.publish_alias(onion=self.onion, public_key=self.public_key)
        removed = self.registry.remove_alias(record.alias)
        self.assertEqual(removed.alias, record.alias)
        self.assertIsNone(self.registry.lookup_alias(record.alias))

    def test_purge_stale(self):
        record = self.registry.publish_alias(onion=self.onion, public_key=self.public_key)
        record.last_seen = record.last_seen.replace(year=2000)
        self.registry.purge_stale(threshold_minutes=1)
        self.assertIsNone(self.registry.lookup_alias(record.alias))

if __name__ == '__main__':
    unittest.main()
