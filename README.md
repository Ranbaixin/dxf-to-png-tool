# DXF 转 PNG 工具

将 DXF 文件批量转换为高分辨率 PNG 图片，完整保留文字标注、线条、图层颜色。

## 环境要求

- **Python** 3.9 或更高版本
- **Windows** / macOS / Linux

## 安装

```bash
pip install ezdxf matplotlib Pillow
```

## 使用方式

把需要转换的 DXF 文件按以下任一种布局放好，然后把脚本 `dxf_to_png.py` 放到文件夹根目录，运行即可。

### 布局 A：多项目（每个项目有 dxf/ 子目录）

```
我的图纸/
├── dxf_to_png.py          ← 放这里
├── 项目A/
│   ├── dxf/               ← DXF 输入
│   │   └── 零件1.dxf
│   └── images/            ← PNG 输出（自动生成）
│       └── 零件1.png
├── 项目B/
│   ├── dxf/
│   │   └── 零件2.dxf
│   └── images/
│       └── 零件2.png
└── ...
```

### 布局 B：扁平目录（所有 DXF 在一个文件夹）

```
我的图纸/
├── dxf_to_png.py          ← 放这里
├── 零件1.dxf
├── 零件2.dxf
├── ...
└── images/                ← PNG 输出（自动生成）
    ├── 零件1.png
    └── 零件2.png
```

### 运行

```bash
cd 我的图纸
python dxf_to_png.py
```

脚本会自动检测目录结构并选择对应模式。

## 参数调整

编辑 `dxf_to_png.py` 顶部这几个变量：

```python
OUTPUT_DPI = 600           # 输出分辨率，越大越清晰，文件也越大
MAX_FIGURE_INCHES = 20     # 最大画布尺寸（英寸）
```

## 输出规格

| 参数 | 值 |
|------|-----|
| 格式 | PNG（RGBA） |
| 分辨率 | 600 DPI（可调） |
| 背景 | 白色 |
| 文字 | 完整保留 |
| 颜色修正 | 白色→深灰（避免白底白字），青色→蓝色（提高对比度） |

## 常见问题

**Q: 中文字体显示方块或乱码？**

A: 脚本会自动匹配系统可用中文字体（楷体→KaiTi、宋体→SimSun）。如果系统中没有对应字体，安装中文字体包即可。

**Q: 图片模糊？**

A: 调大 `OUTPUT_DPI` 或 `MAX_FIGURE_INCHES`。

**Q: 某些颜色看不见？**

A: 修改 `ACI_REMAP` 字典，添加更多颜色映射。ACI 颜色编号参考 AutoCAD 标准色表。
