"""Generate an offline Chinese report from exported result tables."""
import json
from pathlib import Path
import pandas as pd

def table(df):
    return '<div class="table">'+df.to_html(index=False,border=0,float_format=lambda x:f'{x:,.3f}',na_rep='未观测/不适用',escape=True)+'</div>'

def make(root):
    quality=json.loads((root/'data/processed/data_quality.json').read_text(encoding='utf-8'))
    soh=pd.read_csv(root/'data/demo/results/soh/holdout_metrics.csv')
    lobo=pd.read_csv(root/'data/demo/results/soh/lobo_macro_summary.csv')
    battery=pd.read_csv(root/'data/processed/battery_summary.csv')
    rul=pd.read_csv(root/'data/demo/results/rul/rul_metrics.csv')
    carbon=json.loads((root/'data/demo/results/carbon/carbon_summary.json').read_text(encoding='utf-8'))
    checks=json.loads((root/'data/demo/results/verification.json').read_text(encoding='utf-8'))
    bms=pd.read_csv(root/'data/sample/bms/电循智策_BMS数据需求清单.csv')
    names={'linear_regression':'线性回归','random_forest':'随机森林','xgboost':'XGBoost','train_mean':'训练均值对照','cycle_only_linear':'仅循环序号线性对照'}
    hold=soh[['model','n','MAE_pp','RMSE_pp','R2']].copy()
    hold['model']=hold.model.map(names)
    hold.columns=['模型','测试循环数','MAE / 百分点','RMSE / 百分点','R²']
    lm=lobo[['model','MAE_pp_mean','MAE_pp_std','RMSE_pp_mean','R2_mean']].copy()
    lm['model']=lm.model.map(names)
    lm.columns=['模型','平均MAE / 百分点','电芯间MAE标准差','平均RMSE / 百分点','平均R²']
    rb=rul[['battery_id','evaluated_prefixes','MAE_cycles','RMSE_cycles','R2','right_censored']].copy()
    rb.columns=['电芯','评估时间点数','MAE / 循环','RMSE / 循环','R²','右删失']
    bs=battery[['battery_id','discharge_cycles','capacity_first_ah','capacity_last_ah','first_eol_cycle','right_censored']].copy()
    bs.columns=['电芯ID','循环数','首测容量Ah','末测容量Ah','首次EOL循环','右删失']
    contents=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>电循智策 · 技术验证 V0.1</title><style>
