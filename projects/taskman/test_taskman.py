"""Black-box tests: every case drives taskman.py via subprocess against a temp store."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "taskman.py")


class CliTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="taskman-test-")
        self.store = os.path.join(self.tmpdir, "store.json")
        self.addCleanup(shutil.rmtree, self.tmpdir, True)

    def run_cli(self, *args, **kw):
        env = dict(os.environ)
        env["TASKMAN_STORE"] = kw.pop("store", self.store)
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run(
            [sys.executable, SCRIPT] + list(args),
            capture_output=True, text=True, env=env, cwd=self.tmpdir,
        )
        return proc

    def ok(self, *args):
        proc = self.run_cli(*args)
        self.assertEqual(proc.returncode, 0, "stderr=%r" % proc.stderr)
        return proc.stdout

    def read_store(self):
        with open(self.store, encoding="utf-8") as fh:
            return json.load(fh)


class TestAdd(CliTestCase):
    def test_add_creates_store_and_reports_id(self):
        out = self.ok("add", "write", "the", "docs")
        self.assertIn("added task 1: write the docs", out)
        self.assertTrue(os.path.exists(self.store))
        db = self.read_store()
        self.assertEqual(len(db["tasks"]), 1)
        self.assertEqual(db["tasks"][0]["title"], "write the docs")
        self.assertFalse(db["tasks"][0]["done"])

    def test_ids_increment_and_do_not_reuse(self):
        self.ok("add", "one")
        self.ok("add", "two")
        self.ok("rm", "2")
        self.ok("add", "three")
        ids = [t["id"] for t in self.read_store()["tasks"]]
        self.assertEqual(ids, [1, 3])

    def test_priority_and_tags_are_persisted(self):
        self.ok("add", "ship", "-p", "high", "-t", "work,urgent", "-t", "q3")
        task = self.read_store()["tasks"][0]
        self.assertEqual(task["priority"], "high")
        self.assertEqual(task["tags"], ["work", "urgent", "q3"])

    def test_invalid_priority_rejected(self):
        proc = self.run_cli("add", "nope", "-p", "critical")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("invalid choice", proc.stderr)

    def test_whitespace_only_title_rejected(self):
        proc = self.run_cli("add", "   ", "  ")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("title must not be empty", proc.stderr)
        self.assertFalse(os.path.exists(self.store))


class TestList(CliTestCase):
    def test_list_empty_store(self):
        self.assertIn("no tasks", self.ok("list"))

    def test_table_columns_are_aligned(self):
        self.ok("add", "short")
        self.ok("add", "a", "much", "longer", "title", "here")
        lines = self.ok("list").splitlines()
        self.assertEqual(lines[0].split()[:5], ["ID", "DONE", "PRI", "TITLE", "TAGS"])
        self.assertEqual(set(lines[1]) - {" "}, {"-"})
        title_col = lines[0].index("TITLE")
        self.assertTrue(lines[2].startswith(" 1  ") or lines[2].startswith("1  "))
        for row in lines[2:]:
            self.assertEqual(row[title_col:title_col + 1].strip() != "", True)

    def test_done_tasks_hidden_by_default_and_shown_with_all(self):
        self.ok("add", "alpha")
        self.ok("add", "beta")
        self.ok("done", "1")
        default = self.ok("list")
        self.assertNotIn("alpha", default)
        self.assertIn("beta", default)
        every = self.ok("list", "--all")
        self.assertIn("alpha", every)
        self.assertIn("beta", every)
        self.assertIn("alpha", self.ok("list", "--done-only"))

    def test_filter_by_tag_and_priority(self):
        self.ok("add", "tagged", "-t", "home", "-p", "low")
        self.ok("add", "other", "-t", "work", "-p", "high")
        by_tag = self.ok("list", "--tag", "home")
        self.assertIn("tagged", by_tag)
        self.assertNotIn("other", by_tag)
        by_prio = self.ok("list", "--priority", "high")
        self.assertIn("other", by_prio)
        self.assertNotIn("tagged", by_prio)
        self.assertIn("no tasks", self.ok("list", "--tag", "missing"))

    def test_list_json_output_is_valid_and_matches_store(self):
        self.ok("add", "jsonify", "-t", "x")
        out = self.ok("list", "--json")
        payload = json.loads(out)
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["title"], "jsonify")
        self.assertEqual(payload[0]["tags"], ["x"])

    def test_sort_by_priority(self):
        self.ok("add", "lowly", "-p", "low")
        self.ok("add", "urgent", "-p", "high")
        self.ok("add", "middle", "-p", "med")
        lines = self.ok("list", "--sort", "priority").splitlines()
        title_col = lines[0].index("TITLE")
        titles = [line[title_col:].split()[0] for line in lines[2:]]
        self.assertEqual(titles, ["urgent", "middle", "lowly"])


class TestDoneAndRm(CliTestCase):
    def test_done_sets_flag_and_timestamp(self):
        self.ok("add", "finish me")
        out = self.ok("done", "1")
        self.assertIn("completed task 1", out)
        task = self.read_store()["tasks"][0]
        self.assertTrue(task["done"])
        self.assertIsNotNone(task["completed"])

    def test_done_twice_is_idempotent(self):
        self.ok("add", "x")
        self.ok("done", "1")
        out = self.ok("done", "1")
        self.assertIn("already done", out)
        self.assertEqual(sum(1 for t in self.read_store()["tasks"] if t["done"]), 1)

    def test_done_and_rm_accept_multiple_ids(self):
        for name in ("a", "b", "c", "d"):
            self.ok("add", name)
        self.ok("done", "1", "2")
        self.ok("rm", "3", "4")
        db = self.read_store()
        self.assertEqual([t["id"] for t in db["tasks"]], [1, 2])
        self.assertTrue(all(t["done"] for t in db["tasks"]))

    def test_missing_id_errors_without_partial_write(self):
        self.ok("add", "keep")
        proc = self.run_cli("rm", "1", "99")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("no such task: 99", proc.stderr)
        self.assertEqual(len(self.read_store()["tasks"]), 1)

    def test_non_integer_id_rejected(self):
        proc = self.run_cli("done", "abc")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("invalid int value", proc.stderr)


class TestStats(CliTestCase):
    def test_stats_on_empty_store(self):
        out = self.ok("stats")
        self.assertRegex(out, r"total\s+0")
        self.assertRegex(out, r"percent done\s+0\.0%")

    def test_stats_counts_and_percentage(self):
        self.ok("add", "a", "-p", "high", "-t", "work")
        self.ok("add", "b", "-p", "low", "-t", "work")
        self.ok("add", "c", "-p", "high")
        self.ok("add", "d")
        self.ok("done", "1")
        out = self.ok("stats")
        self.assertRegex(out, r"total\s+4")
        self.assertRegex(out, r"open\s+3")
        self.assertRegex(out, r"done\s+1")
        self.assertRegex(out, r"percent done\s+25\.0%")
        self.assertRegex(out, r"open/high\s+1")
        self.assertRegex(out, r"tag/work\s+2")


class TestHelpAndJson(CliTestCase):
    def test_top_level_and_subcommand_help_exit_cleanly(self):
        for args in (("--help",), ("add", "-h"), ("list", "-h"), ("done", "-h"),
                     ("rm", "-h"), ("stats", "-h")):
            proc = self.run_cli(*args)
            self.assertEqual(proc.returncode, 0, "args=%r stderr=%r" % (args, proc.stderr))
            self.assertIn("usage:", proc.stdout)

    def test_stats_json_output_is_valid(self):
        self.ok("add", "a", "-p", "high", "-t", "work")
        self.ok("add", "b")
        self.ok("done", "1")
        payload = json.loads(self.ok("stats", "--json"))
        self.assertEqual(payload["total"], 2)
        self.assertEqual(payload["done"], 1)
        self.assertEqual(payload["open_by_priority"]["high"], 0)
        self.assertEqual(payload["tags"]["work"], 1)


class TestStoreHandling(CliTestCase):
    def test_store_flag_overrides_env(self):
        other = os.path.join(self.tmpdir, "nested", "other.json")
        self.ok("--store", other, "add", "elsewhere")
        self.assertTrue(os.path.exists(other))
        self.assertFalse(os.path.exists(self.store))
        self.assertIn("elsewhere", self.ok("--store", other, "list"))

    def test_corrupt_store_reports_error(self):
        with open(self.store, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        proc = self.run_cli("list")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("corrupt store", proc.stderr)

    def test_no_command_prints_help(self):
        proc = self.run_cli()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("usage:", proc.stdout)

    def test_data_survives_separate_invocations(self):
        self.ok("add", "persisted")
        self.assertIn("persisted", self.ok("list"))
        self.assertIn("persisted", self.ok("list"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
