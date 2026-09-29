"""Create V4 figures and a research-progress report strictly from saved results.

Each figure is rendered from its exported CSV, so the figure data are reusable.
The document does not edit the application form or represent an authored paper.
"""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

METHODS = ['train_mean', 'train_median', 'ridge', 'random_forest', 'hist_gradient_boosting']
LABELS = dict(zip(METHODS, ['训练均值', '训练中位数', 'Ridge', '随机森林', '直方图梯度提升']))
LABELS.update(prefix_formula='前缀公式', without_soc='去 SOC', without_current='去电流',
    without_soc_current='去 SOC 与电流', without_voltage='去电压', without_temperature='去温度',
    without_cell_gap='去单体压差', noise_1pct='1% 噪声', noise_5pct='5% 噪声', missing_10pct='10% 元素缺失')
COLORS = ['#777777', '#CC79A7', '#0072B2', '#009E73', '#D55E00']
FIGS = ['model_comparison', 'window_mae', 'formula_comparison', 'coverage_risk', 'ablation',
        'condition_strata', 'learning_curve', 'error_distribution', 'group_cv', 'stress',
        'vehicle_errors', 'predictions']
CAPTIONS = ['固定测试集十分钟输入的五方法比较', '相同长充电队列的观测窗口比较',
    '各窗口公式可计算子集内的公平比较', '验证集选择质量阈值后的覆盖与误差',
    '十分钟随机森林三随机种子的特征消融', '训练集确定边界的工况分层误差',
    '不同训练车辆数量下的验证集学习曲线', '固定测试集五方法绝对误差分布',
    '训练车辆内五折分组验证', '十分钟随机森林的模拟输入压力测试',
    '固定测试车辆的五方法逐车误差', '十分钟随机森林预测与容量代理标签']
ROOT = Path('outputs/challenge_cup_v4')


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def configure_style():
    plt.rcParams.update({'font.sans-serif': ['Microsoft YaHei', 'SimHei', 'DejaVu Sans'],
        'font.size': 10, 'axes.labelsize': 11, 'xtick.labelsize': 10, 'ytick.labelsize': 10,
        'axes.unicode_minus': False, 'axes.spines.top': False, 'axes.spines.right': False,
        'axes.linewidth': .7, 'axes.edgecolor': '#666666', 'figure.facecolor': 'white',
        'axes.facecolor': 'white', 'savefig.facecolor': 'white', 'svg.fonttype': 'path'})


def canvas(nrows=1, ncols=1):
    return plt.subplots(nrows, ncols, figsize=(8, 4.5), layout='constrained')


def grid(ax, which='y'):
    ax.grid(axis=which, color='#E5E7E9', lw=.6)
    ax.set_axisbelow(True)


def lollipop(ax, labels, values, errors=None, colors=None):
    y = np.arange(len(values))
    ax.hlines(y, 0, values, color='#C8CED2', lw=1.3)
    ax.scatter(values, y, s=45, color=colors or COLORS[2], zorder=3)
    if errors is not None:
        ax.errorbar(values, y, xerr=errors, fmt='none', color='#444444', capsize=3, lw=1)
    for a, b in zip(values, y):
        ax.annotate(f'{a:.3f}', (a, b), xytext=(7, 5 if errors is not None else 0),
                    textcoords='offset points', va='center', fontsize=10)
    ax.set_yticks(y, labels)
    ax.set_ylim(len(values)-.4, -.6)
    ax.set_xlim(0, max(np.asarray(values)+(np.asarray(errors) if errors is not None else 0))*1.25)
    ax.set_xlabel('容量代理 MAE / Ah（越低越好）')
    grid(ax, 'x')


