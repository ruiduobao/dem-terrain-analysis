import os
import sys
import pytest

# Use the module already loaded by conftest
import dem_terrain_analysis as mod


class TestCLIHelp:
    """Test CLI help and version output."""

    def test_cli_help(self, capsys):
        """Test --help flag."""
        sys.argv = ['dem-terrain-analysis', '--help']
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
        assert exc_info.value.code == 0

    def test_cli_version(self, capsys):
        """Test --version flag."""
        sys.argv = ['dem-terrain-analysis', '--version']
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
        assert exc_info.value.code == 0


class TestCLISubcommands:
    """Test CLI subcommand parsing."""

    def test_parser_slope(self):
        """Test slope subcommand parser."""
        parser = mod.create_parser()
        args = parser.parse_args(['slope', 'input.tif', '--output', 'out.tif', '--unit', 'percent'])
        assert args.command == 'slope'
        assert args.input == 'input.tif'
        assert args.output == 'out.tif'
        assert args.unit == 'percent'

    def test_parser_aspect(self):
        """Test aspect subcommand parser."""
        parser = mod.create_parser()
        args = parser.parse_args(['aspect', 'input.tif'])
        assert args.command == 'aspect'

    def test_parser_hillshade(self):
        """Test hillshade subcommand parser."""
        parser = mod.create_parser()
        args = parser.parse_args(['hillshade', 'input.tif', '--azimuth', '270', '--altitude', '30'])
        assert args.command == 'hillshade'
        assert args.azimuth == 270.0
        assert args.altitude == 30.0

    def test_parser_contour(self):
        """Test contour subcommand parser."""
        parser = mod.create_parser()
        args = parser.parse_args(['contour', 'input.tif', '--interval', '5'])
        assert args.command == 'contour'
        assert args.interval == 5.0

    def test_parser_curvature(self):
        """Test curvature subcommand parser."""
        parser = mod.create_parser()
        args = parser.parse_args(['curvature', 'input.tif', '--type', 'profile'])
        assert args.command == 'curvature'
        assert args.type == 'profile'

    def test_parser_tri(self):
        """Test tri subcommand parser."""
        parser = mod.create_parser()
        args = parser.parse_args(['tri', 'input.tif'])
        assert args.command == 'tri'

    def test_parser_tpi(self):
        """Test tpi subcommand parser."""
        parser = mod.create_parser()
        args = parser.parse_args(['tpi', 'input.tif', '--window', '5'])
        assert args.command == 'tpi'
        assert args.window == 5

    def test_parser_batch(self):
        """Test batch subcommand parser."""
        parser = mod.create_parser()
        args = parser.parse_args(['batch', 'input.tif', '--output-dir', '/tmp/out'])
        assert args.command == 'batch'
        assert args.output_dir == '/tmp/out'

    def test_parser_flowdir(self):
        """Test flowdir subcommand parser."""
        parser = mod.create_parser()
        args = parser.parse_args(['flowdir', 'input.tif'])
        assert args.command == 'flowdir'

    def test_parser_flowacc(self):
        """Test flowacc subcommand parser."""
        parser = mod.create_parser()
        args = parser.parse_args(['flowacc', 'input.tif'])
        assert args.command == 'flowacc'

    def test_parser_viewshed(self):
        """Test viewshed subcommand parser."""
        parser = mod.create_parser()
        args = parser.parse_args(['viewshed', 'input.tif', '--obs-row', '10', '--obs-col', '20'])
        assert args.command == 'viewshed'
        assert args.obs_row == 10
        assert args.obs_col == 20


class TestCLINoCommand:
    """Test CLI with no command."""

    def test_no_command(self):
        """Test that no command exits with error."""
        sys.argv = ['dem-terrain-analysis']
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
        assert exc_info.value.code == 1


class TestCLIMissingInput:
    """Test CLI with missing input file."""

    def test_missing_input(self):
        """Test that missing input file exits with error."""
        sys.argv = ['dem-terrain-analysis', 'slope', 'nonexistent.tif']
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
        assert exc_info.value.code == 1


class TestCLIOutputNaming:
    """Test default output naming."""

    def test_slope_default_output(self, synthetic_tiff_path, tmp_path):
        """Test default output path for slope."""
        output = mod.analyze_dem(synthetic_tiff_path, 'slope')
        assert output.endswith('_slope.tif')
        assert os.path.exists(output)
        os.remove(output)

    def test_aspect_default_output(self, synthetic_tiff_path, tmp_path):
        """Test default output path for aspect."""
        output = mod.analyze_dem(synthetic_tiff_path, 'aspect')
        assert output.endswith('_aspect.tif')
        assert os.path.exists(output)
        os.remove(output)

    def test_hillshade_default_output(self, synthetic_tiff_path, tmp_path):
        """Test default output path for hillshade."""
        output = mod.analyze_dem(synthetic_tiff_path, 'hillshade')
        assert output.endswith('_hillshade.tif')
        assert os.path.exists(output)
        os.remove(output)

    def test_contour_default_output(self, synthetic_tiff_path, tmp_path):
        """Test default output path for contour."""
        output = mod.analyze_dem(synthetic_tiff_path, 'contour')
        assert output.endswith('_contour.geojson')
        assert os.path.exists(output)
        os.remove(output)
