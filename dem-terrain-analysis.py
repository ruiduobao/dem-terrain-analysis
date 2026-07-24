#!/usr/bin/env python3
"""
DEM Terrain Analysis - Pure Python terrain derivative generator.

Generates slope, aspect, hillshade, contour lines, curvature, TRI, TPI,
roughness, flow direction, flow accumulation, watershed, and viewshed
from GeoTIFF DEM files using only Python standard library.

Privacy: No data is transmitted externally. All processing is local.
User-Agent: dem-terrain-analysis/0.1.0
License: MIT-0
Author: rui.duobao
"""

import argparse
import json
import math
import os
import struct
import sys
import zlib
from collections import deque
from pathlib import Path

__version__ = "0.1.0"
__author__ = "rui.duobao"

USER_AGENT = f"dem-terrain-analysis/{__version__}"


# ============================================================================
# GeoTIFF Reader/Writer (pure Python)
# ============================================================================

class GeoTIFF:
    """Minimal GeoTIFF reader/writer using only stdlib."""

    def __init__(self):
        self.width = 0
        self.height = 0
        self.nodata = None
        self.data = []
        self.pixel_scale = (1.0, 1.0, 0.0)
        self.tie_point = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        self.geo_keys = {}
        self.is_geotiff = False
        self.bits_per_sample = 32
        self.sample_format = 3  # IEEE float
        self.compression = 1
        self.samples_per_pixel = 1
        self.planar_config = 1
        self.rows_per_strip = 0
        self.strip_offsets = []
        self.strip_byte_counts = []

    @staticmethod
    def read(filepath):
        """Read a GeoTIFF file and return a GeoTIFF instance."""
        g = GeoTIFF()
        with open(filepath, 'rb') as f:
            data = f.read()

        # Read TIFF header
        byte_order = data[0:2]
        if byte_order == b'II':
            endian = '<'
        elif byte_order == b'MM':
            endian = '>'
        else:
            raise ValueError("Not a valid TIFF file")

        magic = struct.unpack_from(endian + 'H', data, 2)[0]
        if magic != 42:
            raise ValueError("Not a valid TIFF file")

        ifd_offset = struct.unpack_from(endian + 'I', data, 4)[0]
        g._parse_ifd(data, ifd_offset, endian)
        g._parse_geotiff_tags(data, endian)
        g._read_strips(data, endian)

        # Convert raw data to float grid
        g._decode_pixels(data, endian)
        return g

    def _parse_ifd(self, data, offset, endian):
        """Parse IFD entries."""
        num_entries = struct.unpack_from(endian + 'H', data, offset)[0]
        pos = offset + 2

        tags = {}
        for _ in range(num_entries):
            tag = struct.unpack_from(endian + 'H', data, pos)[0]
            type_id = struct.unpack_from(endian + 'H', data, pos + 2)[0]
            count = struct.unpack_from(endian + 'I', data, pos + 4)[0]
            value_raw = data[pos + 8:pos + 12]
            tags[tag] = (type_id, count, value_raw)
            pos += 12

        self._process_tags(tags, data, endian)

        # Parse next IFD for sub-IFDs if needed
        next_offset = struct.unpack_from(endian + 'I', data, pos)[0]

    def _process_tags(self, tags, data, endian):
        """Process TIFF tags."""
        type_sizes = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8}

        def read_value(tag_entry):
            type_id, count, raw = tag_entry
            size = type_sizes.get(type_id, 0) * count
            if size <= 4:
                return self._decode_tiff_value(raw, type_id, count, endian)
            else:
                # Value is a pointer
                offset = struct.unpack(endian + 'I', raw)[0]
                return self._decode_tiff_value(data[offset:offset + size], type_id, count, endian)

        if 256 in tags:  # ImageWidth
            self.width = read_value(tags[256])
            if isinstance(self.width, tuple):
                self.width = self.width[0]
        if 257 in tags:  # ImageLength
            self.height = read_value(tags[257])
            if isinstance(self.height, tuple):
                self.height = self.height[0]
        if 258 in tags:  # BitsPerSample
            val = read_value(tags[258])
            if isinstance(val, tuple):
                self.bits_per_sample = val[0]
            else:
                self.bits_per_sample = val
        if 259 in tags:  # Compression
            self.compression = read_value(tags[259])
            if isinstance(self.compression, tuple):
                self.compression = self.compression[0]
        if 273 in tags:  # StripOffsets
            val = read_value(tags[273])
            if isinstance(val, (list, tuple)):
                self.strip_offsets = list(val)
            else:
                self.strip_offsets = [val]
        if 278 in tags:  # RowsPerStrip
            self.rows_per_strip = read_value(tags[278])
            if isinstance(self.rows_per_strip, tuple):
                self.rows_per_strip = self.rows_per_strip[0]
        if 279 in tags:  # StripByteCounts
            val = read_value(tags[279])
            if isinstance(val, (list, tuple)):
                self.strip_byte_counts = list(val)
            else:
                self.strip_byte_counts = [val]
        if 282 in tags:  # XResolution
            pass
        if 284 in tags:  # PlanarConfiguration
            self.planar_config = read_value(tags[284])
            if isinstance(self.planar_config, tuple):
                self.planar_config = self.planar_config[0]
        if 339 in tags:  # SampleFormat
            val = read_value(tags[339])
            if isinstance(val, tuple):
                self.sample_format = val[0]
            else:
                self.sample_format = val

        # GDAL NODATA
        if 42113 in tags:
            nodata_str = read_value(tags[42113])
            if isinstance(nodata_str, (list, tuple)):
                nodata_str = ''.join(chr(b) for b in nodata_str if b != 0)
            elif isinstance(nodata_str, bytes):
                nodata_str = nodata_str.decode('ascii', errors='ignore').strip('\x00')
            try:
                self.nodata = float(nodata_str)
            except (ValueError, TypeError):
                pass

    def _decode_tiff_value(self, raw, type_id, count, endian):
        """Decode TIFF value from raw bytes."""
        if type_id == 1:  # BYTE
            return struct.unpack(endian + 'B' * count, raw[:count])
        elif type_id == 2:  # ASCII
            return raw[:count]
        elif type_id == 3:  # SHORT
            return struct.unpack(endian + 'H' * count, raw[:count * 2])
        elif type_id == 4:  # LONG
            return struct.unpack(endian + 'I' * count, raw[:count * 4])
        elif type_id == 5:  # RATIONAL
            vals = []
            for i in range(count):
                num = struct.unpack_from(endian + 'I', raw, i * 8)[0]
                den = struct.unpack_from(endian + 'I', raw, i * 8 + 4)[0]
                vals.append(num / den if den != 0 else 0)
            return tuple(vals)
        elif type_id == 6:  # SBYTE
            return struct.unpack(endian + 'b' * count, raw[:count])
        elif type_id == 7:  # UNDEFINED
            return raw[:count]
        elif type_id == 8:  # SSHORT
            return struct.unpack(endian + 'h' * count, raw[:count * 2])
        elif type_id == 9:  # SLONG
            return struct.unpack(endian + 'i' * count, raw[:count * 4])
        elif type_id == 10:  # SRATIONAL
            vals = []
            for i in range(count):
                num = struct.unpack_from(endian + 'i', raw, i * 8)[0]
                den = struct.unpack_from(endian + 'i', raw, i * 8 + 4)[0]
                vals.append(num / den if den != 0 else 0)
            return tuple(vals)
        elif type_id == 11:  # FLOAT
            return struct.unpack(endian + 'f' * count, raw[:count * 4])
        elif type_id == 12:  # DOUBLE
            return struct.unpack(endian + 'd' * count, raw[:count * 8])
        return raw

    def _parse_geotiff_tags(self, data, endian):
        """Parse GeoTIFF-specific tags."""
        # GeoTIFF uses tags 33550 (ModelPixelScale), 33922 (ModelTiepoint),
        # 34735 (GeoKeyDirectory), 34736 (GeoDoubleParams), 34737 (GeoAsciiParams)
        ifd_offset = struct.unpack_from(endian + 'I', data, 4)[0]
        num_entries = struct.unpack_from(endian + 'H', data, ifd_offset)[0]
        pos = ifd_offset + 2

        tags = {}
        for _ in range(num_entries):
            tag = struct.unpack_from(endian + 'H', data, pos)[0]
            type_id = struct.unpack_from(endian + 'H', data, pos + 2)[0]
            count = struct.unpack_from(endian + 'I', data, pos + 4)[0]
            value_raw = data[pos + 8:pos + 12]
            tags[tag] = (type_id, count, value_raw)
            pos += 12

        type_sizes = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 11: 4, 12: 8}

        def read_raw(tag_entry):
            type_id, count, raw = tag_entry
            size = type_sizes.get(type_id, 0) * count
            if size <= 4:
                return raw
            else:
                offset = struct.unpack(endian + 'I', raw)[0]
                return data[offset:offset + size]

        # 33550 - ModelPixelScaleTag
        if 33550 in tags:
            raw = read_raw(tags[33550])
            self.pixel_scale = struct.unpack(endian + 'ddd', raw[:24])
            self.is_geotiff = True

        # 33922 - ModelTiepointTag
        if 33922 in tags:
            raw = read_raw(tags[33922])
            count = tags[33922][1]
            self.tie_point = struct.unpack(endian + 'd' * count, raw[:count * 8])
            self.is_geotiff = True

        # 34735 - GeoKeyDirectoryTag
        if 34735 in tags:
            raw = read_raw(tags[34735])
            count = tags[34735][1]
            keys = struct.unpack(endian + 'H' * count, raw[:count * 2])
            if len(keys) >= 4:
                for i in range(4, len(keys) - 2, 4):
                    key_id = keys[i]
                    tiff_tag = keys[i + 1]
                    count_val = keys[i + 2]
                    value_offset = keys[i + 3]
                    self.geo_keys[key_id] = (tiff_tag, count_val, value_offset)
            self.is_geotiff = True

    def _read_strips(self, data, endian):
        """Read strip data."""
        self._raw_strips = []
        for i, offset in enumerate(self.strip_offsets):
            byte_count = self.strip_byte_counts[i] if i < len(self.strip_byte_counts) else 0
            if byte_count == 0:
                byte_count = len(data) - offset
            strip_data = data[offset:offset + byte_count]

            if self.compression == 5:  # LZW
                strip_data = self._decompress_lzw(strip_data)
            elif self.compression == 8:  # Deflate
                strip_data = zlib.decompress(strip_data, -15)

            self._raw_strips.append(strip_data)

    def _decompress_lzw(self, data):
        """Decompress LZW data."""
        # Simplified LZW decompression for TIFF
        min_code_size = 8
        clear_code = 256
        eoi_code = 257

        table = {}
        for i in range(256):
            table[i] = bytes([i])

        result = bytearray()
        code_size = 9
        next_code = 258
        bit_pos = 0

        prev_entry = None

        while bit_pos + code_size <= len(data) * 8:
            # Read code
            code = 0
            for bit in range(code_size):
                byte_idx = (bit_pos + bit) // 8
                bit_idx = 7 - ((bit_pos + bit) % 8)
                if byte_idx < len(data):
                    code |= ((data[byte_idx] >> bit_idx) & 1) << (code_size - 1 - bit)

            bit_pos += code_size

            if code == eoi_code:
                break
            if code == clear_code:
                table = {}
                for i in range(256):
                    table[i] = bytes([i])
                next_code = 258
                code_size = 9
                prev_entry = None
                continue

            if code in table:
                entry = table[code]
            elif prev_entry is not None and code == next_code:
                entry = prev_entry + prev_entry[0:1]
            else:
                break

            result.extend(entry)

            if prev_entry is not None and next_code < 4096:
                table[next_code] = prev_entry + entry[0:1]
                next_code += 1
                if next_code > (2 ** code_size - 1) and code_size < 12:
                    code_size += 1

            prev_entry = entry

        return bytes(result)

    def _decode_pixels(self, data, endian):
        """Decode pixel data to float grid."""
        raw = b''.join(self._raw_strips)
        self.data = []

        if self.bits_per_sample == 32 and self.sample_format == 3:
            fmt = endian + 'f'
            step = 4
        elif self.bits_per_sample == 64 and self.sample_format == 3:
            fmt = endian + 'd'
            step = 8
        elif self.bits_per_sample == 32 and self.sample_format == 1:
            fmt = endian + 'I'
            step = 4
        elif self.bits_per_sample == 16 and self.sample_format == 1:
            fmt = endian + 'H'
            step = 2
        elif self.bits_per_sample == 16 and self.sample_format == 2:
            fmt = endian + 'h'
            step = 2
        elif self.bits_per_sample == 32 and self.sample_format == 2:
            fmt = endian + 'i'
            step = 4
        else:
            fmt = endian + 'f'
            step = 4

        total_pixels = self.width * self.height
        max_available = len(raw) // step

        for row in range(self.height):
            row_data = []
            for col in range(self.width):
                idx = row * self.width + col
                if idx < max_available:
                    val = struct.unpack_from(fmt, raw, idx * step)[0]
                    row_data.append(float(val))
                else:
                    row_data.append(0.0)
            self.data.append(row_data)

    @staticmethod
    def write(filepath, data, width, height, nodata=None, pixel_scale=None, tie_point=None, compression=1):
        """Write a grid to GeoTIFF format."""
        endian = '<'

        # Prepare pixel data as float32
        pixel_bytes = bytearray()
        nodata_val = nodata if nodata is not None else -9999.0

        for row in range(height):
            for col in range(width):
                if row < len(data) and col < len(data[row]):
                    val = data[row][col]
                    if val is None or (isinstance(val, float) and math.isnan(val)):
                        val = nodata_val
                else:
                    val = nodata_val
                pixel_bytes.extend(struct.pack(endian + 'f', float(val)))

        raw_pixel_data = bytes(pixel_bytes)

        # Build extra data first to know its size
        extra_data = bytearray()
        nodata_str = str(nodata_val) if nodata is not None else None

        # XResolution (RATIONAL = 2x LONG = 8 bytes)
        extra_data.extend(struct.pack(endian + 'II', 1, 1))
        # YResolution
        extra_data.extend(struct.pack(endian + 'II', 1, 1))
        # PixelScale (3 doubles = 24 bytes)
        if pixel_scale is not None:
            ps = pixel_scale if len(pixel_scale) == 3 else (pixel_scale[0], pixel_scale[1], 0.0)
            extra_data.extend(struct.pack(endian + 'ddd', *ps))
        # Tiepoint (6 doubles = 48 bytes)
        if tie_point is not None:
            tp = tie_point if len(tie_point) == 6 else (0, 0, 0, tie_point[0], tie_point[1], tie_point[2])
            extra_data.extend(struct.pack(endian + 'dddddd', *tp))
        # NODATA string
        if nodata_str is not None:
            extra_data.extend(nodata_str.encode('ascii') + b'\x00')

        # Header: 8 bytes
        header = b'II'  # Little-endian
        header += struct.pack(endian + 'H', 42)  # Magic
        header += struct.pack(endian + 'I', 8)  # IFD offset

        # Count tags
        num_tags = 14  # Base tags
        if pixel_scale is not None:
            num_tags += 1
        if tie_point is not None:
            num_tags += 1
        if nodata is not None:
            num_tags += 1

        ifd_size = 2 + num_tags * 12 + 4
        data_offset = 8 + ifd_size
        strip_data_offset = data_offset + len(extra_data)

        # Build IFD - each entry is exactly 12 bytes: tag(2) + type(2) + count(4) + value/offset(4)
        ifd = struct.pack(endian + 'H', num_tags)

        def ifd_entry(tag, typ, count, val):
            """Create a 12-byte IFD entry."""
            return struct.pack(endian + 'HHI', tag, typ, count) + struct.pack(endian + 'I', val)

        # Standard TIFF tags
        ifd += ifd_entry(256, 4, 1, width)              # ImageWidth (LONG)
        ifd += ifd_entry(257, 4, 1, height)             # ImageLength (LONG)
        ifd += ifd_entry(258, 3, 1, 32)                 # BitsPerSample (SHORT)
        ifd += ifd_entry(259, 3, 1, compression)        # Compression (SHORT)
        ifd += ifd_entry(262, 3, 1, 1)                  # PhotometricInterpretation (SHORT)
        ifd += ifd_entry(273, 4, 1, strip_data_offset)  # StripOffsets (LONG)
        ifd += ifd_entry(277, 3, 1, 1)                  # SamplesPerPixel (SHORT)
        ifd += ifd_entry(278, 4, 1, height)             # RowsPerStrip (LONG)
        ifd += ifd_entry(279, 4, 1, len(raw_pixel_data)) # StripByteCounts (LONG)
        ifd += ifd_entry(282, 5, 1, data_offset)        # XResolution (RATIONAL, pointer)
        ifd += ifd_entry(283, 5, 1, data_offset + 8)    # YResolution (RATIONAL, pointer)
        ifd += ifd_entry(284, 3, 1, 1)                  # PlanarConfiguration (SHORT)
        ifd += ifd_entry(296, 3, 1, 1)                  # ResolutionUnit (SHORT)
        ifd += ifd_entry(339, 3, 1, 3)                  # SampleFormat (SHORT)

        offset_pos = data_offset + 16  # After XRes(8) + YRes(8)
        if pixel_scale is not None:
            ifd += ifd_entry(33550, 12, 3, offset_pos)  # ModelPixelScale (DOUBLE, pointer)
            offset_pos += 24
        if tie_point is not None:
            ifd += ifd_entry(33922, 12, 6, offset_pos)  # ModelTiepoint (DOUBLE, pointer)
            offset_pos += 48
        if nodata is not None:
            ifd += ifd_entry(42113, 2, len(nodata_str), offset_pos)  # GDAL_NODATA (ASCII, pointer)

        # Next IFD offset = 0
        ifd += struct.pack(endian + 'I', 0)

        # Write file
        with open(filepath, 'wb') as f:
            f.write(header)
            f.write(ifd)
            f.write(extra_data)
            f.write(raw_pixel_data)

    def get_geo_transform(self):
        """Return (x_origin, pixel_width, y_origin, pixel_height)."""
        if len(self.tie_point) >= 6:
            x_origin = self.tie_point[3]
            y_origin = self.tie_point[4]
        else:
            x_origin = 0.0
            y_origin = 0.0

        if len(self.pixel_scale) >= 2:
            pixel_width = self.pixel_scale[0]
            pixel_height = -self.pixel_scale[1]  # Negative for north-up
        else:
            pixel_width = 1.0
            pixel_height = -1.0

        return (x_origin, pixel_width, y_origin, pixel_height)

    def get_pixel_value(self, row, col):
        """Get pixel value at row, col."""
        if 0 <= row < self.height and 0 <= col < self.width:
            return self.data[row][col]
        return self.nodata

    def set_pixel_value(self, row, col, value):
        """Set pixel value at row, col."""
        if 0 <= row < self.height and 0 <= col < self.width:
            self.data[row][col] = value


