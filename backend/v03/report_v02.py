"""Chinese V0.2 comparison report and scientific figures."""
import json
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .report import table

NAMES={'v01_trend':'V0.1容量趋势','training_rate':'训练电芯速率参考','blended_rate':'局部与参考速率融合','random_forest_rul':'随机森林RUL'}

def make(root):
    out=root/'data/demo/results/figures';out.mkdir(exist_ok=True)
    pred=pd.read_csv(root/'data/demo/results/rul_v02/predictions.csv')
    scores=pd.read_csv(root/'data/demo/results/rul_v02/metrics_by_cell.csv')
    macro=pd.read_csv(root/'data/demo/results/rul_v02/macro_metrics.csv')
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.18})
    fig,axes=plt.subplots(2,2,figsize=(11,8))
    newmodels=['training_rate','blended_rate','random_forest_rul']
    labels=['Training-cell rate','Blended rate','Random forest']
    for ax,(b,g) in zip(axes.flat,pred.groupby('test_battery')):
        base=g[g.model=='training_rate']
        if base.true_rul_cycles.notna().any():ax.plot(base.cycle,base.true_rul_cycles,color='#252525',lw=2,label='Observed RUL')
        for m,label,color in zip(newmodels,labels,['#da9b32','#087f8c','#6750a4']):
            rows=g[g.model==m];ax.plot(rows.cycle,rows.predicted_rul_cycles,label=label,color=color,lw=1.5)
        ax.set(title=b+(' (right-censored)' if base.right_censored.iloc[0] else ' (held-out)'),
               xlabel='Current discharge cycle',ylabel='Remaining discharge cycles')
        ax.legend(fontsize=8)
    fig.suptitle('V0.2 exploratory RUL | measured-capacity histories; training cells isolated',fontsize=12)
    fig.tight_layout()
    for ext in ['png','svg']:fig.savefig(out/f'rul_v02_curves.{ext}',dpi=170,bbox_inches='tight')
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,5))
    order=['v01_trend','training_rate','blended_rate','random_forest_rul']
    ms=macro.set_index('model').loc[order];vals=ms.MAE_cycles
    ax.barh(['V0.1 trend','Training-cell rate','Blended rate','Random forest'],vals,color=['#af6666','#da9b32','#087f8c','#6750a4'])
    for i,v in enumerate(vals):ax.text(v+1,i,f'{v:.2f}',va='center')
    ax.set(xlabel='MAE (discharge cycles), unweighted mean over 3 held-out cells',
           title='RUL error comparison | reused dataset; not new external validation',xlim=(0,max(vals)*1.15))
    fig.tight_layout()
    for ext in ['png','svg']:fig.savefig(out/f'rul_v02_mae.{ext}',dpi=170,bbox_inches='tight')
    plt.close(fig)
    sm=macro.copy();sm['model']=sm.model.map(NAMES);sm.columns=['方法','平均MAE（循环）','平均RMSE（循环）','平均R²']
    by=scores[~scores.right_censored][['battery_id','model','evaluated_prefixes','MAE_cycles','RMSE_cycles','R2']].copy()
    by['model']=by.model.map(NAMES);by.columns=['留出电芯','方法','评估时点','MAE（循环）','RMSE（循环）','R²']
    bms=[]
    for tag in ['good','bad']:
        q=json.loads((root/f'data/demo/results/bms_{tag}/summary.json').read_text())
        bms.append({'构造测试文件':tag,'输入行数':q['input_rows'],'通过行数':q['accepted_rows'],'隔离行数':q['rejected_rows'],
                    '错误项':q['error_count'],'警告项':q['warning_count']})
    checks=json.loads((root/'data/demo/results/verification_v02.json').read_text())
    css=(root/'report_v01.html').read_text(encoding='utf-8').split('<style>')[1].split('</style>')[0]
    contents=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>电循智策 V0.2</title><style>{css}</style><main>
