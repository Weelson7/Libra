import os
import sys
import tempfile
import importlib
import time
from pathlib import Path


def run_test():
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))

    with tempfile.TemporaryDirectory() as td:
        os.environ["LIBRA_DATA_DIR"] = str(Path(td) / "data")
        os.environ["LIBRA_KEY_DIR"] = str(Path(td) / "keys")

        import config
        importlib.reload(config)

        # create two identities
        from main import cmd_init
        res1 = cmd_init(passphrase=b"p1", nickname="one")
        peer1 = res1["peer_id"]

        # create second identity manually
        from utils.crypto_utils import generate_rsa_keypair, save_keys_for_peer
        priv2, pub2 = generate_rsa_keypair()
        save_keys_for_peer(priv2, pub2, b"p2", peer_id="peerB")

        # start discovery instances on different ports and target each other
        from peer.peer_discovery import PeerDiscovery

        port1 = 37021
        port2 = 37022

        pd1 = PeerDiscovery(peer_id=peer1, passphrase=b"p1", port=port1, targets=[("127.0.0.1", port2)], use_broadcast=False, interval=1.0)
        pd2 = PeerDiscovery(peer_id="peerB", passphrase=b"p2", port=port2, targets=[("127.0.0.1", port1)], use_broadcast=False, interval=1.0)

        pd1.start()
        pd2.start()

        # give time for beacons to be exchanged
        time.sleep(3)

        # stop discovery instances before inspection to avoid file locks
        pd1.stop()
        pd2.stop()

        # verify pd1's DB has peerB
        from db.db_handler import DBHandler
        db = DBHandler()
        p = db.get_peer("peerB")
        db.close()
        assert p is not None, "peerB should be discovered by pd1"

    print("test_peer_discovery: PASS")


if __name__ == "__main__":
    run_test()