# ============================================================================
# Terrain Analysis Functions
# ============================================================================

def get_3x3_window(geo, row, col, nodata_val=-9999.0):
    """Extract 3x3 window around (row, col). Returns 3x3 list or None if nodata."""
    window = []
    for dr in range(-1, 2):
        row_data = []
        for dc in range(-1, 2):
            r, c = row + dr, col + dc
            if 0 <= r < geo.height and 0 <= c < geo.width:
                val = geo.data[r][c]
                if geo.nodata is not None and val == geo.nodata:
                    return None
                if math.isnan(val):
                    return None
                row_data.append(val)
            else:
                # Use center value for edge cells
                row_data.append(geo.data[row][col])
        window.append(row_data)
    return window


def compute_slope(window, cell_size_x=1.0, cell_size_y=1.0, unit='degrees'):
    """
    Compute slope using Zevenbergen-Thorne method.
    window: 3x3 list [[a,b,c],[d,e,f],[g,h,i]]
    Returns slope in degrees or percent.
    """
    a, b, c = window[0]
    d, e, f = window[1]
    g, h, i = window[2]

    dzdx = ((c + 2*f + i) - (a + 2*d + g)) / (8 * cell_size_x)
    dzdy = ((g + 2*h + i) - (a + 2*b + c)) / (8 * cell_size_y)

    slope_rad = math.atan(math.sqrt(dzdx**2 + dzdy**2))

    if unit == 'percent':
        return math.tan(slope_rad) * 100
    else:
        return math.degrees(slope_rad)


