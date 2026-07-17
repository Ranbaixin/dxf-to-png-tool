#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DXF -> PNG Batch Converter  (V1.1)
===================================
给定根目录，自动查找所有 */dxf/*.dxf，在 dxf 同级生成 images/ 并转换。

用法:  修改 ROOT_DIR 后运行:  python dxf_to_png.py
依赖:   pip install ezdxf matplotlib Pillow
"""

import logging
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
ROOT_DIR = Path(r"C:\Users\Ran-xin\Desktop\kuak\new")  # 根目录，按需修改
OUTPUT_DPI = 600               # 输出分辨率
MAX_FIGURE_INCHES = 20         # 最大画布尺寸（英寸）
MAX_PIXELS = 12000             # 单边最大像素，超出自动降 DPI
SKIP_EXISTING = True           # 跳过已存在的 PNG
SAVE_FAILED_LIST = True        # 保存失败文件清单

# ACI 颜色修正：白色(7)在白底不可见→深灰(250)，青色(4)低对比→蓝(5)
ACI_REMAP = {7: 250, 4: 5}

# ---------------------------------------------------------------------------
# 日志
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 清理日志中不需要的模块
# ---------------------------------------------------------------------------
for mod in ["matplotlib.font_manager", "matplotlib", "PIL"]:
    logging.getLogger(mod).setLevel(logging.WARNING)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

try:
    import ezdxf
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    from ezdxf.addons.drawing.config import Configuration, ColorPolicy, BackgroundPolicy
except ImportError as e:
    log.error(f"缺少依赖: {e}")
    log.error("请运行: pip install ezdxf matplotlib Pillow")
    sys.exit(1)


# ===================================================================
# 工具函数
# ===================================================================

def build_font_map():
    """扫描系统字体，建立 DXF 样式→系统字体映射。中文优先用 Microsoft YaHei。"""
    available = {f.name for f in fm.fontManager.ttflist}

    # DXF 样式名 → 首选字体
    mapping = {
        "Arial":    "Arial",      "Standard": "Arial",
        "楷体":     "KaiTi",      "宋体":     "SimSun",
        "romsim":   "SimHei",
    }
    # 中文 fallback 链
    chinese_fb = ["Microsoft YaHei", "SimHei", "KaiTi", "SimSun"]
    # 通用 fallback
    generic_fb = ["Arial", "sans-serif"]

    resolved = {}
    for dxf_style, preferred in mapping.items():
        if preferred in available:
            resolved[dxf_style] = preferred
        else:
            for fb in chinese_fb + generic_fb:
                if fb in available:
                    resolved[dxf_style] = fb
                    break
            else:
                resolved[dxf_style] = "sans-serif"

    log.info("字体映射:")
    for k, v in resolved.items():
        log.info(f"  {k} -> {v}")
    return resolved


def safe_read_dxf(path: Path):
    """
    安全读取 DXF，损坏/空文件/编码问题不崩，返回 None。
    发现 DXF 有异常结构时自动尝试不同编码。
    """
    if path.stat().st_size == 0:
        log.warning(f"  空文件，跳过: {path.name}")
        return None

    for encoding in [None, "utf-8", "gb2312", "gbk", "latin-1"]:
        try:
            return ezdxf.readfile(str(path))
        except UnicodeDecodeError:
            continue
        except ezdxf.DXFStructureError as e:
            log.warning(f"  DXF 结构错误: {path.name} ({e})")
            return None
        except IOError as e:
            log.warning(f"  无法读取文件: {path.name} ({e})")
            return None
        except Exception as e:
            # 其他未知错误，换编码再试一次
            continue
    log.warning(f"  无法解码 DXF: {path.name}")
    return None


def _remap_colors(entity):
    """递归修正 ACI 颜色，白底白字→深灰、青色→蓝色。"""
    if entity.dxf.hasattr("color") and 0 <= entity.dxf.color <= 256:
        if entity.dxf.color in ACI_REMAP:
            entity.dxf.color = ACI_REMAP[entity.dxf.color]
    if entity.dxftype() == "INSERT" and hasattr(entity, "attribs"):
        try:
            for a in entity.attribs():
                _remap_colors(a)
        except Exception:
            pass


def fix_document_colors(doc):
    """对文档所有块和模型空间的实体做颜色修正。"""
    for blk in doc.blocks:
        for e in blk:
            _remap_colors(e)
    for e in doc.modelspace():
        _remap_colors(e)


# ===================================================================
# 目录扫描
# ===================================================================

def find_project_dirs(root: Path):
    """
    扫描根目录，返回 [(项目名, dxf目录, images目录), ...]。
    跳过无 dxf/ 子目录的项目。
    """
    projects = []
    for item in sorted(root.iterdir()):
        if not item.is_dir():
            continue
        dxf_dir = item / "dxf"
        if dxf_dir.exists() and dxf_dir.is_dir():
            img_dir = item / "images"
            projects.append((item.name, dxf_dir, img_dir))
    return projects


def collect_dxf_files(dxf_dir: Path):
    """
    收集 dxf 目录下所有 .dxf 文件，排除临时文件。
    """
    files = []
    for f in sorted(dxf_dir.glob("*.dxf")):
        if f.stat().st_size == 0:
            log.warning(f"  跳过空文件: {f.name}")
            continue
        if f.name.startswith("~$") or f.name.endswith(".bak"):
            continue
        files.append(f)
    return files


# ===================================================================
# 单文件转换
# ===================================================================

def convert_dxf_to_png(dxf_path: Path, png_path: Path, font_map: dict):
    """将单个 DXF 渲染为 PNG。返回 True 成功，异常直接抛出交给外层处理。"""
    doc = safe_read_dxf(dxf_path)
    if doc is None:
        raise ValueError("无法读取 DXF 文件")

    # 空图纸检测
    msp = doc.modelspace()
    if len(msp) == 0 and len(doc.blocks) <= 2:  # 只有默认块
        raise ValueError("DXF 无实体内容（空图纸）")

    # 颜色修正
    fix_document_colors(doc)

    config = Configuration(
        color_policy=ColorPolicy.COLOR,
        background_policy=BackgroundPolicy.WHITE,
    )

    # 获取图纸范围
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

    # 自适应 DPI：防止超大图爆内存
    dpi = OUTPUT_DPI
    if w * dpi / MAX_FIGURE_INCHES > MAX_PIXELS:
        dpi = int(MAX_PIXELS * MAX_FIGURE_INCHES / w)
        log.info(f"  DPI 自适应: {OUTPUT_DPI} -> {dpi}")

    # 画布尺寸
    if w > h:
        fw, fh = MAX_FIGURE_INCHES, max(MAX_FIGURE_INCHES * h / w, 2)
    else:
        fh, fw = MAX_FIGURE_INCHES, max(MAX_FIGURE_INCHES * w / h, 2)

    # 渲染
    fig = None
    try:
        fig = plt.figure(figsize=(fw, fh))
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(xs[0], xs[1])
        ax.set_ylim(ys[0], ys[1])
        ax.set_aspect("equal")
        ax.axis("off")

        ctx = RenderContext(doc)
        out = MatplotlibBackend(ax)
        Frontend(ctx, out, config=config).draw_layout(msp, finalize=True)

        png_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(str(png_path), dpi=dpi, bbox_inches="tight",
                    pad_inches=0.1, facecolor="white", edgecolor="none")
    finally:
        if fig is not None:
            plt.close(fig)
        plt.close("all")


# ===================================================================
# 批量转换
# ===================================================================

def batch_convert(root: Path):
    """主流程：扫描→遍历→转换→报告。单文件失败不影响后续。"""
    log.info(f"根目录: {root}")
    log.info(f"分辨率: {OUTPUT_DPI} DPI, 画布: {MAX_FIGURE_INCHES}\", 跳过已存在: {SKIP_EXISTING}")
    log.info("")

    if not root.exists():
        log.error(f"根目录不存在: {root}")
        return

    font_map = build_font_map()
    log.info("")

    # ACI 修正说明
    names = {0: "黑", 1: "红", 2: "黄", 3: "绿", 4: "青", 5: "蓝",
             6: "洋红", 7: "白", 250: "深灰"}
    log.info("ACI 颜色修正（白底可见性）:")
    for orig, repl in ACI_REMAP.items():
        log.info(f"  {orig:>3} ({names.get(orig, '?')}) -> {repl} ({names.get(repl, '?')})")
    log.info("")

    # 扫描项目
    projects = find_project_dirs(root)
    if not projects:
        log.error("未找到任何包含 dxf/ 目录的项目文件夹！")
        log.error("请确保目录结构为: 项目名/dxf/*.dxf")
        return

    log.info(f"找到 {len(projects)} 个项目文件夹:\n")

    # 统计
    total_files = 0
    success = 0
    failed = []
    skipped = 0
    start_time = time.time()

    for proj_name, dxf_dir, img_dir in projects:
        dxf_files = collect_dxf_files(dxf_dir)
        if not dxf_files:
            log.info(f"  [{proj_name}] 无 DXF 文件，跳过")
            continue

        log.info(f"  [{proj_name}] {len(dxf_files)} 个 DXF")
        img_dir.mkdir(parents=True, exist_ok=True)

        for idx, dxf_path in enumerate(dxf_files, 1):
            total_files += 1
            png_path = img_dir / (dxf_path.stem + ".png")

            # 跳过已存在
            if SKIP_EXISTING and png_path.exists():
                log.info(f"    [{idx}/{len(dxf_files)}] {dxf_path.name} -> SKIP (已存在)")
                skipped += 1
                continue

            try:
                convert_dxf_to_png(dxf_path, png_path, font_map)
                kb = png_path.stat().st_size / 1024
                log.info(f"    [{idx}/{len(dxf_files)}] {dxf_path.name} -> OK ({kb:.0f} KB)")
                success += 1
            except Exception as e:
                log.error(f"    [{idx}/{len(dxf_files)}] {dxf_path.name} -> FAILED: {e}")
                failed.append((str(dxf_path), str(e)))
                plt.close("all")

    # ================================================================
    # 转换报告
    # ================================================================
    elapsed = time.time() - start_time
    log.info("")
    log.info("=" * 50)
    log.info("  转换报告 / Conversion Report")
    log.info("=" * 50)
    log.info(f"  总文件  : {total_files}")
    log.info(f"  成功    : {success}")
    log.info(f"  失败    : {len(failed)}")
    log.info(f"  跳过    : {skipped}")
    log.info(f"  耗时    : {elapsed:.0f}s ({elapsed/60:.1f} min)")
    log.info("=" * 50)

    if failed:
        log.info("")
        log.info("失败文件列表:")
        for path, err in failed:
            log.info(f"  {Path(path).name}: {err[:80]}")

        if SAVE_FAILED_LIST:
            failed_path = root / "failed_files.txt"
            with open(failed_path, "w", encoding="utf-8") as f:
                for path, err in failed:
                    f.write(f"{path}\n  ERROR: {err}\n\n")
            log.info(f"")
            log.info(f"  失败清单已保存: {failed_path}")


# ===================================================================
# 入口
# ===================================================================

def main():
    batch_convert(ROOT_DIR)


if __name__ == "__main__":
    main()
