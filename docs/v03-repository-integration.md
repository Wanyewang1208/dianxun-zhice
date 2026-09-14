# V0.3 仓库集成

基于团队 main 的 eb190cf，导入已交付模块。frontend 保持字节不变；共享目录的 README 保留原协作说明并补充 V0.3 状态。根 README 更新后端启动入口；.gitignore 仅追加本地原始数据/上传文件规则。

新增 backend API、model 模型与推理、carbon 核算、data 公开数据及 V0.1/V0.2 历史索引、docs 接口文档、tests、scripts。未上传 ZIP、依赖目录、缓存、真实车辆数据或密钥。

本次是模块集成；前端尚未改为调用 assessment，待组员按照 docs/integration_guide.md 接入。现有 V0.3 测试记录为离线交付快照，当前集成验证见 repository_test_results.txt。

团队说明建议 feature → dev → main；导入通过功能分支评审，不自动合并主分支。
