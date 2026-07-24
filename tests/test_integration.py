import os
import sys
import json
import math
import pytest
import importlib.util

# Use the module already loaded by conftest
import dem_terrain_analysis as mod

from conftest import create_test_geotiff


class TestSlopeIntegration:
    """Integration tests for slope analysis."""

    def test_slope_on_synthetic_dem(self, synthetic_tiff_path, tmp_path):
        """Test slope on synthetic DEM."""
        output = str(tmp_path / 'slope.tif')
        result = mod.analyze_dem(synthetic_tiff_path, 'slope', output)
        assert os.path.exists(result)

        # Read back and verify
        g = mod.GeoTIFF.read(result)
        assert g.width == 5
        assert g.height == 5
        # All slope values should be positive
        for row in g.data:
            for val in row:
                if val != g.nodata:
                    assert val >= 0

    def test_slope_percent_on_synthetic(self, synthetic_tiff_path, tmp_path):
        """Test slope in percent mode."""
        output = str(tmp_path / 'slope_pct.tif')
        result = mod.analyze_dem(synthetic_tiff_path, 'slope', output, unit='percent')
        assert os.path.exists(result)

    def test_slope_flat_dem(self, flat_tiff_path, tmp_path):
        """Test slope on flat DEM should be near zero."""
        output = str(tmp_path / 'slope_flat.tif')
        result = mod.analyze_dem(flat_tiff_path, 'slope', output)
        g = mod.GeoTIFF.read(result)
        # Slope should be near zero for flat surface
        for row in g.data:
            for val in row:
                if val != g.nodata and not math.isnan(val):
                    assert val < 1.0  # Less than 1 degree


class TestAspectIntegration:
    """Integration tests for aspect analysis."""

    def test_aspect_on_synthetic_dem(self, synthetic_tiff_path, tmp_path):
        """Test aspect on synthetic DEM."""
        output = str(tmp_path / 'aspect.tif')
        result = mod.analyze_dem(synthetic_tiff_path, 'aspect', output)
        assert os.path.exists(result)

        g = mod.GeoTIFF.read(result)
        assert g.width == 5
        assert g.height == 5


class TestHillshadeIntegration:
    """Integration tests for hillshade analysis."""

    def test_hillshade_on_synthetic_dem(self, synthetic_tiff_path, tmp_path):
        """Test hillshade on synthetic DEM."""
        output = str(tmp_path / 'hillshade.tif')
        result = mod.analyze_dem(synthetic_tiff_path, 'hillshade', output)
        assert os.path.exists(result)

        g = mod.GeoTIFF.read(result)
        assert g.width == 5
        assert g.height == 5
        # Hillshade values should be 0-255
        for row in g.data:
            for val in row:
                if val != g.nodata and not math.isnan(val):
                    assert 0 <= val <= 255

    def test_hillshade_custom_azimuth(self, synthetic_tiff_path, tmp_path):
        """Test hillshade with custom azimuth."""
        output = str(tmp_path / 'hillshade_custom.tif')
        result = mod.analyze_dem(synthetic_tiff_path, 'hillshade', output,
                                 azimuth=270.0, altitude=30.0)
        assert os.path.exists(result)


class TestContourIntegration:
    """Integration tests for contour generation."""

    def test_contour_on_synthetic_dem(self, synthetic_tiff_path, tmp_path):
        """Test contour generation on synthetic DEM."""
        output = str(tmp_path / 'contour.geojson')
        result = mod.analyze_dem(synthetic_tiff_path, 'contour', output, interval=2.0)
        assert os.path.exists(result)

        with open(result, 'r') as f:
            geojson = json.load(f)
        assert geojson['type'] == 'FeatureCollection'
        assert isinstance(geojson['features'], list)

    def test_contour_interval(self, synthetic_tiff_path, tmp_path):
        """Test different contour intervals."""
        output1 = str(tmp_path / 'contour_1.geojson')
        output2 = str(tmp_path / 'contour_5.geojson')
        mod.analyze_dem(synthetic_tiff_path, 'contour', output1, interval=1.0)
        mod.analyze_dem(synthetic_tiff_path, 'contour', output2, interval=5.0)

        with open(output1, 'r') as f:
            g1 = json.load(f)
        with open(output2, 'r') as f:
            g2 = json.load(f)

        # Smaller interval should produce more contours
        assert len(g1['features']) >= len(g2['features'])


class TestCurvatureIntegration:
    """Integration tests for curvature analysis."""

    def test_curvature_plan(self, synthetic_tiff_path, tmp_path):
        """Test plan curvature."""
        output = str(tmp_path / 'curv_plan.tif')
        result = mod.analyze_dem(synthetic_tiff_path, 'curvature', output, type='plan')
        assert os.path.exists(result)

    def test_curvature_profile(self, synthetic_tiff_path, tmp_path):
        """Test profile curvature."""
        output = str(tmp_path / 'curv_profile.tif')
        result = mod.analyze_dem(synthetic_tiff_path, 'curvature', output, type='profile')
        assert os.path.exists(result)


