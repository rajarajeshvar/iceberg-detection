import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import json
import torch
import cv2
import numpy as np
import rasterio

try:
    from path_utils import PROJECT_ROOT, resolve_path
except ImportError:
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from path_utils import PROJECT_ROOT, resolve_path

from models.segformer import SegFormerB0Iceberg
from training.dataset import get_dataloaders
from training.evaluate import compute_segmentation_metrics

def diagnose_dataset_and_errors():
    print("="*70)
    print("PHASE 1: DATA & MASK DEEP VALIDATION")
    print("="*70)
    
    train_npz = np.load(resolve_path("data/processed/train.npz"))
    val_npz = np.load(resolve_path("data/processed/val.npz"))
    test_npz = np.load(resolve_path("data/processed/test.npz"))
    
    X_tr, Y_tr = train_npz["images"], train_npz["masks"]
    X_val, Y_val = val_npz["images"], val_npz["masks"]
    X_te, Y_te = test_npz["images"], test_npz["masks"]
    
    print(f"Train Set: {X_tr.shape} images, {Y_tr.shape} masks")
    print(f"Val Set:   {X_val.shape} images, {Y_val.shape} masks")
    print(f"Test Set:  {X_te.shape} images, {Y_te.shape} masks")
    
    # Class imbalance stats
    for name, Y in [("Train", Y_tr), ("Val", Y_val), ("Test", Y_te)]:
        iceberg_px = int((Y > 0).sum())
        total_px = int(Y.size)
        bg_px = total_px - iceberg_px
        ratio = iceberg_px / total_px
        pos_weight = bg_px / max(1, iceberg_px)
        
        # Count empty scenes
        empty_scenes = sum(1 for i in range(len(Y)) if (Y[i] > 0).sum() == 0)
        
        # Iceberg size distribution in pixels
        sizes = [(Y[i] > 0).sum() for i in range(len(Y)) if (Y[i] > 0).sum() > 0]
        
        print(f"\n{name} Split Imbalance Stats:")
        print(f"  - Total Pixels: {total_px:,} | Background: {bg_px:,} ({(bg_px/total_px)*100:.2f}%)")
        print(f"  - Iceberg Pixels: {iceberg_px:,} ({(ratio)*100:.2f}%)")
        print(f"  - Imbalance Ratio (Neg:Pos): {pos_weight:.2f} : 1")
        print(f"  - Empty Scenes (0 iceberg px): {empty_scenes} / {len(Y)}")
        if sizes:
            print(f"  - Iceberg sizes per tile: min={min(sizes)} px, median={int(np.median(sizes))} px, max={max(sizes)} px")

    # Inspect SAR pixel intensities on foreground vs background
    print("\nSAR Intensity Breakdown (Foreground vs Background across Train Set):")
    tr_fg_mask = Y_tr[:, 0] > 0
    tr_bg_mask = ~tr_fg_mask
    
    for c in range(3):
        fg_vals = X_tr[:, c][tr_fg_mask]
        bg_vals = X_tr[:, c][tr_bg_mask]
        print(f"  Channel {c}:")
        print(f"    Iceberg (FG): Mean={fg_vals.mean():.4f}, Std={fg_vals.std():.4f}, 5th%={np.percentile(fg_vals, 5):.4f}, 95th%={np.percentile(fg_vals, 95):.4f}")
        print(f"    Background:   Mean={bg_vals.mean():.4f}, Std={bg_vals.std():.4f}, 5th%={np.percentile(bg_vals, 5):.4f}, 95th%={np.percentile(bg_vals, 95):.4f}")

    print("\n" + "="*70)
    print("PHASE 2: QUALITATIVE ERROR ANALYSIS ON VALIDATION SET")
    print("="*70)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = SegFormerB0Iceberg(num_classes=2).to(device)
    ckpt = torch.load(resolve_path("outputs/checkpoints/best_model.pt"), map_location=device)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    
    err_dir = resolve_path("outputs/error_analysis")
    os.makedirs(err_dir, exist_ok=True)
    
    error_categories = {
        "missed_iceberg": 0,          # Recall < 0.2 when GT > 0
        "partial_segmentation": 0,    # 0.2 <= Recall < 0.7
        "boundary_error": 0,          # Dice between 0.5 and 0.8
        "false_positive_clean": 0,    # Pred > 0 when GT == 0
        "false_positive_heavy": 0,    # Precision < 0.3 when GT > 0
        "correct_high_quality": 0,    # Dice >= 0.7
        "true_negative_clean": 0      # Pred == 0 and GT == 0
    }
    
    detailed_samples = []
    
    with torch.no_grad():
        for i in range(len(X_val)):
            img = X_val[i]  # (3, 256, 256)
            gt = Y_val[i, 0]  # (256, 256)
            
            inp = torch.tensor(img, dtype=torch.float32).unsqueeze(0).to(device)
            probs = model.predict_probability(inp).squeeze(0).cpu().numpy()
            pred = (probs >= 0.5).astype(np.int64)
            
            m = compute_segmentation_metrics(pred, gt)
            gt_px = int(gt.sum())
            pred_px = int(pred.sum())
            
            # Categorize
            if gt_px == 0:
                if pred_px == 0:
                    cat = "true_negative_clean"
                else:
                    cat = "false_positive_clean"
            else:
                if pred_px == 0 or m["recall"] < 0.2:
                    cat = "missed_iceberg"
                elif m["precision"] < 0.3:
                    cat = "false_positive_heavy"
                elif m["recall"] < 0.7:
                    cat = "partial_segmentation"
                elif m["dice_f1"] >= 0.7:
                    cat = "correct_high_quality"
                else:
                    cat = "boundary_error"
                    
            error_categories[cat] += 1
            
            sample_report = {
                "val_idx": i,
                "category": cat,
                "gt_pixels": gt_px,
                "pred_pixels": pred_px,
                "dice": round(m["dice_f1"], 4),
                "iou": round(m["iceberg_iou"], 4),
                "precision": round(m["precision"], 4),
                "recall": round(m["recall"], 4)
            }
            detailed_samples.append(sample_report)
            
            # Generate qualitative 4-panel image for visual inspection
            sar_gray = (np.clip(img[0], 0, 1) * 255).astype(np.uint8)
            sar_bgr = cv2.cvtColor(sar_gray, cv2.COLOR_GRAY2BGR)
            
            # GT Overlay (Green)
            gt_overlay = sar_bgr.copy()
            gt_overlay[gt > 0] = [0, 255, 0]
            
            # Prediction Overlay (Red = Pred, Yellow = Overlap)
            pred_overlay = sar_bgr.copy()
            pred_overlay[pred > 0] = [0, 0, 255] # Red for pred
            pred_overlay[np.logical_and(pred > 0, gt > 0)] = [0, 255, 255] # Yellow for True Positive
            
            # Probability Heatmap
            prob_color = cv2.applyColorMap((probs * 255).astype(np.uint8), cv2.COLORMAP_JET)
            
            top = np.hstack([sar_bgr, gt_overlay])
            bot = np.hstack([prob_color, pred_overlay])
            quad = np.vstack([top, bot])
            
            # Add text
            header = f"Val #{i:02d} | Cat: {cat} | Dice: {m['dice_f1']:.2f} | P: {m['precision']:.2f} | R: {m['recall']:.2f}"
            cv2.putText(quad, header, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
            
            cv2.imwrite(os.path.join(err_dir, f"val_{i:02d}_{cat}.png"), quad)

    print("\nValidation Set Error Distribution (38 samples):")
    for k, v in error_categories.items():
        print(f"  - {k:24s}: {v:2d} samples ({(v/len(X_val))*100:.1f}%)")
        
    with open(os.path.join(err_dir, "diagnosis_report.json"), "w") as f:
        json.dump({
            "error_categories": error_categories,
            "detailed_samples": detailed_samples
        }, f, indent=2)
        
    print("\nSaved qualitative analysis images to outputs/error_analysis/")
    return error_categories, detailed_samples

if __name__ == "__main__":
    diagnose_dataset_and_errors()
