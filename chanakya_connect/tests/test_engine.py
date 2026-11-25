"""Comprehensive unit tests for ChanakyaConnect Core Engine and DSA structures."""

import os
import tempfile
import time
import unittest
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.data_structures import HashTable, MaxHeap, Queue, SocialGraph, Stack, Trie
from core.engine import ChanakyaConnectEngine


class TestDataStructures(unittest.TestCase):
    def test_hashtable_put_get_delete_resize(self):
        ht = HashTable(initial_capacity=8)
        for i in range(40):
            ht.put(f"key_{i}", i * 10)
        self.assertEqual(len(ht), 40)
        self.assertEqual(ht.get("key_25"), 250)
        self.assertTrue(ht.delete("key_25"))
        self.assertIsNone(ht.get("key_25"))
        self.assertEqual(len(ht), 39)

    def test_trie_prefix_search(self):
        trie = Trie()
        trie.insert("shrish", "shrish")
        trie.insert("Shrish Hegde", "shrish")
        trie.insert("shreya", "shreya")
        trie.insert("ananya", "ananya")
        self.assertEqual(trie.search_prefix("shr"), ["shreya", "shrish"])
        self.assertEqual(trie.search_prefix("an"), ["ananya"])
        self.assertEqual(trie.search_prefix("xyz"), [])

    def test_queue_and_stack(self):
        q = Queue()
        q.enqueue("a")
        q.enqueue("b")
        self.assertEqual(q.dequeue(), "a")
        self.assertEqual(q.dequeue(), "b")
        self.assertIsNone(q.dequeue())

        st = Stack()
        st.push("page1")
        st.push("page2")
        self.assertEqual(st.pop(), "page2")
        self.assertEqual(st.pop(), "page1")
        self.assertIsNone(st.pop())

    def test_max_heap(self):
        h = MaxHeap()
        h.push(10.0, "low")
        h.push(50.0, "high")
        h.push(30.0, "mid")
        self.assertEqual(h.pop(), "high")
        self.assertEqual(h.pop(), "mid")
        self.assertEqual(h.pop(), "low")

    def test_graph_bfs_jaccard_communities(self):
        g = SocialGraph()
        for u in ["a", "b", "c", "d", "e", "f"]:
            g.add_user(u)
        # Component 1: a-b-c-d
        for u, v in [("a", "b"), ("b", "c"), ("c", "d")]:
            g.send_request(u, v)
            g.accept_request(v, u)
        # Component 2: e-f
        g.send_request("e", "f")
        g.accept_request("f", "e")

        deg, path = g.bfs_degree_and_path("a", "d")
        self.assertEqual(deg, 3)
        self.assertEqual(path, ["a", "b", "c", "d"])

        deg_none, path_none = g.bfs_degree_and_path("a", "e")
        self.assertIsNone(deg_none)
        self.assertEqual(path_none, [])

        recs = g.people_you_may_know("a")
        self.assertEqual(recs[0][0], "c")
        self.assertGreater(recs[0][1], 0.0)

        comms = g.detect_communities()
        self.assertEqual(len(comms), 2)
        self.assertEqual(comms[0], ["a", "b", "c", "d"])
        self.assertEqual(comms[1], ["e", "f"])


class TestEngineAndPersistence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.tmp.close()
        os.remove(self.tmp.name)

    def tearDown(self):
        if os.path.exists(self.tmp.name):
            os.remove(self.tmp.name)

    def test_full_workflow_and_restart_persistence(self):
        eng = ChanakyaConnectEngine(storage_path=self.tmp.name)
        ok, _ = eng.signup("alice", "secret123", "Alice Rao", "B.Tech CSAI", 2, "AI bio", ["Python"])
        self.assertTrue(ok)
        ok, _ = eng.signup("bob", "secret123", "Bob Nair", "B.Tech EECS", 2, "Robotics", ["C++"])
        self.assertTrue(ok)

        # Password must not be stored in plain text
        stored_user = eng.users.get("alice")
        self.assertNotEqual(stored_user.password_hash, "secret123")

        ok, _, tok = eng.login("alice", "secret123")
        self.assertTrue(ok)
        self.assertIsNotNone(tok)

        # Connection + Post + Comment tree + Undo delete
        eng.send_connection_request("alice", "bob")
        eng.accept_connection_request("bob", "alice")

        _, _, post = eng.create_post("bob", "First hardware prototype!")
        time.sleep(0.01)
        _, _, post2 = eng.create_post("bob", "Second update!")

        feed = eng.get_home_feed("alice")
        self.assertEqual(len(feed), 2)
        self.assertEqual(feed[0]["post_id"], post2["post_id"])  # newest first

        # Nested comment tree
        _, _, c1 = eng.add_comment("alice", post["post_id"], "Nice!")
        _, _, c2 = eng.add_comment("bob", post["post_id"], "Thanks!", parent_comment_id=c1["comment_id"])
        self.assertIsNotNone(c2)

        # Delete & Undo Delete (Stack)
        ok, _ = eng.delete_post("bob", post["post_id"])
        self.assertTrue(ok)
        self.assertEqual(len(eng.get_user_posts("bob")), 1)
        ok, _, restored = eng.undo_delete_post("bob")
        self.assertTrue(ok)
        self.assertEqual(restored["post_id"], post["post_id"])

        # Restart simulation: load fresh engine from same JSON file
        eng2 = ChanakyaConnectEngine(storage_path=self.tmp.name)
        self.assertEqual(len(eng2.users), 2)
        self.assertTrue(eng2.graph.are_connected("alice", "bob"))
        self.assertEqual(len(eng2.get_home_feed("alice")), 2)
        self.assertEqual(eng2.search_users("ali")[0]["username"], "alice")



    def test_linkedin_jobs_dms_endorsements(self):
        eng = ChanakyaConnectEngine(storage_path=self.tmp.name)
        eng.signup("alice", "secret123", "Alice", "B.Tech CSAI", 2, "", ["Python", "DSA"])
        eng.signup("bob", "secret123", "Bob", "B.Tech EECS", 2, "", ["C++"])

        ok, _ = eng.endorse_skill("bob", "alice", "Python")
        self.assertTrue(ok)
        self.assertEqual(eng.get_profile("alice")["endorsements"]["Python"], ["bob"])

        _, _, j1 = eng.create_job("bob", "Python Intern", "Lab", "Bangalore", "Internship", "Desc", ["Python", "DSA"])
        _, _, j2 = eng.create_job("bob", "VLSI Intern", "Lab", "Bangalore", "Internship", "Desc", ["Verilog"])
        jobs = eng.get_jobs_for_user("alice")
        self.assertEqual(jobs[0]["job_id"], j1["job_id"])
        self.assertEqual(jobs[0]["skill_match_pct"], 100.0)
        self.assertEqual(jobs[1]["skill_match_pct"], 0.0)

        ok, _ = eng.apply_to_job("alice", j1["job_id"])
        self.assertTrue(ok)
        ok, _ = eng.respond_to_job_application("bob", j1["job_id"], "alice", "accepted")
        self.assertTrue(ok)
        self.assertEqual(eng.get_jobs_for_user("alice")[0]["my_status"], "accepted")

        ok, _, _ = eng.send_message("alice", "bob", "Hello Bob!")
        self.assertTrue(ok)
        self.assertEqual(len(eng.get_messages("alice", "bob")), 1)


if __name__ == "__main__":
    unittest.main()