:root{{color-scheme:light}}*{{box-sizing:border-box}}body{{margin:0;background:#f3f5f5;color:#162b32;font:16px/1.8 "Microsoft YaHei",system-ui,sans-serif}}
main{{max-width:1120px;margin:auto;padding:48px 28px}}header{{border-top:5px solid #087f8c;padding:28px 0}}.eyebrow{{color:#087f8c;letter-spacing:2px;font-size:13px}}h1{{font-size:38px;line-height:1.3;margin:12px 0}}h2{{font-size:25px;margin:0 0 18px}}h3{{font-size:18px}}
.muted{{color:#526970}}.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:24px 0}}.card,section{{background:white;border:1px solid #dce4e5;border-radius:12px;padding:24px}}.value{{font-size:30px;font-weight:700;color:#087f8c}}section{{margin:24px 0}}.callout{{background:#fff5e5;border-left:4px solid #d49128;padding:14px 18px;margin:18px 0}}.table{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;font-size:14px}}th{{background:#eef4f4;text-align:left}}th,td{{padding:10px 12px;border-bottom:1px solid #e1e8e9;white-space:nowrap}}img{{max-width:100%;height:auto;border:1px solid #e5eaea;border-radius:6px}}a{{color:#006e7c}}code{{background:#eff3f4;padding:2px 5px;border-radius:3px}}footer{{color:#526970;font-size:13px}}@media(max-width:650px){{.cards{{grid-template-columns:1fr}}h1{{font-size:29px}}main{{padding:24px 14px}}section{{padding:18px}}}}@media print{{body{{background:white}}section{{break-inside:avoid}}main{{padding:0}}}}
</style><main><header><div class="eyebrow">电循智策 / PUBLIC CELL VALIDATION / V0.1</div><h1>技术验证已运行，能力边界清晰</h1><p class="muted">NASA公开实验电芯 · 独立电芯SOH验证 · RUL方法基线 · 碳活动数据接口</p><p>本报告来自随包保存的原始预测及指标表，不使用虚构车企数据。原始数据、程序、模型和结果可在同一目录复现。</p></header>
<div class="cards"><div class="card"><div class="value">4颗电芯</div><div>训练3颗 · 完整留出B0018</div></div><div class="card"><div class="value">{quality['cycle_rows']:,}次循环</div><div>{quality['timeseries_rows']:,}条放电信号记录</div></div><div class="card"><div class="value">{checks['checks_passed']}项复核</div><div>源文件哈希、分组隔离与指标复算等</div></div></div>
<section><h2>01 / 数据与退化轨迹</h2><p>来源为<a href="https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/">NASA PCoE官方列出的下载</a>。容量目标保留原始测量值，SOH = Capacity / 2 Ah × 100%。{quality['excluded_cycles']}个循环因质量规则排除；循环不是独立电池样本。</p>{table(bs)}<p><img src="data/demo/results/figures/degradation_curves.png" alt="四颗NASA电芯真实容量退化轨迹"></p><p class="muted">不同电芯放电截止电压不同。B0007最低容量约1.400455 Ah，尚未跨过1.4 Ah；不能将其四舍五入后当作EOL。</p></section>
<section><h2>02 / SOH：按电芯隔离的测试</h2><p>B0005、B0006、B0007训练，共504行；B0018测试，共132行。使用放电前600秒的电压、电流、温度和循环序号，排除容量、SOH标签、全程时长和未来数据。预处理仅在训练集拟合，超参数固定。</p>{table(hold)}<p><img src="data/demo/results/figures/soh_true_vs_predicted.png" alt="B0018真实SOH与三种模型预测曲线"></p><p><img src="data/demo/results/figures/soh_parity.png" alt="真实值预测值散点图"></p><h3>四折留一电芯敏感性分析</h3>{table(lm)}<p><img src="data/demo/results/figures/lobo_mae.png" alt="每次留出一颗电芯的MAE比较"></p><div class="callout">XGBoost在B0018的MAE最低；随机森林的四电芯平均MAE稍低。线性回归在B0007的MAE约14.13个百分点，跨电芯稳定性较差。只有4颗电芯，未做实车和独立外部数据验证；不能推广成产品精度承诺。</div></section>
<section><h2>03 / RUL：计算已跑通，预测仍不可靠</h2><p>阈值来自原始NASA README：2 Ah衰减30%至1.4 Ah。每个时点只取此前最近30次实测容量拟合直线并外推。未跨阈值电芯保留右删失，不计算虚假的真实RUL。依赖实测容量，并非BMS端到端预测。</p>{table(rb)}<p><img src="data/demo/results/figures/rul_baseline.png" alt="RUL趋势外推及真实RUL对比"></p><div class="callout">B0005早期容量变化小，线性外推出现数千循环预测，MAE约161.42循环。B0018也有明显高估。保留原始误差，不事后裁剪改善分数；暂不用于寿命承诺。真实EOL仅用于离线评估。</div></section>
<section><h2>04 / 生命周期碳计算器</h2><p>活动量×排放因子，覆盖制造、使用、维护运输和退役处理。可编辑 <a href="carbon/carbon_factors.csv">carbon_factors.csv</a> 和 <a href="carbon/example_activities.csv">示例活动表</a> 后重算。</p><p>假设60 kWh、400 kg电池包；使用阶段仅计输入30000与输出27000 kWh的差额3000 kWh损耗。制造、运输、退役因子和所有活动量均为演示参数。电力采用<a href="https://www.mee.gov.cn/ywdt/zbft/202510/t20251024_1130763.shtml">官方2024年度0.5777 kgCO2e/kWh</a>。</p><p><img src="data/demo/results/figures/carbon_example.png" alt="四个生命周期阶段的演示碳排放"></p><div class="callout">演示合计：{carbon['total_kgCO2e']:,.3f} kgCO2e。不是NASA电芯的碳足迹或项目实测碳足迹。未实施完整LCA数据库、第三方核查或回收信用抵扣；须按真实边界替换数据和因子。</div></section>
<section><h2>05 / BMS清单与复现入口</h2><p><a href="data/sample/bms/电循智策_BMS数据需求清单.csv">下载{len(bms)}项BMS数据需求清单</a>：必须、强烈建议、可选三级，含单位、频率建议、质量规则和NASA是否具备。六张空白接入表位于bms目录，不含虚构实车记录。</p><p>运行见<a href="README.md">README</a>；实验边界见<a href="docs/DATA_CARD.md">数据说明</a>；核算方法见<a href="carbon/README.md">碳模块说明</a>。</p><p><code>python run_all.py --allow-demo-carbon</code></p><p class="muted">首次需Python 3.12及requirements.txt依赖。原始数据已包含。版本、预测和复核记录保存在results中。</p></section>
<footer>下一阶段：授权真实BMS片段与独立容量标签，更多电池ID和工况，容量定义核对，可追溯制造回收因子。未取得车企合作、实车数据、专利或认证。</footer></main></html>'''
    (root/'report_v01.html').write_text(contents,encoding='utf-8')
    print('Generated report_v01.html',flush=True)

if __name__=='__main__': make(Path(__file__).resolve().parents[2])
