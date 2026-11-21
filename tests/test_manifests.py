"""四份宿主清单的契约：版本一致、路径存在、skill 名与目录名一致。

宿主判断"有没有更新"只看清单里的版本号，所以版本漂移不是审美问题，
是"用户永远收不到更新"这种静默故障。这一组测试把它变成红的。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills" / "rp-factory"
SKILL_MD = SKILL / "SKILL.md"
CHANGELOG = REPO / "CHANGELOG.md"

MANIFESTS = [
    "package.json",
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    ".codex-plugin/plugin.json",
    ".agents/plugins/marketplace.json",
    "host-adapters/dsh/plugin/package.json",
]

VERSION_RE = re.compile(r"^  version:\s*(\S+)\s*$", re.M)
NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.M)


def load(rel: str) -> dict:
    return json.loads((REPO / rel).read_text(encoding="utf-8"))


def declared_versions(data: dict) -> list[str]:
    out = []
    if "version" in data:
        out.append(data["version"])
    for plugin in data.get("plugins", []) or []:
        if isinstance(plugin, dict) and "version" in plugin:
            out.append(plugin["version"])
    return out


def skill_version() -> str:
    m = VERSION_RE.search(SKILL_MD.read_text(encoding="utf-8"))
    assert m, "SKILL.md 缺少 metadata.version"
    return m.group(1)


class TestManifestFiles(unittest.TestCase):
    def test_all_manifests_are_valid_json(self):
        for rel in MANIFESTS:
            with self.subTest(manifest=rel):
                self.assertIsInstance(load(rel), dict)

    def test_versions_match_skill_md(self):
        expected = skill_version()
        for rel in MANIFESTS:
            for got in declared_versions(load(rel)):
                with self.subTest(manifest=rel):
                    self.assertEqual(got, expected, f"{rel} 的版本与 SKILL.md 不一致")

    def test_changelog_head_matches(self):
        m = re.search(r"^##\s+([0-9]+\.[0-9]+\.[0-9]+)", CHANGELOG.read_text(encoding="utf-8"), re.M)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), skill_version())

    def test_sync_script_reports_clean(self):
        proc = subprocess.run([sys.executable, str(REPO / "scripts" / "sync-manifests.py"), "--check"],
                              cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
        self.assertEqual(proc.returncode, 0, (proc.stdout or "") + (proc.stderr or ""))


class TestSkillShape(unittest.TestCase):
    def test_skill_dir_name_matches_front_matter(self):
        """DSH 与 Codex 都要求目录名 == front matter 的 name，不符直接装不上。"""
        m = NAME_RE.search(SKILL_MD.read_text(encoding="utf-8").split("---")[1])
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "rp-factory")
        self.assertEqual(SKILL.name, "rp-factory")

    def test_skill_dir_has_only_runtime_things(self):
        self.assertEqual(sorted(p.name for p in SKILL.iterdir()),
                         ["SKILL.md", "examples", "references", "scripts", "templates"])


class TestHostPointers(unittest.TestCase):
    def test_claude_plugin_points_at_root(self):
        plugin = load(".claude-plugin/plugin.json")
        self.assertEqual(plugin["skills"], ["."])
        self.assertEqual(plugin["license"], "MIT")

    def test_claude_marketplace_is_relative(self):
        """相对路径让「市场仓库 == 插件仓库」，安装不必再 clone 一次（也不必连 GitHub）。"""
        plugins = load(".claude-plugin/marketplace.json")["plugins"]
        self.assertEqual(len(plugins), 1)
        self.assertEqual(plugins[0]["name"], "rp-factory")
        self.assertTrue(str(plugins[0]["source"]).startswith("./"))

    def test_codex_plugin_skills_path_exists(self):
        plugin = load(".codex-plugin/plugin.json")
        rel = plugin["skills"].lstrip("./").rstrip("/")
        self.assertTrue((REPO / rel / "SKILL.md").is_file(), plugin["skills"])
        self.assertTrue(plugin["interface"]["defaultPrompt"])

    def test_codex_marketplace_source_resolves(self):
        entry = load(".agents/plugins/marketplace.json")["plugins"][0]
        self.assertEqual(entry["source"]["source"], "local")
        self.assertTrue((REPO / entry["source"]["path"]).is_dir())

    def test_npm_files_include_skill(self):
        pkg = load("package.json")
        self.assertIn("skills/rp-factory/", pkg["files"])
        self.assertEqual(pkg["pi"]["skills"], ["./skills/rp-factory"])
        self.assertEqual(pkg["license"], "MIT")
        self.assertIn("pi-package", pkg["keywords"])

    def test_license_file_exists(self):
        text = (REPO / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("MIT License", text)


class TestDshPlugin(unittest.TestCase):
    def test_plugin_registers_one_skill(self):
        script = (
            "import('./host-adapters/dsh/plugin/index.js').then(m => {"
            "  const c = m.loadSkillCatalog('skills');"
            "  const p = m.createProvider(c);"
            "  return p.list().then(l => p.get(l[0]).then(d => {"
            "    console.log(JSON.stringify({n: l.length, name: d.name, model: d.invocation.modelInvocable}));"
            "  }));"
            "}).catch(e => { console.error(e.message); process.exit(1); })"
        )
        proc = subprocess.run(["node", "--input-type=module", "-e", script],
                              cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(proc.returncode, 0, (proc.stdout or "") + (proc.stderr or ""))
        data = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(data["n"], 1)
        self.assertEqual(data["name"], "rp-factory")
        # SKILL.md 锁了 disable-model-invocation: true
        self.assertFalse(data["model"])

    def test_preset_mount_can_override_invocation(self):
        """`RP-Factory` 预设挂的那份带 modelInvocable: true——选了预设就是显式进流程。

        不带这个开关时模型读不到 SKILL.md（真机会话 session-111be7e6 里，
        用户选了预设、说「开始」，模型摸黑找了五个回合才报告「skill 没装上」）。
        """
        script = (
            "import('./host-adapters/dsh/plugin/index.js').then(m => {"
            "  const c = m.loadSkillCatalog('skills');"
            "  m.applyModelInvocation(c, true);"
            "  console.log(JSON.stringify({m: c[0].invocation.modelInvocable}));"
            "}).catch(e => { console.error(e.message); process.exit(1); })"
        )
        proc = subprocess.run(["node", "--input-type=module", "-e", script],
                              cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(proc.returncode, 0, (proc.stdout or "") + (proc.stderr or ""))
        self.assertTrue(json.loads(proc.stdout.strip().splitlines()[-1])["m"])


class TestDshBundlePatch(unittest.TestCase):
    """bundle 补丁一次给两样东西：skill provider + 可选的 RP-Factory 预设。

    预设 ID 必须与 skill 名一致（`rp-factory`），否则用户看到「RP-Factory」预设，敲命令却提领不到 skill；
    工具集也必须真的裁过——留着 subagent/workflow 的话，「一次只跑一个阶段」只是句劝告。
    """

    ADAPTER = REPO / "host-adapters" / "dsh" / "plugin"

    @classmethod
    def setUpClass(cls):
        import yaml

        class Loader(yaml.SafeLoader):
            pass

        # 补丁里的 `!!js <expr>` 由 DSH 的 compose 求值；测试只关心行结构，当字符串读。
        Loader.add_constructor("tag:yaml.org,2002:js", lambda loader, node: loader.construct_scalar(node))
        text = (cls.ADAPTER / "cordis.patch.yml").read_text(encoding="utf-8")
        documents = yaml.load(text, Loader=Loader)
        cls.rows = documents[0]["insert"]

    def row_named(self, name):
        for row in self.rows:
            if row.get("name") == name:
                return row
        self.fail(f"cordis.patch.yml 里没有 name 为 {name} 的行")

    def test_rows_are_unique_and_complete(self):
        self.assertTrue(self.rows)
        ids = [row.get("id") for row in self.rows]
        self.assertEqual(len(ids), len(set(ids)), f"行 id 重复：{ids}")
        for row in self.rows:
            self.assertTrue(row.get("id"), f"行缺 id：{row}")
            self.assertTrue(row.get("name"), f"行缺 name：{row}")

    def test_patch_ships_plugin_and_preset(self):
        self.assertEqual(self.row_named("rp-factory-dsh")["id"], "rp-factory")
        preset = self.row_named("@deepseek-ai/dsh-agent-preset")
        self.assertEqual(preset["config"]["id"], "rp-factory")
        self.assertEqual(preset["config"]["name"], "RP-Factory")

    def test_preset_plugins_are_lean_but_keep_skill_tool(self):
        preset = self.row_named("@deepseek-ai/dsh-agent-preset")
        plugins = preset["config"]["plugins"]
        ids = [plugin.get("id") for plugin in plugins]
        self.assertEqual(len(ids), len(set(ids)), f"预设插件 id 重复：{ids}")
        for plugin in plugins:
            self.assertTrue(plugin.get("id") and plugin.get("name"), f"预设插件缺 id/name：{plugin}")

        # 斜杠命令的入口：没有 tool-skill，预设里的会话根本看不到这个 skill
        self.assertIn("tool-skill", ids)
        # 「一次只跑一个阶段」：这些一旦在，模型可以自己把流程拆散跑完
        banned = {"tool-subagent", "tool-subagent-fork", "tool-workflow", "plan-mode",
                  "command-goal", "tool-goal", "tool-schedule", "tool-jobs", "tool-office"}
        self.assertEqual(banned & set(ids), set(), "预设里不该有会自己跑完整个流程的工具")
        persona = next(plugin for plugin in plugins if plugin["id"] == "persona")
        self.assertIn("/rp-factory", persona["config"]["prefix"])

    def test_preset_mounts_model_invocable_skill(self):
        """预设必须自己再挂一份 provider，并允许模型直接读 SKILL.md。

        否则用户「选了预设 → 说开始」时读不到 skill：人格要求「先按 SKILL.md 判阶段」，
        模型却只能去磁盘摸黑找文件（真机会话 session-111be7e6 的现场）。
        """
        preset = self.row_named("@deepseek-ai/dsh-agent-preset")
        plugins = preset["config"]["plugins"]
        row = next((p for p in plugins if p.get("name") == "rp-factory-dsh"), None)
        self.assertIsNotNone(row, "预设里没挂 rp-factory-dsh，模型读不到 SKILL.md")
        self.assertIs(row["config"]["modelInvocable"], True)


if __name__ == "__main__":
    unittest.main()
