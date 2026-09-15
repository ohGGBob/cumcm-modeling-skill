#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze.py — 数模 skill 自带的数据分析 + 可视化工具

三个子命令，全部对真实落盘的数值产物工作，直接落实 SKILL.md 里的
「三层验证 / 离群审计 / 期望量级自检」：

  1) matrix  多管线结果对比：共识区间、离群检测、ECharts 平行坐标 HTML
  2) field   单一结果场可视化：温度/水分的时间序列 + 径向剖面（PNG）
  3) check   期望量级自检：对照 expected.json 打越界

依赖（按需，缺失时给出可读提示而非崩溃）：
  - 必需：Python 3.8+ 标准库
  - matrix/check：无第三方依赖（用 csv）
  - field：pandas + openpyxl + matplotlib（缺失则提示）

用法示例：
  python analyze.py matrix results.csv --out-prefix out/comparison
  python analyze.py field  result1.xlsx --mode temperature --t 100,600,1800 --r 0,0.5,1.0,1.5,2.0
  python analyze.py check  results.csv --expected expected.json
"""
import argparse
import csv
import json
import math
import os
import statistics
import sys

# ---- 输出编码与 Windows 控制台兼容 ----
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# ======================================================================
# 通用：数值列识别 + 离群检测
# ======================================================================

def _to_float(x):
    s = str(x).strip()
    if s in ("", "nan", "NaN", "None", "-", "—", "N/A"):
        return None
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def _median(xs):
    return statistics.median(xs)


def _iqr_outliers(values):
    """返回 (下界, 上界, 离群索引列表)。用稳健的 IQR.*1.5 判据。"""
    xs = sorted(values)
    n = len(xs)
    q1 = xs[int(n * 0.25)]
    q3 = xs[int(n * 0.75)]
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return lo, hi, [i for i, v in enumerate(values) if v < lo or v > hi]


# ======================================================================
# matrix：多管线对比
# ======================================================================

def cmd_matrix(args):
    rows, header = _load_csv(args.csv)
    if len(header) < 2:
        sys.exit("CSV 至少需要两列：第一列=名称，其余=数值指标。")
    metrics = header[1:]
    rows = [r for r in rows if any(cell.strip() for cell in r)]
    names = [r[0].strip() for r in rows]
    ncols = min([len(r) for r in rows] + [len(header)])
    metrics = metrics[: ncols - 1]
    data = {}
    for c, m in enumerate(metrics):
        data[m] = [_to_float(r[c + 1]) if c + 1 < len(r) else None for r in rows]
    # 去掉全空指标列
    metrics = [m for m in metrics if any(v is not None for v in data[m])]

    print(f"== matrix：{len(names)} 条管线 × {len(metrics)} 个指标 ==")
    report = ["# 多管线结果对比", ""]
    report.append(f"- 管线数：{len(names)}　指标数：{len(metrics)}")
    report.append("")

    table = _matrix_result_table(metrics, names, data)
    print(table)
    report.append(table)
    report.append("")

    # 离群汇总
    report.append("## 离群标记（IQR×1.5 判据）")
    report.append("")
    changed = False
    for m in metrics:
        vals = data[m]
        idx = [i for i, v in enumerate(vals) if v is not None]
        if len(idx) < 4:
            continue
        clean = [vals[i] for i in idx]
        lo, hi, bad = _iqr_outliers(clean)
        for b in bad:
            changed = True
            report.append(
                f"- **{m}**：`{names[idx[b]]}` = {clean[b]:.6g} "
                f"（共识区间 [{lo:.4g}, {hi:.4g}] 之外）"
            )
    if not changed:
        report.append("- 无离群（无任何指标落在 IQR×1.5 之外）。")
    report.append("")

    # 共识区间表
    report.append("## 共识区间（中位数 ± 离群剔除后的 min–max）")
    report.append("")
    rep = "| 指标 | n | 中位数 | 共识区间 | 离群管线 |\n|---|---|---|---|---|\n"
    for m in metrics:
        vals = [v for v in data[m] if v is not None]
        if not vals:
            continue
        med = _median(vals)
        lo, hi, bad = _iqr_outliers(vals)
        inliers = [v for i, v in enumerate(vals) if i not in bad]
        inlo, inhi = min(inliers), max(inliers)
        badnames = ", ".join(names[i] for i, v in enumerate(data[m]) if v is not None and (v < lo or v > hi))
        rep += f"| {m} | {len(vals)} | {med:.6g} | [{inlo:.4g}, {inhi:.4g}] | {badnames or '—'} |\n"
    report.append(rep)
    report.append("")

    md = "\n".join(report)
    if args.out_prefix:
        _write_text(args.out_prefix + ".md", md)
        html_path = args.out_prefix + ".html"
        _write_text(html_path, _parallel_chart(metrics, names, data))
        print(f"已写出：{args.out_prefix}.md 与 {args.out_prefix}.html")
    else:
        print(md)


def _load_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = list(csv.reader(f))
    if not reader:
        sys.exit("CSV 为空。")
    header = [h.strip() for h in reader[0]]
    rows = reader[1:]
    return rows, header


def _matrix_result_table(metrics, names, data):
    head = "| 管线 | " + " | ".join(metrics) + " |\n"
    sep = "| --- " * (len(metrics) + 1) + "|\n"
    lines = [head, sep]
    for i, nm in enumerate(names):
        cells = []
        for m in metrics:
            v = data[m][i]
            cells.append(f"{v:.6g}" if v is not None else "—")
        lines.append(f"| {nm} | " + " | ".join(cells) + " |\n")
    return "".join(lines)


def _parallel_chart(metrics, names, data):
    """ECharts 平行坐标图：每条管线一条折线，离群线一眼可见。"""
    series = []
    for i, nm in enumerate(names):
        vals = []
        for m in metrics:
            v = data[m][i]
            vals.append(v if v is not None else "null")
        series.append({"name": nm, "value": vals, "lineStyle": {"width": 1.4}})
    cfg = {
        "parallelAxis": [{"dim": i, "name": m} for i, m in enumerate(metrics)],
        "series": [{
            "type": "parallel", "data": series,
            "parallelAxisId": "a", "lineStyle": {"width": 1.4},
        }],
    }
    return _echarts_html("多管线平行坐标对比", cfg, metrics)


# ======================================================================
# field：单一结果场可视化
# ======================================================================

def cmd_field(args):
    try:
        import pandas as pd
    except ImportError:
        sys.exit("field 需要 pandas，请先 `pip install pandas openpyxl matplotlib`。")

    if args.mode == "both":
        modes = ["temperature", "moisture"]
    else:
        modes = [args.mode]

    frames = {}
    for mode in modes:
        sheet = args.temp_sheet if mode == "temperature" else args.moist_sheet
        df = pd.read_excel(args.xlsx, sheet_name=sheet, header=None)
        df = df.apply(pd.to_numeric, errors="coerce")
        # 约定：首行为距离表头、首列为时间（左上角单元格常为标签，忽略）
        radius = df.iloc[0, 1:].astype(float).tolist()
        time = df.iloc[1:, 0].astype(float).tolist()
        grid = df.iloc[1:, 1:].astype(float)
        frames[mode] = {"radius": radius, "time": time, "grid": grid}

    t_list = [float(x) for x in args.t.split(",")] if args.t else _default_times(frames[modes[0]]["time"])
    r_list = [float(x) for x in args.r.split(",")] if args.r else _default_radius(frames[modes[0]]["radius"])

    # 文本摘要
    print(f"== field：{args.xlsx} ({', '.join(modes)}) ==")
    for mode in modes:
        f = frames[mode]
        print(f"[{mode}] 时间 {len(f['time'])} 步, 半径 {len(f['radius'])} 列")
        for r in r_list:
            ri = _nearest(f["radius"], r)
            if ri < 0:
                continue
            vals = [f["grid"].iloc[_nearest(f["time"], t), ri] for t in t_list]
            vs = "  ".join(f"t={t:g}:{v:.4g}" for t, v in zip(t_list, vals))
            print(f"  r={r:g}cm -> {vs}")
        for t in t_list:
            ti = _nearest(f["time"], t)
            col = f["grid"].iloc[ti]
            print(f"  t={t:g}s -> [min={col.min():.4g}, max={col.max():.4g}]")

    if args.out:
        _plot_fields(frames, modes, t_list, r_list, args.out)
        print(f"已写出 PNG：{args.out}")


def _default_times(time):
    n = len(time)
    # 取 4 个锚点：起点、前 1/3、前 2/3、终点
    return [time[0], time[n // 3], time[2 * n // 3], time[-1]]


def _default_radius(radius):
    return [radius[0], radius[len(radius) // 2], radius[-1]]


def _nearest(xs, target):
    if not xs:
        return -1
    return min(range(len(xs)), key=lambda i: abs(xs[i] - target))


def _plot_fields(frames, modes, t_list, r_list, out):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        sys.exit("field --out 需要 matplotlib，请先 `pip install matplotlib`。")

    n = len(modes)
    figsize = (6 * max(1, len(t_list)), 4.2 * n)
    fig, axes = plt.subplots(n, 1, figsize=figsize, squeeze=False)
    for ax, mode in zip(axes[:, 0], modes):
        f = frames[mode]
        for r in r_list:
            ri = _nearest(f["radius"], r)
            series = [f["grid"].iloc[_nearest(f["time"], t), ri] for t in t_list]
            ax.plot([float(t) for t in t_list], series, marker="o", label=f"r={r:g} cm")
        ax.set_title(mode)
        ax.set_xlabel("time (s)")
        ax.set_ylabel("value")
        ax.legend()
        ax.grid(True)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


# ======================================================================
# check：期望量级自检
# ======================================================================

def cmd_check(args):
    with open(args.expected, encoding="utf-8") as f:
        spec = json.load(f)  # {"指标名": [min, max]} 或 {"指标名": {"min":..,"max":..}}
    rows, header = _load_csv(args.csv)
    metrics = header[1:]
    names = [r[0] for r in rows]
    print(f"== check：对照 {len(spec)} 条期望范围 ==")
    bad = 0
    for m, lo_hi in spec.items():
        if m not in metrics:
            print(f"  ! 指标 `{m}` 不在 CSV 中，跳过")
            continue
        if isinstance(lo_hi, dict):
            lo, hi = lo_hi.get("min"), lo_hi.get("max")
        else:
            lo, hi = lo_hi[0], lo_hi[1]
        col = metrics.index(m)
        for i, nm in enumerate(names):
            v = _to_float(rows[i][1 + col])
            if v is None:
                continue
            if (lo is not None and v < lo) or (hi is not None and v > hi):
                bad += 1
                print(f"  ✗ {m}: `{nm}` = {v:.6g} 越界 [{lo}, {hi}]")
    if bad == 0:
        print("  ✓ 全部指标落在期望范围内。")
    else:
        print(f"  （共 {bad} 处越界）")


# ======================================================================
# ECharts HTML 骨架（自包含，CDN 引用 ECharts）
# ======================================================================

def _echarts_html(title, option, axis_names):
    import json as _json
    payload = _json.dumps(option, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
</head><body style="margin:8px;font-family:sans-serif">
<div id="chart" style="width:100%;height:88vh"></div>
<script>
const option = {payload};
option.parallelAxis = option.parallelAxis.map(a => ({{...a, axisLabel:{{show:true}}, nameTextStyle:{{fontSize:11}}}}));
const chart = echarts.init(document.getElementById('chart'));
chart.setOption(option);
window.addEventListener('resize', () => chart.resize());
</script>
</body></html>
"""


