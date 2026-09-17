# 中英文界面 / Bilingual UI

右上角选择「中文」或「English」。首次默认中文，浏览器保存语言偏好；刷新后沿用。切换时不重置表单，不重新请求评估，不改变已有结果。

## 实现位置

- `frontend/src/i18n/catalog.ts`：导航、表单、按钮、错误和范围说明。
- `frontend/src/i18n/evidence.ts`：已知后端状态、原因和证据说明。
- `frontend/src/i18n/index.ts`：显示翻译、模板、偏好存储。
- `frontend/src/i18n/useLanguage.ts`：React 更新与文档语言。

使用本地词典，无外部翻译服务。数值、单位、模型和电池标识及 API 请求结构保持不变。品牌、输入快照等原始数据不翻译。未知后端说明保留原文；新增后端原因需同时补充词典。浏览器自身文件选择器和打印窗口遵循浏览器/系统语言。

NASA 公开电芯、容量型 SOH、RUL 证据不足、Demo / Prototype 碳和决策等真实性边界在两种语言中均保留。翻译不改变算法有效性或验证范围。

## 验证

2026-09-17 本地通过：TypeScript 检查、生产构建、i18n 测试、现有 integration 测试、4 项 Sites worker 测试和 model-check。

浏览器验证：中文和英文界面；英文刷新保持；填写容量 60 / 49.44 后切换不丢失；用户品牌 Health 保持原文；手动结果 SOH 82.40% 和请求编号在切换后保持；手动与 NASA 英文报告无遗漏中文说明。

运行（frontend 目录）：

```sh
npm run build
node --test tests/i18n.test.mjs tests/integration.test.mjs tests/sites-worker.test.mjs
npm run test:models
```

本次为本地功能分支 `feature/bilingual-interface`。尚未推送 GitHub 或合入 dev/main。
