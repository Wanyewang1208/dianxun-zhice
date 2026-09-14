# NASA FY08Q4 数据说明与事实边界

## 来源与取得

来自[NASA PCoE官方资源页](https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/)直接列出的[电池数据ZIP](https://phm-datasets.s3.amazonaws.com/NASA/5.+Battery+Data+Set.zip)。下载成功后从内部 `1. BatteryAgingARC-FY08Q4.zip` 提取 B0005、B0006、B0007、B0018 原始MAT和README。`data/raw/provenance.json` 记录原始下载链接、时间、压缩包和各原始文件SHA256。无需Kaggle账户或非官方镜像。NASA目录的另一[数据说明页](https://data.nasa.gov/dataset/li-ion-battery-aging-datasets)描述了标签及用途。

引用：B. Saha and K. Goebel (2007), “Battery Data Set”, NASA Prognostics Data Repository, NASA Ames Research Center, Moffett Field, CA。原始材料保持其来源权利；本包不擅自将NASA数据标为MIT许可。

## 实验条件

四个18650锂离子电芯在室温环境下进行加速循环老化。细分化学体系未在本次原始说明中确认，不推断为LFP或NMC。额定容量2 Ah；SOH定义为放电Capacity / 2 Ah ×100%，不是除以首循环容量。

原始README给出的充电为1.5 A恒流至4.2 V，再恒压至20 mA；放电为约2 A。B0005/B0006/B0007/B0018截止电压依次为2.7/2.5/2.2/2.5 V。README同时将Capacity字段描述为放电至2.7 V的容量；本版保留其原始容量值，不对这一描述与不同截止电压的关系进行未经证实的重算或统一修正。这是跨电芯比较的重要局限，应在进一步研究中核对容量积分定义。

EOL阈值按原始README采用1.4 Ah，即额定容量衰减30%，SOH=70%。这不是普遍适用于实车的退役标准。代码把首次观测容量<=1.4 Ah定义为不可逆的首达事件；后续容量回升不撤销事件。未跨阈值电芯标记右删失，不能把记录结束当作EOL。

## 结构化输出

`cycles.csv` 一行是一颗电芯的一次放电操作。`cycle` 是该电芯放电操作从1起的顺序号；`operation_index` 是原MAT中包含充电和阻抗的总操作序号。两者均不是等效满循环数。时间戳保留源起始时间，原始资料未给时区，不强行标为UTC。

`discharge_timeseries.csv.gz` 为完整放电信号长表，按 battery_id、cycle、time_s 唯一，包含起始时间、电压V、电流A、温度℃。可用pandas读取或常规解压软件解压。充电/阻抗仍在原始MAT中，本版没有提取为模型特征。原始实际放电字段名是 Current_load/Voltage_load；本版使用实测Current_measured/Voltage_measured，避免README字段命名差异造成误读。

清洗只检查有限数值、负相对时间、重复时间和排序；对时间重复保留第一条并记录数量；不对容量衰退曲线作全序列平滑，不人为删除容量回升点，不补造数据。输入窗口覆盖不足或时间间隙>60秒时排除该循环并记录。容量检查范围为0到3 Ah，是本数据技术质量筛查规则，不能泛化到电池包。实际清洗结果见 data_quality.json 和 cleaning_issues.csv。

## SOH预测时间点与泄漏防护

预测时间是某次实验放电开始后的第600秒。只使用原始 Time<=600 的电压、电流和温度，在线性插值网格60至600秒上计算特征。600秒处如无精确样本，仅保持600秒前最后一次观测，允许最多30秒；不会从600秒之后取点插值。均值和斜率在固定网格上计算。

模型包含放电序号、四个固定时点电压、窗口电压均值/斜率、电流均值/标准差、温度均值/升幅、环境温度。包括cycle会利用实验老化进程，因此另外报告cycle-only线性基准。容量、SOH、完整放电时长、样本总数、全程Ah积分、电池ID和未来循环均不进入特征。

监督标签来自本次放电结束后得到的容量，仅供训练/评估；预测可用信息截止600秒。真实应用还需确定统一可重复测试程序，不能把任意驾驶片段直接套入这个固定放电窗口。

训练B0005/B0006/B0007，完全留出B0018（按ID）。预处理仅在训练电芯拟合，固定参数、固定随机种子，不根据测试分数调参。另行进行四折留一电芯验证，参数不变，仅用于敏感性分析，不声称第二个独立外部验证。四个电芯样本规模很小，循环行之间高度相关；不能把636行描述为636颗电池。

## 不具备的验证

不是中国真实整车BMS数据；没有车厂合作、商业试点、专利或产品认证成果。未验证不同化学体系、车用大电池包、动态工况、温度泛化或真实交易效果。当前碳模块独立于电芯模型，其假设60kWh电池包不是NASA实验对象。尚未形成可信的SOH/RUL到退役路径和碳收益联合决策模型。