# ======================================================================
# CLI
# ======================================================================

def main(argv=None):
    p = argparse.ArgumentParser(description="数模 skill 数据分析与可视化工具")
    sub = p.add_subparsers(dest="cmd", required=True)

    pm = sub.add_parser("matrix", help="多管线结果对比 + 离群检测 + 平行坐标 HTML")
    pm.add_argument("csv", help="结果矩阵 CSV（首列=名称，其余=数值指标）")
    pm.add_argument("--out-prefix", help="输出前缀，生成 .md 与 .html")

    pf = sub.add_parser("field", help="单一结果场可视化（时间序列 + 剖面）")
    pf.add_argument("xlsx", help="result xlsx（首行=距离表头，首列=时间）")
    pf.add_argument("--mode", default="both", choices=["temperature", "moisture", "both"])
    pf.add_argument("--temp-sheet", default="温度", help="温度工作表名")
    pf.add_argument("--moist-sheet", default="水分浓度", help="水分工作表名")
    pf.add_argument("--t", help="逗号分隔的时间锚点，如 100,600,1800")
    pf.add_argument("--r", help="逗号分隔的半径锚点，如 0,0.5,1.0,1.5,2.0")
    pf.add_argument("--out", help="输出 PNG 路径")

    pc = sub.add_parser("check", help="期望量级自检")
    pc.add_argument("csv")
    pc.add_argument("--expected", required=True, help='JSON：{"指标": [min, max]}')

    args = p.parse_args(argv)
    {"matrix": cmd_matrix, "field": cmd_field, "check": cmd_check}[args.cmd](args)


def _write_text(path, text):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    main()