def compute_aspect(window, cell_size_x=1.0, cell_size_y=1.0):
    """
    Compute aspect using Zevenbergen-Thorne method.
    Returns aspect in degrees from north (0-360).
    """
    a, b, c = window[0]
    d, e, f = window[1]
    g, h, i = window[2]

    dzdx = ((c + 2*f + i) - (a + 2*d + g)) / (8 * cell_size_x)
    dzdy = ((g + 2*h + i) - (a + 2*b + c)) / (8 * cell_size_y)

    if dzdx == 0 and dzdy == 0:
        return -1  # Flat

    aspect_rad = math.atan2(-dzdy, dzdx)
    aspect_deg = math.degrees(aspect_rad)

    # Convert to geographic convention (0=north, clockwise)
    aspect = 90.0 - aspect_deg
    if aspect < 0:
        aspect += 360.0
    if aspect >= 360.0:
        aspect -= 360.0

    return aspect


def compute_hillshade(window, cell_size_x=1.0, cell_size_y=1.0,
                      azimuth=315.0, altitude=45.0):
    """
    Compute hillshade value (0-255).
    azimuth: sun azimuth in degrees (0=north, clockwise)
    altitude: sun altitude in degrees above horizon
    """
    a, b, c = window[0]
    d, e, f = window[1]
    g, h, i = window[2]

    dzdx = ((c + 2*f + i) - (a + 2*d + g)) / (8 * cell_size_x)
    dzdy = ((g + 2*h + i) - (a + 2*b + c)) / (8 * cell_size_y)

    # Slope and aspect
    slope_rad = math.atan(math.sqrt(dzdx**2 + dzdy**2))
    aspect_rad = math.atan2(-dzdy, dzdx)

    # Zenith and azimuth in radians
    zenith_rad = math.radians(90.0 - altitude)
    azimuth_rad = math.radians(azimuth)

    # Hillshade formula
    hs = (math.cos(zenith_rad) * math.cos(slope_rad) +
          math.sin(zenith_rad) * math.sin(slope_rad) *
          math.cos(azimuth_rad - math.pi/2 - aspect_rad))

    # Scale to 0-255
    hs = max(0, min(255, int(hs * 255)))
    return hs


