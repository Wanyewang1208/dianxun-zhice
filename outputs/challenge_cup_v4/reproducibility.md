# V4复现说明

请在另一个检出目录和独立环境中复现，避免覆盖已审阅证据。Python 3.12.14；数值环境依赖见08_reproducibility/requirements-v4.lock。随机森林200树、叶节点最少5样本；其余参数与固定实验设计见V4_PROTOCOL.md。V4训练代码和协议SHA保存在run_manifest.json。

在仓库根目录按顺序运行：

```text
python -m research.public_battery.download_ev_source --destination ../public-ev-fixed-source
```

将经过校验的20个RAR解压到独立的../public-ev-csv目录，文件应为#1.csv至#20.csv。脚本不会更改原始CSV；重新读取时核对V3原始校验值。

```text
python -m research.public_battery.windows_v4 --csv-dir ../public-ev-csv
python -m research.public_battery.upgrade_v4
python -m research.public_battery.quality_refresh_v4
python -m research.public_battery.verify_upgrade_v4
python -m unittest discover -s tests -p "test_*.py"
python -m research.public_battery.report_upgrade_v4
python -m research.public_battery.defense_v4
```

阈值刷新步骤只处理SOC增量浮点边界，候选阈值和模型不变。1e-9比较容差避免名义上的2或10个百分点被二进制表示误排除。刷新前CSV仍存于06_verification；报告和图表读取刷新后的结果。不能省略此步骤。

仅从图对应CSV重绘：

```text
python -m research.public_battery.report_upgrade_v4 --regenerate-from-csv --figures-only
```

数字和预测应在所列容差内一致；压缩文件的字节哈希可能随工具、压缩头时间等变化，不能把压缩字节不等自动当成数值不等。

PPT生成器需要Codex演示文稿运行库和Windows PowerPoint导出，普通Python环境不具备这个额外条件。Word用python-docx生成，交付PDF由Microsoft Word导出，所有页面均检查。已提供可直接使用的PPTX、DOCX和PDF。运行库不存在时可直接用CSV/SVG在常规办公软件重排，不影响独立复算。

08_reproducibility/repo_files是相关研究源码快照，保留仓库相对目录；完整执行优先使用GitHub V4分支的全仓库。它不是一个自带Python解释器或全部原始数据的安装包。源数据许可见同目录EV_SOURCE_LICENSE.txt。

没有重训或覆盖网页生产模型；旧模型跨版本兼容警告已单列，网页联调不在本轮研究优先验收范围。
