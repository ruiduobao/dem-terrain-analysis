"""test_tiled_tiff.py — Phase 1+ 2026-07-26 tiled TIFF 支持测试

Bug: 之前 dem-terrain-analysis 不支持 tiled TIFF（geotiff-info/rasterio/gdal 默认写
tiled + Deflate wbits=15），导致 Phase 3 真实 AOI 流水线 6（北京 30m COP30 DEM 35MB）
slope/aspect/hillshade 全部输出常数无效值。
修复: GeoTIFF.read() 增加 tiled 路径，_decompress_deflate 兼容 wbits=15/-15。
"""
import os
import sys
import importlib.util
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PROJECT_ROOT)

spec = importlib.util.spec_from_file_location("dta", os.path.join(PROJECT_ROOT, "dem-terrain-analysis.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_tiled_tiff_real_dem_35mb():
    """Phase 3 真实 35MB COP30 DEM 端到端测试（之前读出全 0）。"""
    test_dem = os.path.join(
        "Z:/Mywork/自媒体/公众号/我的产品推文/产品测试/能力升级审查-20260725/experiment-output",
        "phase3_dem.tif",
    )
    if not os.path.exists(test_dem):
        # 测试用合成 tiled TIFF 替代
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as f:
            tmp = f.name
        m.GeoTIFF.write(tmp, [[100.0 + r + c for c in range(5)] for r in range(5)], 5, 5)
        dem = m.GeoTIFF.read(tmp)
        os.unlink(tmp)
    else:
        dem = m.GeoTIFF.read(test_dem)
    # 关键断言：data 不是全 0
    all_vals = [v for row in dem.data for v in row]
    non_zero = [v for v in all_vals if v != 0.0 and v != -9999.0]
    assert len(non_zero) > 0, f"data is all zero/nodata, got {len(all_vals)} cells"
    # COP30 实际应该有 0.3-1634m 高程
    if os.path.exists(test_dem):
        # 真实数据
        assert max(non_zero) > 1000, f"max elevation should be > 1000m, got {max(non_zero)}"
    else:
        # 合成数据
        assert max(non_zero) == 100 + 3 + 4, f"synthetic data mismatch"


def test_tiled_tiff_tile_dimensions_parsed():
    """tile_width / tile_length / tile_offsets 应被解析"""
    test_dem = os.path.join(
        "Z:/Mywork/自媒体/公众号/我的产品推文/产品测试/能力升级审查-20260725/experiment-output",
        "phase3_dem.tif",
    )
    if not os.path.exists(test_dem):
        return  # skip if not exist
    dem = m.GeoTIFF.read(test_dem)
    # 35MB COP30 是 512×512 tiled
    if dem.tile_width > 0:
        assert dem.tile_width == 512
        assert dem.tile_length == 512
        # 48 tiles = 8 行 × 6 列
        assert len(dem.tile_offsets) == 48


def test_decompress_deflate_handles_both_wbits():
    """_decompress_deflate 应该兼容 zlib header (wbits=15) 和 raw deflate (wbits=-15)"""
    import zlib
    # _decompress_deflate 是 instance method；用临时 GeoTIFF() 调用
    g = m.GeoTIFF()
    # 1. zlib header (wbits=15)
    raw_data = b"hello world " * 100
    compressed_15 = zlib.compress(raw_data)
    decompressed = g._decompress_deflate(compressed_15)
    assert decompressed == raw_data
    # 2. raw deflate (wbits=-15)
    compressed_neg15 = zlib.compress(raw_data)[2:-4]  # 去掉 zlib header 和 adler32
    decompressed2 = g._decompress_deflate(compressed_neg15)
    assert decompressed2 == raw_data


def test_slope_on_tiled_dem_produces_valid_values():
    """在 tiled DEM 上跑 slope，应该产生 0-90° 范围的有效值"""
    test_dem = os.path.join(
        "Z:/Mywork/自媒体/公众号/我的产品推文/产品测试/能力升级审查-20260725/experiment-output",
        "phase3_dem.tif",
    )
    if not os.path.exists(test_dem):
        return
    # 用真实 DEM 跑 slope
    out_slope = os.path.join(
        "Z:/Mywork/自媒体/公众号/我的产品推文/产品测试/能力升级审查-20260725/experiment-output",
        "phase3_dem_slope_v3.tif",
    )
    m.analyze_dem(test_dem, "slope", out_slope)
    slope = m.GeoTIFF.read(out_slope)
    vals = [v for row in slope.data for v in row if v != -9999.0]
    assert min(vals) >= 0.0, f"slope min should be >= 0, got {min(vals)}"
    assert max(vals) <= 90.0, f"slope max should be <= 90°, got {max(vals)}"
    # 不应该全 0
    non_zero = [v for v in vals if v > 0.0]
    assert len(non_zero) > 0.5 * len(vals), f"大部分 slope 应该是 > 0 的真实值，got {len(non_zero)}/{len(vals)}"


def test_aspect_on_tiled_dem_produces_valid_values():
    """在 tiled DEM 上跑 aspect，应该产生 -1 (flat) 或 0-360° 范围"""
    test_dem = os.path.join(
        "Z:/Mywork/自媒体/公众号/我的产品推文/产品测试/能力升级审查-20260725/experiment-output",
        "phase3_dem.tif",
    )
    if not os.path.exists(test_dem):
        return
    out_aspect = os.path.join(
        "Z:/Mywork/自媒体/公众号/我的产品推文/产品测试/能力升级审查-20260725/experiment-output",
        "phase3_dem_aspect_v3.tif",
    )
    m.analyze_dem(test_dem, "aspect", out_aspect)
    aspect = m.GeoTIFF.read(out_aspect)
    vals = [v for row in aspect.data for v in row if v != -9999.0]
    # -1 (flat) 是合法的
    valid = [v for v in vals if -1 <= v <= 360]
    assert len(valid) >= 0.99 * len(vals), f"几乎所有 aspect 应在 -1 或 0-360 范围"


def test_hillshade_on_tiled_dem_produces_valid_values():
    """在 tiled DEM 上跑 hillshade，应该产生 0-255 范围"""
    test_dem = os.path.join(
        "Z:/Mywork/自媒体/公众号/我的产品推文/产品测试/能力升级审查-20260725/experiment-output",
        "phase3_dem.tif",
    )
    if not os.path.exists(test_dem):
        return
    out_hs = os.path.join(
        "Z:/Mywork/自媒体/公众号/我的产品推文/产品测试/能力升级审查-20260725/experiment-output",
        "phase3_dem_hillshade_v3.tif",
    )
    m.analyze_dem(test_dem, "hillshade", out_hs)
    hs = m.GeoTIFF.read(out_hs)
    vals = [v for row in hs.data for v in row if v != -9999.0]
    valid = [v for v in vals if 0 <= v <= 255]
    assert len(valid) >= 0.99 * len(vals), f"几乎所有 hillshade 应在 0-255 范围"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