def compute_curvature(window, cell_size_x=1.0, cell_size_y=1.0, curv_type='plan'):
    """
    Compute curvature using Zevenbergen-Thorne method.
    curv_type: 'plan' for plan curvature, 'profile' for profile curvature
    """
    a, b, c = window[0]
    d, e, f = window[1]
    g, h, i = window[2]

    dx = cell_size_x
    dy = cell_size_y

    # Second derivatives
    d2zdx2 = ((c + 2*f + i) - 2*(b + 2*e + h) + (a + 2*d + g)) / (3 * dx * dx)
    d2zdy2 = ((g + 2*h + i) - 2*(d + 2*e + f) + (a + 2*b + c)) / (3 * dy * dy)
    d2zdxdy = ((a + 2*b + c) - (g + 2*h + i) - (a + 2*d + g) + (c + 2*f + i)) / (4 * dx * dy) * -1

    # First derivatives
    dzdx = ((c + 2*f + i) - (a + 2*d + g)) / (8 * dx)
    dzdy = ((g + 2*h + i) - (a + 2*b + c)) / (8 * dy)

    p = dzdx
    q = dzdy
    denom = p*p + q*q

    if curv_type == 'plan':
        # Plan curvature
        if denom == 0:
            return 0.0
        return -2.0 * (d2zdx2 * q * q - 2 * d2zdxdy * p * q + d2zdy2 * p * p) / denom
    else:
        # Profile curvature
        if denom == 0:
            return 0.0
        return -2.0 * (d2zdx2 * p * p + 2 * d2zdxdy * p * q + d2zdy2 * q * q) / denom


