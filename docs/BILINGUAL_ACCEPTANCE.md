# 中英文功能验收（2026-09-17）

范围：现有界面本地化验收与修正，没有增加业务功能。基于本地 `feature/bilingual-interface`，不代表远程 dev 最新状态。

## 场景与证据

| 场景 | 结果 |
|---|---|
| 无语言偏好的新站点来源首次访问 | 默认中文；单元测试同时覆盖空值、非法偏好与存储不可用 |
| English → 刷新 → 关闭标签页 → 重新打开 | English 仍为选中状态 |
| 本地 Demo 五个模块 | 健康、寿命、碳、决策、报告英文内容无中文文案遗漏 |
| NASA 样例 | BMS 校验、统一评估、SHAP、碳、四路径和报告可用；英文报告无中文说明遗漏 |
| 手动录入 | 60 / 49.44 得到 82.40%；缺少 RUL/SHAP/碳证据时仍标记不可用 |
| Manual Demo | 原型寿命与剩余价值有明确 Demo 边界；五个模块英文无中文说明遗漏 |
| 额定容量 0 | 中文与英文错误提示随选择更新 |
| 不良合成 BMS CSV | 7 行通过、6 行拒绝、3 条警告；时间、范围、极值、重复与间隔错误说明均支持切换 |
| 输入和结果不丢失 | 品牌原文 Health、容量 60 / 49.44、SOH 82.40% 和请求编号切换后不变 |
| 公式和单位 | SOH、碳公式原文保持；数字、kWh、CNY、kgCO₂e、tCO₂e、专业缩写不变 |
| 窄屏 | 390px 内嵌真实浏览上下文检查英文表单与手动/NASA报告，另复验中文 NASA 报告；弹窗宽度 341px，scrollWidth 341px；修复后 SHAP 子元素无横向溢出 |
| 桌面布局 | 现有石墨黑/薄荷绿布局保留，语言控件可见；无页面横向溢出 |

静态检查覆盖 src 内中文字符串；唯一刻意保留的中文是语言切换自身的「中文」和对应中文 aria 标签。技术字段、模型特征、调用方原文不做机器翻译。首次访问通过同一构建的 localhost 新来源核对，未清除用户已有站点数据。窄屏临时测试页不纳入版本库。

## 本轮修正

- 中文界面保留 Demo 标记和碳公式，不将模型标记隐藏在中文概述中。
- 上传文件名与 CSV 错误字段 ID 保持原文；布尔值以是/否、Yes/No 展示。
- 非 UTF-8 文件使用可翻译的统一错误文案。
- 补齐 BMS 质量错误、时间间隔、元数据单位说明；保留电池 ID 与单位。
- 补齐 SHAP 增减方向说明，并修复窄屏长英文溢出。
- 补充偏好、单位/公式、Demo 标记、未知消息保留及动态错误模板测试。

## 文件范围

- 新增 `frontend/src/i18n/{index,catalog,evidence,bms,useLanguage}.ts`。
- 新增 `frontend/tests/i18n.test.mjs` 和 `docs/BILINGUAL_UI.md`、本验收记录。
- 更新 `frontend/src/App.tsx`、`styles.css`、`pages/Overview.tsx`。
- 更新 `components/AssessmentControls.tsx`、`LiveResults.tsx`、`ManualAssessment.tsx`、`ModuleDialog.tsx`、`charts/DegradationChart.tsx`、`layout/Sidebar.tsx` 与 8 个现有 overview 组件。
- `frontend/AGENTS.md` 记录已批准的中英文范围。
- 后端、模型、碳算法、数据、依赖文件和锁文件未修改。

## 测试

在 frontend 目录：

```sh
npm run build
node --test tests/i18n.test.mjs tests/integration.test.mjs tests/sites-worker.test.mjs
npm run test:models
```

通过：TypeScript `tsc --noEmit`、Vite 生产构建、i18n 回归、9 项 integration 检查及 manual/manual_demo 两种变体、4 项 Sites worker 测试、model-check。

仓库根目录：

```sh
python -m unittest discover -s tests -v
python scripts/smoke_test.py --base-url http://127.0.0.1:8023
python scripts/smoke_manual.py --base-url http://127.0.0.1:8023
```

99 项后端测试通过。NASA 和手动 API 冒烟通过；NASA SOH 77.39439392089844%、RUL 36.285552574482374 参考循环、碳总量 5560.654 kgCO₂e，与公开电芯/模拟场景边界分别保留。测试使用本机已有依赖和 Node/npm 运行时，不改依赖版本。

## 已知边界

- 浏览器原生文件选择器、打印窗口跟随浏览器/系统语言；不是应用文案。
- 未知未来后端说明保留原文，需要同步扩展词典；未承诺任意输入的通用自动翻译。
- 语言切换保留输入和结果；刷新仍按原项目行为重置评估。语言偏好独立保留。本轮不增加历史记录功能。
- 关闭重开测试针对标签页；未关闭用户整个浏览器。未做真实手机设备和多浏览器矩阵测试。
- 已验收页面报告内容；未新增或验证独立 PDF 引擎，导出仍调用浏览器打印。
- 未推送、未合并远程分支、未部署。公开电芯验证不等于实车验证。
