"""Build the V4 defense deck from completed experiment files.

Python only reads result tables and creates the presentation specification.
The bundled JavaScript Artifact Tool authors editable slide text and tables.
This file never trains a model, changes the source deck, or invents results.
Run only after the independent experimental review grants the results-ready flag.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
from zipfile import ZipFile
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = Path(os.environ.get("CODEX_ARTIFACT_RUNTIME", "C:/Users/Serein/.cache/codex-runtimes/codex-primary-runtime"))
SKILL = Path(os.environ.get("CODEX_PRESENTATION_SKILL", "C:/Users/Serein/.codex/plugins/cache/openai-primary-runtime/presentations/26.905.11957/skills/presentations"))
LABELS = {"train_mean": "训练均值", "train_median": "训练中位数", "ridge": "Ridge", "random_forest": "随机森林", "hist_gradient_boosting": "直方图梯度提升"}
METHODS = tuple(LABELS)
SOURCES = {
    "data": "https://github.com/BatICM/battery-charging-data-of-on-road-electric-vehicles",
    "paper": "https://doi.org/10.1016/j.apenergy.2023.120954",
    "formula": "https://raw.githubusercontent.com/BatICM/battery-charging-data-of-on-road-electric-vehicles/main/capacity_extract.py",
    "notice": "https://hjxy.sicau.edu.cn/info/1013/16303.htm",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"Empty result file: {path}")
    return rows


def column(row: dict, *names: str) -> str:
    for name in names:
        if name in row:
            return row[name]
    raise KeyError(f"Expected one of {names}; found {list(row)}")


def number(row: dict, *names: str) -> float:
    result = float(column(row, *names))
    if not math.isfinite(result):
        raise ValueError(f"Non-finite value in {names}: {row}")
    return result


def method(row: dict) -> str:
    return column(row, "method", "model", "experiment")


def mae(row: dict) -> float:
    return number(row, "mae_ah", "mae", "MAE")


def window(row: dict) -> int:
    return int(float(column(row, "window_s", "window_seconds", "window")))


def is_true(value: str) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def exact(rows: list[dict], description: str) -> dict:
    if len(rows) != 1:
        raise ValueError(f"{description}: expected one row, got {len(rows)}")
    return rows[0]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(output: Path, private: Path, verification: Path) -> dict:
    metrics = output / "02_metrics"
    required = [metrics / name for name in (
        "all_metrics.csv", "matched_formula_comparison.csv", "quality_coverage.csv",
        "group_cv.csv", "learning_curve.csv",
    )]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Required V4 experiments are missing: " + ", ".join(missing))
    if not verification.is_file():
        raise FileNotFoundError(f"Independent verification record is required: {verification}")
    verification_record = json.loads(verification.read_text(encoding="utf-8-sig"))
    if verification_record.get("passed") is not True:
        raise ValueError("Independent verification has not passed")
    if verification_record.get("models_reloaded") != 15:
        raise ValueError("Independent verification did not reload all 15 V4 models")
    if verification_record.get("all_prediction_ids_unique_and_complete") is not True:
        raise ValueError("Independent prediction-ID completeness verification is missing")
    verified_hashes = verification_record.get("verified_inputs_sha256", {})
    for path in required:
        matches = [value for key, value in verified_hashes.items() if str(key).replace("\\", "/").endswith("02_metrics/" + path.name)]
        if len(matches) != 1 or matches[0] != sha(path):
            raise ValueError(f"Result file does not match the independently verified hash: {path}")
    all_rows = read_csv(required[0])
    main_rows = [r for r in all_rows if column(r, "group") == "primary" and column(r, "split") == "test" and window(r) == 600]
    primary = {m: exact([r for r in main_rows if method(r) == m], "primary " + m) for m in METHODS}
    counts = {(int(number(r, "n", "samples", "n_samples")), int(number(r, "vehicles", "n_vehicles"))) for r in primary.values()}
    if len(counts) != 1:
        raise ValueError("The five main methods do not share the same test cohort")
    test_n, test_vehicles = next(iter(counts))
    best = min(METHODS, key=lambda m: mae(primary[m]))
    rf = primary["random_forest"]
    rf_improvement = (1 - mae(rf) / mae(primary["train_mean"])) * 100
    v3_rows = read_csv(ROOT / "outputs/challenge_cup_v3/02_metrics/model_comparison.csv")
    v3_rf = exact([r for r in v3_rows if method(r) == "random_forest" and r["split"] == "test"], "V3 random forest")
    seed_rows = read_csv(ROOT / "outputs/challenge_cup_v3/02_metrics/seed_results.csv")
    seed_maes = [mae(r) for r in seed_rows]
    formula_rows = read_csv(required[1])
    coverage_rows = read_csv(required[2])
    chosen = [r for r in coverage_rows if is_true(column(r, "selected_on_validation"))]
    if not chosen:
        raise ValueError("No validation-selected quality rule is recorded")
    cv_rows = read_csv(required[3])
    learning_rows = read_csv(required[4])
    rf_windows = {w: exact([r for r in all_rows if r["group"] == "primary" and r["split"] == "test" and window(r) == w and method(r) == "random_forest"], f"RF window {w}") for w in (120, 300, 600)}
    paired = {}
    for w in (120, 300, 600):
        paired[w] = {m: exact([r for r in formula_rows if r["split"] == "test" and window(r) == w and number(r, "threshold") == 1 and method(r) == m], f"matched {w} {m}") for m in ("random_forest", "prefix_formula")}
        if number(paired[w]["random_forest"], "n") != number(paired[w]["prefix_formula"], "n"):
            raise ValueError("Formula and RF have unequal matched sample counts")
    gate = exact([r for r in chosen if r["split"] == "test"], "validation-selected rule on test")
    gate_relative_change = (1 - mae(gate) / mae(rf)) * 100
    window_decreasing = all(mae(rf_windows[a]) >= mae(rf_windows[b]) for a, b in ((120, 300), (300, 600)))
    rf_short_better = mae(paired[120]["random_forest"]) < mae(paired[120]["prefix_formula"])
    formula_long_better = mae(paired[600]["prefix_formula"]) < mae(paired[600]["random_forest"])
    formula_conclusion = "短窗口随机森林更优，10分钟直接公式更优" if rf_short_better and formula_long_better else "方法优势必须连同观察窗口与样本范围报告"
    gate_conclusion = f"保留{number(gate, 'coverage'):.2%}的记录，误差变化很小" if abs(gate_relative_change) < 1 else f"保留{number(gate, 'coverage'):.2%}的记录，MAE为{mae(gate):.4f} Ah"

    # The published V3 counts remain historical facts. Any new extraction must
    # be reconciled before the source-cohort statement is carried into the deck.
    if (test_n, test_vehicles) != (5982, 4):
        raise ValueError("V4 test cohort differs from V3. Update data slide from the discrepancy audit first")

    figure_names = [
        "fig_01_model_comparison.png", "fig_02_window_mae.png", "fig_03_formula_comparison.png",
        "fig_04_coverage_risk.png", "fig_05_ablation.png", "fig_06_condition_strata.png",
        "fig_07_learning_curve.png", "fig_08_error_distribution.png", "fig_09_group_cv.png",
        "fig_10_stress.png", "fig_11_vehicle_errors.png", "fig_12_predictions.png",
    ]
    figures = {name: output / "05_figures/png" / name for name in figure_names}
    for path in figures.values():
        if not path.is_file():
            raise FileNotFoundError(f"Figure missing: {path}")

    slides = []

    def add(title, conclusion, limitation, notes, *, kind="text", figure=None, lines=None, table=None, backup=False):
        item = dict(title=title, conclusion=conclusion, limitation=limitation, notes=notes, kind=kind, backup=backup)
        if figure:
            item["figure"] = str(figures[figure])
        if lines:
            item["lines"] = lines
        if table:
            item["table"] = table
        slides.append(item)

    common_notes = "数据来源：" + SOURCES["data"] + "\n来源论文：" + SOURCES["paper"] + "\n模型与容量代理用于当前公开来源内的探索性研究。"

    add("电循智策", "基于BMS多维运行数据的动力电池健康评估\n与循环利用决策研究", "当前研究：短时充电信息的容量参考预测",
        "各位老师好，我们研究的是：观察一辆车开始充电后的几分钟，能不能给出有依据的容量参考，以及哪些情况需要进一步复核。这里的容量参考根据充电记录计算，真实健康度和实际退役判断还需要独立检测。\n" + common_notes,
        kind="cover", lines=["挑战杯校内预选赛研究汇报", "四川农业大学资源学院", "韩沅峰　王曦晨　廖宝桢"])

    add("一个具体的研究问题", "看前几分钟充电信息，能给出多可靠的容量参考？", "缺少独立检测报告时，模型输出需要说明依据与适用条件。",
        "车辆有很多充电记录，但并没有给我们每次充电对应的专业容量报告。因此我们先研究一个能检验的小问题：用前几分钟的信息预测整段记录算出来的容量参考。此次升级进一步问，模型比直接用公式算好多少，以及哪些记录应当提示复核。",
        lines=["运行记录：电压、电流、电量、温度", "研究任务：短时信息预测整段容量参考", "评价问题：误差多大，适合多少记录"])

    add("数据与车辆划分", f"20辆公开商用车，固定测试含{test_n:,}段记录", "同一辆车的片段只属于一个集合，片段数量不等于独立车辆数量。",
        "数据来自原作者公开的20辆商用车。V3重新读取约1610万行记录，得到29697段符合筛选条件的充电记录。14辆训练、2辆验证、4辆固定测试，同一辆车不跨集合。本轮已经看过旧测试结果，不能称为完全未知的盲测。\n" + common_notes,
        kind="table", table=[["集合", "车辆编号", "车辆数", "充电片段"], ["训练", "1至14", "14", "20,851"], ["验证", "15至16", "2", "2,864"], ["固定测试", "17至20", "4", f"{test_n:,}"], ["总计", "1至20", "20", "29,697"]])

    add("容量参考与比较方法", "公式和模型必须在相同记录上比较", "参考值与输入共享电流和SOC信息，仍需独立实测容量校准。",
        "整段充电电量除以SOC增加比例，得到容量参考。这是原作者已有的计算关系，我们没有发明这个公式。模型只看前120、300或600秒。除了均值和中位数，我们让短窗口公式也参加比较：如果直接计算已经更好，就应该报告它，而不能只和较弱基线比。\n原作者公式：" + SOURCES["formula"],
        kind="table", table=[["方法", "使用的信息", "回答的问题"], ["训练均值 / 中位数", "训练容量参考的统计量", "复杂预测是否有必要"], ["前缀直接公式", "前几分钟电量及SOC变化", "模型是否优于简单计算"], ["Ridge / 随机森林 / 梯度提升", "同一短窗口运行特征", "不同模型带来多少误差差异"]])

    main_description = "；".join(f"{LABELS[m]} {mae(primary[m]):.4f} Ah" for m in METHODS)
    add("五种统计与学习方法", f"本页五种方法中，{LABELS[best]}MAE最低，为{mae(primary[best]):.4f} Ah", "此页未包含直接公式，公式在后页同子集比较，均为容量代理误差。",
        "这一页比较五种方法，测试车辆与记录完全相同。MAE就是平均偏离容量参考多少Ah，越小越好。实际结果为：" + main_description + f"。随机森林相对训练均值的MAE变化为降低{rf_improvement:.2f}%。最低值只是当前比较结果，不据此把测试集当调参集。\n来源：02_metrics/all_metrics.csv，primary、600秒、test。",
        kind="figure", figure="fig_01_model_comparison.png")

    add("观察2分钟5分钟与10分钟", "本次随机森林误差随观察延长而下降" if window_decreasing else "更多观测时间未带来一致改善", "队列经过整段记录筛选，不能直接代表所有在线短时充电。",
        "我们分别只看前2分钟、5分钟和10分钟，重新提取特征并训练。三种窗口使用同一批完整片段。随机森林MAE依次为" + "、".join(f"{mae(rf_windows[w]):.4f}" for w in (120, 300, 600)) + " Ah。这个实验量化多看几分钟带来的变化。完整片段筛选使用了未来记录，所以结果还不能直接作为所有实时短片段的可用率。\n来源：02_metrics/all_metrics.csv，窗口120、300、600秒。",
        kind="figure", figure="fig_02_window_mae.png")

    add("模型与直接公式的公平比较", formula_conclusion, "只在SOC增量达到同一条件的共同记录上比较，并同步报告覆盖率。",
        "公式在短时间内可能因SOC变化太小而不稳定，所以不能拿全部模型样本和少量公式样本直接比较。这里使用SOC增加至少1个百分点的相同子集。" + "。".join(f"{w//60}分钟时，随机森林{mae(paired[w]['random_forest']):.4f} Ah，公式{mae(paired[w]['prefix_formula']):.4f} Ah，共{int(number(paired[w]['prefix_formula'], 'n'))}段，占测试队列{number(paired[w]['prefix_formula'], 'coverage'):.2%}" for w in (120, 300, 600)) + "。这说明必须按时间条件讨论方法优势，不能只和平均值比较就宣称学习模型更好。\n来源：02_metrics/matched_formula_comparison.csv，阈值1个百分点。\n" + SOURCES["formula"],
        kind="figure", figure="fig_03_formula_comparison.png")

    add("覆盖多少记录与误差多少", gate_conclusion, "规则在验证集选择，覆盖率只针对已筛选的完整片段队列。",
        "覆盖率是全部指定记录中保留多少比例，误差是保留记录的预测表现。" + f"验证集选定SOC增量至少{number(gate, 'threshold'):g}个百分点，测试保留{number(gate, 'coverage'):.2%}，排除{int(number(gate, 'n_rejected'))}段。随机森林MAE由{mae(rf):.4f}变为{mae(gate):.4f} Ah。" + "当前变化不能包装成可靠性大幅提升，更不能视为电池安全筛查。规则先在验证集固定，再评价测试集。\n来源：02_metrics/quality_coverage.csv，selected_on_validation。",
        kind="figure", figure="fig_04_coverage_risk.png")

    add("删除信息后的预测变化", "特征贡献由删除后的实际误差检验", "消融反映当前任务依赖，不是因果作用，也不消除标签构造关联。",
        "我们把一组输入去掉后重新训练，看误差怎样变化。这就是特征消融。如果删掉某组信息反而更好，就不能宣传更多特征一定更好。SOC和电流还参与容量参考计算，因此这类依赖不能解释成独立健康规律。\n来源：05_figures/fig_05_ablation.png及对应CSV。",
        kind="figure", figure="fig_05_ablation.png")

    add("更换验证车辆后的表现", "车辆组合差异是模型适用性的关键检查", "车辆分组验证在训练车辆内部进行，不能当作外部车型验证。",
        "我们在训练车辆内部轮换验证车辆，重复五次。每次都把某些车辆完全留给验证。这样检查结果是否依赖某一组车。折间误差如果差异较大，我们就应强调车辆差异，而不是用单次最低误差代表所有车辆。\n来源：02_metrics/group_cv.csv。",
        kind="figure", figure="fig_09_group_cv.png")

    add("研究结果怎样帮助后续应用", "先提供可追溯的容量参考，再安排独立检测", "网页原型与真实SOH、碳收益、退役安全验证分别评价。",
        "目前可以把运行记录、预测参考、数据质量和来源说明整理成报告，帮助研究人员识别需要复核的情况。团队已有网页与前期电芯研究，但本轮指标不能代替它们的独立验证，也不能直接决定电池去回收还是梯次利用。真实处置还需要容量、安全、绝缘等证据。",
        lines=["本轮研究：容量参考、误差、适用条件", "既有原型：结果展示与情景分析框架", "后续验证：实测容量、新来源车辆、真实使用场景"])

    add("阶段结论与下一步", formula_conclusion, "算法和容量计算关系来自既有方法，尚无独立实测SOH与处置效果验证。",
        f"我们的阶段成果，是把公开车辆数据上的短时容量参考预测，推进到更强基线、不同窗口和覆盖率的比较。V3随机森林MAE为{mae(v3_rf):.4f} Ah，本轮同任务随机森林为{mae(rf):.4f} Ah，历史结果保留。" + formula_conclusion + "，所以不能说机器学习始终最好。筛选规则也没有带来大幅误差改善。真正新增的是具体实验问题和可复查发现，下一步最重要的是独立实测容量和新来源车辆。后面为答疑备用图。",
        lines=[f"V3 / V4同任务随机森林MAE　{mae(v3_rf):.4f} / {mae(rf):.4f} Ah", "更强参照改变了对方法优势的判断", "下一步：用专业容量检测检验参考值是否可信"])

    backup_figures = [
        ("不同工况下的误差", "总体平均值需要结合工况分组解释", "分组样本量与车辆构成会影响结果，不把相关差异写成原因。", "fig_06_condition_strata.png", "把记录按温度、SOC或电流条件分组后，检查同一模型在哪些条件下更容易出错。请先看每组有多少记录和几辆车，再解释误差差异。"),
        ("训练车辆数量与预测表现", "增加车辆后的变化要用实际曲线回答", "子集之间并非完全独立，学习曲线不证明扩容后必然提升。", "fig_07_learning_curve.png", "逐步增加用于训练的车辆数量，观察误差如何变化。这个实验用于判断现有数据数量限制，不承诺增加数据一定改善，更不能把同一来源扩容称为跨车型验证。"),
        ("噪声与缺失压力测试", "输入质量变化会影响预测，幅度由实验报告", "扰动发生在特征层，不等同真实传感器故障或持续通信丢包。", "fig_10_stress.png", "给输入增加规定强度的扰动或随机遮掉一部分信息，再看固定模型误差变化。这检查模型对特征质量的敏感性，不是现场设备可靠性认证。"),
        ("绝对误差分布", "误差分布补充平均数看不到的差异", "曲线描述本测试集合，不能给每辆新车作性能承诺。", "fig_08_error_distribution.png", "平均误差会把所有记录混在一起。这张图显示不同误差范围包含多少记录，帮助观察较大误差的尾部。它是总体评价，不是每个预测都拥有的置信区间。"),
        ("每辆测试车的误差", "总体结果不能替代每辆车的结果", "固定测试只有4辆车，不以片段数量夸大独立样本规模。", "fig_11_vehicle_errors.png", "把4辆测试车分别列出，可以看见总体平均是否掩盖某一辆的偏差。车辆样本数不同，所以还需要区分片段加权和车辆等权的指标。"),
        ("预测值与容量参考值", "散点中的偏差展示模型尚未解释的变化", "横轴是计算参考值，不是专业实测容量真值。", "fig_12_predictions.png", "每个点是一段充电记录，越靠近相等参考线，预测越接近计算标签。低值高估或高值低估应当如实解释。图中的目标值仍由充电记录计算，不能称为真实SOH。"),
    ]
    for title, conclusion, limit, figure, notes in backup_figures:
        add(title, conclusion, limit, notes + "\n来源：05_figures/" + figure + "及对应实验CSV。", kind="figure", figure=figure, backup=True)

    add("V3历史重复训练与结果保存", f"三随机种子历史MAE均值为{statistics.mean(seed_maes):.4f} Ah", "历史实验说明V3随机设置敏感性，不替代V4新增协议的验证。",
        f"本页单独保留V3历史记录。三个种子17、42、2026，MAE均值{statistics.mean(seed_maes):.4f} Ah，样本标准差{statistics.stdev(seed_maes):.4f} Ah。V4的新窗口、公式参照和覆盖率试验需要各自保存预测与校验，不能拿历史通过测试代替本轮验证。\n来源：outputs/challenge_cup_v3/02_metrics/seed_results.csv。",
        kind="table", table=[["V3种子", "固定测试MAE / Ah"], *[[r["seed"], f"{mae(r):.4f}"] for r in seed_rows]], backup=True)

    add("来源与学生承担工作", "公开来源、实际分工与研究产物一一对应", "团队未发表论文，不将外部方向指导或AI辅助包装成独立成果。",
        "数据和容量计算参考Deng等2023年论文及原作者公开仓库。韩沅峰推进研究、数据、模型与测试，王曦晨推进网页原型，廖宝桢整合图表和汇报材料。AI辅助需要学生理解、复核并对提交内容负责。所有新数值对应V4结果文件，V3历史结果另行保留。\n" + common_notes + "\n比赛通知：" + SOURCES["notice"] + "。20页及5+3安排来自四川农业大学环境学院公开的校内预选赛通知，团队所属资源学院的正式安排仍需核对。",
        lines=["韩沅峰　研究组织、数据、模型与测试", "王曦晨　网页原型设计与实现", "廖宝桢　成果整合、图表与汇报材料", "数据与方法来源　Deng等，Applied Energy，2023，339，120954"], backup=True)

    if len(slides) > 20:
        raise ValueError(f"Deck exceeds the 20-slide cap: {len(slides)}")
    for index, slide in enumerate(slides, 1):
        slide["index"] = index
        slide["notes"] += "\n讲解顺序：做了什么、为什么做、结果说明什么、仍有什么限制。"

    return {
        "slides": slides,
        "primary": primary,
        "v3_rf": v3_rf,
        "source_hashes": {str(p.relative_to(ROOT)): sha(p) for p in required},
        "verification": {"path": str(verification), "sha256": sha(verification)},
        "source_rows": {"formula": len(formula_rows), "quality": len(coverage_rows), "quality_selected": len(chosen), "cv": len(cv_rows), "learning": len(learning_rows)},
        "sources": SOURCES,
        "output": str(output / "07_materials" / "电循智策_挑战杯研究升级版_V4.pptx"),
        "workspace": str(ROOT), "private": str(private), "skill": str(SKILL),
        "runtime_python": str(RUNTIME / "dependencies/python/python.exe"),
        "artifact_module": str(RUNTIME / "dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs"),
    }


BUILDER = r'''
import fs from "node:fs/promises";
import path from "node:path";
import {pathToFileURL} from "node:url";
const spec=JSON.parse(await fs.readFile(process.argv[2],"utf8"));
const {Presentation,PresentationFile}=await import(pathToFileURL(spec.artifact_module));
const {finalizePresentation}=await import(pathToFileURL(path.join(spec.skill,"container_tools/artifact_tool_utils.mjs")));
const p=Presentation.create({slideSize:{width:1280,height:720}});
const C={navy:"#101C30",blue:"#276CC9",cyan:"#45C9EA",ink:"#192B43",muted:"#51637C",light:"#E8EEF5",white:"#FFFFFF"};
const family="Microsoft YaHei";
const tables=[];
function text(s,t,x,y,w,h,size=27,color=C.ink,bold=false){
 const a=s.shapes.add({geometry:"textbox",name:t.slice(0,42),position:{left:x,top:y,width:w,height:h},fill:"none",line:{fill:"none",width:0}});
 a.text=t;a.text.style={typeface:family,fontSize:size,color,bold,autoFit:"none"};return a;
}
function table(s,rows,y=225){
 const n=rows[0].length;
 const widths=n===4?[260,280,210,370]:n===3?[345,390,385]:[560,560];
 const height=Math.min(340,rows.length*68);
 const a=s.tables.add({rows:rows.length,columns:n,left:80,top:y,width:1120,height,columnWidths:widths,values:rows});
 for(let r=0;r<rows.length;r++)for(let c=0;c<n;c++){
  let cell=a.getCell(r,c);cell.fill=r===0?C.navy:r%2?"#F2F5F9":C.white;
  cell.text.style={typeface:family,fontSize:n===3?24:27,color:r===0?C.white:C.ink,bold:r===0};
 }
 a.borders.assign({fill:"#CED8E5",width:0.5,style:"solid"});tables.push(p.slides.items.indexOf(s)+1);
}
for(const item of spec.slides){
 const s=p.slides.add();s.background.fill=item.kind==="cover"?C.navy:C.white;
 if(item.kind==="cover"){
  text(s,item.lines[0],82,70,1100,45,24,C.cyan);
  text(s,item.title,78,186,1120,120,82,C.white,true);
  text(s,item.conclusion,82,350,1100,135,37,C.white,true);
  text(s,item.limitation,82,531,1100,48,26,C.cyan);
  text(s,item.lines.slice(1).join("　　"),82,630,1100,38,22,"#BACADA");
 }else{
  text(s,item.title,65,item.kind==="figure"?28:40,1150,62,40,C.ink,true);
  text(s,item.conclusion,68,item.kind==="figure"?96:119,1136,item.kind==="figure"?44:68,item.kind==="figure"?26:28,C.blue,true);
  if(item.kind==="figure"){
   s.images.add({blob:new Uint8Array(await fs.readFile(item.figure)),contentType:"image/png",alt:item.title+"：现有机器结果生成的科研图",fit:"contain",position:{left:190,top:146,width:900,height:506.25}});
  }else if(item.kind==="table"){
   table(s,item.table,220);
  }else{
   const lines=item.lines??[];const spacing=lines.length>3?75:102;
   for(let i=0;i<lines.length;i++)text(s,lines[i],80,224+i*spacing,1100,72,lines.length>3?29:32,C.ink,i===0);
  }
  text(s,item.limitation,68,item.kind==="figure"?658:626,1120,item.kind==="figure"?37:51,item.kind==="figure"?19:20,C.muted);
  text(s,(item.backup?"答疑备用　":"")+String(item.index).padStart(2,"0")+" / "+spec.slides.length,1055,687,170,24,15,C.muted);
 }
 s.speakerNotes.textFrame.setText(item.notes);
}
await fs.mkdir(spec.private,{recursive:true});await fs.mkdir(path.dirname(spec.output),{recursive:true});
const candidate=path.join(spec.private,"candidate.pptx");
await(await PresentationFile.exportPptx(p)).save(candidate);
await finalizePresentation({
 workspaceDir:spec.workspace,candidatePath:candidate,finalPath:spec.output,
 explicitTotalSlideCount:spec.slides.length,requiredNativeTableOwnerSlides:tables,requiredNativeChartOwnerSlides:[],
 pythonExecutable:spec.runtime_python,
 integrityValidatorPath:path.join(spec.skill,"container_tools/inspect_presentation_package_integrity.py"),
 layoutValidatorPath:path.join(spec.skill,"container_tools/inspect_presentation_layout_geometry.py"),
 layoutArgs:["--expected-slide-size-emu","12192000,6858000","--validate-heading-fit",...tables.flatMap(n=>["--require-native-table-slide",String(n)])],
 fontPolicy:{basis:"design",families:[family]},verifyArtifactToolImport:true,
 receiptPath:path.join(spec.private,"presentation_validation.json")
});
console.log(JSON.stringify({pptx:spec.output,slides:spec.slides.length,editableTables:tables}));
'''


def export_pdf_and_check(spec: dict) -> None:
    """Use a new read-only PowerPoint instance and keep visual QA private."""
    pptx = Path(spec["output"])
    pdf = pptx.with_suffix(".pdf")
    previews = Path(spec["private"]) / "rendered"
    previews.mkdir(exist_ok=True)
    env = os.environ.copy()
    env["DX_PPT_SOURCE"] = str(pptx)
    env["DX_PPT_PDF"] = str(pdf)
    env["DX_PPT_PREVIEWS"] = str(previews)
    script = r'''
$ErrorActionPreference = 'Stop'
$deckApp = New-Object -ComObject PowerPoint.Application
$deckDoc = $null
try {
    $deckApp.AutomationSecurity = 3
    $deckDoc = $deckApp.Presentations.Open($env:DX_PPT_SOURCE, -1, 0, 0)
    $deckDoc.SaveAs($env:DX_PPT_PDF, 32)
    for ($n = 1; $n -le $deckDoc.Slides.Count; $n++) {
        $imagePath = Join-Path $env:DX_PPT_PREVIEWS ('slide-{0:D2}.png' -f $n)
        $deckDoc.Slides.Item($n).Export($imagePath, 'PNG', 1600, 900)
    }
    Write-Output ('PowerPoint exported ' + $deckDoc.Slides.Count + ' slides')
} finally {
    if ($null -ne $deckDoc) { $deckDoc.Close() }
    $deckApp.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($deckApp) | Out-Null
}
'''
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True, env=env, cwd=ROOT)
    check_export(spec)


def check_export(spec: dict) -> None:
    pptx = Path(spec["output"])
    pdf = pptx.with_suffix(".pdf")
    previews = Path(spec["private"]) / "rendered"
    with ZipFile(pptx) as archive:
        source_titles = []
        for slide in spec["slides"]:
            node = ET.fromstring(archive.read(f"ppt/slides/slide{slide['index']}.xml"))
            text = "".join(node.itertext())
            if slide["title"] not in text:
                raise ValueError(f"Editable title missing on slide {slide['index']}")
            source_titles.append(slide["title"])
        notes_count = sum(name.startswith("ppt/notesSlides/notesSlide") and name.endswith(".xml") for name in archive.namelist())
        if notes_count != len(spec["slides"]):
            raise ValueError(f"Expected one notes page per slide, found {notes_count}")
    if len(list(previews.glob("slide-*.png"))) != len(spec["slides"]):
        raise ValueError("Not every slide has a PowerPoint preview")
    record = {
        "pptx": str(pptx), "pptx_sha256": sha(pptx), "pdf": str(pdf), "pdf_sha256": sha(pdf),
        "slide_count": len(spec["slides"]), "notes_count": notes_count,
        "editable_titles": source_titles, "powerpoint_exported": True,
        "every_slide_visual_review_complete": False,
        "preview_directory": str(previews),
    }
    try:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(str(pdf))
        if len(doc) != len(spec["slides"]):
            raise ValueError("PDF page count differs from PPTX")
        record["pdf_pages"] = len(doc)
        page_texts = []
        for i, page in enumerate(doc):
            textpage = page.get_textpage()
            try:
                page_texts.append(textpage.get_text_range())
            finally:
                textpage.close()
                page.close()
        record["pdf_text_pages"] = page_texts
        doc.close()
    except ImportError:
        record["pdf_text_check"] = "pypdfium2 unavailable; visual review still required"
    (Path(spec["private"]) / "export_check.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/challenge_cup_v4")
    parser.add_argument("--verification", type=Path, required=True)
    parser.add_argument("--results-ready", action="store_true", help="Explicitly acknowledge the independent results review is complete")
    parser.add_argument("--spec-only", action="store_true", help="Validate inputs and write the slide spec without exporting")
    args = parser.parse_args()
    if not args.results_ready:
        parser.error("Wait for independent verification and approval to build, then pass --results-ready")
    private = ROOT / ".v4_presentation_build"
    private.mkdir(exist_ok=True)
    spec = prepare(args.output.resolve(), private, args.verification.resolve())
    spec_path = private / "presentation_spec.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    (private / "build.mjs").write_text(BUILDER, encoding="utf-8")
    if args.spec_only:
        print(json.dumps({"spec": str(spec_path), "slides": len(spec["slides"]), "rendered": False}, ensure_ascii=False))
        return
    node = RUNTIME / "dependencies/node/bin/node.exe"
    runtime_env = os.environ.copy()
    runtime_env.update({"RUNTIME_NODE": str(node), "RUNTIME_NODE_MODULES": str(RUNTIME / "dependencies/node/node_modules"), "RUNTIME_PYTHON": spec["runtime_python"], "SKILL_DIR": str(SKILL)})
    subprocess.run([str(node), str(private / "build.mjs"), str(spec_path)], check=True, cwd=ROOT, env=runtime_env)
    export_pdf_and_check(spec)
    print("PPTX and PDF exported in PowerPoint. Every-slide visual review is still required.")


if __name__ == "__main__":
    main()
