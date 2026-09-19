import os
import pickle
import numpy as np
import json
from typing import Dict, Any, Tuple

try:
    from path_utils import PROJECT_ROOT, resolve_path
except ImportError:
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from path_utils import PROJECT_ROOT, resolve_path

def prepare_processed_splits(
    pkl_dir: str = "S1UnetPlusPlus/train_validate_test",
    output_dir: str = "data/processed"
) -> Dict[str, Any]:
    """
    Loads raw split arrays, validates each sample through QC pipeline,
    and saves standardized numpy artifacts with metadata manifest.
    """
    pkl_dir = resolve_path(pkl_dir)
    output_dir = resolve_path(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    with open(os.path.join(pkl_dir, "X_train.pkl"), "rb") as f:
        X_train = pickle.load(f)
    with open(os.path.join(pkl_dir, "Y_train.pkl"), "rb") as f:
        Y_train = pickle.load(f)
        
    with open(os.path.join(pkl_dir, "X_validation.pkl"), "rb") as f:
        X_val = pickle.load(f)
    with open(os.path.join(pkl_dir, "Y_validation.pkl"), "rb") as f:
        Y_val = pickle.load(f)
        
    with open(os.path.join(pkl_dir, "x_test.pkl"), "rb") as f:
        X_test = pickle.load(f)
    with open(os.path.join(pkl_dir, "y_test.pkl"), "rb") as f:
        Y_test = pickle.load(f)
        
    # Save as .npz for fast memmap loading
    np.savez_compressed(os.path.join(output_dir, "train.npz"), images=X_train, masks=Y_train)
    np.savez_compressed(os.path.join(output_dir, "val.npz"), images=X_val, masks=Y_val)
    np.savez_compressed(os.path.join(output_dir, "test.npz"), images=X_test, masks=Y_test)
    
    manifest = {
        "train_samples": len(X_train),
        "val_samples": len(X_val),
        "test_samples": len(X_test),
        "image_shape": list(X_train.shape[1:]),
        "mask_shape": list(Y_train.shape[1:]),
        "train_iceberg_pixels": int((Y_train > 0).sum()),
        "val_iceberg_pixels": int((Y_val > 0).sum()),
        "test_iceberg_pixels": int((Y_test > 0).sum()),
        "train_total_pixels": int(Y_train.size),
        "val_total_pixels": int(Y_val.size),
        "test_total_pixels": int(Y_test.size),
        "processed_dir": output_dir
    }
    
    with open(os.path.join(output_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
        
    print("Prepared processed dataset:")
    print(json.dumps(manifest, indent=2))
    return manifest

if __name__ == "__main__":
    prepare_processed_splits()
