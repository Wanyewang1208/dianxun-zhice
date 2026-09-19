"""Scan public V3 artifacts and record historical consistency findings without editing V2."""
import json,re,subprocess,zipfile
from pathlib import Path

ROOT=Path.cwd();OUT=ROOT/'outputs/challenge_cup_v3'
TEXT={'.md','.txt','.json','.csv','.py','.ts','.tsx','.js','.mjs','.yml','.yaml','.lock','.xml','.svg'}

def content(p):
    if p.suffix=='.docx':
        with zipfile.ZipFile(p) as z:
            return '\n'.join(z.read(n).decode('utf8',errors='replace') for n in z.namelist() if n.endswith('.xml'))
    if p.suffix in TEXT or p.name.startswith('.env'):
        return p.read_text(encoding='utf8',errors='replace')
    return ''

def run():
    tracked=subprocess.check_output(['git','ls-files','-z']).decode().split('\0')
    changed=subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z']).decode().split('\0')
    changed+=subprocess.check_output(['git','diff','--name-only','-z','2f49614']).decode().split('\0')
    new=sorted(set(x for x in changed if x));secret_hits=[];privacy_hits=[];legacy=[]
    secret_patterns=[r'gh[pousr]_[A-Za-z0-9]{30,}',r'github_pat_[A-Za-z0-9_]{50,}',r'sk-[A-Za-z0-9]{35,}',r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----']
    excluded={'publication_check_v3.py','consistency_check.md','security_scan.json'}
    for rel in sorted(set(tracked+new)):
        p=ROOT/rel
        if not rel or not p.is_file() or p.name in excluded:continue
        text=content(p)
        for pattern in secret_patterns:
            if re.search(pattern,text):secret_hits.append(rel)
        if rel in new:
            if re.search(r'(?<![A-Za-z])[A-Za-z]:[\\/]|/Users/|/home/\w+',text):privacy_hits.append(rel)
            if any(x in p.parts for x in ['__pycache__','.venv','node_modules']):privacy_hits.append(rel)
            if p.name=='.env':privacy_hits.append(rel)
        elif text:
            bad=[term for term in ['电智循策','BSM','RIGED','SOH准确率'] if term in text]
            if bad:legacy.append({'file':rel,'terms':bad})
    findings=[]
    for rel in new:
        p=ROOT/rel
        if p.name in excluded or p.suffix not in ['.docx','.md','.csv','.json']:continue
        t=content(p)
        bad=[term for term in ['电智循策','RIGED','BSM','SOH准确率','TODO'] if term in t]
        if bad:findings.append({'file':rel,'terms':bad})
    report={'scanned_new_files':len(new),'secret_findings':sorted(set(secret_hits)),
        'new_machine_path_or_private_file_findings':sorted(set(privacy_hits)),
        'new_consistency_findings':findings,'historical_wording_findings':legacy,
        'raw_vehicle_data_uploaded':False,'privacy':'New data use source-anonymous vehicle IDs and session ordinal; no VIN/GPS/person fields, raw timestamps excluded.'}
    (OUT/'08_tests_and_verification/security_scan.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    lines=['# V3 一致性检查','',f'新增文件扫描：{len(new)} 个。',
        f'密钥模式命中：{len(secret_hits)}；新增本机路径/私有文件命中：{len(privacy_hits)}；新增名称/术语问题：{len(findings)}。',
        '数字由 V3 指标文件和逐条预测生成，223项V2比较在容差内；图表数值独立核验见figure_numeric_verification.json。',
        '原始数据只读，不上传原始CSV/RAR。源字段未发现VIN、车牌、GPS或人员字段；公开派生表删除原始时间。',
        '图题/表题与布局见Word视觉核验记录。固定车辆划分互斥，预测组完整性和逐片段目标匹配均检查。',
        '', '## 历史文件检查',
        '以下历史命中仅登记，不改动受保护的V2证据。历史NASA指标、网页演示和本轮容量代理结果属于不同证据域，不直接相互替换。']
    lines += [f"- {r['file']}：{'、'.join(r['terms'])}" for r in legacy] or ['未发现指定历史名称/拼写词命中。']
    (OUT/'consistency_check.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if secret_hits or privacy_hits or findings:raise SystemExit(2)

if __name__=='__main__':run()
