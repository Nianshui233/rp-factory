"""用发布入口复核 EJS、MVU 和酒馆包的技术契约。"""
import json
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/dry-run-盐湖守夜人"
TRACE = EXAMPLE / "制作文件"
ASSETS = TRACE / "产物"
PACKAGE = EXAMPLE / "导入包"


def validate(script, *args):
    return subprocess.run([sys.executable, str(ROOT / "scripts" / script), *map(str, args)],
                          capture_output=True, text=True, encoding="utf-8")


class RuntimeContracts(unittest.TestCase):
    def test_controller_compiles_and_all_three_tiers_are_reachable(self):
        src = next((ASSETS / "ejs").glob("*.ejs")).read_text(encoding="utf-8")
        variants = [(src, None), (src.rsplit("<%_ } _%>", 1)[0], "E00"),
                    (src.replace(">= 67", ">= 33"), "E06")]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "controller.ejs"
            for content, error in variants:
                with self.subTest(error=error):
                    path.write_text(content, encoding="utf-8")
                    run = validate("validate-ejs.py", path)
                    self.assertEqual(run.returncode, int(error is not None), run.stdout + run.stderr)
                    if error:
                        self.assertIn(error, run.stdout)

    def test_mvu_rejects_changed_lower_bound(self):
        contract = yaml.safe_load((TRACE / "项目记录" / "contract.yaml").read_text(encoding="utf-8"))
        contract["naming"]["axes"][0]["range"][0] = -50
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "contract.yaml"
            path.write_text(yaml.safe_dump(contract, allow_unicode=True), encoding="utf-8")
            run = validate("validate-mvu.py", ASSETS / "mvu", "--contract", path)
            self.assertEqual(run.returncode, 1, run.stdout)
            self.assertIn("M04", run.stdout)

    def test_negative_lower_bound_in_schema_matches_contract(self):
        contract = yaml.safe_load((TRACE / "项目记录" / "contract.yaml").read_text(encoding="utf-8"))
        for axis in contract["naming"]["axes"]:
            axis["range"][0] = -50
        with tempfile.TemporaryDirectory() as folder:
            dest = Path(folder)
            shutil.copytree(ASSETS / "mvu", dest / "mvu")
            schema = dest / "mvu/变量结构.js"
            schema.write_text(schema.read_text(encoding="utf-8").replace("clamp(v, 0, 上界)",
                                                                         "clamp(v, -50, 上界)"),
                              encoding="utf-8")
            path = dest / "contract.yaml"
            path.write_text(yaml.safe_dump(contract, allow_unicode=True), encoding="utf-8")
            run = validate("validate-mvu.py", dest / "mvu", "--contract", path)
            self.assertEqual(run.returncode, 0, run.stdout)

    def test_final_mvu_statusbar_must_read_saved_state(self):
        with tempfile.TemporaryDirectory() as folder:
            dest = Path(folder)
            for src in PACKAGE.glob("*.json"):
                (dest / src.name).write_bytes(src.read_bytes())
            target = dest / "正则.json"
            scripts = json.loads(target.read_text(encoding="utf-8"))
            for script in scripts:
                if "状态栏" in script["scriptName"]:
                    script["findRegex"] = "<状态栏>(.*)</状态栏>"
                    script["replaceString"] = "<body>$1</body>"
            target.write_text(json.dumps(scripts, ensure_ascii=False), encoding="utf-8")
            run = validate("validate-st-package.py", dest, "--contract", TRACE / "项目记录" / "contract.yaml")
            self.assertEqual(run.returncode, 1, run.stdout)
            self.assertIn("X07", run.stdout)

    def test_packaged_hud_renders_current_floor_and_zero(self):
        # 仅运行仓库自带的固定样包。消息读取、宿主 DOM 用本地测试对象提供。
        code = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const rules = JSON.parse(fs.readFileSync(process.argv[1], 'utf8'));
// 界面是手动粘贴的：测试里用包内的 .html 模拟“粘到替换里”这一步
const pasted = fs.readFileSync(process.argv[2], 'utf8');
let message = '<StatusPlaceHolderImpl/>';
let usedPaste = false;
for (const rule of rules) {
  if (!rule.markdownOnly || rule.disabled || !rule.placement.includes(2)) continue;
  const match = rule.findRegex.match(/^\/(.*)\/(\w*)$/);
  const regex = match ? new RegExp(match[1], match[2]) : new RegExp(rule.findRegex);
  const pending = String(rule.replaceString).startsWith('【尚未粘贴界面】');
  const repl = pending ? pasted : rule.replaceString;
  if (pending && regex.test(message)) usedPaste = true;
  message = message.replace(regex, repl);
}
assert.equal(usedPaste, true, '状态栏正则应该是待粘贴态，且 html 能接上');
const script = message.match(/<script>([\s\S]*?)<\/script>/)[1];
const root = {innerHTML: ''};
let record = {角色: {祁昭: {wick: 0, tide: 82}}};
const readIds = [];
const host = {
  document: {getElementById: () => root},
  waitGlobalInitialized: async () => {},
  getCurrentMessageId: () => 3,
  Mvu: {getMvuData: ({type, message_id}) => {
    assert.equal(type, 'message');
    readIds.push(message_id);
    return message_id === 3 ? {stat_data: record} : {};
  }}
};
(async () => {
  vm.runInNewContext(script, host);
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(readIds, [3, 2]);
  assert.match(root.innerHTML, />0</);
  assert.match(root.innerHTML, />82</);
  record = undefined;
  vm.runInNewContext(script, host);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(root.innerHTML, '');
})().catch(error => { console.error(error); process.exitCode = 1; });
"""
        run = subprocess.run(["node", "-e", code, str(PACKAGE / "正则.json"),
                              str(PACKAGE / "白潮 状态栏.html")],
                             capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(run.returncode, 0, run.stderr)
