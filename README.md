# 电循智策 DianXun ZhiCe

新能源汽车动力电池全生命周期智能评估与绿色决策平台。

项目面向二手新能源汽车交易评估与退役动力电池流转，连接电池健康、剩余寿命、生命周期碳足迹与绿色决策。

## 核心模块

- Battery Health / SOH：电池健康状态评估。
- Remaining Useful Life / RUL：剩余使用寿命预测。
- Carbon Passport：生命周期碳核算与因子溯源。
- Green Decision：安全筛选与多指标去向决策。
- Assessment Report：统一评估结果和报告。

**当前完成范围：Overview 前端 Demo 与 BMS 质量检查入口。** 已实现双场景切换、数字护照、技术预览及示例评估交互。其余正式子页尚未实现。前端已连接后端评估及 BMS 校验 API，并提供手动录入和持久化中英文切换。全部场景数据、曲线、因子及建议均为演示内容，不代表真实检测或验证结果。详见 [BMS 质量入口说明](docs/bms-quality-fix.md)。

## 项目目录

```text
DianXunZhiCe/
├─ frontend/       # 当前 React + TypeScript + Vite Web Demo
│  ├─ src/         # 页面、组件、示例数据及前端计算函数
│  ├─ public/      # 电池图片等静态素材
│  ├─ scripts/     # 构建辅助脚本
│  ├─ tests/       # 模型计算与静态站点相关测试
│  ├─ docs/        # 现有前端截图和视觉验收证据
│  └─ package.json
├─ backend/        # V0.3 本地 API 与统一 assessment
├─ model/          # 公开电芯 SOH/RUL 模型与真实 TreeSHAP
├─ carbon/         # 独立生命周期碳核算与因子说明
├─ data/           # 公开处理后数据、合成样例及 V0.1/V0.2 版本索引
├─ docs/           # 项目协作、接口和比赛材料说明
├─ README.md
└─ .gitignore
```

现有前端算法仍在 `frontend/src/lib/`，示例场景仍在 `frontend/src/data/demoBattery.ts`。本次只整理工程，不将可运行逻辑强行拆成尚未实现的服务。

## 本地运行

安装 Node.js 22.18+ 与 npm，在仓库根目录执行：

```sh
cd frontend
npm install
npm run dev
```

打开终端输出的本地地址。Vite 默认端口为 5173；端口被占用时以终端实际输出为准。

```sh
# 以下命令在 frontend/ 内执行
npm run build
npm run test:models
npm run test:sites
```

构建包含 TypeScript 检查，静态页面输出到 `frontend/dist/client/`。`.openai/`、`worker/` 及构建辅助脚本保留，不会自动部署。使用 npm 时以 `package-lock.json` 为准；现有 pnpm 配置保留供已有使用者使用，同一次依赖修改不要混用两种包管理器。

## 团队协作

1. 每个任务先建立 Issue，写明范围、验收条件与负责模块。
2. 共享接口或数据字段变更先在 `docs/` 讨论，标明单位、来源、版本、缺失值与错误语义。
3. 从 `dev` 创建短期功能分支，避免多人同时直接改同一主分支。
4. 完成后提交 Pull Request 到 `dev`，说明变更、截图和验证结果，由至少一名组员评审。
5. `dev` 通过集成检查后再合并到 `main`，用于稳定演示版本。
6. 不提交账号密钥、个人数据、依赖目录和构建产物。模型与数据贡献要记录许可证、来源及演示/真实属性。

### Git 分支建议

- `main`：稳定、可展示版本。
- `dev`：团队集成分支。
- `feature/xxx`：单一功能，例如 `feature/battery-health`。

初始化远程仓库并推送 main 后，可以建立 dev：

```sh
git switch -c dev
git push -u origin dev
# 之后从最新 dev 开始工作
git switch dev
git pull --ff-only
git switch -c feature/battery-health
```

### 提交规范

```text
feat: 增加电池健康分析页面
fix: 修复场景切换后的寿命显示
docs: 补充评估接口字段说明
refactor: 抽离可复用护照组件
data: 增加带来源的示例数据集
model: 增加 RUL 基线验证
```

提交前执行与变更相关的检查，前端至少执行 `npm run build` 和 `npm run test:models`。

## 首次连接 GitHub

在 GitHub 网站新建名为 `DianXunZhiCe` 的**空仓库**，选择公开或私有，暂不勾选自动添加 README、.gitignore 或 LICENSE。复制该仓库真实 HTTPS 或 SSH 地址。

在本项目根目录中执行，先将下面的占位符替换为真实仓库地址：

```sh
git add .
git diff --cached --stat
git commit -m "chore: organize DianXunZhiCe collaboration repository"
git remote add origin <你的真实仓库URL>
git push -u origin main
```

`<你的真实仓库URL>` 只是占位符，不可直接执行。如 Git 提示缺少身份，先设置自己的 `user.name` 与 `user.email`。HTTPS 推送按 GitHub 提示完成认证，或使用已配置的 SSH。若之后已有 origin，先运行 `git remote -v` 检查，不要重复添加。

本次本地整理不创建 GitHub 仓库、不设置 origin、不提交或推送代码。未添加 LICENSE，待团队确定授权方式后再选择。

更多内容见 [前端说明](frontend/README.md)、[文档导航](docs/README.md) 与 [迁移记录](docs/repository-setup.md)。

## V0.3 后端原型接入

在仓库根目录使用 Python 3.12：

```powershell
py -3.12 scripts/start_backend.py
```

服务启动后，在另一终端执行 `.venv\Scripts\python.exe scripts/smoke_test.py`。前端统一调用 `POST /api/v1/assessment`，见 [API 契约](docs/API_CONTRACT.md) 和 [联调说明](docs/integration_guide.md)。

前端已连接后端评估、手动录入和 BMS 质量检查，支持中文/English 切换并保存选择。Vite 默认将同源 API 代理到 127.0.0.1:8013，生产需配置同源后端服务，或设置 VITE_API_BASE_URL 及后端 CORS。NASA 电芯输出、BMS 质量检查和示例电池包方案分别展示；尚未完成真实车辆验证。

联调说明见 [前端联调说明](docs/FRONTEND_INTEGRATION.md)，本轮修复见 [BMS 质量说明](docs/bms-quality-fix.md)。
