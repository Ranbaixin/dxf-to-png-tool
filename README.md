# DXF to PNG Converter / DXF 转 PNG 工具

将 AutoCAD DXF 文件批量转换为高分辨率 PNG 图片，完美保留所有文字标注、尺寸标号、线条和图层颜色。

Convert AutoCAD DXF files to high-resolution PNG images, preserving all text annotations, line work, and layer colors.

## 特性 / Features

-   **批量转换** — 自动扫描目录，支持 `*/dxf/` 子目录和扁平目录两种布局
-   **高清晰度** — 默认 600 DPI、20 英寸画布，最小文字也能清晰可读
-   **文字完整保留** — 包括 TEXT、MTEXT 实体，支持中文（楷体/宋体/微软雅黑）
-   **智能颜色修正** — 自动将白底不可见的白色文字转为深灰、低对比青色转为蓝色
-   **跨平台** — Windows / macOS / Linux 均可运行
-   **零配置** — 开箱即用，自动检测目录结构

## 环境要求 / Requirements

-   **Python** 3.9+
-   **依赖包**：`ezdxf` `matplotlib` `Pillow`

## 安装 / Installation

```bash
# 克隆仓库
git clone https://github.com/Ranbaixin/dxf-to-png-tool.git
cd dxf-to-png-tool

# 安装依赖
pip install -r requirements.txt
```

> `requirements.txt` 内容：
> ```
> ezdxf>=1.3.0
> matplotlib>=3.7.0
> Pillow>=9.0.0
> ```

## 快速开始 / Quick Start

1.  把 DXF 文件按以下任一种布局放好
2.  把 `dxf_to_png.py` 放到文件夹根目录
3.  运行 `python dxf_to_png.py`

### 布局 A：多项目结构 / Project Sub-directories

每个项目目录下有一个 `dxf/` 文件夹，脚本在 `dxf/` **旁边**生成 `images/`。

```
图纸根目录/
├── dxf_to_png.py            ← 放这里
├── 项目A/
│   ├── dxf/                 ← DXF 输入
│   │   ├── 零件1.dxf
│   │   └── 零件2.dxf
│   └── images/              ← PNG 输出（自动创建）
│       ├── 零件1.png
│       └── 零件2.png
├── 项目B/
│   ├── dxf/
│   │   └── 零件3.dxf
│   └── images/
│       └── 零件3.png
└── ...
```

### 布局 B：扁平结构 / Flat Directory

所有 DXF 直接放在根目录，`images/` 也在根目录下。

```
图纸根目录/
├── dxf_to_png.py            ← 放这里
├── 零件1.dxf
├── 零件2.dxf
├── 零件3.dxf
└── images/                  ← PNG 输出（自动创建）
    ├── 零件1.png
    ├── 零件2.png
    └── 零件3.png
```

脚本运行时会**自动检测**目录结构，无需手动选择模式。

### 作为 Python 库使用 / Use as a Library

```python
from pathlib import Path
from dxf_to_png import convert_dxf_to_png, build_font_map

font_map = build_font_map()
convert_dxf_to_png(
    Path("input.dxf"),
    Path("output.png"),
    font_map,
)
```

## 参数调整 / Configuration

编辑 `dxf_to_png.py` 顶部变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OUTPUT_DPI` | 600 | 输出分辨率。越大越清晰，文件也越大 |
| `MAX_FIGURE_INCHES` | 20 | 最大画布尺寸（英寸）|
| `ACI_REMAP` | `{7: 250, 4: 5}` | ACI 颜色映射（原色号→目标色号） |

### ACI 标准色表 / Standard ACI Colors

| 色号 | 颜色 | 说明 |
|------|------|------|
| 0 | 黑 | 默认已可见 |
| 1 | 红 | 可见 |
| 2 | 黄 | 可见 |
| 3 | 绿 | 可见 |
| 4 | 青 | **默认低对比度 → 映射为蓝** |
| 5 | 蓝 | 可见 |
| 6 | 洋红 | 可见 |
| 7 | 白 | **白底不可见 → 映射为深灰(250)** |

如遇其他颜色在白底上不可见，在 `ACI_REMAP` 字典中添加映射即可。

## 输出规格 / Output Specs

| 参数 | 值 |
|------|-----|
| 格式 | PNG（RGBA） |
| 分辨率 | 600 DPI（约 4200×3000 px） |
| 背景 | 白色 |
| 文字 | TEXT / MTEXT / DIMENSION 全部保留 |
| 字体 | 自动匹配系统字体（楷体→KaiTi、宋体→SimSun） |
| 文件大小 | 约 100–300 KB/张（视图纸复杂度） |

## 常见问题 / FAQ

**Q: 中文字体显示方块或乱码？**

A: 脚本自动映射常用中文字体。如仍有问题，检查系统是否安装了中文字体（SimSun / KaiTi / Microsoft YaHei），或修改 `build_font_map()` 函数中的映射。

**Q: 图片模糊？**

A: 增大 `OUTPUT_DPI`（如 1200）或 `MAX_FIGURE_INCHES`（如 32）。注意文件大小会相应增大。

**Q: 某些颜色在白底上看不见？**

A: 将对应的 ACI 色号添加到 `ACI_REMAP` 字典中。

**Q: 转换速度慢？**

A: 600 DPI 下约 0.5–3 秒/张（取决于 DXF 复杂度和文件大小）。如需更快，可降低 DPI。

**Q: 支持什么版本的 DXF？**

A: 通过 ezdxf 支持 AC1009 (R12) 到 AC1032 (AutoCAD 2018) 的所有版本。实测已覆盖 Tekla Structures 生成的所有版本。

## 项目结构 / Project Structure

```
dxf-to-png-tool/
├── dxf_to_png.py       # 主转换脚本
├── README.md           # 本文档
├── requirements.txt    # Python 依赖
├── .gitignore
└── .gitattributes
```

仓库地址：https://github.com/Ranbaixin/dxf-to-png-tool

## License

MIT

---

**仓库地址**: [https://github.com/Ranbaixin/dxf-to-png-tool](https://github.com/Ranbaixin/dxf-to-png-tool)