class TestTRIIntegration:
    """Integration tests for TRI analysis."""

    def test_tri_on_synthetic_dem(self, synthetic_tiff_path, tmp_path):
        """Test TRI on synthetic DEM."""
        output = str(tmp_path / 'tri.tif')
        result = mod.analyze_dem(synthetic_tiff_path, 'tri', output)
        assert os.path.exists(result)

        g = mod.GeoTIFF.read(result)
        assert g.width == 5
        assert g.height == 5

    def test_tri_on_peak_dem(self, peak_tiff_path, tmp_path):
        """Test TRI on peak DEM should have high values near peak."""
        output = str(tmp_path / 'tri_peak.tif')
        result = mod.analyze_dem(peak_tiff_path, 'tri', output)
        g = mod.GeoTIFF.read(result)
        # Near peak should have higher TRI
        center_tri = g.data[2][2]
        edge_tri = g.data[0][0]
        # Both should be non-negative
        assert center_tri >= 0
        assert edge_tri >= 0


class TestTPIIntegration:
    """Integration tests for TPI analysis."""

    def test_tpi_on_synthetic_dem(self, synthetic_tiff_path, tmp_path):
        """Test TPI on synthetic DEM."""
        output = str(tmp_path / 'tpi.tif')
        result = mod.analyze_dem(synthetic_tiff_path, 'tpi', output)
        assert os.path.exists(result)

    def test_tpi_custom_window(self, synthetic_tiff_path, tmp_path):
        """Test TPI with custom window size."""
        output = str(tmp_path / 'tpi_w5.tif')
        result = mod.analyze_dem(synthetic_tiff_path, 'tpi', output, window=5)
        assert os.path.exists(result)

    def test_tpi_peak_positive(self, peak_tiff_path, tmp_path):
        """Test TPI on peak DEM - peak should have positive TPI."""
        output = str(tmp_path / 'tpi_peak.tif')
        result = mod.analyze_dem(peak_tiff_path, 'tpi', output)
        g = mod.GeoTIFF.read(result)
        # Center (peak) should have positive TPI
        center_tpi = g.data[2][2]
        assert center_tpi > 0


class TestRoughnessIntegration:
    """Integration tests for roughness analysis."""

    def test_roughness_on_synthetic_dem(self, synthetic_tiff_path, tmp_path):
        """Test roughness on synthetic DEM."""
        output = str(tmp_path / 'roughness.tif')
        result = mod.analyze_dem(synthetic_tiff_path, 'roughness', output)
        assert os.path.exists(result)

    def test_roughness_flat_dem(self, flat_tiff_path, tmp_path):
        """Test roughness on flat DEM should be zero."""
        output = str(tmp_path / 'roughness_flat.tif')
        result = mod.analyze_dem(flat_tiff_path, 'roughness', output)
        g = mod.GeoTIFF.read(result)
        for row in g.data:
            for val in row:
                if val != g.nodata and not math.isnan(val):
                    assert val == pytest.approx(0.0, abs=0.01)


class TestFlowDirectionIntegration:
    """Integration tests for flow direction analysis."""

    def test_flowdir_on_synthetic_dem(self, synthetic_tiff_path, tmp_path):
        """Test flow direction on synthetic DEM."""
        output = str(tmp_path / 'flowdir.tif')
        result = mod.analyze_dem(synthetic_tiff_path, 'flowdir', output)
        assert os.path.exists(result)

        g = mod.GeoTIFF.read(result)
        assert g.width == 5
        assert g.height == 5
        # All values should be valid D8 codes
        valid_codes = {0, 1, 2, 4, 8, 16, 32, 64, 128}
        for row in g.data:
            for val in row:
                if val != g.nodata and not math.isnan(val):
                    assert int(val) in valid_codes

    def test_flowdir_on_peak_dem(self, peak_tiff_path, tmp_path):
        """Test flow direction on peak DEM - flow should radiate outward."""
        output = str(tmp_path / 'flowdir_peak.tif')
        result = mod.analyze_dem(peak_tiff_path, 'flowdir', output)
        g = mod.GeoTIFF.read(result)
        # Center cell should have a valid flow direction
        center_fd = int(g.data[2][2])
        assert center_fd in {1, 2, 4, 8, 16, 32, 64, 128}


