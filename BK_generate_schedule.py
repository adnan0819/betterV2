#!/usr/bin/env python3
"""
Build schedule.json for the pairwise crown-outline rater study.

Usage (from the study_data folder):
    python generate_schedule.py mX        where mX is YOUR method folder, e.g. m3

Design
  - Hub screens: every crop x every baseline vs ours. Each judged twice (pass A and pass B).
  - Baseline-only screens: random crop, random pair of baselines. Judged once.
  - Gold screens: 3 per rater, one broken overlay vs a real overlay of the same crop.
  - Blocks of BLOCK real screens + GOLD_PER_BLOCK gold screens, one block per rater.
The output never says which method is "ours".
"""
import json, os, random, sys
from collections import Counter

SEED = 20261028
BLOCK = 40
GOLD_PER_BLOCK = 3
BASELINE_ONLY = 400
ROOT = os.path.dirname(os.path.abspath(__file__))

if len(sys.argv) != 2 or not sys.argv[1].startswith("m"):
    sys.exit("usage: python generate_schedule.py mX   (your method folder, e.g. m3)")
OURS = sys.argv[1]

random.seed(SEED)

EXTS = (".jpg", ".jpeg", ".png")

def pngs(folder):
    p = os.path.join(ROOT, folder)
    return sorted(os.path.splitext(f)[0] for f in os.listdir(p) if f.lower().endswith(EXTS))

def ext_of(folder):
    p = os.path.join(ROOT, folder)
    exts = {os.path.splitext(f)[1].lower() for f in os.listdir(p) if f.lower().endswith(EXTS)}
    assert len(exts) == 1, f"{folder} mixes extensions: {exts}"
    return exts.pop()

methods = sorted([d for d in os.listdir(ROOT) if d.startswith("m") and d[1:].isdigit()],
                 key=lambda s: int(s[1:]))
assert OURS in methods, f"{OURS} not found among {methods}"
baselines = [m for m in methods if m != OURS]

crops = pngs("raw")
assert crops, "raw/ is empty"
EXT = ext_of("raw")
for m in methods:
    assert ext_of(m) == EXT, f"{m} uses a different extension than raw/"
    missing = set(crops) - set(pngs(m))
    assert not missing, f"{m} is missing {len(missing)} crops, e.g. {sorted(missing)[:3]}"
for kind in ("empty", "shift", "blobs"):
    assert ext_of(os.path.join("gold", kind)) == EXT, f"gold/{kind} uses a different extension than raw/"

gold = []
for kind in ("empty", "shift", "blobs"):
    for c in pngs(os.path.join("gold", kind)):
        assert c in crops, f"gold/{kind}/{c}{EXT} is not one of the raw crops"
        gold.append((kind, c))
assert len(gold) == GOLD_PER_BLOCK, f"expected {GOLD_PER_BLOCK} gold files, found {len(gold)}"

def make(crop, a, b, kind):
    left, right = (a, b) if random.random() < 0.5 else (b, a)
    return {"crop": crop, "left": left, "right": right, "type": kind}

hub = [(c, b) for c in crops for b in baselines]
pass_a = [make(c, OURS, b, "hub") for c, b in hub]
pass_a += [make(random.choice(crops), *random.sample(baselines, 2), "bo") for _ in range(BASELINE_ONLY)]
random.shuffle(pass_a)
pass_b = [make(c, OURS, b, "hub") for c, b in hub]
random.shuffle(pass_b)
screens = pass_a + pass_b
for i, s in enumerate(screens):
    s["id"] = i

blocks = [screens[i:i + BLOCK] for i in range(0, len(screens), BLOCK)]
for blk in blocks:
    for kind, crop in gold:
        real = random.choice(methods)
        g = make(crop, real, f"gold_{kind}", "gold")
        pos = random.randint(3, len(blk))
        blk.insert(pos, g)

out = {"ext": EXT, "block_size": BLOCK, "gold_per_block": GOLD_PER_BLOCK, "n_blocks": len(blocks), "blocks": blocks}
with open(os.path.join(ROOT, "schedule.json"), "w") as f:
    json.dump(out, f, separators=(",", ":"))

# ---- summary ----
real = [s for blk in blocks for s in blk if s["type"] != "gold"]
appear = Counter(); left = Counter(); pair = Counter(); per_crop = Counter()
for s in real:
    appear[s["left"]] += 1; appear[s["right"]] += 1; left[s["left"]] += 1
    pair[tuple(sorted((s["left"], s["right"])))] += 1
    if s["type"] == "hub":
        per_crop[s["crop"]] += 1
print(f"image extension {EXT}")
print(f"crops {len(crops)}  methods {len(methods)}  ours {OURS}  baselines {len(baselines)}")
print(f"hub screens {len(hub)} x2 = {2*len(hub)}, baseline-only {BASELINE_ONLY}, total real {len(real)}")
print(f"blocks (raters) {len(blocks)}, each {BLOCK} real + {GOLD_PER_BLOCK} gold")
print("\nmethod  appearances  on-left")
for m in methods:
    print(f"{m:6}  {appear[m]:11}  {left[m]:7}")
print("\nours vs each baseline (should all be 2 x crops):")
for b in baselines:
    print(f"  {OURS} vs {b}: {pair[tuple(sorted((OURS, b)))]}")
assert all(pair[tuple(sorted((OURS, b)))] == 2 * len(crops) for b in baselines)
assert all(per_crop[c] == 2 * len(baselines) for c in crops)
assert all(s["left"] != s["right"] for s in real)
print("\nall checks passed -> schedule.json written")
