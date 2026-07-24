---
name: dem-terrain-analysis
display_name: DEM Terrain Analysis
version: 0.1.0
author: rui.duobao
license: MIT-0
description: |
  DEM地形分析工具 - 从DEM数据生成坡度、坡向、山体阴影、等高线、曲率、流向、汇流等地形产品
  DEM Terrain Analysis - Generate slope, aspect, hillshade, contour, curvature, flow direction, accumulation from DEM data
runtime: python>=3.9
tags:
  - terrain
  - dem
  - gis
  - slope
  - aspect
  - hillshade
  - contour
  - hydrology
  - watershed
  - viewshed
---

# DEM Terrain Analysis

从DEM（数字高程模型）数据派生常见地形产品的纯Python CLI工具。

## 功能特性

- **坡度 (Slope)** - 高程变化率，支持度数和百分比
- **坡向 (Aspect)** - 坡面朝向（北向起算角度）
- **山体阴影 (Hillshade)** - 模拟光照的可视化产品
- **等高线 (Contour)** - 指定间距的等值线（GeoJSON矢量）
- **曲率 (Curvature)** - 平面曲率和剖面曲率
- **地形粗糙度指数 (TRI)** - 相邻像元高程差
- **地形位置指数 (TPI)** - 相对邻域高程
- **粗糙度 (Roughness)** - 邻域最大高程差
- **流向 (Flow Direction)** - D8算法最陡下降方向
- **汇流累积 (Flow Accumulation)** - 上游汇流像元数
- **流域划分 (Watershed)** - 给定出口点划定上游流域
- **视域 (Viewshed)** - 给定观察点的可视区域

## 使用方法

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

# TRI/TPI/粗糙度
python dem-terrain-analysis.py tri input_dem.tif --output tri.tif
python dem-terrain-analysis.py tpi input_dem.tif --output tpi.tif --window 3
python dem-terrain-analysis.py roughness input_dem.tif --output roughness.tif

# 水文分析
python dem-terrain-analysis.py flowdir input_dem.tif --output flowdir.tif
python dem-terrain-analysis.py flowacc input_dem.tif --output flowacc.tif

# 批量生成所有产品
python dem-terrain-analysis.py batch input_dem.tif --output-dir ./terrain/
```

## 算法说明

- **3×3窗口卷积**: 坡度、坡向、山体阴影、曲率使用3×3窗口的Zevenbergen-Thorne算法
- **D8流向**: 计算8个方向的坡度，选择最陡方向作为流向
- **Marching Squares**: 等高线生成使用marching squares算法提取等值线
- **纯Python实现**: 仅使用Python标准库，无外部依赖