<header><div class="eyebrow">电循智策 / TECHNICAL VALIDATION / V0.2</div><h1>RUL改进与BMS接入检查</h1><p>本版在原V0.1成果上增加三种寿命估计方法，以及可运行的核心BMS数据校验。原始SOH结果、碳计算器和数据来源证据随包保留。</p></header>
<div class="callout">重要边界：V0.1已经查看过这4颗电芯，本轮属于同数据集探索性改进，不是新的独立外部验证。RUL输入仍需历史实测容量。BMS演示文件全是明确标注的软件构造数据，尚未取得真实车辆数据。</div>
<section><h2>01 / 原因与方法</h2><p>B0005第34循环，原方法因退化斜率接近零，将实际剩余91循环外推为约2228循环。V0.2比较：其他训练电芯的整体退化速率参考；本电芯局部速率与参考速率各占50%；固定参数随机森林。所有新方法按电芯隔离，参数在首轮V0.2评分前固定。</p><p>每次从3颗已观测EOL电芯中留出1颗，用其余2颗训练；B0007右删失，仅生成预测，不参与监督训练和误差计算。各方法统一在第30循环至首次EOL之前评估，避免靠更换样本美化对比。</p></section>
<section><h2>02 / 对比结果</h2>{table(sm)}<p><img src="data/demo/results/figures/rul_v02_mae.png" alt="RUL平均误差比较"></p>{table(by)}<p><img src="data/demo/results/figures/rul_v02_curves.png" alt="逐电芯RUL轨迹与预测"></p><div class="callout">改进明显，但三个终点样本不足以支撑泛化承诺。参考速率本身已取得较低误差，说明本数据集的共同实验老化条件贡献较大。随机森林不具备可靠的分布外外推能力，也没有校准置信区间。不能将结果换算成实车剩余年份或里程。</div><p><a href="data/demo/results/figures/rul_baseline.png">查看未裁剪的V0.1 RUL极端预测图</a> · <a href="data/demo/results/rul_v02/protocol.json">实验参数与分组记录</a></p></section>
<section><h2>03 / BMS文件接入</h2><p>检查明确时区、单位声明、唯一键、数值缺失、SOC范围和极值关系；统一时间到UTC、按声明统一电流方向；重复或不合格记录隔离，断档等输出警告。输出通过记录、隔离记录、问题清单和可配套重用的标准化元数据，不自动预测实车SOH/RUL。</p>{table(pd.DataFrame(bms))}<p>好文件12行通过；坏文件包含重复、无时区、缺电流、SOC越界、极值倒置，6行被隔离。两个文件均为synthetic_fixture，不是实测验证。</p><p><a href="data/sample/bms/接入检查说明_V0.2.md">接入操作说明</a> · <a href="data/sample/bms/metadata_v02_template.csv">V0.2元数据空模板</a> · <a href="data/demo/results/bms_bad/issues.csv">错误文件的检查明细</a></p></section>
<section><h2>04 / 复现与交付</h2><p>本轮通过32项单元测试、原83项结果复核和新增{checks['checks_passed']}项V0.2结果复核。预测值、按电芯误差、训练模型、测试样例和来源哈希均已保存。</p><p><code>python run_v02.py</code> 重跑本轮；<code>python run_all.py --allow-demo-carbon</code> 从原始数据重跑所有模块。首次按README安装Python依赖。</p><p><a href="README.md">当前README</a> · <a href="report_v01.html">V0.1基础结果报告</a> · <a href="docs/RUL_V0.2.md">RUL方法与局限</a></p></section>
<footer>下一步需要真实授权数据和独立容量标签，以及更多未使用过的寿命终点电芯。当前没有新增实车数据、车企合作、专利或碳因子核实成果。</footer></main></html>'''
    (root/'report_v02.html').write_text(contents,encoding='utf-8')
    print('Saved V0.2 report and two PNG/SVG figures')

if __name__=='__main__':make(Path(__file__).resolve().parents[2])