def render_figure(index, d, root):
    """Read no scores other than those present in this figure's source CSV."""
    if index == 1:
        fig, ax = canvas()
        d = d.set_index('experiment').loc[METHODS].reset_index()
        lollipop(ax, [LABELS[x] for x in d.experiment], d.mae_ah.to_numpy(), colors=COLORS)
        ax.text(1, 1.02, f'600 秒输入 · 历史固定测试集 · n={int(d.n.iloc[0]):,}',
                transform=ax.transAxes, ha='right', fontsize=10)
    elif index == 2:
        fig, ax = canvas()
        for i, method in enumerate(METHODS):
            q = d[d.experiment == method].sort_values('window_s')
            ax.plot(q.window_s/60, q.mae_ah, 'o-', lw=1.6, ms=5, color=COLORS[i], label=LABELS[method])
        ax.set(xlim=(0, 10.7), ylim=(0, d.mae_ah.max()*1.2), xticks=[0,2,5,10],
               xlabel='可用观测时长 / 分钟', ylabel='容量代理 MAE / Ah')
        ax.legend(ncol=3, loc='upper center', frameon=False, fontsize=9)
        ax.text(.02,.03,f'各窗口相同测试片段 n={int(d.n.iloc[0]):,}；完整片段筛选后的离线队列', transform=ax.transAxes, fontsize=9)
        grid(ax)
    elif index == 3:
        fig, axs = canvas(1,3)
        for ax, (w,q) in zip(axs, d.groupby('window_s')):
            q = q.set_index('experiment').loc[['prefix_formula','random_forest']].reset_index()
            ax.bar([0,1],q.mae_ah, width=.42, color=[COLORS[4],COLORS[3]])
            for i, v in enumerate(q.mae_ah):
                ax.text(i,v+q.mae_ah.max()*.045,f'{v:.3f}',ha='center',fontsize=10)
            ax.set_xticks([0,1],['公式','随机森林'])
            ax.set_ylim(0,q.mae_ah.max()*1.35)
            ax.set_title(f'{int(w/60)} 分钟',fontsize=11)
            ax.set_xlabel(f'n={int(q.n.iloc[0]):,} · 覆盖 {q.coverage.iloc[0]:.1%}',fontsize=9)
            grid(ax)
        axs[0].set_ylabel('容量代理 MAE / Ah')
        fig.suptitle('每个窗口内取相同 ΔSOC ≥ 1 个百分点子集；各面板纵轴刻度不同',fontsize=10)
    elif index == 4:
        fig, ax = canvas()
        for split, color, label, marker in [('validation',COLORS[2],'验证车辆','o'),('test',COLORS[3],'历史测试车辆','s')]:
            q = d[d.split == split].sort_values('threshold')
            ax.plot(q.coverage*100,q.vehicle_macro_mae_ah,marker+'-',color=color,label=label,ms=5,lw=1.3)
            for row in q.itertuples():
                if row.threshold in [5,10]:
                    ax.annotate(f'{int(row.threshold)}', (row.coverage*100,row.vehicle_macro_mae_ah),
                        xytext=(4,5 if split=='validation' else -12), textcoords='offset points',fontsize=8,color=color)
            chosen = q[q.selected_on_validation.astype(str).str.lower()=='true']
            ax.scatter(chosen.coverage*100,chosen.vehicle_macro_mae_ah,s=135,facecolors='none',edgecolors=color,lw=1.7,zorder=5)
        ax.set(xlim=(0,105),ylim=(0,d.vehicle_macro_mae_ah.max()*1.2),
               xlabel='保留样本比例 / %',ylabel='车辆等权 MAE / Ah')
        ax.legend(frameon=False,loc='upper right')
        selected_threshold=int(d.loc[d.selected_on_validation.astype(str).str.lower()=='true','threshold'].iloc[0])
        ax.text(.025,.045,f'候选阈值 0、1、2、3、5、10；空心大圆标出所选 {selected_threshold} 个百分点规则\n接近 100% 覆盖的候选点重叠；分母为既有长充电队列',transform=ax.transAxes,fontsize=9)
        grid(ax)
    elif index == 5:
        fig, ax = canvas()
        order = ['random_forest','without_soc','without_current','without_soc_current','without_voltage','without_temperature','without_cell_gap']
        q = d.groupby('experiment').mae_ah.agg(['mean','std']).loc[order]
        labs = ['全特征']+[LABELS[x] for x in order[1:]]
        lollipop(ax,labs,q['mean'].to_numpy(),q['std'].to_numpy())
        ax.text(1,1.02,'每项三个随机种子；点为均值，横线为标准差',ha='right',transform=ax.transAxes,fontsize=9)
    elif index == 6:
        fig, axs = canvas(2,2)
        descriptions = {'soc_start':'起始 SOC / %','tmax_mean':'前缀最高温度均值 / ℃',
                        'current_abs':'平均电流绝对值 / A','prefix_soc_gain_pct':'前缀 SOC 增量 / 百分点'}
        for ax, (feat,q) in zip(axs.ravel(), d.groupby('feature',sort=False)):
            q = q.sort_values('bin')
            ax.plot(range(len(q)), q.mae_ah, 'o-',color=COLORS[3],lw=1.3)
            ax.set_xticks(range(len(q)), q.bin_label,fontsize=8)
            ax.set_title(descriptions[feat],fontsize=10)
            for i,row in enumerate(q.itertuples()):
                ax.annotate(f'{row.mae_ah:.2f}\nn={row.n:,}', (i,row.mae_ah), xytext=(0,6),textcoords='offset points',ha='center',fontsize=8)
            ax.set_ylim(0,q.mae_ah.max()*1.42)
            ax.set_xlim(-.35,len(q)-.65)
            ax.set_ylabel('MAE / Ah',fontsize=9)
            grid(ax)
    elif index == 7:
        fig, ax = canvas()
        for i,(seed,q) in enumerate(d.groupby('repeat_seed')):
            ax.plot(q.training_vehicle_count,q.mae_ah,'o-',color=COLORS[i+2],lw=1.1,ms=4,label=f'抽车排列 {seed}')
        means = d.groupby('training_vehicle_count').mae_ah.mean()
        ax.plot(means.index,means.values,'k--',lw=1.3,label='三排列均值')
        ax.set(xlim=(0,15),ylim=(0,d.mae_ah.max()*1.2),xticks=[0,4,6,8,10,12,14],
               xlabel='参与训练的车辆数量',ylabel='验证集 MAE / Ah')
        ax.legend(frameon=False,ncol=2,fontsize=9)
        ax.text(.02,.035,'仅验证车辆 15—16；每个排列内嵌套抽车\n14 车端点复用同一拟合，三点不代表三次独立训练',transform=ax.transAxes,fontsize=9)
        grid(ax)
    elif index == 8:
        fig, ax = canvas()
        for i,method in enumerate(METHODS):
            q = d[d.experiment==method].sort_values('absolute_error_ah')
            ax.plot(q.absolute_error_ah,q.cumulative_fraction*100,color=COLORS[i],label=LABELS[method],lw=1.4)
        ax.set(xlim=(0,d.absolute_error_ah.max()*1.02),ylim=(0,101),xlabel='绝对误差 / Ah',ylabel='累计样本比例 / %')
        ax.legend(frameon=False,loc='lower right',fontsize=9)
        grid(ax)
    elif index == 9:
        fig, ax = canvas()
        q = d.groupby('experiment').mae_ah.agg(['mean','std']).loc[METHODS]
        lollipop(ax,[LABELS[x] for x in METHODS],q['mean'].to_numpy(),q['std'].to_numpy(),colors=COLORS)
        ax.text(1,1.02,'600 秒输入；训练车辆内五折；点为均值，横线为标准差',ha='right',transform=ax.transAxes,fontsize=9)
    elif index == 10:
        fig, ax = canvas()
        order = ['random_forest','noise_1pct','noise_5pct','missing_10pct']
        q = d.set_index('experiment').loc[order]
        lollipop(ax,['原始输入']+[LABELS[x] for x in order[1:]],q.mae_ah.to_numpy(),colors=[COLORS[3]]+[COLORS[2]]*3)
        ax.text(1,1.02,'冻结随机森林；仅改变输入，不改变标签',transform=ax.transAxes,ha='right',fontsize=9)
    elif index == 11:
        fig, ax = canvas()
        vehicles = sorted(d.vehicle.unique())
        for i,method in enumerate(METHODS):
            q=d[d.experiment==method].set_index('vehicle').loc[vehicles]
            ax.plot(range(len(vehicles)),q.mae_ah,'o-',color=COLORS[i],label=LABELS[method],lw=1.3,ms=5)
        counts = d[d.experiment=='random_forest'].set_index('vehicle').loc[vehicles]
        ax.set_xticks(range(len(vehicles)),[f'车辆 {int(v.split("_")[-1])}\nn={int(counts.loc[v,"n"]):,}' for v in vehicles])
        ax.set(ylim=(0,d.mae_ah.max()*1.25),ylabel='容量代理 MAE / Ah',xlabel='历史固定测试车辆')
        ax.legend(frameon=False,ncol=3,fontsize=9,loc='upper center')
        grid(ax)
    elif index == 12:
        fig, ax = canvas()
        for i,(vehicle,q) in enumerate(d.groupby('vehicle')):
            ax.scatter(q.proxy_capacity_ah,q.predicted_ah,s=5,alpha=.25,color=COLORS[i+1],rasterized=True,
                       label=f'车辆 {int(vehicle.split("_")[-1])}')
        maximum = max(d.proxy_capacity_ah.max(), d.predicted_ah.max())*1.03
        ax.plot([0,maximum],[0,maximum],ls='--',color='#555555',lw=1,label='预测等于标签')
        ax.set(xlim=(0,maximum),ylim=(0,maximum),xlabel='整段计算的容量代理标签 / Ah',ylabel='随机森林预测 / Ah')
        ax.set_aspect('equal',adjustable='box')
        e=d.predicted_ah-d.proxy_capacity_ah
        r2=1-float((e**2).sum())/float(((d.proxy_capacity_ah-d.proxy_capacity_ah.mean())**2).sum())
        ax.text(.03,.97,f'MAE={abs(e).mean():.3f} Ah\nRMSE={np.sqrt((e**2).mean()):.3f} Ah\nR²={r2:.3f}',
                transform=ax.transAxes,va='top',fontsize=9)
        ax.legend(frameon=False,loc='lower right',fontsize=8,markerscale=2)
        grid(ax,'both')
    else:
        raise ValueError(index)
    name=f'fig_{index:02d}_{FIGS[index-1]}'
    fig.savefig(root/'png'/f'{name}.png',dpi=300)
    fig.savefig(root/'svg'/f'{name}.svg',dpi=300)
    plt.close(fig)


