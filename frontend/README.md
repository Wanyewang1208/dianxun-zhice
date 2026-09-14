# 电循智策 · Overview Web Demo

本轮只实现 Overview 首页。使用已选方案 1 的主视觉，将方案 3 的模型、预测和溯源表达整合为下半部技术预览。没有开发其余五个正式子页面。

## 本地运行

需要 Node.js 22.18+（或更新 LTS）与 npm。

```sh
npm install
npm run dev
```

```sh
npm run build
npm run test:models
```

此目录是协作仓库中的 `frontend/`。从仓库根目录先执行 `cd frontend`，再运行以上命令。`npm run dev` 默认使用 Vite 默认端口，实际地址以终端输出为准。生产输出在 `frontend/dist/client`。本项目没有发布到互联网。团队协作说明见 [根 README](../README.md)。

## 本轮实现

- OverviewHero：三行品牌 Hero、场景选择、开始评估按钮。
- ScenarioSwitch：默认二手车场景，切换后护照、四项指标、Insight、推荐、技术预览同步变化。
- BatteryPassport：电池 ID、LFP、额定容量、里程、循环次数及电池包概念图。
- IntelligenceMetric：SOH、RUL、生命周期碳足迹、Risk，数字过渡动画。
- LifecycleFlow：Vehicle → Battery Data → Health → Remaining Life → Carbon → Green Decision。
- DianXunIntelligence：可折叠的三条双语 Insight、同步推荐及解释入口。
- TechnologyPreview：BatteryHealthPreview / RULPreview / CarbonPreview，容量公式、线性预测曲线、五阶段碳占比。
- InnovationStory：Detection → Prediction → Evaluation → Decision，解释产品创新。
- Sidebar、CountUp、DegradationChart、ModuleDialog 等共享组件。

## 交互

- 场景切换为真实前端状态，动画约 380ms，支持减少动态效果偏好。
- 开始评估：900ms 模拟分析，五阶段状态，完成后显示当前场景结果；可关闭取消。
- Insight 折叠与展开；推荐和各模块入口可打开说明弹窗。
- 正式子页尚未开发。侧栏及技术卡片的箭头打开明确标注范围的说明弹窗，不伪装成已完成的子页。
- 模态框使用原生 dialog，支持 Escape、焦点约束、关闭及返回技术预览。
- 图表自适应，历史实线、预测虚线、参考线、圆角 Tooltip；图表独立加载。
- 按钮具备 hover / active / focus / loading 状态，卡片轻微上移，进入动画 400ms。

## 数据与模型口径

唯一场景入口：`src/data/demoBattery.ts`。

| 数据 | 二手车示例 | 退役电池示例 |
| --- | --- | --- |
| Battery ID | DXZC-A02-2026 | DXZC-B07-2026 |
| Current / Initial capacity | 49.44 / 60 kWh | 41.22 / 60 kWh |
| Calculated SOH | 82.4% | 68.7% |
| Current cycle / Assumed EOL | 1,126 / 2,046 | 2,310 / 2,620 |
| RUL | 920 cycles | 310 cycles |
| EOL reference | 80% 车用参考线 | 60% 梯次参考线 |
| Lifecycle carbon | 8.72 tCO₂e | 9.72 tCO₂e |
| Risk | LOW | MEDIUM |
| Suggested path | Continue Vehicle Use | Second-Life Utilization |

退役场景中未由原始简报给出的里程、循环数、容量、EOL、碳排放等为本轮补充的**演示假设**，不是实测值。其中碳使用阶段从 2.12 t 增至 3.12 t，其他阶段保持相同示例假设。

- `calculateSOH(current, initial)`：实际计算 current / initial × 100。
- `getBatteryModel()` / `calculateBaselineRUL()`：从当前观测点到假定 EOL 的**局部线性基线**；通过 a + bn 求交点。参数为演示预设，不宣称从 BMS 拟合或经真实数据验证。
- 历史曲线是容量退化的合成示意，不是真实检测历史；预测线使用上述局部基线。
- `calculateEmission(activity, factor)` 与 `calculateLifecycleCarbon()`：先算 kgCO₂e，再合计换算 tCO₂e。制造 5.84、运输 0.31、使用 2.12、维护 0.19、退役 0.26，相加为 8.72。
- 原材料计入制造阶段，退役阶段为情景估计；所有因子属于 Demo Dataset。0.42 kgCO₂e/kWh 是青海 2026 的**示例因子标签**，不是已核验的地区电网因子。
- 当前不执行安全准入算法，也未实现动态多指标权重决策；退役建议明确以通过安全筛选为前提。
- 没有接入任何外部 AI 服务；DianXun Intelligence 为示例规则和场景结果展示。

## 验证

- `npm run build`：通过，包含 TypeScript 严格类型检查。
- `npm run test:models`：通过，验证容量比值、非法参数、两个基线终点、RUL、曲线衔接和碳排放计算。
- 浏览器：Codex in-app browser，检查 1280 / 1440 / 1920 宽度，无页面水平溢出。
- 场景切换、评估完成、折叠区、说明弹窗、侧栏五个入口与返回：通过。
- 浏览器 console error / warning：本次检查返回空列表。
- 视觉检查见 `design-qa.md`；截图在 `docs/`。

## 尚未实现

Battery Health、Remaining Life、Carbon Passport、Green Decision、Assessment Report 正式页面；真实 BMS 解析、真实检测数据、真实碳因子库、训练模型、Safety Gate、可调决策权重、报告导出、后端、登录、账户与数据库。本轮按要求在 Overview 完成后停止。

## 素材

`public/assets/battery-pack.png` 为按方案 1 参考生成的电池包概念素材，使用内置 Image Gen；非真实产品照片。生成目标：石墨黑 EV 电池包、斜向俯视、克制冷色边缘光、深色背景、无文字和 UI。图标为 Lucide React；未使用自制 SVG 图标或外部 stock 图片。字体采用系统 Segoe UI / Microsoft YaHei 等回退，确保本地无需网络字体。