def compute_tri(window):
    """Compute Terrain Ruggedness Index (Riley et al. 1999)."""
    center = window[1][1]
    total = 0.0
    count = 0
    for dr in range(3):
        for dc in range(3):
            if dr == 1 and dc == 1:
                continue
            diff = window[dr][dc] - center
            total += diff * diff
            count += 1
    return math.sqrt(total / count) if count > 0 else 0.0


def compute_tpi(window):
    """Compute Topographic Position Index."""
    center = window[1][1]
    total = 0.0
    count = 0
    for dr in range(3):
        for dc in range(3):
            if dr == 1 and dc == 1:
                continue
            total += window[dr][dc]
            count += 1
    mean_neighbor = total / count if count > 0 else center
    return center - mean_neighbor


def compute_roughness(window):
    """Compute roughness (max elevation difference in window)."""
    min_val = float('inf')
    max_val = float('-inf')
    for row in window:
        for val in row:
            if val < min_val:
                min_val = val
            if val > max_val:
                max_val = val
    return max_val - min_val


# D8 flow direction encoding
# 64  128  1
# 32  0    2
# 16  8    4
D8_CODES = [
    [64, 128, 1],
    [32, 0, 2],
    [16, 8, 4]
]

D8_OFFSETS = {
    1: (-1, 1),
    2: (0, 1),
    4: (1, 1),
    8: (1, 0),
    16: (1, -1),
    32: (0, -1),
    64: (-1, -1),
    128: (-1, 0)
}

# Distances for D8 (diagonal = sqrt(2), cardinal = 1)
D8_DISTANCES = {
    1: math.sqrt(2),
    2: 1.0,
    4: math.sqrt(2),
    8: 1.0,
    16: math.sqrt(2),
    32: 1.0,
    64: math.sqrt(2),
    128: 1.0
}


def compute_flow_direction(row, col, dem, nodata_val=-9999.0):
    """Compute D8 flow direction for a single cell."""
    height = dem.height
    width = dem.width
    center_val = dem.data[row][col]

    if dem.nodata is not None and center_val == dem.nodata:
        return 0

    max_drop = -float('inf')
    max_dir = 0

    for dr in range(-1, 2):
        for dc in range(-1, 2):
            if dr == 0 and dc == 0:
                continue
            r, c = row + dr, col + dc
            if 0 <= r < height and 0 <= c < width:
                neighbor_val = dem.data[r][c]
                if dem.nodata is not None and neighbor_val == dem.nodata:
                    continue
                dist = math.sqrt(dr*dr + dc*dc)
                drop = (center_val - neighbor_val) / dist
                if drop > max_drop:
                    max_drop = drop
                    max_dir = D8_CODES[dr + 1][dc + 1]

    return max_dir


def compute_flow_direction_grid(dem):
    """Compute D8 flow direction for entire grid."""
    height = dem.height
    width = dem.width
    result = []

    for row in range(height):
        row_data = []
        for col in range(width):
            fd = compute_flow_direction(row, col, dem, dem.nodata)
            row_data.append(float(fd))
        result.append(row_data)

    return result


def compute_flow_accumulation(flow_dir_grid, width, height):
    """Compute flow accumulation from flow direction grid."""
    # Initialize accumulation grid with 1 for each cell
    acc = [[1.0 for _ in range(width)] for _ in range(height)]

    # Build downstream mapping
    downstream = [[0 for _ in range(width)] for _ in range(height)]
    in_degree = [[0 for _ in range(width)] for _ in range(height)]

    for row in range(height):
        for col in range(width):
            fd = int(flow_dir_grid[row][col])
            if fd in D8_OFFSETS:
                dr, dc = D8_OFFSETS[fd]
                nr, nc = row + dr, col + dc
                if 0 <= nr < height and 0 <= nc < width:
                    downstream[row][col] = (nr, nc)
                    in_degree[nr][nc] += 1

    # Topological sort using BFS
    queue = deque()
    for row in range(height):
        for col in range(width):
            if in_degree[row][col] == 0:
                queue.append((row, col))

    while queue:
        row, col = queue.popleft()
        if downstream[row][col] != 0:
            nr, nc = downstream[row][col]
            acc[nr][nc] += acc[row][col]
            in_degree[nr][nc] -= 1
            if in_degree[nr][nc] == 0:
                queue.append((nr, nc))

    return acc


def compute_watershed(flow_dir_grid, outlet_row, outlet_col, width, height):
    """Delineate watershed for given outlet point."""
    # Reverse flow direction to find upstream cells
    upstream = [[[] for _ in range(width)] for _ in range(height)]

    for row in range(height):
        for col in range(width):
            fd = int(flow_dir_grid[row][col])
            if fd in D8_OFFSETS:
                dr, dc = D8_OFFSETS[fd]
                nr, nc = row + dr, col + dc
                if 0 <= nr < height and 0 <= nc < width:
                    upstream[nr][nc].append((row, col))

    # BFS from outlet
    watershed = [[0.0 for _ in range(width)] for _ in range(height)]
    visited = [[False for _ in range(width)] for _ in range(height)]
    queue = deque()
    queue.append((outlet_row, outlet_col))
    visited[outlet_row][outlet_col] = True
    watershed[outlet_row][outlet_col] = 1.0

    while queue:
        row, col = queue.popleft()
        for ur, uc in upstream[row][col]:
            if not visited[ur][uc]:
                visited[ur][uc] = True
                watershed[ur][uc] = 1.0
                queue.append((ur, uc))

    return watershed


