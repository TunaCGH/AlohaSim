import csv, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

N = 20
ORDER = ["PureAloha_Low", "PureAloha_Moderate", "PureAloha_High",
         "SlottedAloha_Low", "SlottedAloha_Moderate", "SlottedAloha_High"]
D = {}
for r in csv.DictReader(open("analysis/summary_table.csv")):
    D.setdefault(r["config"], {})[r["metric"]] = (float(r["mean"]), float(r["std"]))

OFFS = {"PureAloha_Low": (8, -14), "SlottedAloha_Low": (-8, 10)}
XL = "Measured offered load G"

def pt(ax, metric, scale=1.0):
    for c in ORDER:
        pure = c.startswith("Pure")
        x, xs = D[c]["G"]; y, ys = D[c][metric]
        ax.errorbar(x, y * scale, xerr=xs, yerr=ys * scale, fmt="o" if pure else "s",
                    color="tab:red" if pure else "tab:blue", capsize=3, markersize=8)
        ax.annotate(c.replace("Aloha_", " "), (x, y * scale), textcoords="offset points",
                    xytext=OFFS.get(c, (6, 6)), fontsize=8)
    ax.set_xlabel(XL); ax.grid(True, alpha=.3)

gs = [i / 100 for i in range(1, 301)]

# Graph 1
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(gs, [g * math.exp(-2 * g) for g in gs], "--", color="tab:red", alpha=.5, label="Pure theory S=G e^(-2G)")
ax.plot(gs, [g * math.exp(-g) for g in gs], "--", color="tab:blue", alpha=.5, label="Slotted theory S=G e^(-G)")
ax.plot(gs, [g * (1 - g / N) ** (2 * (N - 1)) for g in gs if g < N], ":", color="tab:red", label="Pure, N=20 (approx.)")
ax.plot(gs, [g * (1 - g / N) ** (N - 1) for g in gs if g < N], ":", color="tab:blue", label="Slotted, N=20")
pt(ax, "S"); ax.set_ylabel("Normalized throughput S")
ax.set_title("Graph 1: Throughput vs Offered Load"); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig("analysis/graph1_throughput_vs_G.png", dpi=150); plt.close(fig)

# Graph 2 (ms, linear)
fig, ax = plt.subplots(figsize=(8, 5))
ax.axhline(1.010, ls=":", color="tab:red", alpha=.6, label="T + prop = 1.010 ms")
ax.axhline(1.510, ls=":", color="tab:blue", alpha=.6, label="T + prop + T/2 = 1.510 ms")
pt(ax, "meanDelay", 1000); ax.set_ylabel("Mean delay [ms] (successful packets)")
ax.set_ylim(0.9, 1.9); ax.set_title("Graph 2: Average Delay vs Load"); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig("analysis/graph2_delay_vs_G.png", dpi=150); plt.close(fig)

# Graph 3
fig, ax = plt.subplots(figsize=(8, 5))
gg = [i / 100 for i in range(1, 181)]
ax.plot(gg, [1 - math.exp(-2 * g) for g in gg], "--", color="tab:red", alpha=.5, label="Pure theory 1-e^(-2G)")
ax.plot(gg, [1 - math.exp(-g) for g in gg], "--", color="tab:blue", alpha=.5, label="Slotted theory 1-e^(-G)")
OFFS["PureAloha_Low"]=(8,6); OFFS["SlottedAloha_Low"]=(8,-14); OFFS.update({"PureAloha_Low": (8, 6), "SlottedAloha_Low": (8, -14)}); pt(ax, "collisionRatio"); ax.set_ylabel("Collision ratio")
ax.set_title("Graph 3: Collision Ratio vs Load"); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig("analysis/graph3_collision_vs_G.png", dpi=150); plt.close(fig)
print("OK")
