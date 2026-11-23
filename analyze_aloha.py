#!/usr/bin/env python3
"""
Stage D - ALOHA results analysis.
Usage (run from the AlohaSim project folder):
    python3 analyze_aloha.py results
Needs: matplotlib  (pip install matplotlib)
Outputs go to ./analysis/ : raw_runs.csv, summary_table.csv, graph1/2/3 PNG files.
"""
import csv, glob, math, os, re, statistics, sys
from collections import defaultdict

RESULTS = sys.argv[1] if len(sys.argv) > 1 else "results"
OUT = "analysis"
os.makedirs(OUT, exist_ok=True)

ORDER = ["PureAloha_High", "PureAloha_Moderate", "PureAloha_Low",
         "SlottedAloha_High", "SlottedAloha_Moderate", "SlottedAloha_Low"]
SERVER_KEYS = ["Gnew", "G", "S", "collisionRatio", "meanDelay",
               "rxPackets", "okPackets", "collisionEvents"]
HOST_KEYS = ["generated", "dropped", "attempts", "delivered"]

# ---------- 1. read every .sca ----------
runs = []          # one dict per file
scalar_names_seen = set()
for path in sorted(glob.glob(os.path.join(RESULTS, "*.sca"))):
    m = re.match(r"(.+)-#(\d+)\.sca$", os.path.basename(path))
    if not m:
        continue                       # skips files with other naming (old sweeps)
    cfg, rep = m.group(1), int(m.group(2))
    if cfg not in ORDER:
        continue
    rec = {"config": cfg, "rep": rep, "file": os.path.basename(path)}
    host_sum = defaultdict(float)
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.startswith("scalar "):
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            module, name, value = parts[1], parts[2].strip('"'), parts[-1]
            try:
                v = float(value)
            except ValueError:
                continue
            scalar_names_seen.add(name)
            if module.endswith("server"):
                rec[name] = v
            elif ".host[" in module and name in HOST_KEYS:
                host_sum[name] += v
    for k in HOST_KEYS:
        rec["host_" + k] = host_sum.get(k, float("nan"))
    runs.append(rec)

if not runs:
    sys.exit("Khong tim thay file .sca hop le trong '%s'" % RESULTS)

print("Scalar names found:", sorted(scalar_names_seen))
count = defaultdict(int)
for r in runs:
    count[r["config"]] += 1
for c in ORDER:
    flag = "" if count[c] == 5 else "   <-- KIEM TRA: khong du 5 file"
    print("%-24s %d file%s" % (c, count[c], flag))

# derived metric: attempts per delivered packet (retransmission indicator)
for r in runs:
    d = r.get("host_delivered", float("nan"))
    r["attempts_per_delivered"] = (r["host_attempts"] / d) if d and d == d else float("nan")

METRICS = ["Gnew", "G", "S", "collisionRatio", "meanDelay",
           "attempts_per_delivered", "host_dropped"]

# ---------- 2. raw table ----------
cols = ["config", "rep"] + METRICS + ["rxPackets", "okPackets", "collisionEvents", "file"]
with open(os.path.join(OUT, "raw_runs.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(cols)
    for r in sorted(runs, key=lambda r: (ORDER.index(r["config"]), r["rep"])):
        w.writerow([r.get(c, "") for c in cols])

# ---------- 3. summary (mean / min / max / std over repetitions) ----------
def stats(vals):
    vals = [v for v in vals if v == v]
    if not vals:
        return (float("nan"),) * 4
    sd = statistics.stdev(vals) if len(vals) > 1 else 0.0
    return statistics.mean(vals), min(vals), max(vals), sd

summary = {}
with open(os.path.join(OUT, "summary_table.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["config", "n_runs", "metric", "mean", "min", "max", "std"])
    for c in ORDER:
        rs = [r for r in runs if r["config"] == c]
        summary[c] = {}
        for m_ in METRICS:
            st = stats([r.get(m_, float("nan")) for r in rs])
            summary[c][m_] = st
            w.writerow([c, len(rs), m_] + ["%.6g" % x for x in st])

print("\n=== SUMMARY (mean +- std) ===")
print("%-24s %8s %8s %8s %10s %12s" % ("config", "Gnew", "G", "S", "collRatio", "meanDelay[s]"))
for c in ORDER:
    s = summary[c]
    print("%-24s %8.3f %8.3f %8.3f %10.3f %12.4g" % (
        c, s["Gnew"][0], s["G"][0], s["S"][0], s["collisionRatio"][0], s["meanDelay"][0]))

# ---------- 4. graphs ----------
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    sys.exit("Chua co matplotlib. Chay: pip install matplotlib  roi chay lai script.")

def style(c):
    pure = c.startswith("Pure")
    return ("tab:red" if pure else "tab:blue"), ("o" if pure else "s")

def label(c):
    return c.replace("Aloha_", " ").replace("Pure", "Pure").replace("Slotted", "Slotted")

def point_plot(metric, ylabel, title, fname, theory=False, logy=False):
    fig, ax = plt.subplots(figsize=(8, 5))
    if theory:
        xs = [i / 100 for i in range(1, 301)]
        ax.plot(xs, [g * math.exp(-2 * g) for g in xs], "--", color="tab:red", alpha=.5,
                label="Pure ALOHA theory  S=G e^{-2G}")
        ax.plot(xs, [g * math.exp(-g) for g in xs], "--", color="tab:blue", alpha=.5,
                label="Slotted ALOHA theory  S=G e^{-G}")
    for c in ORDER:
        x, xs_ = summary[c]["G"][0], summary[c]["G"][3]
        y, ys_ = summary[c][metric][0], summary[c][metric][3]
        col, mk = style(c)
        ax.errorbar(x, y, xerr=xs_, yerr=ys_, fmt=mk, color=col, capsize=3, markersize=8)
        ax.annotate(label(c), (x, y), textcoords="offset points", xytext=(6, 6), fontsize=8)
    ax.set_xlabel("Measured offered load G (incl. retransmissions)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    if logy:
        ax.set_yscale("log")
    ax.grid(True, alpha=.3)
    if theory:
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, fname), dpi=150)
    plt.close(fig)

point_plot("S", "Normalized throughput S", "Graph 1: Throughput vs Offered Load",
           "graph1_throughput_vs_G.png", theory=True)
point_plot("meanDelay", "Mean delay [s]", "Graph 2: Average Delay vs Load",
           "graph2_delay_vs_G.png", logy=True)
point_plot("collisionRatio", "Collision ratio", "Graph 3: Collision Ratio vs Load",
           "graph3_collision_vs_G.png")

print("\nXong. Xem thu muc '%s/': raw_runs.csv, summary_table.csv, 3 file graph*.png" % OUT)
