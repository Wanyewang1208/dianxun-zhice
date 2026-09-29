"""Plain-language team guide from V4 result tables, separate from formal application."""
from pathlib import Path
import json
import pandas as pd
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path('outputs/challenge_cup_v4')


def main():
    metrics = pd.read_csv(ROOT/'02_metrics/all_metrics.csv')
    fair = pd.read_csv(ROOT/'02_metrics/matched_formula_comparison.csv')
    quality = pd.read_csv(ROOT/'02_metrics/quality_coverage.csv')
    primary = metrics[(metrics.group=='primary')&(metrics.split=='test')]
    def score(name,w=600): return float(primary[(primary.experiment==name)&(primary.window_s==w)].iloc[0].mae_ah)
    def formula(w): return fair[(fair.window_s==w)&(fair.split=='test')&(fair.threshold==1)&(fair.experiment=='prefix_formula')].iloc[0]
    def paired_rf(w): return fair[(fair.window_s==w)&(fair.split=='test')&(fair.threshold==1)&(fair.experiment=='random_forest')].iloc[0]
    rf = score('random_forest'); median = score('train_median'); hgb = score('hist_gradient_boosting')
    gate=quality[(quality.split=='test')&quality.selected_on_validation].iloc[0]
    doc=Document(); sec=doc.sections[0]
    for borders in doc.styles.element.xpath('.//w:pBdr'):
        borders.getparent().remove(borders)
    sec.top_margin=sec.bottom_margin=Cm(1.9);sec.left_margin=sec.right_margin=Cm(2.1)
    for name in ['Normal','Title','Heading 1','Heading 2']:
        s=doc.styles[name]; s.font.name='Microsoft YaHei'; s.font.color.rgb=RGBColor(0,0,0)
        s.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'微软雅黑')
    normal=doc.styles['Normal'];normal.font.size=Pt(11);normal.paragraph_format.line_spacing=1.25;normal.paragraph_format.space_after=Pt(7)
    footer=sec.footer.paragraphs[0];footer.alignment=2
    field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)
    def p(t): doc.add_paragraph(t)
    def h(t): doc.add_heading(t,1)
    def page(): doc.add_page_break()
    doc.add_heading('电循智策 V4 组员理解与答辩手册',0)
    p('用途：先让三名组员讲清楚项目，再练习五分钟陈述和追问。这里的数字来自本轮机器结果，不代替正式申报表；我们没有据此宣称已经撰写或发表论文。')
    h('先用一辆车理解我们的工作')
    p('一辆车充电时，会记录电压、电流、电量百分比和温度。我们把这些记录当作电池的运行日记。整段充电结束后，可以用充入的电量和电量百分比增幅，推算一个容量参考值。它叫容量代理，单位Ah，不能直接当作专业检测结果。')
    p('现在的问题是：只看到充电前2、5或10分钟，能不能提前估计这个参考值？我们既让模型预测，也用相同时间范围内的数据直接套公式，比较误差和能够计算的比例。')
    h('这轮升级具体增加了什么')
    for t in [
        '原来只看前10分钟，现在增加前2分钟和5分钟，并保证三组来自同一批29,697个片段。',
        '原来比较均值、Ridge和随机森林，现在增加训练中位数、同窗口公式，以及固定配置的直方图梯度提升树对照。后者是已有算法，不是团队原创。',
        '把SOC与电流分别删除再训练，检查不同信息的作用；增加工况分层、误差尾部统计和训练车辆数量实验。',
        '同时报告数据筛选后的误差和保留比例，保留不改善的结果；筛选阈值由验证车辆决定，不根据测试成绩挑选。']:
        p(t)
    p(f'V3的10分钟随机森林结果复现为{rf:.4f} Ah。V4的中位数基线为{median:.4f} Ah，梯度提升树为{hgb:.4f} Ah。模型多了不代表自动更准，必须查看下面的公平对照。')
    page();h('真正要背熟的结果和含义')
    for w in [120,300,600]:
        f=formula(w)
        paired=fair[(fair.window_s==w)&(fair.split=='test')&(fair.threshold==1)&(fair.experiment=='random_forest')].iloc[0]
        p(f'观察{w//60}分钟：全样本随机森林MAE为{score("random_forest",w):.4f} Ah；在SOC增量至少1个百分点的同一{int(f.n)}个片段上，公式MAE为{f.mae_ah:.4f} Ah、随机森林为{paired.mae_ah:.4f} Ah，可比较比例{f.coverage:.2%}。全样本与筛选子集的指标不能交叉排名。')
    p(f'验证集选定的SOC增量阈值为{gate.threshold:g}个百分点；测试队列保留{gate.coverage:.2%}，保留样本RF MAE为{gate.mae_ah:.4f} Ah。这是已筛选长充电片段内的经验分析，不是对所有在线数据的可用率承诺。')
    p('本轮最值得讲的发现：2分钟和5分钟时，随机森林比同窗口公式更接近全段容量代理；10分钟时，公式反而更好。说明方法的适用性随观测长度变化。我们没有预设机器学习一定优于公式，也没有根据这一轮已知测试结果发布自动切换策略。')
    p('筛选并没有带来明显改善：保留样本的误差只略微变化，不能宣传为显著增强可靠性。更不能把不输出的片段默认为安全或正常。')
    h('五个容易混淆的词')
    for a,b in [('SOC','现在还有多少电，例如手机显示剩余60%；不是健康度。'),('容量代理','用运行数据推算的容量参考值，可能有测量和算法误差。'),('MAE','预测与参考值之间平均差多少Ah，越小越接近参考值。'),('覆盖率','在当前指定队列中，满足某个计算或筛选条件的样本比例。'),('模型验证','在明确数据和任务下比较结果；不等于电池安全认证或产品落地。')]: p(a+'：'+b)
    page();h('每一种实验具体在问什么')
    experiments=[
        ('模型对照','在同一车辆划分和同一目标上比较五种方法，三种学习模型使用同10维输入。均值和中位数代表不看单次工况也能给出的参照；Ridge、随机森林和梯度提升树检验是否能利用运行特征。目的不是凑模型数量。'),
        ('观测时间对照','分别只读前2、5、10分钟。回答少等几分钟会损失多少预测表现。全样本RF变化较小，但仍需要连同简单公式一起评价实际意义。'),
        ('同窗口公式对照','用同一时段充入的电量除以SOC增幅，直接计算。只在相同片段上比较公式与模型，回答为什么需要模型。公式额外直接使用窗口终点SOC，属于相同时间范围而非完全相同特征表达。'),
        ('删除特征的实验','重新训练时故意不提供某类信息，观察误差变化。用来研究模型依赖哪些输入；删掉压差后更好，只说明当前任务和配置下没从它获益，不能说压差对安全诊断没有用。'),
        ('不同车辆与五折分组','先列出每辆测试车的误差，再只在14辆训练车内分五组轮流留出评价。回答结果是否过度依赖某几辆车；不能把重复划分当成新增车辆或外部验证。'),
        ('随机种子与车辆数量','更换三个随机种子看算法波动；按三种固定顺序逐步加入4到14辆训练车，只看验证车辆成绩。回答模型稳定性和继续增加车辆是否值得研究；14辆端点共用同一拟合，不算三次独立实验。'),
        ('噪声 缺失 工况和误差尾部','在测试特征中模拟扰动和缺失，并按训练集确定的工况边界查看误差。回答模型在哪些条件更易偏离，以及少数大误差有多大。模拟特征扰动不是现场传感器故障试验。'),
        ('筛选覆盖率','在验证车辆上决定SOC增量门槛，再报告测试车辆保留多少片段、剩下误差多大。回答少输出一些结果是否改善表现；本轮改善很小，应如实保留这个发现。'),
        ('程序与证据复核','从保存的预测文件重新算指标，重新加载模型，核查划分和图表数字。回答研究结果能否被追溯和复算，不回答电池是否安全。')]
    for index,(title,body) in enumerate(experiments):
        if index==5: page();h('实验目的 续')
        doc.add_heading(title,2);p(body)
    page();h('五分钟陈述示例')
    speech=[
        '各位老师好，我们的项目是电循智策。长期目标是为动力电池状态分析和循环利用提供数据依据。本轮研究聚焦一个问题：只看到充电开始后的少量记录，能否估计整段记录对应的容量参考值，以及什么时候需要提示信息不足。',
        '我们使用20辆真实商用车的公开充电数据，重新读取约1610万行记录，按固定规则得到29,697个片段。数据由原作者公开，不是我们自行采集。由于缺少对应的独立实测容量标签，本轮使用电流积分和SOC变化构造容量代理，不把它当成真实SOH。',
        '我们把前2、5、10分钟作为三个观测窗口，使用同一批片段和同一目标进行比较。14辆车用于训练，2辆保留为验证，4辆为历史固定测试，同一车辆不会跨集合。测试成绩在此前研究中已查看，因此本轮是回顾性补充研究。',
        '与前期工作相比，这次最关键的补充是公平参照。除了均值、Ridge、随机森林，我们增加训练中位数和同窗口直接公式，并报告公式可计算的比例。这样可以回答：学习方法是否比现成的计算方法提供更多价值，而不仅仅比较算法名字。',
        f'最重要的发现是，方法的优劣会随观察时间变化。2分钟时，在相同的{int(formula(120).n):,}个片段上，随机森林误差约{paired_rf(120).mae_ah:.3f} Ah，公式约{formula(120).mae_ah:.3f} Ah；5分钟时随机森林仍略好；10分钟时，公式误差约{formula(600).mae_ah:.3f} Ah，反而优于随机森林约{rf:.3f} Ah。因此我们不主张一味使用复杂模型，而是研究不同观测条件下各方法的适用范围。这些结果只针对容量代理。',
        '我们还分别删除SOC、电流、电压、温度和压差特征，检查模型依赖哪些信息；用分组验证和逐车辆误差观察车辆差异；通过输入扰动、缺失、工况分层和车辆数量实验研究适用条件。全部结果保留，不因为某个新方法没有改善就删除它。',
        '本项目的阶段贡献是把短时观测、公式参照、学习方法和覆盖率放在同一框架下进行实证比较，而不是宣称发明了公开公式或通用算法。模型、预测和图表源数据均已保存，能够独立复算。',
        '目前仍有两项关键限制：容量代理与输入共享电流和SOC信号；车辆来自同一来源和车型。因此下一步是获取配对的独立容量检测结果，并在冻结方案后开展新车辆验证。网页、碳和路径模块作为后续应用框架，不替代专业检测与真实处置判断。谢谢老师。']
    for text in speech:p(text)
    page();h('最可能被追问的问题')
    qa=[
        ('你们自己的贡献是什么','我们对同一队列设置2、5、10分钟观测，增加同时间公式与中位数参照，同时分析可计算比例、车辆差异和误差。贡献是具体实验和发现；算法、公式与公开数据保留原作者来源。'),
        ('为什么不直接用公式','这正是V4补做的对照。不能预设机器学习更好，我们报告两者在同一片段上的误差，以及公式无法计算或SOC增量不足的比例。'),
        ('公式和标签使用同样的电流SOC，是否循环论证','两者属于同源信号：前缀公式与全段标签数学结构相同。因此这个比较只说明对全段容量代理的提前近似能力，不能证明真实容量或健康度识别。'),
        ('是不是已经排除所有数据泄漏','已检查前缀不读未来、车辆集合不交叉、预处理只拟合训练数据。但整个有效片段队列是按完整记录筛选的，并非任意在线短片段；标签独立性仍未解决。'),
        ('为什么没有拿这些数据预测真实SOH','缺少与记录相匹配的独立容量检测和参考容量。除以额定容量不能消除代理标签的测量误差，也不自动构成真实SOH验证。'),
        ('新模型一定比旧模型好了吗','不一定。新对照的价值是检验旧结论是否充分；结果不改善同样要报告，不能只留下最好的分数。'),
        ('筛掉难样本以后误差下降算不算作弊','如果同时公开阈值如何由验证集确定、保留和拒绝比例、逐车结果，并且不在测试集选阈值，可以作为选择性输出分析；不能只展示筛选后的好分数。'),
        ('自动化测试通过代表什么','V3的12项研究测试与本轮新增检查有各自范围。通过代表设置的程序和产物检查通过，包括指标复算等，不代表模型达到电池安全、真实健康或企业部署标准。'),
        ('能不能决定电池梯次利用还是回收','目前不能。还需要独立容量、内阻、绝缘、安全和真实处置结局等证据。本轮只是容量参考分析及后续应用的基础。'),
        ('学生做了哪些工作，AI有没有帮助','按实际工作说明研究决策、数据整理、模型运行、网页和材料贡献。工具确有辅助，不能掩饰为未经辅助原创；每位成员必须能解释自己负责的结果并复查。')]
    for q,a in qa: doc.add_heading(q,2);p(a)
    h('组员分工与排练')
    p('建议分工，不作为已完成的新贡献：主讲人负责研究问题、标签、实验和局限；原型负责人核对网页版本与研究结果展示边界；材料负责人核对每页图表、讲稿与结果表一致。上台人数与具体时长以本院安排为准。')
    p('第一轮每人用一分钟解释“我们预测什么”。第二轮互相追问“为什么不直接用公式”和“为什么不是SOH”。第三轮对照图表读出样本、单位和结论，不背算法术语。最后计时排练，主讲优先窗口和公平对照，详细消融、学习曲线放问答备查。')
    h('下一阶段最有价值的外部证据')
    p('寻找同一电池、相近时间的BMS记录和独立容量测试。记录匿名电池编号、体系、额定参数、检测日期、温度、充放电条件、测得Ah和附近运行记录。由具备条件的专业机构检测，不把BMS自报容量当作独立测量。少量案例先验证流程，不能包装成大规模外部验证。')
    p('提前冻结模型后再评价新车辆。单纯重排现有20辆车不能变成新的外部盲测。若没有获得新标签，就把贡献限定在短时容量代理的比较和可靠性分析。')
    p('已核对的川农校内公开通知要求20页以内PPT并以PDF提交，半决赛采用5+3。通知来自环境学院公开页；资源学院的时间和具体提交要求仍以本院通知为准。来源：https://hjxy.sicau.edu.cn/info/1013/16303.htm')
    out=ROOT/'07_materials';out.mkdir(parents=True,exist_ok=True)
    doc.save(out/'电循智策_V4组员理解与答辩手册.docx')
    (out/'五分钟答辩稿.txt').write_text('\n\n'.join(speech),encoding='utf-8')
    print('guide generated')


if __name__=='__main__': main()
