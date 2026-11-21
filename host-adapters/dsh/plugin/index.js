/**
 * RP-Factory — DeepSeek Harness 宿主插件。
 *
 * 只做一件事：把包内的 `skills/rp-factory` 注册成一个 DSH skill provider。
 * 每条 skill 以自己所在目录为资源基，所以 SKILL.md 里写的
 * `references/…`、`scripts/…` 这类相对路径在 DSH 里能照常解析。
 *
 * 没有 front door、没有 agent preset、没有客户端面板：RP-Factory 只有一个 skill，
 * 靠 `/skill:rp-factory` 显式调用（SKILL.md 里锁了 disable-model-invocation）。
 */
import { existsSync, readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const name = "rp-factory";
// 需要宿主提供 skills 服务（provider 注册点）；没有 webServer 之类别的依赖
export const inject = ["skills"];

const PLUGIN_ROOT = path.dirname(fileURLToPath(import.meta.url));
const PACKAGED_SKILLS = path.join(PLUGIN_ROOT, "skills");
// 从源码树跑（host-adapters/dsh/plugin → 仓库根）时的回退
const SOURCE_REPO_ROOT = path.resolve(PLUGIN_ROOT, "..", "..", "..");
const SOURCE_SKILLS = path.join(SOURCE_REPO_ROOT, "skills");
const PROVIDER_NAME = "rp-factory";
// 与 @deepseek-ai/dsh-skill 的 BUNDLED_SKILL_RANK 对齐：打包进来的 skill 属于最高一档
const SKILL_RANK = 600;
const SKILL_NAME = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

function resolveSkillsRoot() {
  if (existsSync(PACKAGED_SKILLS)) return PACKAGED_SKILLS;
  if (existsSync(SOURCE_SKILLS)) return SOURCE_SKILLS;
  throw new Error(`RP-Factory skill bundle is missing: expected ${PACKAGED_SKILLS}`);
}

function stripQuotes(value) {
  const text = value.trim();
  if (text.length >= 2 && text.startsWith('"') && text.endsWith('"')) return text.slice(1, -1);
  if (text.length >= 2 && text.startsWith("'") && text.endsWith("'")) return text.slice(1, -1);
  return text;
}

/** 只认 RP-Factory 用到的 front matter 形态：name / description 单行，metadata 是嵌套块。 */
export function parseFrontMatter(sourceText, label) {
  const text = sourceText.replace(/^\uFEFF/, "").replace(/\r\n?/g, "\n");
  const lines = text.split("\n");
  if (lines[0].trim() !== "---") throw new Error(`SKILL.md front matter 必须从第 1 行开始：${label}`);
  const end = lines.findIndex((line, index) => index > 0 && line.trim() === "---");
  if (end < 0) throw new Error(`SKILL.md front matter 没有闭合：${label}`);

  const fields = Object.create(null);
  for (let index = 1; index < end; index += 1) {
    const line = lines[index];
    if (/^\s/.test(line)) continue; // 嵌套块（metadata:）不参与
    const match = /^([A-Za-z0-9_-]+):(?:[ \t]*(.*))?$/.exec(line);
    if (!match) continue;
    const value = (match[2] ?? "").trim();
    if (value.length > 0) fields[match[1]] = stripQuotes(value);
  }

  const skillName = fields.name ?? "";
  const description = fields.description ?? "";
  if (!SKILL_NAME.test(skillName)) throw new Error(`SKILL.md 的 name 不合法（"${skillName}"）：${label}`);
  if (description.trim().length === 0) throw new Error(`SKILL.md 缺少 description：${label}`);

  const disableModel = (fields["disable-model-invocation"] ?? "").trim().toLowerCase();
  const userInvocable = (fields["user-invocable"] ?? "").trim().toLowerCase();
  return {
    meta: {
      name: skillName,
      description,
      invocation: {
        modelInvocable: disableModel === "true" ? false : true,
        userInvocable: userInvocable === "false" ? false : true,
      },
    },
    content: lines.slice(end + 1).join("\n").replace(/^\n+/, "").trimEnd(),
  };
}

export function loadSkillCatalog(skillsRoot) {
  const entries = readdirSync(skillsRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .sort();
  const catalog = [];
  for (const directoryName of entries) {
    const directory = path.join(skillsRoot, directoryName);
    const skillFile = path.join(directory, "SKILL.md");
    if (!existsSync(skillFile)) continue;
    const parsed = parseFrontMatter(readFileSync(skillFile, "utf8"), skillFile);
    if (parsed.meta.name !== directoryName) {
      throw new Error(`SKILL.md 的 name "${parsed.meta.name}" 与目录名 "${directoryName}" 不一致`);
    }
    catalog.push({
      ...parsed.meta,
      source: "bundled",
      rank: SKILL_RANK,
      provider: PROVIDER_NAME,
      path: skillFile,
      locator: { index: catalog.length },
      resourceBase: { kind: "directory", path: directory },
      content: parsed.content,
    });
  }
  if (catalog.length === 0) throw new Error(`RP-Factory skill bundle 是空的：${skillsRoot}`);
  return catalog;
}

function toCandidate(record) {
  const { content, ...rest } = record;
  return rest;
}

export function createProvider(catalog) {
  return {
    name: PROVIDER_NAME,
    async list() {
      return catalog.map(toCandidate);
    },
    async get(candidate) {
      const index = candidate?.locator?.index;
      if (typeof index !== "number") return undefined;
      return catalog[index];
    },
  };
}

export function apply(ctx, config = {}) {
  const skillsRoot = config.skillsRoot ?? resolveSkillsRoot();
  const catalog = loadSkillCatalog(skillsRoot);
  ctx.skills.registerProvider(() => createProvider(catalog));
  ctx.logger?.info?.(`RP-Factory DSH: registered ${catalog.length} skill from ${skillsRoot}`);
}
