# 工程整理记录 · 2026-09-14

- 原工程：任务目录下 `outputs/dianxun-demo/`。
- 新仓库：`outputs/DianXunZhiCe/`。
- 原工程整体迁移为 `frontend/`，包括源码、静态素材、构建脚本、测试、配置、锁文件、前端文档及截图。
- 同时迁移本地 `node_modules/` 和 `dist/` 以保留开发环境；它们由根 `.gitignore` 排除，不上传 Git。
- 迁移前后对 49 个源码、配置和文档文件计算 SHA-256，全部一致。随后仅更新前端 README 中关于目录和预览的说明。
- 修复 303 个本地依赖 junction 的绝对目标，避免依赖仍指向旧目录。源码、Vite 配置与构建脚本采用工程内相对路径，无需改动。
- 新增 backend、model、carbon、data、docs 的 README 和根目录 README、.gitignore。
- 未移动任务级 `work/` 和旧交付 ZIP；它们不属于新仓库，旧 ZIP 是迁移前快照。
- 初始化前，任务目录及原前端均不是 Git 仓库；没有删除或重写 Git 历史。
- 未创建 LICENSE，未添加 GitHub 远程地址，未创建提交或执行 push。

## 迁移后验证

- 在 `frontend/` 执行 `npm run build`：通过，TypeScript 与 Vite 构建正常。
- `npm run test:models`：通过。
- `npm run test:sites`：4 项测试全部通过。
- 从新目录启动 Vite，本地页面正常显示四项评估指标。
- Git 初始化完成，分支为 main，尚无提交、暂存文件或远程仓库。
- `git status --short` 显示新仓库文件未跟踪；node_modules、dist 等已正确忽略。
