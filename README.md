# DEM Terrain Analysis

[English](#english) | [中文](#中文)

---

## English

### Introduction

DEM Terrain Analysis is a pure Python CLI tool for generating terrain derivatives from DEM (Digital Elevation Model) data. It processes GeoTIFF files without any external dependencies (no numpy, scipy, GDAL, or rasterio required).

### Features

| Analysis | Description | Output |
|----------|-------------|--------|
| **Slope** | Rate of elevation change | GeoTIFF (degrees or percent) |
| **Aspect** | Direction of slope face | GeoTIFF (degrees from north) |
| **Hillshade** | Simulated illumination | GeoTIFF (0-255) |
| **Contour** | Lines of equal elevation | GeoJSON |
| **Curvature** | Rate of slope change | GeoTIFF (plan/profile) |
| **TRI** | Terrain Ruggedness Index | GeoTIFF |
| **TPI** | Topographic Position Index | GeoTIFF |
| **Roughness** | Max elevation difference | GeoTIFF |
| **Flow Direction** | D8 steepest descent | GeoTIFF |
| **Flow Accumulation** | Upstream cell count | GeoTIFF |
| **Watershed** | Upstream drainage area | GeoTIFF |
| **Viewshed** | Visible area from observer | GeoTIFF |

### Installation

No installation required! Just download and run:

```bash
python dem-terrain-analysis.py --help
```

**Requirements:** Python 3.9+ (standard library only)

### Usage

```bash
# Slope analysis
python dem-terrain-analysis.py slope input_dem.tif --output slope.tif --unit degrees

# Aspect analysis
python dem-terrain-analysis.py aspect input_dem.tif --output aspect.tif

# Hillshade
python dem-terrain-analysis.py hillshade input_dem.tif --output hillshade.tif --azimuth 315 --altitude 45

# Contour lines
python dem-terrain-analysis.py contour input_dem.tif --output contour.geojson --interval 10

# Curvature
python dem-terrain-analysis.py curvature input_dem.tif --output curvature.tif --type plan

# TRI, TPI, Roughness
python dem-terrain-analysis.py tri input_dem.tif --output tri.tif
python dem-terrain-analysis.py tpi input_dem.tif --output tpi.tif --window 3
python dem-terrain-analysis.py roughness input_dem.tif --output roughness.tif

# Hydrology
python dem-terrain-analysis.py flowdir input_dem.tif --output flowdir.tif
python dem-terrain-analysis.py flowacc input_dem.tif --output flowacc.tif

# Batch (all products at once)
python dem-terrain-analysis.py batch input_dem.tif --output-dir ./terrain/
```

### Parameters

| Command | Parameter | Description | Default |
|---------|-----------|-------------|---------|
| `slope` | `--unit` | Output unit: `degrees` or `percent` | `degrees` |
| `hillshade` | `--azimuth` | Sun azimuth (0-360) | `315` |
| `hillshade` | `--altitude` | Sun altitude (0-90) | `45` |
| `contour` | `--interval` | Contour interval (meters) | `10` |
| `curvature` | `--type` | `plan` or `profile` | `plan` |
| `tpi` | `--window` | Neighborhood window size | `3` |
| `viewshed` | `--obs-row` | Observer row index | center |
| `viewshed` | `--obs-col` | Observer column index | center |
| `viewshed` | `--obs-height` | Observer height (m) | `1.7` |
| `viewshed` | `--target-height` | Target height (m) | `0` |

### Algorithm Descriptions

**Slope/Aspect/Hillshade:** Uses Zevenbergen-Thorne 3×3 window convolution method. Computes first derivatives (dz/dx, dz/dy) to determine gradient magnitude and direction.

**D8 Flow Direction:** For each cell, computes slope to all 8 neighbors and assigns flow to the steepest downslope neighbor. Encoded as powers of 2: 1=E, 2=SE, 4=S, 8=SW, 16=W, 32=NW, 64=N, 128=NE.

**Flow Accumulation:** Uses topological sort (BFS) on the flow direction network to efficiently compute upstream drainage area for each cell.

**Contour Lines:** Implements marching squares algorithm to extract isolines at specified elevation intervals.

**TRI (Terrain Ruggedness Index):** Square root of mean squared elevation difference between a cell and its 8 neighbors.

**TPI (Topographic Position Index):** Difference between cell elevation and mean elevation of its neighborhood.

### License

MIT-0 (No Attribution Required)

---

## 中文

### 简介

DEM地形分析是一个纯Python CLI工具，用于从DEM（数字高程模型）数据生成地形衍生产品。它处理GeoTIFF文件，无需任何外部依赖（不需要numpy、scipy、GDAL或rasterio）。

### 功能特性

| 分析类型 | 说明 | 输出格式 |
|---------|------|---------|
| **坡度** | 高程变化率 | GeoTIFF（度数或百分比） |
| **坡向** | 坡面朝向 | GeoTIFF（北向起算角度） |
| **山体阴影** | 模拟光照效果 | GeoTIFF（0-255） |
| **等高线** | 等值线 | GeoJSON |
| **曲率** | 坡度变化率 | GeoTIFF（平面/剖面） |
| **地形粗糙度指数** | 相邻像元高程差 | GeoTIFF |
| **地形位置指数** | 相对邻域高程 | GeoTIFF |
| **粗糙度** | 最大高程差 | GeoTIFF |
| **流向** | D8最陡下降方向 | GeoTIFF |
| **汇流累积** | 上游汇流像元数 | GeoTIFF |
| **流域** | 上游汇水区域 | GeoTIFF |
| **视域** | 观察点可视区域 | GeoTIFF |

### 安装

无需安装！直接下载运行：

```bash
python dem-terrain-analysis.py --help
```

**要求：** Python 3.9+（仅使用标准库）

### 使用方法

```bash
# 坡度分析
python dem-terrain-analysis.py slope input_dem.tif --output slope.tif --unit degrees

# 坡向分析
python dem-terrain-analysis.py aspect input_dem.tif --output aspect.tif

# 山体阴影
python dem-terrain-analysis.py hillshade input_dem.tif --output hillshade.tif --azimuth 315 --altitude 45

# 等高线
python dem-terrain-analysis.py contour input_dem.tif --output contour.geojson --interval 10

# 曲率
python dem-terrain-analysis.py curvature input_dem.tif --output curvature.tif --type plan

# TRI、TPI、粗糙度
python dem-terrain-analysis.py tri input_dem.tif --output tri.tif
python dem-terrain-analysis.py tpi input_dem.tif --output tpi.tif --window 3
python dem-terrain-analysis.py roughness input_dem.tif --output roughness.tif

# 水文分析
python dem-terrain-analysis.py flowdir input_dem.tif --output flowdir.tif
python dem-terrain-analysis.py flowacc input_dem.tif --output flowacc.tif

# 批量生成（一次性生成所有产品）
python dem-terrain-analysis.py batch input_dem.tif --output-dir ./terrain/
```

### 参数说明

| 命令 | 参数 | 说明 | 默认值 |
|------|------|------|--------|
| `slope` | `--unit` | 输出单位：`degrees`（度）或 `percent`（百分比） | `degrees` |
| `hillshade` | `--azimuth` | 太阳方位角（0-360） | `315` |
| `hillshade` | `--altitude` | 太阳高度角（0-90） | `45` |
| `contour` | `--interval` | 等高距（米） | `10` |
| `curvature` | `--type` | `plan`（平面）或 `profile`（剖面） | `plan` |
| `tpi` | `--window` | 邻域窗口大小 | `3` |
| `viewshed` | `--obs-row` | 观察者行索引 | 中心 |
| `viewshed` | `--obs-col` | 观察者列索引 | 中心 |
| `viewshed` | `--obs-height` | 观察者高度（米） | `1.7` |
| `viewshed` | `--target-height` | 目标高度（米） | `0` |

### 算法说明

**坡度/坡向/山体阴影：** 使用Zevenbergen-Thorne 3×3窗口卷积方法。计算一阶导数（dz/dx, dz/dy）来确定梯度大小和方向。

**D8流向：** 对每个像元计算到所有8个邻居的坡度，将流向分配给最陡的下坡邻居。编码为2的幂次：1=东, 2=东南, 4=南, 8=西南, 16=西, 32=西北, 64=北, 128=东北。

**汇流累积：** 使用拓扑排序（BFS）在流向网络上高效计算每个像元的上游汇水面积。

**等高线：** 实现marching squares算法，在指定高程间隔提取等值线。

**TRI（地形粗糙度指数）：** 像元与其8个邻居之间高程差的均方根。

**TPI（地形位置指数）：** 像元高程与其邻域平均高程的差值。

### 许可证

MIT-0（无需署名）
