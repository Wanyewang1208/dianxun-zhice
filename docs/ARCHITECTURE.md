# 结构与复用记录

本包只交付七个可合并目录和 MERGE_GUIDE，不创建团队仓库、frontend 或 Git 远程。

```text
existing frontend
   -> backend.app (HTTP / CORS / envelope / errors)
   -> backend.routes.api -> backend.services.assessment
        -> model.inference / explain_soh
        -> carbon.calculator
        -> backend.v03.bms_validate / decision
        -> data (public cell samples + separately labelled demo scenarios)
```

复用映射：

| V0.3 位置 | 当前位置 | 改动 |
|---|---|---|
| src/core.py、rul.py、rul_v02.py、train_soh.py、explain_soh.py | model/ 同名文件 | 仅路径迁移，新增 inference 适配，不重训 |
| models/ | model/ | 原 joblib 字节保持一致 |
| src/carbon.py | carbon/calculator.py | 核心算术不变，CLI 默认因子路径适配 |
| src/bms_validate.py、decision.py | backend/v03/ 同名文件 | 原验证/安全/多指标算法保留，资源路径适配 |
| src/integration.py、api_server.py | backend/v03/ | 原成功契约兼容 |
| src/prepare_data.py、download_data.py | backend/v03/ | 原数据处理/下载代码保留，API 不自动下载 |
| tests/ | tests/ | 53 项原测试只适配 import/path |
| bms/、decision/、results/、integration/ | data/sample/bms、data/demo/decision、data/demo/results、docs/v03_integration | 按统一项目职责归类 |

新增：backend/app.py、config.py、routes/api.py、schemas/requests.py、services/assessment.py；model/inference.py；tests/test_api_v1.py；scripts/start_backend.py、smoke_test.py；docs/API_CONTRACT.md、integration_guide.md、examples、schema、版本与因子 metadata、MERGE_GUIDE。

backend/v03 中 model/carbon 同名文件只是兼容导入，算法只维护一处。目录变动没有引入另一套 XGBoost、SHAP 或多目标决策实现。

无数据持久化、无后台队列、无公网发布。当前一体化接口整合独立证据域，不声称任意 BMS 上传后已能生成可信整车 SOH/RUL。
