import unittest
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sync.crdt_engine import CRDTEngine

class TestCRDTEngine(unittest.TestCase):

    def setUp(self):
        self.crdt = CRDTEngine()

    def test_update_vector_clock(self):
        self.crdt.update_vector_clock("peer1")
        self.assertEqual(self.crdt.vector_clocks["peer1"], 1)
        self.crdt.update_vector_clock("peer1")
        self.assertEqual(self.crdt.vector_clocks["peer1"], 2)

    def test_merge_vector_clocks(self):
        self.crdt.vector_clocks = {"peer1": 2, "peer2": 3}
        incoming_clock = {"peer1": 5, "peer3": 1}
        self.crdt.merge_vector_clocks(incoming_clock)
        self.assertEqual(self.crdt.vector_clocks["peer1"], 5)
        self.assertEqual(self.crdt.vector_clocks["peer2"], 3)
        self.assertEqual(self.crdt.vector_clocks["peer3"], 1)

    def test_add_message(self):
        self.crdt.add_message("msg1", "Hello, World!", "peer1")
        self.assertIn("msg1", self.crdt.messages)
        self.assertEqual(self.crdt.messages["msg1"]["content"], "Hello, World!")
        self.assertEqual(self.crdt.messages["msg1"]["peer_id"], "peer1")

    def test_get_missing_messages(self):
        self.crdt.add_message("msg1", "Hello, World!", "peer1")
        self.crdt.add_message("msg2", "Another message", "peer2")
        known_clock = {"peer1": 0}
        missing = self.crdt.get_missing_messages(known_clock)
        self.assertEqual(len(missing), 2)
        self.assertEqual(missing[0]["content"], "Hello, World!")
        self.assertEqual(missing[1]["content"], "Another message")

if __name__ == "__main__":
    unittest.main()