def make_figures(root):
    configure_style()
    figs=root/'05_figures'
    for suffix in ['png','svg','source_csv']: (figs/suffix).mkdir(parents=True,exist_ok=True)
    met=pd.read_csv(root/'02_metrics/all_metrics.csv')
    primary=met[(met.group=='primary')&(met.split=='test')]
    pred=pd.read_csv(root/'03_predictions/all_predictions.csv.gz')
    mainpred=pred[(pred.group=='primary')&(pred.split=='test')&(pred.window_s==600)].copy()
    fair=pd.read_csv(root/'02_metrics/matched_formula_comparison.csv')
    strata=pd.read_csv(root/'02_metrics/condition_strata.csv')
    strata=strata[(strata.split=='test')&(strata.window_s==600)&(strata.experiment=='random_forest')].copy()
    edges=load_json(root/'06_verification/condition_bin_edges.json')
    def describe_bin(row):
        bounds=edges[f'600_{row.feature}']; low,high=bounds[row.bin:row.bin+2]
        return f'≤{high:.1f}' if low is None else (f'>{low:.1f}' if high is None else f'{low:.1f}—{high:.1f}')
    strata['bin_label']=[describe_bin(row) for row in strata.itertuples()]
    cdf=[]
    for method,q in mainpred.groupby('experiment'):
        q=q.copy();q['absolute_error_ah']=abs(q.predicted_ah-q.proxy_capacity_ah)
        q=q.sort_values(['absolute_error_ah','segment_id']);q['cumulative_fraction']=np.arange(1,len(q)+1)/len(q)
        cdf.append(q)
    cv=pd.read_csv(root/'02_metrics/group_cv.csv')
    veh=pd.read_csv(root/'02_metrics/per_vehicle.csv')
    sources=[primary[primary.window_s==600],primary,
        fair[(fair.split=='test')&(fair.threshold==1)&fair.experiment.isin(['prefix_formula','random_forest'])],
        pd.read_csv(root/'02_metrics/quality_coverage.csv'),
        met[(met.split=='test')&met.group.isin(['seed','ablation'])],strata,
        pd.read_csv(root/'02_metrics/learning_curve.csv'),pd.concat(cdf),cv[cv.window_s==600],
        pd.concat([primary[(primary.window_s==600)&(primary.experiment=='random_forest')],met[(met.group=='stress')&(met.split=='test')]]),
        veh[(veh.window_s==600)&(veh.split=='test')],mainpred[mainpred.experiment=='random_forest']]
    audit=[]
    for i,data in enumerate(sources,1):
        name=f'fig_{i:02d}_{FIGS[i-1]}'; csv=figs/'source_csv'/f'{name}.csv'
        data.to_csv(csv,index=False,encoding='utf-8-sig')
        exported=pd.read_csv(csv)
        render_figure(i,exported,figs)
        audit.append({'figure':name,'caption':CAPTIONS[i-1],'rows':len(data),'source_sha256':sha(csv),
            'png_sha256':sha(figs/'png'/f'{name}.png'),'svg_sha256':sha(figs/'svg'/f'{name}.svg'),
            'width_px':2400,'height_px':1350,'dpi':300})
    write_json(figs/'figure_manifest.json',audit)
    return audit


