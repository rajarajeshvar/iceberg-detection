import os
import sys
import json
import rasterio
import numpy as np
from typing import Dict, Any

def inspect_single_tiff(filepath: str) -> Dict[str, Any]:
    """
    Performs comprehensive numerical, structural, and geospatial inspection on a single TIFF file.
    """
    if not os.path.exists(filepath):
        return {"error": f"File does not exist: {filepath}"}
        
    with rasterio.open(filepath) as src:
        arr = src.read()
        n_nans = int(np.isnan(arr).sum())
        n_infs = int(np.isinf(arr).sum())
        
        valid_mask = ~np.isnan(arr)
        if valid_mask.any():
            min_v = float(np.min(arr[valid_mask]))
            max_v = float(np.max(arr[valid_mask]))
            mean_v = float(np.mean(arr[valid_mask]))
            std_v = float(np.std(arr[valid_mask]))
        else:
            min_v, max_v, mean_v, std_v = 0.0, 0.0, 0.0, 0.0
            
        channel_stats = []
        for c in range(src.count):
            c_data = arr[c]
            c_valid = ~np.isnan(c_data)
            if c_valid.any():
                channel_stats.append({
                    "channel": c,
                    "min": float(np.min(c_data[c_valid])),
                    "max": float(np.max(c_data[c_valid])),
                    "mean": float(np.mean(c_data[c_valid])),
                    "std": float(np.std(c_data[c_valid])),
                    "nans": int(np.isnan(c_data).sum())
                })
            else:
                channel_stats.append({"channel": c, "all_nan": True})
                
        return {
            "filename": os.path.basename(filepath),
            "width": src.width,
            "height": src.height,
            "bands": src.count,
            "dtypes": [str(d) for d in src.dtypes],
            "crs": str(src.crs) if src.crs else None,
            "transform": list(src.transform) if src.transform else None,
            "bounds": [src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top] if src.transform else None,
            "nodata": src.nodata,
            "global_min": min_v,
            "global_max": max_v,
            "global_mean": mean_v,
            "global_std": std_v,
            "total_nans": n_nans,
            "total_infs": n_infs,
            "channel_stats": channel_stats
        }

if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = "S1UnetPlusPlus/imgs/S1A_EW_GRDM_1SDH_20160607T191602_20160607T191702_011609_011BF1_E168_3996_40_rm_thermal_noise_hvTrue_rm_texture_noise_hvTrue_25WES_2_2__ID24.tif"
    res = inspect_single_tiff(path)
    print(json.dumps(res, indent=2))
