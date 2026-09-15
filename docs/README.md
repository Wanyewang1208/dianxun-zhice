# docs · 项目文档与比赛材料

## 职责
维护小组共享的项目说明、架构、接口约定、数据字典和比赛材料导航。

## 推荐文件
可后续添加 `architecture.md`、`api.md`、`data-dictionary.md`、模型说明、核算边界、会议决议和比赛材料索引。接口尚未实现时明确标记“拟议”，不要把计划写成已上线功能。

## 不应该放
密钥、私人聊天、未授权材料、个人敏感信息、node_modules、虚拟环境或构建输出。大体积演示视频建议外部存储，文档保留链接与版本。

## 对接约定
涉及多个模块的协议以本目录为共同依据，通过 Pull Request 评审后同步前端、后端、模型和碳核算负责人。比赛材料须区分已实现、原型验证和未来规划，所有示例注明“情景模拟”。

## 当前文档

- [项目入口与协作说明](../README.md)
- [前端功能与数据口径](../frontend/README.md)
- [前端视觉验收](../frontend/design-qa.md)
- [前端截图](../frontend/docs/)
- [工程迁移记录](repository-setup.md)

原有前端文档与截图保留在 `frontend/` 内，避免破坏现有相对链接。


---

## V0.3 模块接入

新增阶段：[手动录入与剩余价值后端契约](MANUAL_ASSESSMENT.md)，对应统一assessment的manual模式；frontend未修改。

# 交接文档入口

- [合并说明](../MERGE_GUIDE.md)：目录、依赖、启动、测试、未完成项。
- [API 契约](API_CONTRACT.md)：字段、单位、错误码、兼容映射和证据边界。
- [前端联调说明](integration_guide.md)：Base URL、fetch、CORS、CSV 上传。
- [结构与复用映射](ARCHITECTURE.md)：V0.3 代码迁移位置。
- [实际完整请求](examples/assessment.request.json) / [实际完整响应](examples/assessment.response.json)。
- [测试摘要](TEST_RESULTS.md)：本次测试及解压验证记录。
- [模型说明](../model/README.md) / [碳模块](../carbon/README.md) / [历史数据](../data/README.md)。

本包不含 frontend，不覆盖团队根 README 或 .gitignore。所有预测/决策均为原型范围，尚未完成真实车辆验证。