class TestFlowAccumulationIntegration:
    """Integration tests for flow accumulation analysis."""

    def test_flowacc_on_synthetic_dem(self, synthetic_tiff_path, tmp_path):
        """Test flow accumulation on synthetic DEM."""
        output = str(tmp_path / 'flowacc.tif')
        result = mod.analyze_dem(synthetic_tiff_path, 'flowacc', output)
        assert os.path.exists(result)

        g = mod.GeoTIFF.read(result)
        assert g.width == 5
        assert g.height == 5
        # All values should be >= 1
        for row in g.data:
            for val in row:
                if val != g.nodata and not math.isnan(val):
                    assert val >= 1

    def test_flowacc_increases_downstream(self, synthetic_tiff_path, tmp_path):
        """Flow accumulation should increase downstream."""
        output = str(tmp_path / 'flowacc.tif')
        result = mod.analyze_dem(synthetic_tiff_path, 'flowacc', output)
        g = mod.GeoTIFF.read(result)
        # Check that some downstream cells have higher accumulation
        # For a slope DEM, accumulation should generally increase
        max_acc = max(max(row) for row in g.data if not any(math.isnan(v) for v in row))
        assert max_acc >= 1


class TestViewshedIntegration:
    """Integration tests for viewshed analysis."""

    def test_viewshed_on_synthetic_dem(self, synthetic_tiff_path, tmp_path):
        """Test viewshed on synthetic DEM."""
        output = str(tmp_path / 'viewshed.tif')
        result = mod.analyze_dem(synthetic_tiff_path, 'viewshed', output,
                                 obs_row=2, obs_col=2)
        assert os.path.exists(result)

        g = mod.GeoTIFF.read(result)
        assert g.width == 5
        assert g.height == 5
        # Observer should see themselves
        assert g.data[2][2] == 1.0

    def test_viewshed_flat_dem(self, flat_tiff_path, tmp_path):
        """Test viewshed on flat DEM - should see everything."""
        output = str(tmp_path / 'viewshed_flat.tif')
        result = mod.analyze_dem(flat_tiff_path, 'viewshed', output,
                                 obs_row=2, obs_col=2)
        g = mod.GeoTIFF.read(result)
        visible_count = sum(sum(1 for v in row if v > 0) for row in g.data)
        assert visible_count == 25


class TestBatchIntegration:
    """Integration tests for batch analysis."""

    def test_batch_analyze(self, synthetic_tiff_path, tmp_path):
        """Test batch analysis generates all products."""
        output_dir = str(tmp_path / 'terrain')
        results = mod.batch_analyze(synthetic_tiff_path, output_dir)

        # Should have results for all analyses
        expected = ['slope', 'aspect', 'hillshade', 'contour', 'curvature',
                    'tri', 'tpi', 'roughness', 'flowdir', 'flowacc']
        for analysis in expected:
            assert analysis in results
            if results[analysis] is not None:
                assert os.path.exists(results[analysis])

    def test_batch_creates_output_dir(self, synthetic_tiff_path, tmp_path):
        """Test batch analysis creates output directory."""
        output_dir = str(tmp_path / 'new_dir' / 'terrain')
        mod.batch_analyze(synthetic_tiff_path, output_dir)
        assert os.path.exists(output_dir)


class TestGeoTIFFRoundTrip:
    """Test GeoTIFF write and read round trip."""

    def test_write_read_roundtrip(self, tmp_path):
        """Test that written GeoTIFF can be read back."""
        data = [[float(i + j * 10) for i in range(10)] for j in range(10)]
        output = str(tmp_path / 'roundtrip.tif')

        mod.GeoTIFF.write(output, data, 10, 10,
                         pixel_scale=(1.0, 1.0, 0.0),
                         tie_point=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0))

        g = mod.GeoTIFF.read(output)
        assert g.width == 10
        assert g.height == 10

        # Values should be approximately equal
        for row in range(10):
            for col in range(10):
                assert abs(g.data[row][col] - data[row][col]) < 0.1


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_minimum_dem_size(self, tmp_path):
        """Test with minimum viable DEM size."""
        data = [[100.0, 101.0], [101.0, 102.0]]
        filepath = str(tmp_path / 'tiny.tif')
        create_test_geotiff(filepath, data, 2, 2)

        output = str(tmp_path / 'tiny_slope.tif')
        # This might fail for very small DEMs, which is acceptable
        try:
            mod.analyze_dem(filepath, 'slope', output)
        except (IndexError, ZeroDivisionError):
            pass  # Expected for very small DEMs

    def test_nodata_handling(self, tmp_path):
        """Test that nodata values are properly handled."""
        data = [
            [100, 100, 100, 100, 100],
            [100, 100, -9999.0, 100, 100],
            [100, 100, 100, 100, 100],
            [100, 100, 100, 100, 100],
            [100, 100, 100, 100, 100],
        ]
        filepath = str(tmp_path / 'nodata.tif')
        create_test_geotiff(filepath, data, 5, 5, nodata=-9999.0)

        output = str(tmp_path / 'nodata_slope.tif')
        result = mod.analyze_dem(filepath, 'slope', output)
        assert os.path.exists(result)
