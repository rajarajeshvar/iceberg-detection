import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import torch
import numpy as np
import json
import torch.nn.functional as F

try:
    from path_utils import PROJECT_ROOT, resolve_path
except ImportError:
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from path_utils import PROJECT_ROOT, resolve_path

from models.segformer import SegFormerB0Iceberg
from training.evaluate import compute_segmentation_metrics

def sweep_validation_thresholds(ckpt_path="outputs/checkpoints/best_model.pt"):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = SegFormerB0Iceberg(num_classes=2).to(device)
    resolved_ckpt = resolve_path(ckpt_path)
    ckpt = torch.load(resolved_ckpt, map_location=device)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    
    val_npz = np.load(resolve_path("data/processed/val.npz"))
    X_val = val_npz["images"]
    Y_val = val_npz["masks"][:, 0]
    
    # Precompute all validation probability maps
    all_probs = []
    with torch.no_grad():
        for i in range(len(X_val)):
            inp = torch.tensor(X_val[i], dtype=torch.float32).unsqueeze(0).to(device)
            p = model.predict_probability(inp).squeeze(0).cpu().numpy()
            all_probs.append(p)
    all_probs = np.array(all_probs)
    
    thresholds = [0.10, 0.20, 0.30, 0.40, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]
    results = []
    
    print(f"{'Threshold':>9} | {'Dice / F1':>10} | {'IoU':>8} | {'Precision':>10} | {'Recall':>8} | {'Pixel Acc':>10}")
    print("-" * 65)
    
    best_dice = 0.0
    best_t = 0.5
    
    for t in thresholds:
        preds = (all_probs >= t).astype(np.int64)
        m = compute_segmentation_metrics(preds, Y_val)
        dice = m["dice_f1"]
        iou = m["iceberg_iou"]
        prec = m["precision"]
        rec = m["recall"]
        acc = m["pixel_accuracy"]
        
        print(f"{t:9.2f} | {dice*100:9.2f}% | {iou*100:7.2f}% | {prec*100:9.2f}% | {rec*100:7.2f}% | {acc*100:9.2f}%")
        
        results.append({
            "threshold": t,
            "dice": dice,
            "iou": iou,
            "precision": prec,
            "recall": rec,
            "pixel_accuracy": acc
        })
        
        if dice > best_dice:
            best_dice = dice
            best_t = t
            
    print("-" * 65)
    print(f"Optimal Validation Threshold: {best_t:.2f} (Val Dice: {best_dice*100:.2f}%)")
    return best_t, results

if __name__ == "__main__":
    sweep_validation_thresholds()
