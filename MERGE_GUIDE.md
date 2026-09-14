> 历史离线交接说明：本文件随 V0.3 模块导入；当前仓库集成状态请看 docs/v03-repository-integration.md。下文“未上传 GitHub”等表述描述离线交付时点。

# 电循智策 V0.3 可合并模块包

这是合并材料，不是第二套完整仓库。**不含 frontend/，不替换团队 README.md 或 .gitignore，不创建 models/。** 未上传 GitHub。

## 合并到团队 DianXunZhiCe

1. 在团队仓库新建工作分支，将本包 `backend/ model/ carbon/ data/ docs/ tests/ scripts/` 按同名目录逐文件合并；已有同名文件先比较差异，不直接全量覆盖。
2. 保留现有 frontend 所有文件、依赖、锁文件和页面。前端组员根据接口契约自行接入。本包不提供替代页面。
3. 把 `docs/gitignore.append.txt` 的规则追加到团队原 `.gitignore`；可以把本文件的启动摘要加入团队 README。根目录 README/.gitignore 不在本包中，避免覆盖。
4. 依赖独立放在 `backend/requirements.txt`。使用 Python 3.12，模型依赖版本锁定；首次安装需联网。无 npm 操作。

## 启动与测试（在 DianXunZhiCe 根目录）

Windows 一键启动：
```powershell
py -3.12 scripts/start_backend.py
```
macOS/Linux：
```sh
python3.12 scripts/start_backend.py
```
脚本创建 `.venv`、安装后端依赖并启动服务。以后重复运行会按依赖文件哈希跳过未变化的安装。Ctrl+C 停止。

已经安装依赖时直接运行：
```sh
python -m backend.app --port 8013 --allowed-origin http://localhost:5173
```
Windows 新终端执行：
```powershell
.venv\Scripts\python.exe scripts/smoke_test.py
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m backend.v03.verify_v03
```
macOS/Linux 把 `.venv\Scripts\python.exe` 换成 `.venv/bin/python`。

## 调用关系

前端只需向 `http://127.0.0.1:8013/api/v1/assessment` 发一次 JSON 请求，读取统一响应的 `data`。详见 [API 契约](docs/API_CONTRACT.md)、[联调说明](docs/integration_guide.md)。

`backend/routes/api.py` → `backend/services/assessment.py` → `model/inference.py`（SOH/RUL）、`model/explain_soh.py`（真实 TreeSHAP）、`carbon/calculator.py`（活动量×因子）、`backend/v03/decision.py`（原安全门槛与多目标评价）。

模型权重在 `model/*.joblib` 与 `model/rul_v02/*.joblib`。数据路径按项目根目录解析，不依赖个人电脑路径。旧 API `/health` 和 `/v0.3/*` 继续保留原成功响应。

## 数据与包的区别

完整模块包包含 V0.1/V0.2 的处理后数据及结果索引 `data/versions/manifest.json`；相同内容去重，索引保留历史版本、原路径、现路径和 SHA256。压缩时序只保留一份；不含原始 MAT 数据、下载缓存、真实车辆敏感数据或依赖安装目录。

轻量联调包保留同一 API、所有推理必需模型/样例与历史 CSV/JSON 索引，省去约 6MB 压缩实验时序、历史图形和非运行必需基线模型。需要历史复现材料时使用完整模块包。两包都不含前端。

## 尚未完成与真实性边界

- SOH/RUL 只开放本包四个 NASA 电芯的演示推理；任意真实车辆 BMS→SOH/RUL 的特征迁移尚未实现/验证。BMS 上传只做质量检查，不能宣称整车端到端预测已完成。
- RUL 需要至少 30 次历史实测容量，依赖工况；无校准置信区间，不能换算为天数或公里数。
- SHAP 是真实模型贡献，不能解释为物理因果。
- 碳因子有年份/地区/边界差异，来源和置信等级是声明，不等于核查。现有阶段为四组，原材料并入制造，运输与维护合并；尚未拆成六组独立核算。
- 安全阈值、权重、成本与方案数据均为 **Demo / Prototype Parameters**；真实数据标记不会自动获得放行建议。不得替代正式检测或安全认证。
- 前端实际对接、实车验证、企业试用、鉴权/持久化/公网部署均未完成。本服务默认只监听本机。

本次仅整理交付模块，合并和 GitHub 同步由团队后续执行。