def doc_helpers():
    from docx import Document
    from docx.shared import Pt,Cm,RGBColor
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    doc=Document();sec=doc.sections[0]
    sec.page_width=Cm(21);sec.page_height=Cm(29.7)
    sec.top_margin=Cm(1.8);sec.bottom_margin=Cm(1.7);sec.left_margin=Cm(2);sec.right_margin=Cm(2)
    sec.header_distance=Cm(.7);sec.footer_distance=Cm(.7)
    for key,size in [('Normal',10.5),('Title',22),('Subtitle',13),('Heading 1',16),('Heading 2',12),('Caption',9)]:
        st=doc.styles[key];st.font.name='Calibri';st.font.size=Pt(size);st.font.color.rgb=RGBColor(0,0,0)
        st.font.italic=False
        st.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'宋体' if key=='Normal' else '微软雅黑')
        st.paragraph_format.space_after=Pt(7);st.paragraph_format.line_spacing=1.18
        for border in list(st.element.xpath('./w:pPr/w:pBdr')):
            border.getparent().remove(border)
    doc.styles['Title'].paragraph_format.space_after=Pt(13)
    h=sec.header.paragraphs[0];h.text='电循智策  V4 研究进展与实验结果';h.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    for r in h.runs:r.font.size=Pt(8);r.font.color.rgb=RGBColor(0,0,0)
    f=sec.footer.paragraphs[0];f.alignment=WD_ALIGN_PARAGRAPH.CENTER
    f.add_run('第 ');fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');f._p.append(fld);f.add_run(' 页')
    def p(text,style=None):
        a=doc.add_paragraph(text,style);a.paragraph_format.widow_control=True;return a
    def heading(text,newpage=True):
        if newpage:doc.add_page_break()
        return doc.add_heading(text,level=1)
    def table(caption,headers,rows,widths=None):
        c=p(caption,'Caption');c.paragraph_format.keep_with_next=True
        t=doc.add_table(rows=1, cols=len(headers));t.autofit=False
        tpr=t._tbl.tblPr
        borders=OxmlElement('w:tblBorders')
        for edge in ['top','left','bottom','right','insideH','insideV']:
            el=OxmlElement('w:'+edge);el.set(qn('w:val'),'single');el.set(qn('w:sz'),'4');el.set(qn('w:color'),'D9D9D9');borders.append(el)
        tpr.append(borders)
        for i,text in enumerate(headers):t.rows[0].cells[i].text=str(text)
        repeat=OxmlElement('w:tblHeader');t.rows[0]._tr.get_or_add_trPr().append(repeat)
        for row in rows:
            for cell,text in zip(t.add_row().cells,row):cell.text=str(text)
        for ridx,row in enumerate(t.rows):
            for i,c in enumerate(row.cells):
                if widths:c.width=Cm(widths[i])
                tcpr=c._tc.get_or_add_tcPr()
                margins=OxmlElement('w:tcMar')
                for edge in ['top','left','bottom','right']:
                    a=OxmlElement('w:'+edge);a.set(qn('w:w'),'85');a.set(qn('w:type'),'dxa');margins.append(a)
                tcpr.append(margins)
                if ridx==0:
                    sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'E9EEF2');tcpr.append(sh)
                for a in c.paragraphs:
                    a.paragraph_format.space_after=Pt(1);a.paragraph_format.space_before=Pt(1)
                    a.paragraph_format.line_spacing=1.05
                    for r in a.runs:r.font.size=Pt(9);r.bold=ridx==0
            cant=OxmlElement('w:cantSplit');row._tr.get_or_add_trPr().append(cant)
        p('')
        return t
    document_figure_count=0
    def figure(root,index,width=15.8):
        nonlocal document_figure_count
        document_figure_count+=1
        a=p('');a.alignment=WD_ALIGN_PARAGRAPH.CENTER
        a.paragraph_format.keep_with_next=True;a.paragraph_format.space_after=Pt(3)
        a.add_run().add_picture(str(root/'05_figures/png'/f'fig_{index:02d}_{FIGS[index-1]}.png'),width=Cm(width))
        c=p(f'图{document_figure_count}  {CAPTIONS[index-1]}','Caption');c.alignment=WD_ALIGN_PARAGRAPH.CENTER
    return doc,p,heading,table,figure


