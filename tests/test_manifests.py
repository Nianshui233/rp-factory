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


if __name__ == "__main__":
    unittest.main()
