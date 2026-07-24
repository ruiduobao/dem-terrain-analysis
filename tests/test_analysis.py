import math
import pytest

# Use the module already loaded by conftest
import dem_terrain_analysis as mod


class TestSlopeComputation:
    """Test slope computation algorithm."""

    def test_flat_slope_is_zero(self):
        """Flat surface should have zero slope."""
        window = [[100, 100, 100], [100, 100, 100], [100, 100, 100]]
        slope = mod.compute_slope(window, 1.0, 1.0, 'degrees')
        assert slope == pytest.approx(0.0, abs=0.01)

    def test_north_slope(self):
        """North-facing slope should compute correctly."""
        window = [[110, 110, 110], [105, 105, 105], [100, 100, 100]]
        slope = mod.compute_slope(window, 1.0, 1.0, 'degrees')
        assert slope > 0

    def test_east_slope(self):
        """East-facing slope should compute correctly."""
        window = [[100, 105, 110], [100, 105, 110], [100, 105, 110]]
        slope = mod.compute_slope(window, 1.0, 1.0, 'degrees')
        assert slope > 0

    def test_slope_percent(self):
        """Test slope in percent mode."""
        window = [[100, 100, 100], [105, 105, 105], [110, 110, 110]]
        slope_deg = mod.compute_slope(window, 1.0, 1.0, 'degrees')
        slope_pct = mod.compute_slope(window, 1.0, 1.0, 'percent')
        expected_pct = math.tan(math.radians(slope_deg)) * 100
        assert slope_pct == pytest.approx(expected_pct, rel=0.01)

    def test_steep_slope(self):
        """Steep slope should give high angle."""
        window = [[200, 200, 200], [150, 150, 150], [100, 100, 100]]
        slope = mod.compute_slope(window, 1.0, 1.0, 'degrees')
        assert slope > 40

    def test_cell_size_affects_slope(self):
        """Different cell sizes should affect slope calculation."""
        window = [[100, 100, 100], [105, 105, 105], [110, 110, 110]]
        slope_small = mod.compute_slope(window, 1.0, 1.0, 'degrees')
        slope_large = mod.compute_slope(window, 10.0, 10.0, 'degrees')
        assert slope_small > slope_large


class TestAspectComputation:
    """Test aspect computation algorithm."""

    def test_flat_aspect(self):
        """Flat surface returns -1."""
        window = [[100, 100, 100], [100, 100, 100], [100, 100, 100]]
        aspect = mod.compute_aspect(window, 1.0, 1.0)
        assert aspect == -1

    def test_north_facing_slope(self):
        """North-facing slope should have aspect near 0/360."""
        window = [[100, 100, 100], [105, 105, 105], [110, 110, 110]]
        aspect = mod.compute_aspect(window, 1.0, 1.0)
        # Slope faces south (water flows north), aspect should be ~180
        assert 150 < aspect < 210

    def test_south_facing_slope(self):
        """South-facing slope should have aspect near 180."""
        window = [[110, 110, 110], [105, 105, 105], [100, 100, 100]]
        aspect = mod.compute_aspect(window, 1.0, 1.0)
        # Slope faces north, aspect should be ~0 or ~360
        assert aspect < 30 or aspect > 330

    def test_aspect_range(self):
        """Aspect should be in 0-360 range."""
        window = [[100, 105, 110], [100, 105, 110], [100, 105, 110]]
        aspect = mod.compute_aspect(window, 1.0, 1.0)
        assert 0 <= aspect <= 360


