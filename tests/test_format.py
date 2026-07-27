"""Tests for the --format flag on dem-terrain-analysis (batch-D upgrade).

Supports: auto (default — geotiff for raster, geojson for contour),
text (statistical summary in plain text), json (statistical summary as JSON).
"""
import json
import os
import sys
import subprocess
from pathlib import Path

import pytest


# Use the module already loaded by conftest
import dem_terrain_analysis as mod


class TestFormatArgParser:
    def test_default_format(self):
        parser = mod.create_parser()
        args = parser.parse_args(["slope", "input.tif"])
        assert args.format == "auto"

    def test_text_format(self):
        parser = mod.create_parser()
        args = parser.parse_args(["slope", "input.tif", "--format", "text"])
        assert args.format == "text"

    def test_json_format(self):
        parser = mod.create_parser()
        args = parser.parse_args(["slope", "input.tif", "--format", "json"])
        assert args.format == "json"

    def test_geojson_format(self):
        parser = mod.create_parser()
        args = parser.parse_args(["contour", "input.tif", "--format", "geojson"])
        assert args.format == "geojson"

    def test_rejects_unknown_format(self):
        parser = mod.create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["slope", "input.tif", "--format", "xml"])

    def test_format_in_common(self):
        """The --format flag should be available on every subcommand."""
        parser = mod.create_parser()
        for cmd in ("slope", "aspect", "hillshade", "contour", "curvature",
                     "tri", "tpi", "roughness", "flowdir", "flowacc",
                     "watershed", "viewshed", "batch"):
            try:
                if cmd in ("watershed",):
                    args = parser.parse_args([cmd, "input.tif", "--outlet-row", "1",
                                                "--outlet-col", "1"])
                elif cmd == "viewshed":
                    args = parser.parse_args([cmd, "input.tif"])
                elif cmd == "batch":
                    args = parser.parse_args([cmd, "input.tif"])
                else:
                    args = parser.parse_args([cmd, "input.tif"])
                assert hasattr(args, "format"), f"{cmd} missing --format"
            except SystemExit:
                pass  # some commands may require extra args


class TestSummarizeDem:
    def test_summarize_slope_text(self, synthetic_tiff_path, tmp_path):
        out = tmp_path / "summary.txt"
        result = mod.summarize_dem(
            synthetic_tiff_path, "slope", str(out), fmt="text", unit="degrees"
        )
        assert result == str(out)
        assert out.exists()
        text = out.read_text(encoding="utf-8")
        assert "DEM Terrain Analysis" in text
        assert "slope" in text
        assert "Min" in text
        assert "Max" in text
        assert "Mean" in text

    def test_summarize_slope_json(self, synthetic_tiff_path, tmp_path):
        out = tmp_path / "summary.json"
        result = mod.summarize_dem(
            synthetic_tiff_path, "slope", str(out), fmt="json", unit="degrees"
        )
        assert result == str(out)
        with open(out, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["command"] == "slope"
        assert "n_pixels" in data
        assert "min" in data
        assert "max" in data
        assert "mean" in data

    def test_summarize_aspect(self, synthetic_tiff_path, tmp_path):
        out = tmp_path / "aspect_summary.txt"
        result = mod.summarize_dem(
            synthetic_tiff_path, "aspect", str(out), fmt="text"
        )
        assert out.exists()

    def test_summarize_hillshade(self, synthetic_tiff_path, tmp_path):
        out = tmp_path / "hs_summary.json"
        result = mod.summarize_dem(
            synthetic_tiff_path, "hillshade", str(out), fmt="json",
            azimuth=270, altitude=30,
        )
        with open(out, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["command"] == "hillshade"
        assert data["kwargs"]["azimuth"] == 270
        assert data["kwargs"]["altitude"] == 30

    def test_summarize_contour_text(self, peak_tiff_path, tmp_path):
        out = tmp_path / "contour_summary.txt"
        result = mod.summarize_dem(
            peak_tiff_path, "contour", str(out), fmt="text", interval=5.0
        )
        text = out.read_text(encoding="utf-8")
        assert "Contour summary" in text
        assert "interval=5" in text
        assert "Number of contour lines" in text

    def test_summarize_contour_json(self, peak_tiff_path, tmp_path):
        out = tmp_path / "contour_summary.json"
        result = mod.summarize_dem(
            peak_tiff_path, "contour", str(out), fmt="json", interval=5.0
        )
        with open(out, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["command"] == "contour"
        assert data["interval"] == 5.0
        assert "n_contours" in data
        assert "elevations" in data
        assert "counts_per_elevation" in data

    def test_summarize_curvature(self, synthetic_tiff_path, tmp_path):
        out = tmp_path / "curv_summary.txt"
        result = mod.summarize_dem(
            synthetic_tiff_path, "curvature", str(out), fmt="text", type="plan"
        )
        assert out.exists()

    def test_summarize_tri(self, synthetic_tiff_path, tmp_path):
        out = tmp_path / "tri_summary.json"
        result = mod.summarize_dem(
            synthetic_tiff_path, "tri", str(out), fmt="json"
        )
        with open(out, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["command"] == "tri"
        assert data["n_pixels"] > 0

    def test_summarize_default_extension(self, synthetic_tiff_path, tmp_path):
        """No output_path → uses default extension (.txt or .json)."""
        os.chdir(tmp_path)  # so default path can be written
        try:
            text_result = mod.summarize_dem(
                synthetic_tiff_path, "slope", fmt="text", unit="degrees"
            )
            assert text_result.endswith(".txt")
            json_result = mod.summarize_dem(
                synthetic_tiff_path, "slope", fmt="json", unit="degrees"
            )
            assert json_result.endswith(".json")
        finally:
            os.chdir(Path(__file__).parent)


class TestAnalyzeDemWithFormat:
    def test_analyze_dem_text_creates_summary(self, synthetic_tiff_path, tmp_path, capsys):
        """When --format=text is requested, summarize_dem is invoked alongside analyze_dem."""
        # synthetic_tiff_path is already at tmp_path/test_dem.tif (see conftest).
        dem_dir = Path(synthetic_tiff_path).parent
        out_path = dem_dir / "out.tif"

        import sys as _sys
        old_argv = _sys.argv
        try:
            _sys.argv = [
                "dem-terrain-analysis", "slope", str(synthetic_tiff_path),
                "--output", str(out_path),
                "--format", "text",
            ]
            rc = mod.main()
            assert rc is None or rc == 0
        except SystemExit:
            pass
        finally:
            _sys.argv = old_argv
        # The raster was written
        assert out_path.exists(), f"Expected raster at {out_path}"
        # And a text summary was written next to the input DEM
        summary = dem_dir / "test_dem_slope_summary.txt"
        assert summary.exists(), f"Expected summary at {summary}"
        text = summary.read_text(encoding="utf-8")
        assert "DEM Terrain Analysis" in text
