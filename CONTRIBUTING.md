# 贡献指南

感谢参与 Bellows。这个项目目前处于 **v0.0.1 BETA**，边界比功能更重要：请先阅读 [README 的能力边界表](README.md#明确未完成--未验证诚实边界)，不要为「未完成清单」写看起来可用但实际空转的实现。

## 开发环境

- Python ≥ 3.12（CI 使用 3.12）
- Node.js ≥ 22.18 或 ≥ 24.12
- 无需 Docker；如需容器方式见 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

```bash
# 前端依赖
cd apps/web && npm ci

# Python 依赖（含测试与 lint）
cd apps/core && python3 -m pip install -r requirements-dev.txt

# 启动（首次会自动构建前端）
bash scripts/run.sh
```

开发模式（内核热重载 + Vite）：

```bash
cd apps/core && python3 -m bellows_core --data-dir ../../data --port 7801
cd apps/web && npm run dev
```

## 提交前检查

```bash
bash scripts/check.sh     # 等价于下方三条
cd apps/core && ruff check . && ruff format --check .
cd apps/web && npm run type-check && npm run build
cd apps/core && pytest
```

修复 Python 格式化问题用 `ruff format .`；不要手工调整行宽。

## 代码约定

- Python：3.12+ 语法，类型注解尽量完整，模块放在 `apps/core/bellows_core/`；数据库只经由 `db.py`。
- 前端：Vue 3 `<script setup lang="ts">` + Pinia + Vue Router；样式使用 Tailwind v4 与 `fuxsto-design` token，不要引入新的 UI 框架。
- API 变更需同步 [docs/API.md](docs/API.md) 与前端 `src/api.ts`、`src/types.ts`。
- 新增能力必须同步更新 README 的「已实现 / 可用」表；未完成项继续留在边界表里。
- 提交信息使用 Conventional Commits（`feat:`、`fix:`、`docs:`、`chore:` 等），中文正文即可。
- 不要提交 `node_modules/`、`apps/web/dist/`、`data/`、任何真实 Token 或协议端凭据。

## 分支与 PR

1. 从 `main` 创建分支：`feat/xxx`、`fix/xxx`、`docs/xxx`。
2. 一个 PR 只解决一件事，附上复现步骤或截图。
3. PR 模板中的检查项需要如实勾选；CI 必须通过。
4. 维护者合并后由作者补充 `CHANGELOG.md`（或由维护者代为整理）。

## 报告问题

- 缺陷与功能请求：使用仓库的 Issue 模板。
- 安全漏洞：**不要公开开 Issue**，按 [SECURITY.md](SECURITY.md) 私下报告。
- 使用问题：先查 [docs/FAQ.md](docs/FAQ.md)。

## 许可

贡献即表示同意以 [AGPL-3.0](LICENSE) 授权你的改动。请确保你有权提交相关代码。