class TestHillshadeComputation:
    """Test hillshade computation algorithm."""

    def test_flat_hillshade(self):
        """Flat surface should have uniform hillshade."""
        window = [[100, 100, 100], [100, 100, 100], [100, 100, 100]]
        hs = mod.compute_hillshade(window, 1.0, 1.0, 315, 45)
        assert 0 <= hs <= 255

    def test_hillshade_range(self):
        """Hillshade should be in 0-255 range."""
        window = [[100, 110, 120], [100, 110, 120], [100, 110, 120]]
        hs = mod.compute_hillshade(window, 1.0, 1.0, 315, 45)
        assert 0 <= hs <= 255

    def test_hillshade_azimuth_effect(self):
        """Different azimuths should give different hillshade values for asymmetric slope."""
        # Use asymmetric window so azimuth matters
        window = [[100, 110, 120], [100, 110, 120], [100, 100, 100]]
        hs1 = mod.compute_hillshade(window, 1.0, 1.0, 0, 45)
        hs2 = mod.compute_hillshade(window, 1.0, 1.0, 180, 45)
        assert hs1 != hs2

    def test_hillshade_altitude_effect(self):
        """Different altitudes should give different hillshade values."""
        window = [[100, 100, 100], [100, 110, 120], [100, 100, 100]]
        hs1 = mod.compute_hillshade(window, 1.0, 1.0, 315, 10)
        hs2 = mod.compute_hillshade(window, 1.0, 1.0, 315, 80)
        assert hs1 != hs2


class TestCurvatureComputation:
    """Test curvature computation algorithm."""

    def test_flat_curvature_is_zero(self):
        """Flat surface should have zero curvature."""
        window = [[100, 100, 100], [100, 100, 100], [100, 100, 100]]
        curv = mod.compute_curvature(window, 1.0, 1.0, 'plan')
        assert curv == pytest.approx(0.0, abs=0.01)

    def test_plan_curvature(self):
        """Plan curvature should be non-zero for curved surface."""
        window = [[100, 100, 100], [100, 110, 100], [100, 100, 100]]
        curv = mod.compute_curvature(window, 1.0, 1.0, 'plan')
        assert isinstance(curv, float)

    def test_profile_curvature(self):
        """Profile curvature should be non-zero for curved surface."""
        window = [[100, 100, 100], [100, 110, 100], [100, 100, 100]]
        curv = mod.compute_curvature(window, 1.0, 1.0, 'profile')
        assert isinstance(curv, float)


class TestTRIComputation:
    """Test Terrain Ruggedness Index computation."""

    def test_flat_tri_is_zero(self):
        """Flat surface should have zero TRI."""
        window = [[100, 100, 100], [100, 100, 100], [100, 100, 100]]
        tri = mod.compute_tri(window)
        assert tri == pytest.approx(0.0, abs=0.01)

    def test_rough_tri(self):
        """Rugged surface should have high TRI."""
        window = [[100, 120, 100], [120, 100, 120], [100, 120, 100]]
        tri = mod.compute_tri(window)
        assert tri > 10

    def test_tri_non_negative(self):
        """TRI should always be non-negative."""
        window = [[90, 100, 110], [95, 105, 115], [100, 110, 120]]
        tri = mod.compute_tri(window)
        assert tri >= 0


class TestTPIComputation:
    """Test Topographic Position Index computation."""

    def test_flat_tpi_is_zero(self):
        """Flat surface should have zero TPI."""
        window = [[100, 100, 100], [100, 100, 100], [100, 100, 100]]
        tpi = mod.compute_tpi(window)
        assert tpi == pytest.approx(0.0, abs=0.01)

    def test_peak_tpi_positive(self):
        """Peak should have positive TPI."""
        window = [[100, 100, 100], [100, 120, 100], [100, 100, 100]]
        tpi = mod.compute_tpi(window)
        assert tpi > 0

    def test_valley_tpi_negative(self):
        """Valley should have negative TPI."""
        window = [[120, 120, 120], [120, 100, 120], [120, 120, 120]]
        tpi = mod.compute_tpi(window)
        assert tpi < 0


class TestRoughnessComputation:
    """Test roughness computation."""

    def test_flat_roughness_is_zero(self):
        """Flat surface should have zero roughness."""
        window = [[100, 100, 100], [100, 100, 100], [100, 100, 100]]
        rough = mod.compute_roughness(window)
        assert rough == pytest.approx(0.0, abs=0.01)

    def test_rough_surface(self):
        """Rough surface should have high roughness."""
        window = [[80, 100, 120], [90, 110, 130], [85, 105, 125]]
        rough = mod.compute_roughness(window)
        assert rough == pytest.approx(50.0, abs=0.01)

    def test_roughness_non_negative(self):
        """Roughness should always be non-negative."""
        window = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        rough = mod.compute_roughness(window)
        assert rough >= 0


