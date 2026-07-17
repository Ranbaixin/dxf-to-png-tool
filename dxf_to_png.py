#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DXF -> PNG Batch Converter
==========================
Converts DXF files to high-resolution PNG images, preserving all text
annotations, line work, and layers. Supports two directory layouts.

Usage:
    # Mode A: flat directory (all .dxf in current dir)
    python dxf_to_png.py

    # Mode B: project subdirs (each has a dxf/ folder)
    # Auto-detected when */dxf/*.dxf exists

Dependencies: ezdxf, matplotlib, Pillow
    pip install ezdxf matplotlib Pillow
"""

import os
import sys
import time
from pathlib import Path

# -- silence matplotlib font warnings ---------------------------------
import logging
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, ColorPolicy, BackgroundPolicy

# ---------------------------------------------------------------------------
# Settings you can tweak
# ---------------------------------------------------------------------------
OUTPUT_DPI = 600          # image resolution
MAX_FIGURE_INCHES = 20    # max canvas size (inches)

# ACI color index fixes for white background visibility
#   ACI 7 = white  -> invisible on white bg  -> remap to dark gray
#   ACI 4 = cyan   -> low contrast            -> remap to blue
ACI_REMAP = {7: 250, 4: 5}

# ---------------------------------------------------------------------------
# Font mapping (DXF style name -> system font)
# ---------------------------------------------------------------------------
def build_font_map():
    available = {f.name for f in fm.fontManager.ttflist}

    mapping = {
        "Arial":    "Arial",      "Standard": "Arial",
        "楷体":     "KaiTi",      "宋体":     "SimSun",
        "romsim":   "SimHei",
    }
    fallbacks = ["Microsoft YaHei", "SimHei", "SimSun", "Arial"]

    resolved = {}
    for dxf_style, preferred in mapping.items():
        if preferred in available:
            resolved[dxf_style] = preferred
        else:
            for fb in fallbacks:
                if fb in available:
                    resolved[dxf_style] = fb
                    break
            else:
                resolved[dxf_style] = "sans-serif"

    print("Font mapping:")
    for k, v in resolved.items():
        print(f"  {k} -> {v}")
    return resolved


# ---------------------------------------------------------------------------
# Color fix (ACI 7 white & ACI 4 cyan -> visible on white background)
# ---------------------------------------------------------------------------
def _remap_colors(entity):
    if entity.dxf.hasattr("color") and entity.dxf.color in ACI_REMAP:
        entity.dxf.color = ACI_REMAP[entity.dxf.color]
    if entity.dxftype() == "INSERT" and hasattr(entity, "attribs"):
        try:
            for a in entity.attribs():
                _remap_colors(a)
        except Exception:
            pass


def fix_document_colors(doc):
    for blk in doc.blocks:
        for e in blk:
            _remap_colors(e)
    for e in doc.modelspace():
        _remap_colors(e)


# ---------------------------------------------------------------------------
# Core: single DXF -> PNG
# ---------------------------------------------------------------------------
def convert_dxf_to_png(dxf_path: Path, png_path: Path, font_map: dict):
    doc = ezdxf.readfile(str(dxf_path))
    fix_document_colors(doc)
    msp = doc.modelspace()

    config = Configuration(
        color_policy=ColorPolicy.COLOR,
        background_policy=BackgroundPolicy.WHITE,
    )

    # -- drawing extents --
    xs = ys = []
    try:
        bb = ezdxf.bbox.extents(msp, cache=ezdxf.bbox.Cache())
        if bb.has_data:
            xs, ys = [bb.extmin.x, bb.extmax.x], [bb.extmin.y, bb.extmax.y]
    except Exception:
        pass
    if len(xs) < 2:
        xs = [0, doc.header.get("$EXTMAX", (100, 0, 0))[0]]
        ys = [0, doc.header.get("$EXTMAX", (0, 100, 0))[1]]

    w = max(xs[1] - xs[0], 1)
    h = max(ys[1] - ys[0], 1)

    # -- figure size --
    if w > h:
        fw, fh = MAX_FIGURE_INCHES, MAX_FIGURE_INCHES * h / w
    else:
        fh, fw = MAX_FIGURE_INCHES, MAX_FIGURE_INCHES * w / h
    fh = max(fh, 2)

    # -- render --
    fig = plt.figure(figsize=(fw, fh))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(xs[0], xs[1]); ax.set_ylim(ys[0], ys[1])
    ax.set_aspect("equal"); ax.axis("off")

    ctx = RenderContext(doc)
    out = MatplotlibBackend(ax)
    Frontend(ctx, out, config=config).draw_layout(msp, finalize=True)

    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(png_path), dpi=OUTPUT_DPI, bbox_inches="tight",
                pad_inches=0.1, facecolor="white", edgecolor="none")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Scan directory layout
# ---------------------------------------------------------------------------
def scan_dxf_files(root: Path):
    """
    Detect directory layout and return list of (dxf_path, png_path).
    Layout A: */dxf/*.dxf -> output to */images/*.png  (same level as dxf/)
    Layout B: *.dxf      -> output to images/*.png    (under root)
    """
    subdir_dxf = sorted(root.glob("*/dxf/*.dxf"))
    if subdir_dxf:
        return [(p, p.parent.parent / "images" / (p.stem + ".png")) for p in subdir_dxf], "A"
    flat_dxf = sorted(root.glob("*.dxf"))
    if flat_dxf:
        return [(p, root / "images" / (p.stem + ".png")) for p in flat_dxf], "B"
    return [], "none"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    script_dir = Path(__file__).resolve().parent
    print(f"DXF -> PNG Converter")
    print(f"Working dir : {script_dir}")
    print(f"Resolution  : {OUTPUT_DPI} DPI, {MAX_FIGURE_INCHES}\" max canvas")
    print()

    font_map = build_font_map()
    print()

    print("ACI color fix (white background visibility):")
    names = {0:"BLACK",1:"RED",2:"YELLOW",3:"GREEN",4:"CYAN",5:"BLUE",
             6:"MAGENTA",7:"WHITE",250:"DARK GRAY"}
    for orig, repl in ACI_REMAP.items():
        print(f"  ACI {orig:3d} ({names.get(orig,'?')}) -> ACI {repl:3d} ({names.get(repl,'?')})")
    print()

    files, layout = scan_dxf_files(script_dir)

    if not files:
        print("[ERROR] No DXF files found!")
        print("  Layout A: place */dxf/*.dxf in this folder")
        print("  Layout B: place *.dxf directly in this folder")
        return

    print(f"Layout: {'project sub-directories (dxf/ -> images/)' if layout == 'A' else 'flat directory (images/ under root)'}")
    print(f"Found {len(files)} DXF file(s)\n")

    success, failed, start = 0, [], time.time()

    for i, (dxf_path, png_path) in enumerate(files, 1):
        name = png_path.name
        size_mb = dxf_path.stat().st_size / (1024 * 1024)
        print(f"[{i:4d}/{len(files)}] {name} ({size_mb:.1f} MB)", end=" ... ")
        try:
            convert_dxf_to_png(dxf_path, png_path, font_map)
            kb = png_path.stat().st_size / 1024
            print(f"OK ({kb:.0f} KB)")
            success += 1
        except Exception as e:
            print(f"FAILED: {e}")
            failed.append((str(dxf_path), str(e)))

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"Done: {success}/{len(files)} OK, {len(failed)} failed, {elapsed:.0f}s")
    if failed:
        print("Failures:")
        for p, e in failed:
            print(f"  {p}\n    -> {e}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