def make_report(root):
    from docx.shared import Pt
    mat=root/'07_materials';mat.mkdir(parents=True,exist_ok=True)
    met=pd.read_csv(root/'02_metrics/all_metrics.csv')
    primary=met[(met.group=='primary')&(met.split=='test')&(met.window_s==600)].set_index('experiment').loc[METHODS]
    fair=pd.read_csv(root/'02_metrics/matched_formula_comparison.csv')
    fair=fair[(fair.split=='test')&(fair.threshold==1)]
    gate=pd.read_csv(root/'02_metrics/quality_coverage.csv');rule=load_json(root/'06_verification/quality_rule.json')
    chosen=gate[(gate.split=='test')&(gate.threshold==rule['threshold_soc_gain_pct'])].iloc[0]
    baseline_gate=gate[(gate.split=='test')&(gate.threshold==0)].iloc[0]
    data=load_json(root/'01_data/audit.json');manifest=load_json(root/'06_verification/run_manifest.json')
    raw=pd.read_csv(root/'01_data/window_features.csv.gz');six=raw[raw.window_s==600]
    best=primary.mae_ah.idxmin();rf=primary.loc['random_forest'];hgb=primary.loc['hist_gradient_boosting']
    doc,p,h,t,fig=doc_helpers()
    doc.add_paragraph('电循智策',style='Title')
    doc.add_paragraph('短时充电信息与容量代理预测的补充研究',style='Subtitle')
    p('挑战杯研究进展与实验结果  V4  2026年9月29日')
    p('项目正式名称：电循智策——基于BMS多维运行数据的动力电池健康评估与循环利用决策研究。')
    p('本报告说明我们在既有实车容量代理实验上新增了什么、每项实验要回答什么问题，以及目前结果可以支持哪些结论。它是研究进展材料，不是已完成或发表的论文，也不改写原申报表。')
    h('本轮研究结论',False)
    p(f'十分钟输入下，五种方法中固定测试MAE最低的是{LABELS[best]}，为{primary.loc[best,"mae_ah"]:.4f} Ah。新增直方图梯度提升的MAE为{hgb.mae_ah:.4f} Ah；随机森林为{rf.mae_ah:.4f} Ah。新增算法的作用是补充比较，不保证改善，也不据此替换V3模型。')
    comparison_parts=[]
    for w in sorted(fair.window_s.unique()):
        q=fair[fair.window_s==w].set_index('experiment')
        winner='随机森林' if q.loc['random_forest','mae_ah']<q.loc['prefix_formula','mae_ah'] else '前缀公式'
        comparison_parts.append(f'{int(w/60)}分钟时{winner}的MAE较低')
    p('与同窗口公式在相同可计算片段上比较，'+ '，'.join(comparison_parts)+'。因此，不能宣称机器学习在任何观测时长下都优于直接公式。各窗口的子集覆盖不同，不能混用误差。')
    p(f'验证集选择的SOC增量阈值为{int(rule["threshold_soc_gain_pct"])}个百分点，历史测试覆盖{chosen.coverage:.2%}；车辆等权MAE从{baseline_gate.vehicle_macro_mae_ah:.4f}变为{chosen.vehicle_macro_mae_ah:.4f} Ah，变化很小。它提供了筛选与覆盖的量化记录，未形成明显改善或可靠性保证。')
    p('这些结果仍来自原20辆车的长充电片段。我们已经知道V3测试结果，V4属于回顾性补充研究。容量代理与输入共享电流和SOC信息；它不是独立实测SOH，也不能直接决定电池退役去向。')
    t('表1  本轮增加的内容',['类型','新增内容'],[
        ['预测参照','训练中位数、前缀公式、直方图梯度提升'],
        ['研究问题','两分钟、五分钟、十分钟的误差与公式覆盖'],
        ['可靠性分析','SOC阈值的覆盖与误差、工况分层、学习曲线'],
        ['补充验证','六组消融各三种子、五方法分组验证、误差尾部统计']], [3.1,13.5])

    h('1 数据来源与比较方法')
    p(f'我们重新读取公开实车数据的{data["raw_rows"]:,}行原始记录，保留既有{data["vehicles"]}辆车的{data["sessions_each_window"]:,}个有效充电片段。三个窗口使用同一批片段和同一标签，因此{data["window_records"]:,}条窗口特征记录不能当成新增独立样本。原始文件校验与V3对照记录保存在数据审计中。')
    rows=[]
    for split,label in [('train','训练'),('validation','验证'),('test','历史固定测试')]:
        q=six[six.split==split];rows.append([label,q.vehicle.nunique(),f'{len(q):,}'])
    t('表2  按车辆隔离的数据划分',['集合','车辆数','充电片段数'],rows,[6.8,4.8,5.0])
    p('公开数据原作者已使用基于充电电量与SOC变化的容量估计思路。我们沿用这一类计算关系作为容量代理标签，并没有发明该公式。[1—3] 原数据与车辆说明见原作者仓库；实际下载副本固定在既有版本。')
    p('整段容量代理＝整段负电流的时间积分÷3600÷（整段SOC增加百分点÷100）。前缀公式采用相同形式，但积分与SOC增量都只使用该观测窗口内可用的数据。充电电流的符号和SOC单位按数据字典处理。')
    p('模型输入仍为10项特征：起始SOC、起始电压、窗口10%／50%／100%位置电压、平均电流、最高温度均值、温升、平均及最大单体压差。短窗口提取不读取窗口之后的观测。')
    p('原队列的筛选依赖完整充电片段，因此本实验是可获得完整标签的离线队列比较。覆盖率只能解释为这批长充电片段中保留了多少，不能直接推到所有在线充电请求。')
    p('为了公平比较，前缀公式与随机森林在每个窗口使用完全相同的可计算片段；主比较要求前缀SOC增量至少1个百分点。二者观测时点相同，但公式直接使用窗口末SOC，10维模型并未直接输入该值，特征表示并不完全相同。')

    h('2 五种方法是否都值得保留')
    p('训练均值和中位数是无需学习特征关系的参照；Ridge提供线性对照；随机森林和直方图梯度提升提供两种非线性对照。五种方法全部报告，避免只展示其中最好的结果。[4—7]')
    fig(root,1)
    t('表3  十分钟输入的固定测试完整指标',['方法','MAE / Ah','RMSE / Ah','R²'],
      [[LABELS[m],f'{primary.loc[m,"mae_ah"]:.4f}',f'{primary.loc[m,"rmse_ah"]:.4f}',f'{primary.loc[m,"r2"]:.4f}'] for m in METHODS],[6.4,3.4,3.4,3.4])
    p(f'随机森林相对均值基线的MAE降低{(1-rf.mae_ah/primary.loc["train_mean","mae_ah"])*100:.2f}%。新增梯度提升比随机森林的MAE{("降低" if hgb.mae_ah<rf.mae_ah else "增加")}{abs(hgb.mae_ah-rf.mae_ah):.4f} Ah。该差值是描述性结果，未据此声称统计显著或跨车型优势。')
    p('固定配置：Ridge α=10；随机森林200棵树、叶节点最少5个样本；梯度提升最多200轮、学习率0.05、最多15个叶节点、叶节点最少20个样本、L2正则1，关闭提前停止。预处理只拟合训练车辆。')

    h('3 观察多久以及是否需要学习模型')
    p('图2先比较全队列中五种方法随观测时长的变化；图3再单独比较各窗口内相同公式可计算子集。两个问题的分母不同，不能把图2中的误差直接与图3公式误差相减。')
    fig(root,2,width=14.8)
    fig(root,3,width=14.8)
    parts=[]
    for w in sorted(fair.window_s.unique()):
        q=fair[fair.window_s==w].set_index('experiment');a=q.loc['prefix_formula'];b=q.loc['random_forest']
        parts.append(f'{int(w/60)}分钟：同子集n={int(a.n):,}，覆盖{a.coverage:.1%}，公式MAE={a.mae_ah:.3f} Ah，随机森林={b.mae_ah:.3f} Ah')
    p('；'.join(parts)+'。')
    p('公式中SOC增量很小时，分母会放大测量或量化误差。我们不按标签误差删除或裁剪公式异常大值。该比较检验学习模型的必要性，也允许出现公式更好或更多观测不改善的结果。')

    h('4 输出多少结果与误差多大')
    p('我们以SOC增量作为输入信息充分程度的一项检查，阈值候选固定为0、1、2、3、5、10个百分点。仅依据验证车辆15—16选择阈值：总体覆盖至少80%，每辆验证车覆盖至少60%，在可行规则中取车辆等权MAE较低者，并列优先较低阈值。')
    fig(root,4)
    t('表4  验证集所选规则在历史测试集上的表现',['项目','值'],[
      ['所选SOC增量阈值',f'{int(rule["threshold_soc_gain_pct"])} 个百分点'],
      ['历史测试保留片段',f'{int(chosen.n):,} / {int(chosen.n_total):,}'],
      ['历史测试覆盖',f'{chosen.coverage:.2%}'],['历史测试未保留片段',f'{int(chosen.n_rejected):,}'],
      ['筛选前车辆等权MAE',f'{baseline_gate.vehicle_macro_mae_ah:.4f} Ah'],
      ['筛选后车辆等权MAE',f'{chosen.vehicle_macro_mae_ah:.4f} Ah']],[9.2,7.4])
    p('车辆等权MAE先计算每辆车的MAE再取平均，避免记录较多的车辆完全主导评分。筛选降低或提高误差时，都要连同失去多少覆盖一起解释。验证车辆只有两辆，规则可能受这两辆车特点影响。')
    p('这是一项经验性数据筛选分析。阈值不是安全认证，不提供单次预测置信保证；被拒绝也不代表电池危险。正确提示是“当前信息不足，建议继续观察或补充数据”。')

    h('5 哪些输入对当前任务有用')
    p('V3的分组消融在本轮扩展为分别去SOC、去电流、同时去SOC和电流、去电压、去温度、去单体压差。每一项使用17、42、2026三个种子重新训练，报告全部结果。')
    fig(root,5)
    abl=met[(met.split=='test')&met.group.isin(['seed','ablation'])]
    a=abl.groupby('experiment').mae_ah.agg(['mean','std'])
    order=['random_forest','without_soc','without_current','without_soc_current','without_voltage','without_temperature','without_cell_gap']
    t('表5  三随机种子消融统计',['输入设置','MAE均值 / Ah','标准差 / Ah'],
      [[('全特征' if x=='random_forest' else LABELS[x]),f'{a.loc[x,"mean"]:.4f}',f'{a.loc[x,"std"]:.4f}'] for x in order],[8.4,4.1,4.1])
    p('删除特征后的性能变化只能说明当前数据与训练设置下的预测关联，不证明物理因果。尤其SOC和电流参与容量代理计算，模型对它们的依赖不能当成独立健康识别证据。压差信息去除后若改善，也不能推出其物理意义不存在。')

    h('6 模型在哪些工况下误差较大')
    p('我们按起始SOC、最高温度均值、平均电流绝对值和前缀SOC增量分别分层。分层边界由训练数据的三分位数确定，再固定用于验证与测试，不根据测试误差挑选边界。')
    fig(root,6)
    strata=pd.read_csv(root/'02_metrics/condition_strata.csv')
    q=strata[(strata.split=='test')&(strata.window_s==600)&(strata.experiment=='random_forest')]
    t('表6  工况分层样本与误差范围',['分层变量','各层样本数','各层MAE范围 / Ah'],
      [[{'soc_start':'起始SOC','tmax_mean':'温度','current_abs':'电流绝对值','prefix_soc_gain_pct':'SOC增量'}[f],
        ' / '.join(str(int(n)) for n in z.sort_values('bin').n),f'{z.mae_ah.min():.3f}—{z.mae_ah.max():.3f}'] for f,z in q.groupby('feature')],[5.0,6.2,5.4])
    p('分层图用于定位需要进一步检查的数据条件。各层不一定具有相同车辆构成或样本数量，不能把层间误差差异直接解释为温度、电流等因素造成的因果效应。逐车分层结果保存在电子结果文件中。')
    p('实际使用前还需区分：模型对某条件下的容量代理更难预测，和电池本身处于危险状态，是两件不同的事。当前研究没有真实故障标签，不能用这张图推断安全等级。')

    h('7 数据规模与换车验证')
    p('学习曲线使用三个固定抽车排列，分别嵌套选择4、6、8、10、12、14辆训练车，仅在验证车辆15—16上评价。五折验证则在14辆训练车辆内部按车辆轮换验证。[8]')
    fig(root,7,width=14.8)
    fig(root,9,width=14.8)
    p('学习曲线的14车端点复用同一拟合，不是三次独立实验。曲线不单调或不同抽车排列有差异，都是需要报告的结果；不能据此保证增加任意车辆都会改善预测。五折误差的标准差描述车辆组合差异，不是模型对新车型的保证。')

    h('8 平均误差之外还要看什么')
    p('累计误差分布显示多少样本落在某误差范围内；散点图显示预测是否偏向中间值。两个图均使用全部固定测试片段，不只展示表现好的样本。')
    fig(root,8,width=14.8)
    fig(root,12,width=14.8)
    p(f'十分钟随机森林的绝对误差中位数为{rf.median_ae_ah:.3f} Ah，P90为{rf.p90_ae_ah:.3f} Ah，P95为{rf.p95_ae_ah:.3f} Ah，最大值为{rf.max_ae_ah:.3f} Ah；平均有符号偏差为{rf.bias_ah:.3f} Ah。P90表示90%的测试片段误差不超过该值，不能当成未来样本的覆盖保证。')

    h('9 车辆差异与输入压力')
    p('逐车比较避免总体结果掩盖个别车辆表现；压力测试冻结模型和标签，仅在测试特征上加入模拟扰动或缺失。')
    fig(root,11,width=14.8)
    fig(root,10,width=14.8)
    p('1%与5%噪声的标准差按训练特征标准差缩放；10%缺失为随机特征元素缺失，并用训练中位数填补。它不模拟持续丢包、整列字段不可用或真实传感器失效，不能写成已通过现场故障验证。')

    h('10 研究证据与当前局限')
    t('表7  实验目的与可支持的解释',['实验','目的','需要保留的边界'],[
      ['窗口与公式对照','检验信息时长和模型必要性','同子集比较；公式非原创'],
      ['五方法及五折','比较方法与车辆组合变化','不追逐测试分数改选模型'],
      ['分层与消融','定位误差条件和特征关联','不作物理因果解释'],
      ['质量覆盖分析','同时量化误差与可输出比例','不是安全或置信保证'],
      ['学习曲线','检查训练车辆数量和组成','只在两辆验证车评价'],
      ['误差尾部与逐车','暴露均值掩盖的差异','样本相关且车辆数量有限'],
      ['预测复算与模型重载','核对数字可追溯和产物一致','程序检查不等于实车认证']],[4.2,6.2,6.2])
    p('V4保留V3研究证据，单独保存新特征、模型、逐条预测、分组清单、阈值选择和图表数据。V3原有三方法的十分钟结果由本轮重新训练后对照。')
    verification_path=root/'06_verification/independent_verification.json'
    if verification_path.exists():
        check=load_json(verification_path)
        p(f'独立核验从保存的逐条预测重新计算{check["independently_recomputed_metric_rows"]:,}行指标；本轮{check["models_reloaded"]}个模型在同一scikit-learn {manifest["sklearn"]}环境重载，完成{check["full_split_reload_checks"]}项完整验证集与测试集输出核对，核验状态为'+('通过。' if check['passed'] else '未通过。'))
    tests_path=root/'06_verification/python_tests.json'
    if tests_path.exists():
        tests=load_json(tests_path);legacy=tests['legacy_warnings']
        p(f'仓库Python自动化检查共{tests["test_count"]}项，状态为'+('通过。' if tests['passed'] else '未通过。')+
          f'其中旧生产模型出现{legacy["count"]}条版本兼容警告，涉及scikit-learn {legacy["artifact_sklearn"]}保存的模型在{legacy["runtime_sklearn"]}环境加载。本轮新模型重载检查不等于旧模型跨版本兼容性或网页联调已经验证。')
    else:
        p('仓库全套检查涉及的旧生产模型存在scikit-learn版本兼容警告。本轮新训练模型的重载检查不等于旧模型跨版本兼容性或网页联调已经验证；自动化测试详单以电子证据包的核验记录为准。')
    p('最关键局限是标签独立性：前缀输入与整段容量代理都利用电流和SOC，任务可能主要反映同源信息之间的关系。删除部分特征不能完全消除这种关联。只有获得独立实测容量，才能检验当前代理与真实电池状态的对应关系。')
    p('本轮在已知V3结果后设计，是同一车型、同一来源、同一车辆划分上的回顾性拓展；历史固定测试并非全新外部盲测。有效片段通过完整过程筛选，短时窗口不代表随机遇到的所有短充电过程。')
    p('下一阶段应优先获得匹配的实测容量标签，冻结模型后使用新增车辆或新来源数据做外部验证，再逐步研究真实健康度和循环利用辅助决策。网页原型、前期NASA模型及碳和路径情景仍需分别标明验证范围。')

    h('11 资料来源与结果索引')
    refs=[
      '[1] DENG Z, XU L, LIU H, et al. Prognostics of battery capacity based on charging data and data-driven methods for on-road vehicles. Applied Energy, 2023, 339:120954. https://doi.org/10.1016/j.apenergy.2023.120954',
      '[2] BatICM. Battery charging data of on-road electric vehicles. 原作者数据与车辆说明。https://github.com/BatICM/battery-charging-data-of-on-road-electric-vehicles',
      '[3] shiyunliu-battery. Battery charging data of on-road electric vehicles. 实际下载副本，固定版本904a336bc4a8de05acdec2598708fd787bbdb8e3。https://github.com/shiyunliu-battery/battery-charging-data-of-on-road-electric-vehicles',
      '[4] scikit-learn. DummyRegressor. 均值及中位数基线。https://scikit-learn.org/1.7/modules/generated/sklearn.dummy.DummyRegressor.html',
      '[5] scikit-learn. Ridge. https://scikit-learn.org/1.7/modules/generated/sklearn.linear_model.Ridge.html',
      '[6] scikit-learn. RandomForestRegressor. https://scikit-learn.org/1.7/modules/generated/sklearn.ensemble.RandomForestRegressor.html',
      '[7] scikit-learn. HistGradientBoostingRegressor. https://scikit-learn.org/1.7/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html',
      '[8] scikit-learn. GroupKFold. https://scikit-learn.org/1.7/modules/generated/sklearn.model_selection.GroupKFold.html']
    for text in refs:
        a=p(text);a.paragraph_format.space_after=Pt(6)
        for r in a.runs:r.font.size=Pt(9)
    p(f'本轮实际运行版本：Python {manifest["python"]}；scikit-learn {manifest["sklearn"]}。在线文档用于解释方法，真实运行依赖以冻结环境记录为准。数据原作者论文用于来源引用，不表示本团队撰写了论文。')
    t('表8  电子证据包主要目录',['目录','内容'],[
      ['01_data','原始数据核验与三个窗口的特征'],['02_metrics','全部模型、分层、消融、覆盖和验证指标'],
      ['03_predictions','逐条预测与独立复算输入'],['04_models','保存的模型与特征配置'],
      ['05_figures','12图PNG、SVG、CSV及校验清单'],['06_verification','分组、规则、复现与环境记录'],
      ['07_materials','本报告及答辩材料']],[4.4,12.2])
    path=mat/'电循智策_V4研究进展与实验结果.docx';doc.save(path)
    write_json(mat/'report_source_manifest.json',{'report':path.name,'pages_planned':12,'figures':12,
       'source_csv':{p.name:sha(p) for p in (root/'02_metrics').glob('*.csv')},
       'title':'电循智策 短时充电信息与容量代理预测的补充研究','not_authored_paper':True})
    return path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--figures-only',action='store_true');parser.add_argument('--regenerate-from-csv',action='store_true')
    args=parser.parse_args()
    if args.regenerate_from_csv:
        configure_style()
        for i,name in enumerate(FIGS,1):render_figure(i,pd.read_csv(args.root/'05_figures/source_csv'/f'fig_{i:02d}_{name}.csv'),args.root/'05_figures')
    else:make_figures(args.root)
    if not args.figures_only:print(make_report(args.root))


if __name__=='__main__':main()
