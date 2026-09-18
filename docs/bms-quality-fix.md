# BMS 质量入口修复（2026-09-17）

基线：dev / 8de5c08。新增入口位于 Overview 底部、页脚之前。

## 行为

- 上传 UTF-8 时序 CSV 与元数据 CSV，调用 `/api/v1/bms/validate`；结果显示接收/拒绝行数、错误、警告、原始行号，支持下载完整 JSON 质量报告。
- 内置样例来自 `data/sample/bms/synthetic_fixtures`，明确标为合成数据。
- 额外字段不会再静默通过：逐列返回 `unvalidated_column` 警告和未校验字段列表。保留这些列不意味着它们已用于健康、安全判断。
- 重复 CSV 表头直接拒绝；可选里程转换为数值。
- `schema_ready` 保留原有核心字段合格语义。新增 `schema_ready_scope`、`unvalidated_telemetry_columns`、`unvalidated_metadata_columns`、`all_supplied_fields_validated`。后者仅在有接收数据且无错误/警告时为 true，仍然只是约定字段的数据检查，不是安全认证。
- 文件变更清空上次报告；失败显示原因，不返回模拟成功。检查 JSON 编码后的实际请求大小，超时 60 秒。保留 2 MiB / 每表 10,000 行限制。

## 本地连接

前端使用同源相对路径 `/api/v1/bms/validate`。Vite 开发服务器将 `/api/v1` 代理至 `http://127.0.0.1:8013`；按项目原有方式启动 Python 后端和 Vite 即可。

生产部署必须由托管方配置同源 `/api/v1` 后端路由；纯静态站点不具备 Python 服务。此次没有修改或发布线上站点，也未扩大服务器监听范围。

## 数据准备

下载页面中的两个 CSV 样例核对字段。真实数据需用可追溯 ID、真实额定容量、化学体系、单位和电流方向替换样例元数据，`data_origin` 应声明真实来源。不要将合成参数移植成实车事实。

长安原始列名仍需适配，当前不推断单位、状态枚举、时区或身份。单体/探针数组和故障事件仍是未校验扩展字段。上方示例 SOH/RUL、风险和退役建议不使用上传文件，页面明确说明这一点。

## 验证

在仓库根目录运行 `python -m unittest discover -s tests -v`；在 frontend 运行 `npm run build`、`npm run test:models`、`npm run test:sites`、`npm run test:bms`。

浏览器完成合成样例校验及异常 CSV 实际文件选择上传：正常 12/12 接收；异常 13 行中 7 行接收、6 行拒绝、6 个错误和 3 个警告。
