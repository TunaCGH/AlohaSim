#!/usr/bin/env python3
"""Kiem tra log trace ALOHA. Cach dung: python3 check_trace.py trace/PureAloha_Moderate.log"""
import re, sys, bisect
from decimal import Decimal

T_PS, PROP_PS, ACK_PS = 10**9, 10**7, 15 * 10**8   # T=1ms, prop=10us, ackTimeout=1.5ms (don vi ps)
TOL = 1000                                          # dung sai 1 ns

def ps(s): return int((Decimal(s) * Decimal(10**12)).to_integral_value())
def sec(x): return "%.6f s" % (x / 1e12)
def ms(x): return "%.4f ms" % (x / 1e9)

RE_TX  = re.compile(r"t=(\S+)\s+(host\[\d+\])\s+TX start")
RE_TO  = re.compile(r"t=(\S+)\s+(host\[\d+\])\s+TIMEOUT")
RE_LOST= re.compile(r"packet LOST")
RE_RX  = re.compile(r"t=(\S+)\s+SERVER RX start from (host\[\d+\])")
RE_OK  = re.compile(r"t=(\S+)\s+SERVER SUCCESS (host\[\d+\])")
RE_COL = re.compile(r"t=(\S+)\s+SERVER COLLISION of (\d+) packets")

path = sys.argv[1]
slotted = "Slotted" in path
tx, rx, oks, cols, tos = {}, [], [], [], []
lost = 0
for line in open(path, encoding="utf-8", errors="replace"):
    m = RE_TX.search(line)
    if m: tx.setdefault(m.group(2), []).append(ps(m.group(1))); continue
    m = RE_TO.search(line)
    if m: tos.append((ps(m.group(1)), m.group(2))); continue
    if RE_LOST.search(line): lost += 1; continue
    m = RE_RX.search(line)
    if m: rx.append((ps(m.group(1)), m.group(2))); continue
    m = RE_OK.search(line)
    if m: oks.append((ps(m.group(1)), m.group(2))); continue
    m = RE_COL.search(line)
    if m: cols.append((ps(m.group(1)), int(m.group(2)), len(rx)))

n_tx = sum(len(v) for v in tx.values())
print("File: %s   (%s ALOHA)" % (path, "Slotted" if slotted else "Pure"))
print("TX=%d  server RX=%d  SUCCESS=%d  COLLISION events=%d  TIMEOUT=%d  LOST=%d" %
      (n_tx, len(rx), len(oks), len(cols), len(tos), lost))
if n_tx == 0:
    sys.exit("Khong thay dong 'TX start' -> log rong hoac chua tat express mode.")

def last_tx(h, t):
    lst = tx[h]; i = bisect.bisect_left(lst, t) - 1
    return lst[i] if i >= 0 else None

# Kiem tra 1: thanh cong mat T + prop
bad = 0
for t, h in oks:
    s = last_tx(h, t)
    if s is None or abs((t - s) - (T_PS + PROP_PS)) > TOL: bad += 1
print("[1] TX->SUCCESS = T+prop = 1.010 ms : %d/%d dung" % (len(oks) - bad, len(oks)))

# Kiem tra 2: timeout dung 1.5 ms sau TX
bad = 0
for t, h in tos:
    s = last_tx(h, t)
    if s is None or abs((t - s) - ACK_PS) > TOL: bad += 1
print("[2] TIMEOUT = 1.5 ms sau TX          : %d/%d dung" % (len(tos) - bad, len(tos)))

# Kiem tra 3 (Slotted): moi TX nam tren bien slot
if slotted:
    bad = sum(1 for v in tx.values() for t in v if t % T_PS > TOL and T_PS - t % T_PS > TOL)
    print("[3] Slotted: TX la boi cua 1 ms      : %d/%d dung" % (n_tx - bad, n_tx))

# Kiem tra 4: goi thanh cong khong co goi nao khac trong khoang T truoc/sau
rxt = [x[0] for x in rx]
bad = 0
for t, h in oks:
    r = t - T_PS
    i = bisect.bisect_left(rxt, r - TOL)
    if i > 0 and r - rxt[i - 1] < T_PS - TOL: bad += 1
    if i + 1 < len(rxt) and rxt[i + 1] - r < T_PS - TOL: bad += 1
print("[4] SUCCESS co lap (khoang cach >= T): %d/%d dung" % (len(oks) - bad, len(oks)))

# Kiem tra 5: va cham dung luat
bad = 0
for t, n, cnt in cols:
    grp = [x[0] for x in rx[cnt - n:cnt]]
    gaps = [b - a for a, b in zip(grp, grp[1:])]
    ok = all(g < T_PS for g in gaps) if not slotted else all(g == 0 for g in gaps)
    if not ok: bad += 1
rule = "cung slot (cach nhau = 0)" if slotted else "cac TX ke nhau cach < T"
print("[5] COLLISION: %s : %d/%d dung" % (rule, len(cols) - bad, len(cols)))

# Vi du de dua vao bao cao
print("\n--- VI DU THANH CONG ---")
if oks:
    t, h = oks[len(oks) // 2]
    s = last_tx(h, t)
    print("%s: TX=%s, server nhan=%s, SUCCESS=%s (TX->SUCCESS = %s)" %
          (h, sec(s), sec(s + PROP_PS), sec(t), ms(t - s)))
    if slotted: print("   TX mod 1 ms = %d ps (0 = nam dung bien slot)" % (s % T_PS))

print("\n--- VI DU VA CHAM ---")
if cols:
    pick = next((c for c in cols if c[1] == 2), cols[0])
    t, n, cnt = pick
    print("SERVER ket luan COLLISION luc %s (%d goi):" % (sec(t), n))
    prev = None
    for (rt, h) in rx[cnt - n:cnt]:
        s = rt - PROP_PS
        extra = "" if prev is None else "  (cach TX truoc: %s)" % ms(s - prev)
        print("   %s: TX=%s%s" % (h, sec(s), extra)); prev = s
else:
    print("Khong co va cham trong log nay (thu tang sim-time-limit).")