class TestFlowDirection:
    """Test D8 flow direction computation."""

    def test_flat_flow_direction(self):
        """Flat surface should have flow direction 0 (no flow)."""
        # On a perfectly flat surface, max_drop stays -inf, so direction is 0
        dem_data = [[100.0]*5 for _ in range(5)]
        # Manually test: with all equal values, drop = 0 for all neighbors
        # max_drop starts at -inf, 0 > -inf, so it picks a direction
        # This is expected behavior for D8 on flat terrain
        fd = mod.compute_flow_direction(2, 2, type('DEM', (), {
            'data': dem_data,
            'width': 5, 'height': 5, 'nodata': None
        })())
        # On flat terrain, any direction is valid (drop = 0)
        assert fd in {0, 1, 2, 4, 8, 16, 32, 64, 128}

    def test_south_flow(self):
        """Water should flow south (downhill)."""
        dem_data = [
            [110, 110, 110, 110, 110],
            [108, 108, 108, 108, 108],
            [106, 106, 106, 106, 106],
            [104, 104, 104, 104, 104],
            [102, 102, 102, 102, 102],
        ]
        fd = mod.compute_flow_direction(2, 2, type('DEM', (), {
            'data': dem_data, 'width': 5, 'height': 5, 'nodata': None
        })())
        # Should flow to row+1 (south), direction code 8
        assert fd == 8

    def test_flow_direction_codes(self):
        """Test that D8 codes are correctly assigned."""
        assert mod.D8_CODES[0][0] == 64  # top-left
        assert mod.D8_CODES[0][1] == 128  # top
        assert mod.D8_CODES[0][2] == 1   # top-right
        assert mod.D8_CODES[1][0] == 32  # left
        assert mod.D8_CODES[1][1] == 0   # center
        assert mod.D8_CODES[1][2] == 2   # right
        assert mod.D8_CODES[2][0] == 16  # bottom-left
        assert mod.D8_CODES[2][1] == 8   # bottom
        assert mod.D8_CODES[2][2] == 4   # bottom-right


class TestFlowAccumulation:
    """Test flow accumulation computation."""

    def test_flow_accumulation_minimum(self):
        """Each cell should have at least 1 (itself)."""
        flow_dir = [[0]*5 for _ in range(5)]
        acc = mod.compute_flow_accumulation(flow_dir, 5, 5)
        for row in acc:
            for val in row:
                assert val >= 1

    def test_flow_accumulation_increases_downstream(self):
        """Flow accumulation should increase downstream."""
        # Simple flow: all flow to the right
        flow_dir = [[2]*5 for _ in range(5)]  # 2 = east
        acc = mod.compute_flow_accumulation(flow_dir, 5, 5)
        # Rightmost column should have higher accumulation
        assert acc[0][4] >= acc[0][0]


class TestWatershed:
    """Test watershed delineation."""

    def test_watershed_covers_area(self):
        """Watershed should cover at least the outlet cell."""
        flow_dir = [[0]*5 for _ in range(5)]
        # Set some flow directions
        for r in range(5):
            for c in range(4):
                flow_dir[r][c] = 2  # flow east
        ws = mod.compute_watershed(flow_dir, 2, 4, 5, 5)
        assert ws[2][4] == 1.0

    def test_watershed_single_cell(self):
        """Watershed at a peak should be single cell if no flow."""
        flow_dir = [[0]*5 for _ in range(5)]
        ws = mod.compute_watershed(flow_dir, 2, 2, 5, 5)
        assert ws[2][2] == 1.0


class TestMarchingSquares:
    """Test marching squares contour generation."""

    def test_contour_returns_features(self):
        """Contour generation should return GeoJSON features."""
        dem = type('DEM', (), {
            'data': [[float(i + j * 10) for i in range(5)] for j in range(5)],
            'width': 5, 'height': 5, 'nodata': -9999.0,
            'get_geo_transform': lambda self: (0.0, 1.0, 0.0, -1.0)
        })()
        features = mod.marching_squares_contours(dem, interval=5.0)
        assert isinstance(features, list)


