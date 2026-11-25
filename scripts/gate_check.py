#!/usr/bin/env python3
"""事实核查门禁确定性校验（纯标准库）。

输入：一个 trial 目录，含：
  script.md   旁白稿。每句事实旁白一行，格式：
              [S01 -> C01,C02] 旁白正文……
              非事实句（观点/转场）以 [S02 -> NONFACT] 开头可豁免；# 开头与空行忽略。
  claims.json 或 claims.yaml  证据卡集，结构：
              {"generator": "生成者", "l2_reviewer": "复核者",
               "claims": [{"claim_id": "C01", "verdict": "证实",
                           "l3_decision": ""}, ...]}
              verdict 四态：证实/存疑/证伪/查无（兼容 VERIFIED 等英文，见映射）。
              存疑卡被引用时必须有非空 l3_decision（L3 拍板记录）才放行。
  numbers.csv 数字对账表，表头：数字,脚本值,源值,结论
              结论只许「对上」；任一行「对不上」即 FAIL。
  images.json 或 images.yaml  图片卡，结构：
              {"images": [{"image_id": "IMG-01", "source": "链接或出处",
                            "source_type": "官方/媒体/图库/生成图",
                            "is_generated": false, "label": "",
                            "verdict": "可用"}, ...]}
              生成图 label 必须含「示意图」。

输出：打印 PASS/FAIL 报告并写 gate-report.txt 到输入目录；退出码 0=PASS，1=FAIL。
用法：python3 gate_check.py <trial_dir>
"""
import csv, json, re, sys
from pathlib import Path

VERDICT_MAP = {"证实": "证实", "存疑": "存疑", "证伪": "证伪", "查无": "查无",
               "VERIFIED": "证实", "INCONCLUSIVE": "存疑", "REFUTED": "证伪",
               "NOT_FOUND": "查无", "verified": "证实"}

def parse_simple_yaml(text):
    """极简 YAML 子集解析：顶层标量 + claims:/images: 下的扁平字典列表。仅标准库回退路径，机器校验推荐 JSON。"""
    data, cur_list, cur_item, section = {}, None, None, None
    for raw in text.splitlines():
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        if indent == 0 and line.endswith(":") and ":" not in line[:-1]:
            section = line[:-1].strip(); cur_list = []; data[section] = cur_list; cur_item = None; continue
        if indent == 0 and ":" in line:
            k, v = line.split(":", 1); data[k.strip()] = v.strip().strip('"\''); section = None; continue
        if line.startswith("- ") and cur_list is not None:
            cur_item = {}; cur_list.append(cur_item); line = line[2:]
            if ":" in line:
                k, v = line.split(":", 1); cur_item[k.strip()] = v.strip().strip('"\'')
            continue
        if cur_item is not None and ":" in line and not line.startswith("-"):
            k, v = line.split(":", 1); cur_item[k.strip()] = v.strip().strip('"\'')
    return data

def load_struct(d: Path, stem: str):
    for ext in (".json", ".yaml", ".yml"):
        p = d / (stem + ext)
        if p.exists():
            t = p.read_text(encoding="utf-8")
            return (json.loads(t) if ext == ".json" else parse_simple_yaml(t)), p.name
    return None, None

def norm_num(s: str) -> str:
    return s.replace(",", "").replace("，", "").replace("%", "").replace("％", "").strip()

