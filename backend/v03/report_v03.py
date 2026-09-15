"""Static evidence report, not a product Web Demo."""
import json
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from .report import table

def make(root):
    read=lambda p:json.loads((root/p).read_text(encoding='utf-8'))
    case=read('data/demo/results/decision/DEMO_ALL_EVIDENCE.json')
    checks=read('data/demo/results/verification_v03.json')
    rows=pd.DataFrame(case['routes'])
    font=FontProperties(fname='C:/Windows/Fonts/msyh.ttc') if Path('C:/Windows/Fonts/msyh.ttc').exists() else FontProperties()
    fig,ax=plt.subplots(figsize=(9,5))
    for r in case['routes']:
        ax.scatter(r['carbon_kgco2e'],r['npv_cny'],s=130,marker='o' if r['route_id'] in case['pareto_routes'] else 'x')
        ax.annotate(r['route_name'],(r['carbon_kgco2e'],r['npv_cny']),xytext=(8,8),textcoords='offset points',fontproperties=font)
    ax.set_xlabel('Future carbon / kg CO2e (lower is better)');ax.set_ylabel('NPV / CNY (higher is better)')
    ax.set_title('Illustrative scenario | equal 10,000 kWh service over 3 years')
    ax.margins(.25);ax.grid(alpha=.2);fig.tight_layout()
    for ext in ['png','svg']:fig.savefig(root/f'data/demo/results/figures/decision_pareto.{ext}',dpi=170)
    plt.close(fig)
    coverage=pd.DataFrame([
        ['SOH：线性回归 / 随机森林 / XGBoost','已完成公开电芯验证'],
        ['RUL：趋势 / 速率参考 / 随机森林','已完成探索性验证'],
        ['SHAP：全局与单样本解释','已计算留出电芯132条记录'],
        ['碳足迹 / 经济 / 资源 / Pareto决策','可运行原型，参数含示例假设'],
        ['安全硬约束与证据缺失阻断','原型已测试，非安全认证'],
        ['接口与报告输出','独立接口已测试，组员网页待联调'],
        ['真实车辆BMS迁移验证','尚未取得真实数据'],
        ['LightGBM / 深度时序模型 / Monte Carlo','本轮未实施']],columns=['模块','实际状态'])
    coverage.to_csv(root/'data/demo/results/technical_coverage.csv',index=False,encoding='utf-8-sig')
    fig,ax=plt.subplots(figsize=(12,5));ax.axis('off')
    for i,row in coverage.iterrows():
        y=.95-i*.115
        ax.text(.01,y,row.iloc[0],fontproperties=font,fontsize=11,va='top')
        ax.text(.52,y,row.iloc[1],fontproperties=font,fontsize=11,va='top',color='#087f8c' if i<6 else '#986b35')
    fig.tight_layout()
    for ext in ['png','svg']:fig.savefig(root/f'data/demo/results/figures/technical_coverage.{ext}',dpi=170,bbox_inches='tight')
    plt.close(fig)
    gates=[]
    for p in sorted((root/'data/demo/results/decision').glob('DEMO_*.json')):
        c=json.loads(p.read_text(encoding='utf-8'));gates.append({'情景':c['scenario_id'],'可行路径':', '.join(c['feasible_routes']) or '无','模拟推荐':c['recommended_route'] or '暂停，补充证据或专业评估'})
    summary=rows[['route_name','carbon_kgco2e','npv_cny','recovered_kg','technical_score','weighted_score']].copy()
    summary.columns=['路径','未来碳排放kgCO2e','净现值元','回收材料kg','技术假设分','偏好得分']
    css=(root/'report_v01.html').read_text(encoding='utf-8').split('<style>')[1].split('</style>')[0]
    html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>电循智策 V0.3 技术验证</title><style>{css}</style><main>
    <header><div class="eyebrow">电循智策 / V0.3</div><h1>从健康预测到可解释决策</h1><p>SHAP解释 · 安全证据筛选 · 多目标路径比较 · 组员接口交接</p></header>
    <div class="callout">公开NASA电芯模型与示例电池包决策分开呈现。决策参数尚未经真实业务标定，结果不是实车处置指令；组员网页实际联调等待提供网址。</div>
    <section><h2>01 / 实际完成范围</h2>{table(coverage)}<p><a href="data/demo/results/figures/technical_coverage.png">下载技术完成情况图</a> · <a href="report_v02.html">查看V0.2模型精度及数据边界</a></p></section>
    <section><h2>02 / 为什么模型给出这个SOH</h2><p>对留出电芯B0018的132条记录计算精确TreeSHAP，核对基准值与特征贡献之和等于模型预测。贡献单位为SOH百分点。它解释模型如何使用输入，不证明温度或其他因素造成了多少物理衰减。</p><img src="data/demo/results/figures/shap_global.png" alt="全局模型归因"><img src="data/demo/results/figures/shap_local.png" alt="单样本模型归因"><p><a href="docs/SHAP说明.md">方法与来源</a> · <a href="data/demo/results/shap/shap_values.csv">全部归因值</a></p></section>
    <section><h2>03 / 同一服务需求下比较四条路径</h2><p>示例统一为未来3年累计10000kWh储能放电服务，服务缺口由替代方案补足。安全与证据要求先于评分；Pareto同时比较碳、经济、资源和技术。下图仅投影碳与经济两个维度，圆点表示四维非支配方案。</p>{table(summary)}<img src="data/demo/results/figures/decision_pareto.png" alt="模拟决策比较"><p>当前示例均衡偏好推荐“检修后使用”；改变偏好可能改变推荐，不存在脱离假设的唯一最优方案。</p>{table(pd.DataFrame(gates))}<p><a href="data/demo/decision/方法与参数说明.md">规则、单位和参数说明</a> · <a href="data/demo/results/decision/preference_sensitivity.csv">偏好敏感性</a></p></section>
    <section><h2>04 / 验证和交接</h2><p>本轮完整测试入口覆盖53项单元测试，并保留原83项及V0.2的59项结果复核；新增{checks['checks_passed']}项V0.3验收检查。HTTP接口覆盖正常输出、非法输入与安全阻断，尚未调用组员网页。</p><p><a href="docs/v03_integration/联调说明.md">组员联调说明</a> · <a href="data/demo/results/integration/example_report.json">完整示例响应</a> · <a href="docs/真实BMS验证准备.md">真实数据验证准备</a> · <a href="README.md">运行说明</a></p></section>
    <footer>没有新增真实车企数据、合作、专利或商业验证。安全阈值与价值参数为可编辑原型假设。</footer></main></html>'''
    (root/'report.html').write_text(html,encoding='utf-8')
    print('V0.3 report and figures saved')

if __name__=='__main__':make(Path(__file__).resolve().parents[2])
