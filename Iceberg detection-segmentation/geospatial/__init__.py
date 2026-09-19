"""Geospatial processing package for Sentinel-1 SAR Iceberg Segmentation."""

from .metadata import extract_tiff_metadata, parse_s1_filename
from .coordinates import CoordinateTransformer, pixel_to_projected, projected_to_geographic
from .measurements import compute_iceberg_geometric_features

__all__ = [
    "extract_tiff_metadata",
    "parse_s1_filename",
    "CoordinateTransformer",
    "pixel_to_projected",
    "projected_to_geographic",
    "compute_iceberg_geometric_features",
]