def main():
    if len(sys.argv) != 2:
        print("用法: gate_check.py <trial_dir>"); return 2
    d = Path(sys.argv[1]); fails, notes = [], []
    if not d.is_dir():
        print(f"FAIL: 目录不存在 {d}"); return 1
    # --- 加载 ---
    sp = d / "script.md"
    if not sp.exists():
        fails.append("缺 script.md"); script_lines = []
    else:
        script_lines = sp.read_text(encoding="utf-8").splitlines()
    claims_data, claims_file = load_struct(d, "claims")
    if claims_data is None:
        fails.append("缺 claims.json/claims.yaml"); claims_data = {}
    images_data, images_file = load_struct(d, "images")
    if images_data is None:
        fails.append("缺 images.json/images.yaml"); images_data = {}
    # --- 证据卡索引 ---
    claims = {}
    for c in claims_data.get("claims", []) or []:
        cid = str(c.get("claim_id") or c.get("id") or "").strip()
        if cid: claims[cid] = c
    def verdict_of(c):
        v = str(c.get("verdict") or c.get("核查结论") or "").strip()
        return VERDICT_MAP.get(v, v)
    # --- 规则6: L2 复核者存在且 != 生成者 ---
    gen = str(claims_data.get("generator") or claims_data.get("生成者") or "").strip()
    rev = str(claims_data.get("l2_reviewer") or claims_data.get("L2复核者") or "").strip()
    if not gen: fails.append("规则6: 生成者字段(generator)缺失")
    if not rev: fails.append("规则6: L2复核者字段(l2_reviewer)缺失，执行者不自审无法核验")
    elif gen and rev == gen: fails.append(f"规则6: L2复核者与生成者相同（{gen}），违反执行者不自审")
    # --- 规则1-3: 逐句回指与卡结论 ---
    ref_re = re.compile(r"^\[(S\d+)\s*->\s*([^\]]+)\]\s*(.*)$")
    script_numbers = []
    for i, raw in enumerate(script_lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"): continue
        m = ref_re.match(line)
        if not m:
            fails.append(f"规则1: script.md 第{i}行无卡号回指: {line[:60]}"); continue
        sid, refs, body = m.group(1), m.group(2).strip(), m.group(3)
        script_numbers += [(sid, n) for n in re.findall(r"\d+(?:\.\d+)?", body.replace(",", ""))]
        if refs.upper() == "NONFACT": continue
        ref_ids = [r.strip() for r in refs.split(",") if r.strip()]
        if not ref_ids:
            fails.append(f"规则1: {sid} 回指为空"); continue
        for cid in ref_ids:
            c = claims.get(cid)
            if c is None:
                fails.append(f"规则1: {sid} 引用不存在的证据卡 {cid}"); continue
            v = verdict_of(c)
            if v in ("查无", "证伪"):
                fails.append(f"规则3: {sid} 引用{ v }卡 {cid}（断言: {str(c.get('claim') or c.get('断言原文') or '')[:50]}）")
            elif v == "存疑":
                l3 = str(c.get("l3_decision") or c.get("L3拍板记录") or "").strip()
                if l3: notes.append(f"{sid}/{cid} 存疑但有 L3 拍板记录，放行")
                else: fails.append(f"规则2: {sid} 引用存疑卡 {cid} 且无 L3 拍板记录(l3_decision)")
            elif v != "证实":
                fails.append(f"规则2: {sid} 引用卡 {cid} 结论异常: '{v or '空'}'")
    # --- 规则4: 数字对账 ---
    ncsv = d / "numbers.csv"
    table_nums = set()
    if not ncsv.exists():
        fails.append("规则4: 缺 numbers.csv 数字对账表")
    else:
        with ncsv.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        for rno, r in enumerate(rows, 2):
            concl = str(r.get("结论") or r.get("conclusion") or "").strip()
            label = str(r.get("数字") or r.get("label") or f"行{rno}").strip()
            for key in ("数字", "脚本值", "script_value"):
                if r.get(key): table_nums.add(norm_num(str(r[key])))
            if concl == "对不上":
                fails.append(f"规则4: 对账表第{rno}行「{label}」结论=对不上")
            elif concl != "对上":
                fails.append(f"规则4: 对账表第{rno}行「{label}」结论不是「对上」: '{concl}'")
    for sid, n in script_numbers:
        if norm_num(n) not in table_nums:
            fails.append(f"规则4: {sid} 中数字 {n} 未入数字对账表")
    # --- 规则5: 图片卡 ---
    imgs = images_data.get("images", []) or []
    if isinstance(images_data, list): imgs = images_data
    for im in imgs:
        iid = str(im.get("image_id") or im.get("id") or "?").strip()
        src = str(im.get("source") or im.get("来源") or "").strip()
        if not src: fails.append(f"规则5: 图片 {iid} 无来源字段(source)")
        v = str(im.get("verdict") or im.get("结论") or "").strip()
        if v != "可用": fails.append(f"规则5: 图片 {iid} 结论不是「可用」: '{v or '空'}'")
        is_gen = im.get("is_generated") in (True, "true", "True", "是") or "生成" in str(im.get("source_type") or "")
        label = str(im.get("label") or im.get("示意标注") or "")
        if is_gen and "示意图" not in label:
            fails.append(f"规则5: 图片 {iid} 为生成图但未标「示意图」")
    # --- 报告 ---
    status = "PASS" if not fails else "FAIL"
    lines = [f"FACT-CHECK GATE: {status}", f"trial_dir: {d}", f"claims_file: {claims_file}, images_file: {images_file}",
             f"generator: {gen or '?'}, l2_reviewer: {rev or '?'}", f"FAIL原因 {len(fails)} 条:"]
    lines += [f"  - {x}" for x in fails] + ([f"备注: {x}" for x in notes] if notes else [])
    report = "\n".join(lines) + "\n"
    print(report, end="")
    (d / "gate-report.txt").write_text(report, encoding="utf-8")
    return 0 if status == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
