import importlib.util
import os
import sys
import struct
import math
import tempfile

import pytest

# Load the module from the hyphenated filename
_module_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dem-terrain-analysis.py')
_spec = importlib.util.spec_from_file_location('dem_terrain_analysis', _module_path)
dem_terrain_analysis = importlib.util.module_from_spec(_spec)
sys.modules['dem_terrain_analysis'] = dem_terrain_analysis
_spec.loader.exec_module(dem_terrain_analysis)


def create_test_geotiff(filepath, data, width, height, nodata=-9999.0,
                         pixel_scale=(1.0, 1.0, 0.0), tie_point=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)):
    """Create a minimal GeoTIFF file for testing."""
    endian = '<'

    # Prepare pixel data as float32
    pixel_bytes = bytearray()
    for row in range(height):
        for col in range(width):
            if row < len(data) and col < len(data[row]):
                val = float(data[row][col])
            else:
                val = nodata
            pixel_bytes.extend(struct.pack(endian + 'f', val))

    raw_pixel_data = bytes(pixel_bytes)

    # Build extra data
    extra_data = bytearray()
    nodata_str = str(nodata)

    # XResolution (RATIONAL = 2x LONG)
    extra_data.extend(struct.pack(endian + 'II', 1, 1))
    # YResolution
    extra_data.extend(struct.pack(endian + 'II', 1, 1))
    # PixelScale (3 doubles = 24 bytes)
    ps = pixel_scale if len(pixel_scale) == 3 else (pixel_scale[0], pixel_scale[1], 0.0)
    extra_data.extend(struct.pack(endian + 'ddd', *ps))
    # Tiepoint (6 doubles = 48 bytes)
    tp = tie_point if len(tie_point) == 6 else (0, 0, 0, tie_point[0], tie_point[1], tie_point[2])
    extra_data.extend(struct.pack(endian + 'dddddd', *tp))
    # NODATA string
    extra_data.extend(nodata_str.encode('ascii') + b'\x00')

    # Header: 8 bytes
    header = b'II'
    header += struct.pack(endian + 'H', 42)
    header += struct.pack(endian + 'I', 8)

    num_tags = 17
    ifd_size = 2 + num_tags * 12 + 4
    data_offset = 8 + ifd_size
    strip_data_offset = data_offset + len(extra_data)

    # Build IFD - each entry is exactly 12 bytes: tag(2) + type(2) + count(4) + value/offset(4)
    ifd = struct.pack(endian + 'H', num_tags)

    def ifd_entry(tag, typ, count, val):
        return struct.pack(endian + 'HHI', tag, typ, count) + struct.pack(endian + 'I', val)

    ifd += ifd_entry(256, 4, 1, width)              # ImageWidth
    ifd += ifd_entry(257, 4, 1, height)             # ImageLength
    ifd += ifd_entry(258, 3, 1, 32)                 # BitsPerSample
    ifd += ifd_entry(259, 3, 1, 1)                  # Compression
    ifd += ifd_entry(262, 3, 1, 1)                  # PhotometricInterpretation
    ifd += ifd_entry(273, 4, 1, strip_data_offset)  # StripOffsets
    ifd += ifd_entry(277, 3, 1, 1)                  # SamplesPerPixel
    ifd += ifd_entry(278, 4, 1, height)             # RowsPerStrip
    ifd += ifd_entry(279, 4, 1, len(raw_pixel_data)) # StripByteCounts
    ifd += ifd_entry(282, 5, 1, data_offset)        # XResolution
    ifd += ifd_entry(283, 5, 1, data_offset + 8)    # YResolution
    ifd += ifd_entry(284, 3, 1, 1)                  # PlanarConfiguration
    ifd += ifd_entry(296, 3, 1, 1)                  # ResolutionUnit
    ifd += ifd_entry(339, 3, 1, 3)                  # SampleFormat

    offset_pos = data_offset + 16  # After XRes(8) + YRes(8)
    ifd += ifd_entry(33550, 12, 3, offset_pos)      # ModelPixelScale
    offset_pos += 24
    ifd += ifd_entry(33922, 12, 6, offset_pos)      # ModelTiepoint
    offset_pos += 48
    ifd += ifd_entry(42113, 2, len(nodata_str), offset_pos)  # GDAL_NODATA

    # Next IFD offset = 0
    ifd += struct.pack(endian + 'I', 0)

    with open(filepath, 'wb') as f:
        f.write(header)
        f.write(ifd)
        f.write(extra_data)
        f.write(raw_pixel_data)


@pytest.fixture
def simple_dem_data():
    """A simple 5x5 DEM with a slope."""
    return [
        [100, 101, 102, 103, 104],
        [101, 102, 103, 104, 105],
        [102, 103, 104, 105, 106],
        [103, 104, 105, 106, 107],
        [104, 105, 106, 107, 108],
    ]


@pytest.fixture
def flat_dem_data():
    """A flat DEM (all same elevation)."""
    return [[100.0 for _ in range(5)] for _ in range(5)]


@pytest.fixture
def peak_dem_data():
    """A DEM with a central peak."""
    return [
        [100, 100, 100, 100, 100],
        [100, 110, 110, 110, 100],
        [100, 110, 120, 110, 100],
        [100, 110, 110, 110, 100],
        [100, 100, 100, 100, 100],
    ]


@pytest.fixture
def synthetic_tiff_path(simple_dem_data, tmp_path):
    """Create a synthetic GeoTIFF for testing."""
    filepath = str(tmp_path / 'test_dem.tif')
    create_test_geotiff(filepath, simple_dem_data, 5, 5)
    return filepath


@pytest.fixture
def flat_tiff_path(flat_dem_data, tmp_path):
    """Create a flat GeoTIFF for testing."""
    filepath = str(tmp_path / 'flat_dem.tif')
    create_test_geotiff(filepath, flat_dem_data, 5, 5)
    return filepath


@pytest.fixture
def peak_tiff_path(peak_dem_data, tmp_path):
    """Create a peak GeoTIFF for testing."""
    filepath = str(tmp_path / 'peak_dem.tif')
    create_test_geotiff(filepath, peak_dem_data, 5, 5)
    return filepath