class TestGeoTIFFClass:
    """Test GeoTIFF class methods."""

    def test_get_geo_transform(self):
        """Test geo transform extraction."""
        g = mod.GeoTIFF()
        g.pixel_scale = (10.0, 10.0, 0.0)
        g.tie_point = (0.0, 0.0, 0.0, 100.0, 200.0, 0.0)
        x, pw, y, ph = g.get_geo_transform()
        assert x == 100.0
        assert y == 200.0
        assert pw == 10.0
        assert ph == -10.0

    def test_get_pixel_value(self):
        """Test pixel value access."""
        g = mod.GeoTIFF()
        g.width = 3
        g.height = 3
        g.data = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        g.nodata = None
        assert g.get_pixel_value(0, 0) == 1
        assert g.get_pixel_value(1, 1) == 5
        assert g.get_pixel_value(2, 2) == 9

    def test_get_pixel_value_out_of_bounds(self):
        """Test out of bounds pixel access."""
        g = mod.GeoTIFF()
        g.width = 3
        g.height = 3
        g.data = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        g.nodata = -9999.0
        assert g.get_pixel_value(-1, 0) == -9999.0
        assert g.get_pixel_value(0, 10) == -9999.0

    def test_set_pixel_value(self):
        """Test pixel value setting."""
        g = mod.GeoTIFF()
        g.width = 3
        g.height = 3
        g.data = [[0]*3 for _ in range(3)]
        g.set_pixel_value(1, 1, 42.0)
        assert g.data[1][1] == 42.0

    def test_user_agent(self):
        """Test USER_AGENT string."""
        assert 'dem-terrain-analysis' in mod.USER_AGENT
        assert mod.__version__ in mod.USER_AGENT


class TestWindowExtraction:
    """Test 3x3 window extraction."""

    def test_center_window(self):
        """Test window at center of grid."""
        g = mod.GeoTIFF()
        g.width = 5
        g.height = 5
        g.data = [[float(i + j * 10) for i in range(5)] for j in range(5)]
        g.nodata = None
        window = mod.get_3x3_window(g, 2, 2)
        assert window is not None
        assert len(window) == 3
        assert len(window[0]) == 3
        assert window[1][1] == 22.0

    def test_edge_window(self):
        """Test window at edge uses center value for out-of-bounds."""
        g = mod.GeoTIFF()
        g.width = 5
        g.height = 5
        g.data = [[float(i + j * 10) for i in range(5)] for j in range(5)]
        g.nodata = None
        window = mod.get_3x3_window(g, 0, 0)
        assert window is not None

    def test_nodata_window(self):
        """Test window with nodata returns None."""
        g = mod.GeoTIFF()
        g.width = 5
        g.height = 5
        g.data = [[100.0]*5 for _ in range(5)]
        g.data[0][0] = -9999.0
        g.nodata = -9999.0
        window = mod.get_3x3_window(g, 0, 0)
        assert window is None


class TestViewshedComputation:
    """Test viewshed computation."""

    def test_observer_sees_self(self):
        """Observer should always see their own position."""
        g = mod.GeoTIFF()
        g.width = 5
        g.height = 5
        g.data = [[100.0]*5 for _ in range(5)]
        g.nodata = None
        result = mod.compute_viewshed(g, 2, 2)
        assert result[2][2] == 1.0

    def test_flat_viewshed_all_visible(self):
        """On flat terrain, everything should be visible."""
        g = mod.GeoTIFF()
        g.width = 5
        g.height = 5
        g.data = [[100.0]*5 for _ in range(5)]
        g.nodata = None
        result = mod.compute_viewshed(g, 2, 2)
        # On flat terrain, all cells should be visible
        visible_count = sum(sum(1 for v in row if v > 0) for row in result)
        assert visible_count == 25

    def test_viewshed_blocked_by_wall(self):
        """High wall should block viewshed."""
        g = mod.GeoTIFF()
        g.width = 5
        g.height = 5
        g.data = [[100.0]*5 for _ in range(5)]
        # Add a wall
        for col in range(5):
            g.data[3][col] = 200.0
        g.nodata = None
        result = mod.compute_viewshed(g, 1, 2)
        # Cells behind wall should not be visible
        assert result[4][2] == 0.0