def compute_viewshed(dem, obs_row, obs_col, obs_height=1.7, target_height=0.0):
    """
    Compute viewshed using simple line-of-sight algorithm.
    Returns grid where 1 = visible, 0 = not visible.
    """
    height = dem.height
    width = dem.width
    viewshed = [[0.0 for _ in range(width)] for _ in range(height)]

    if obs_row < 0 or obs_row >= height or obs_col < 0 or obs_col >= width:
        return viewshed

    obs_elev = dem.data[obs_row][obs_col]
    if dem.nodata is not None and obs_elev == dem.nodata:
        return viewshed

    obs_elev += obs_height

    # Check visibility for each cell
    for row in range(height):
        for col in range(width):
            if row == obs_row and col == obs_col:
                viewshed[row][col] = 1.0
                continue

            target_elev = dem.data[row][col]
            if dem.nodata is not None and target_elev == dem.nodata:
                continue
            target_elev += target_height

            # Trace line from observer to target
            visible = True
            dr = row - obs_row
            dc = col - obs_col
            dist = math.sqrt(dr*dr + dc*dc)
            if dist == 0:
                viewshed[row][col] = 1.0
                continue

            steps = int(max(abs(dr), abs(dc)))
            if steps == 0:
                viewshed[row][col] = 1.0
                continue

            max_tan = (target_elev - obs_elev) / dist

            for step in range(1, steps):
                t = step / steps
                r = obs_row + dr * t
                c = obs_col + dc * t

                ri = int(round(r))
                ci = int(round(c))

                if 0 <= ri < height and 0 <= ci < width:
                    cell_elev = dem.data[ri][ci]
                    if dem.nodata is not None and cell_elev == dem.nodata:
                        continue

                    step_dist = math.sqrt((r - obs_row)**2 + (c - obs_col)**2)
                    if step_dist > 0:
                        required_tan = (cell_elev - obs_elev) / step_dist
                        if required_tan > max_tan:
                            visible = False
                            break

            if visible:
                viewshed[row][col] = 1.0

    return viewshed


def marching_squares_contours(dem, interval=10.0, nodata_val=-9999.0):
    """
    Generate contour lines using marching squares algorithm.
    Returns list of contour lines as GeoJSON features.
    """
    height = dem.height
    width = dem.width

    # Find elevation range
    min_elev = float('inf')
    max_elev = float('-inf')
    for row in range(height):
        for col in range(width):
            val = dem.data[row][col]
            if dem.nodata is not None and val == dem.nodata:
                continue
            if math.isnan(val):
                continue
            if val < min_elev:
                min_elev = val
            if val > max_elev:
                max_elev = val

    if min_elev == float('inf'):
        return []

    # Generate contour levels
    first_level = math.ceil(min_elev / interval) * interval
    levels = []
    level = first_level
    while level <= max_elev:
        levels.append(level)
        level += interval

    features = []

    # Get geo transform
    x_origin, pixel_width, y_origin, pixel_height = dem.get_geo_transform()

    for contour_level in levels:
        segments = []

        # Process each 2x2 cell
        for row in range(height - 1):
            for col in range(width - 1):
                # Get 4 corners
                tl = dem.data[row][col]
                tr = dem.data[row][col + 1]
                bl = dem.data[row + 1][col]
                br = dem.data[row + 1][col + 1]

                # Skip if any corner is nodata
                if dem.nodata is not None:
                    if (tl == dem.nodata or tr == dem.nodata or
                        bl == dem.nodata or br == dem.nodata):
                        continue

                # Classify corners
                case = 0
                if tl >= contour_level:
                    case |= 8
                if tr >= contour_level:
                    case |= 4
                if br >= contour_level:
                    case |= 2
                if bl >= contour_level:
                    case |= 1

                if case == 0 or case == 15:
                    continue

                # Interpolate edge crossings
                def interp_y(v1, v2, y1, y2, level):
                    if v2 == v1:
                        return (y1 + y2) / 2
                    return y1 + (level - v1) / (v2 - v1) * (y2 - y1)

                def interp_x(v1, v2, x1, x2, level):
                    if v2 == v1:
                        return (x1 + x2) / 2
                    return x1 + (level - v1) / (v2 - v1) * (x2 - x1)

                # World coordinates
                x0 = x_origin + col * pixel_width
                x1 = x_origin + (col + 1) * pixel_width
                y0 = y_origin + row * pixel_height
                y1 = y_origin + (row + 1) * pixel_height

                # Generate line segments based on case
                line_segments = marching_squares_case(
                    case, tl, tr, br, bl,
                    x0, x1, y0, y1,
                    interp_x, interp_y
                )

                segments.extend(line_segments)

        if segments:
            # Convert to GeoJSON coordinates
            coords = []
            for seg in segments:
                coords.append(seg)

            feature = {
                "type": "Feature",
                "properties": {
                    "elevation": contour_level
                },
                "geometry": {
                    "type": "MultiLineString" if len(coords) > 1 else "LineString",
                    "coordinates": coords if len(coords) > 1 else coords[0]
                }
            }
            features.append(feature)

    return features


def marching_squares_case(case, tl, tr, br, bl, x0, x1, y0, y1, interp_x, interp_y):
    """Generate line segments for a marching squares case."""
    level = (tl + tr + br + bl) / 4  # Approximate level for interpolation

    # Edge midpoints
    top = (interp_x(tl, tr, x0, x1, level), y0)
    bottom = (interp_x(bl, br, x0, x1, level), y1)
    left = (x0, interp_y(tl, bl, y0, y1, level))
    right = (x1, interp_y(tr, br, y0, y1, level))

    segments = []

    if case == 1:
        segments.append([left, bottom])
    elif case == 2:
        segments.append([bottom, right])
    elif case == 3:
        segments.append([left, right])
    elif case == 4:
        segments.append([top, right])
    elif case == 5:
        # Saddle point - two segments
        segments.append([left, top])
        segments.append([bottom, right])
    elif case == 6:
        segments.append([top, bottom])
    elif case == 7:
        segments.append([left, top])
    elif case == 8:
        segments.append([top, left])
    elif case == 9:
        segments.append([top, bottom])
    elif case == 10:
        # Saddle point - two segments
        segments.append([top, right])
        segments.append([left, bottom])
    elif case == 11:
        segments.append([top, right])
    elif case == 12:
        segments.append([left, right])
    elif case == 13:
        segments.append([bottom, right])
    elif case == 14:
        segments.append([left, bottom])

    return segments


# ============================================================================
# Batch Processing
# ============================================================================

def analyze_dem(input_path, analysis_type, output_path=None, **kwargs):
    """Run a single terrain analysis."""
    dem = GeoTIFF.read(input_path)

    cell_size_x = abs(dem.pixel_scale[0]) if len(dem.pixel_scale) >= 2 else 1.0
    cell_size_y = abs(dem.pixel_scale[1]) if len(dem.pixel_scale) >= 2 else 1.0

    if output_path is None:
        base = os.path.splitext(input_path)[0]
        ext = '.geojson' if analysis_type == 'contour' else '.tif'
        output_path = f"{base}_{analysis_type}{ext}"

    result = None

    if analysis_type == 'slope':
        unit = kwargs.get('unit', 'degrees')
        result = []
        for row in range(dem.height):
            row_data = []
            for col in range(dem.width):
                w = get_3x3_window(dem, row, col, dem.nodata)
                if w is None:
                    row_data.append(dem.nodata if dem.nodata else -9999.0)
                else:
                    row_data.append(compute_slope(w, cell_size_x, cell_size_y, unit))
            result.append(row_data)
        GeoTIFF.write(output_path, result, dem.width, dem.height,
                      nodata=dem.nodata, pixel_scale=dem.pixel_scale,
                      tie_point=dem.tie_point)

    elif analysis_type == 'aspect':
        result = []
        for row in range(dem.height):
            row_data = []
            for col in range(dem.width):
                w = get_3x3_window(dem, row, col, dem.nodata)
                if w is None:
                    row_data.append(dem.nodata if dem.nodata else -9999.0)
                else:
                    row_data.append(compute_aspect(w, cell_size_x, cell_size_y))
            result.append(row_data)
        GeoTIFF.write(output_path, result, dem.width, dem.height,
                      nodata=dem.nodata, pixel_scale=dem.pixel_scale,
                      tie_point=dem.tie_point)

    elif analysis_type == 'hillshade':
        azimuth = kwargs.get('azimuth', 315.0)
        altitude = kwargs.get('altitude', 45.0)
        result = []
        for row in range(dem.height):
            row_data = []
            for col in range(dem.width):
                w = get_3x3_window(dem, row, col, dem.nodata)
                if w is None:
                    row_data.append(dem.nodata if dem.nodata else -9999.0)
                else:
                    row_data.append(float(compute_hillshade(w, cell_size_x, cell_size_y, azimuth, altitude)))
            result.append(row_data)
        GeoTIFF.write(output_path, result, dem.width, dem.height,
                      nodata=dem.nodata, pixel_scale=dem.pixel_scale,
                      tie_point=dem.tie_point)

    elif analysis_type == 'contour':
        interval = kwargs.get('interval', 10.0)
        features = marching_squares_contours(dem, interval)
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, indent=2)

    elif analysis_type == 'curvature':
        curv_type = kwargs.get('type', 'plan')
        result = []
        for row in range(dem.height):
            row_data = []
            for col in range(dem.width):
                w = get_3x3_window(dem, row, col, dem.nodata)
                if w is None:
                    row_data.append(dem.nodata if dem.nodata else -9999.0)
                else:
                    row_data.append(compute_curvature(w, cell_size_x, cell_size_y, curv_type))
            result.append(row_data)
        GeoTIFF.write(output_path, result, dem.width, dem.height,
                      nodata=dem.nodata, pixel_scale=dem.pixel_scale,
                      tie_point=dem.tie_point)

    elif analysis_type == 'tri':
        result = []
        for row in range(dem.height):
            row_data = []
            for col in range(dem.width):
                w = get_3x3_window(dem, row, col, dem.nodata)
                if w is None:
                    row_data.append(dem.nodata if dem.nodata else -9999.0)
                else:
                    row_data.append(compute_tri(w))
            result.append(row_data)
        GeoTIFF.write(output_path, result, dem.width, dem.height,
                      nodata=dem.nodata, pixel_scale=dem.pixel_scale,
                      tie_point=dem.tie_point)

    elif analysis_type == 'tpi':
        window_size = kwargs.get('window', 3)
        result = []
        for row in range(dem.height):
            row_data = []
            for col in range(dem.width):
                if window_size == 3:
                    w = get_3x3_window(dem, row, col, dem.nodata)
                else:
                    # Larger window - compute mean of neighborhood
                    half = window_size // 2
                    center = dem.data[row][col]
                    if dem.nodata is not None and center == dem.nodata:
                        row_data.append(dem.nodata)
                        continue
                    total = 0.0
                    count = 0
                    for dr in range(-half, half + 1):
                        for dc in range(-half, half + 1):
                            r, c2 = row + dr, col + dc
                            if 0 <= r < dem.height and 0 <= c2 < dem.width:
                                v = dem.data[r][c2]
                                if dem.nodata is None or v != dem.nodata:
                                    total += v
                                    count += 1
                    mean = total / count if count > 0 else center
                    row_data.append(center - mean)
                    continue

                if w is None:
                    row_data.append(dem.nodata if dem.nodata else -9999.0)
                else:
                    row_data.append(compute_tpi(w))
            result.append(row_data)
        GeoTIFF.write(output_path, result, dem.width, dem.height,
                      nodata=dem.nodata, pixel_scale=dem.pixel_scale,
                      tie_point=dem.tie_point)

    elif analysis_type == 'roughness':
        result = []
        for row in range(dem.height):
            row_data = []
            for col in range(dem.width):
                w = get_3x3_window(dem, row, col, dem.nodata)
                if w is None:
                    row_data.append(dem.nodata if dem.nodata else -9999.0)
                else:
                    row_data.append(compute_roughness(w))
            result.append(row_data)
        GeoTIFF.write(output_path, result, dem.width, dem.height,
                      nodata=dem.nodata, pixel_scale=dem.pixel_scale,
                      tie_point=dem.tie_point)

    elif analysis_type == 'flowdir':
        result = compute_flow_direction_grid(dem)
        GeoTIFF.write(output_path, result, dem.width, dem.height,
                      nodata=dem.nodata, pixel_scale=dem.pixel_scale,
                      tie_point=dem.tie_point)

    elif analysis_type == 'flowacc':
        flow_dir = compute_flow_direction_grid(dem)
        result = compute_flow_accumulation(flow_dir, dem.width, dem.height)
        GeoTIFF.write(output_path, result, dem.width, dem.height,
                      nodata=dem.nodata, pixel_scale=dem.pixel_scale,
                      tie_point=dem.tie_point)

    elif analysis_type == 'viewshed':
        obs_row = kwargs.get('obs_row', dem.height // 2)
        obs_col = kwargs.get('obs_col', dem.width // 2)
        obs_height = kwargs.get('obs_height', 1.7)
        target_height = kwargs.get('target_height', 0.0)
        result = compute_viewshed(dem, obs_row, obs_col, obs_height, target_height)
        GeoTIFF.write(output_path, result, dem.width, dem.height,
                      nodata=dem.nodata, pixel_scale=dem.pixel_scale,
                      tie_point=dem.tie_point)

    else:
        raise ValueError(f"Unknown analysis type: {analysis_type}")

    return output_path


def batch_analyze(input_path, output_dir, **kwargs):
    """Run all terrain analyses on a DEM."""
    os.makedirs(output_dir, exist_ok=True)

    analyses = ['slope', 'aspect', 'hillshade', 'contour', 'curvature',
                'tri', 'tpi', 'roughness', 'flowdir', 'flowacc']

    results = {}
    for analysis in analyses:
        ext = '.geojson' if analysis == 'contour' else '.tif'
        output_path = os.path.join(output_dir, f"{analysis}{ext}")
        try:
            result = analyze_dem(input_path, analysis, output_path, **kwargs)
            results[analysis] = result
            print(f"  {analysis}: {result}")
        except Exception as e:
            print(f"  {analysis}: ERROR - {e}")
            results[analysis] = None

    return results


# ============================================================================
# CLI Interface
# ============================================================================

def create_parser():
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog='dem-terrain-analysis',
        description='DEM Terrain Analysis - Generate terrain derivatives from DEM data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python dem-terrain-analysis.py slope input.tif --output slope.tif --unit degrees
  python dem-terrain-analysis.py aspect input.tif --output aspect.tif
  python dem-terrain-analysis.py hillshade input.tif --azimuth 315 --altitude 45
  python dem-terrain-analysis.py contour input.tif --interval 10
  python dem-terrain-analysis.py batch input.tif --output-dir ./terrain/
        """
    )
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')

    subparsers = parser.add_subparsers(dest='command', help='Analysis type')

    # Common arguments
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('input', help='Input DEM GeoTIFF file')
    common.add_argument('--output', '-o', help='Output file path')

    # Slope
    p_slope = subparsers.add_parser('slope', parents=[common], help='Compute slope')
    p_slope.add_argument('--unit', choices=['degrees', 'percent'], default='degrees',
                         help='Output unit (default: degrees)')

    # Aspect
    subparsers.add_parser('aspect', parents=[common], help='Compute aspect')

    # Hillshade
    p_hs = subparsers.add_parser('hillshade', parents=[common], help='Compute hillshade')
    p_hs.add_argument('--azimuth', type=float, default=315.0, help='Sun azimuth (default: 315)')
    p_hs.add_argument('--altitude', type=float, default=45.0, help='Sun altitude (default: 45)')

    # Contour
    p_contour = subparsers.add_parser('contour', parents=[common], help='Generate contour lines')
    p_contour.add_argument('--interval', type=float, default=10.0, help='Contour interval (default: 10)')

    # Curvature
    p_curv = subparsers.add_parser('curvature', parents=[common], help='Compute curvature')
    p_curv.add_argument('--type', choices=['plan', 'profile'], default='plan',
                        help='Curvature type (default: plan)')

    # TRI
    subparsers.add_parser('tri', parents=[common], help='Compute Terrain Ruggedness Index')

    # TPI
    p_tpi = subparsers.add_parser('tpi', parents=[common], help='Compute Topographic Position Index')
    p_tpi.add_argument('--window', type=int, default=3, help='Window size (default: 3)')

    # Roughness
    subparsers.add_parser('roughness', parents=[common], help='Compute roughness')

    # Flow Direction
    subparsers.add_parser('flowdir', parents=[common], help='Compute D8 flow direction')

    # Flow Accumulation
    subparsers.add_parser('flowacc', parents=[common], help='Compute flow accumulation')

    # Watershed
    p_ws = subparsers.add_parser('watershed', parents=[common], help='Delineate watershed')
    p_ws.add_argument('--outlet-row', type=int, required=True, help='Outlet row index')
    p_ws.add_argument('--outlet-col', type=int, required=True, help='Outlet column index')

    # Viewshed
    p_vs = subparsers.add_parser('viewshed', parents=[common], help='Compute viewshed')
    p_vs.add_argument('--obs-row', type=int, help='Observer row (default: center)')
    p_vs.add_argument('--obs-col', type=int, help='Observer column (default: center)')
    p_vs.add_argument('--obs-height', type=float, default=1.7, help='Observer height (default: 1.7)')
    p_vs.add_argument('--target-height', type=float, default=0.0, help='Target height (default: 0)')

    # Batch
    p_batch = subparsers.add_parser('batch', parents=[common], help='Generate all products')
    p_batch.add_argument('--output-dir', '-d', default='./terrain/', help='Output directory')

    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    print(f"DEM Terrain Analysis v{__version__}")
    print(f"Input: {args.input}")

    if args.command == 'batch':
        output_dir = args.output_dir
        print(f"Output directory: {output_dir}")
        print("Running all analyses...")
        results = batch_analyze(args.input, output_dir)
        print(f"\nCompleted {len(results)} analyses.")
    else:
        kwargs = {}

        if args.command == 'slope':
            kwargs['unit'] = args.unit
        elif args.command == 'hillshade':
            kwargs['azimuth'] = args.azimuth
            kwargs['altitude'] = args.altitude
        elif args.command == 'contour':
            kwargs['interval'] = args.interval
        elif args.command == 'curvature':
            kwargs['type'] = args.type
        elif args.command == 'tpi':
            kwargs['window'] = args.window
        elif args.command == 'viewshed':
            if args.obs_row is not None:
                kwargs['obs_row'] = args.obs_row
            if args.obs_col is not None:
                kwargs['obs_col'] = args.obs_col
            kwargs['obs_height'] = args.obs_height
            kwargs['target_height'] = args.target_height

        output = analyze_dem(args.input, args.command, args.output, **kwargs)
        print(f"Output: {output}")

    print("Done.")


if __name__ == '__main__':
    main()
