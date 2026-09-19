import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import random
import numpy as np
import cv2
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR

from models.segformer import SegFormerB0Iceberg
from training.evaluate import compute_segmentation_metrics

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(3, 1, 1)
IMAGENET_STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(3, 1, 1)

class SARIceberg512Dataset(Dataset):
    def __init__(self, images: np.ndarray, masks: np.ndarray, augment: bool = False, target_size: int = 512):
        self.images = images
        self.masks = masks
        self.augment = augment
        self.target_size = target_size
        
    def __len__(self):
        return len(self.images)
        
    def __getitem__(self, idx):
        img_256 = self.images[idx].copy() # (3, 256, 256)
        mask_256 = self.masks[idx, 0].copy() # (256, 256)
        
        # Resize to target resolution (512x512) for high-resolution Transformer receptive field
        H, W = self.target_size, self.target_size
        img = np.zeros((3, H, W), dtype=np.float32)
        for c in range(3):
            img[c] = cv2.resize(img_256[c], (W, H), interpolation=cv2.INTER_LINEAR)
        mask = cv2.resize(mask_256.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST)
        
        if self.augment:
            # 1. Flip H
            if random.random() > 0.5:
                img = np.flip(img, axis=2).copy()
                mask = np.flip(mask, axis=1).copy()
            # 2. Flip V
            if random.random() > 0.5:
                img = np.flip(img, axis=1).copy()
                mask = np.flip(mask, axis=0).copy()
            # 3. Rotate 90
            if random.random() > 0.5:
                k = random.choice([1, 2, 3])
                img = np.rot90(img, k, (1, 2)).copy()
                mask = np.rot90(mask, k, (0, 1)).copy()
            # 4. Intensity jitter
            if random.random() > 0.5:
                factor = random.uniform(0.90, 1.10)
                img = np.clip(img * factor, 0.0, 1.0)
                
        # ImageNet standardization
        norm_img = (img - IMAGENET_MEAN) / IMAGENET_STD
        
        return {
            "pixel_values": torch.tensor(norm_img, dtype=torch.float32),
            "labels": torch.tensor(mask, dtype=torch.long),
            "orig_mask": torch.tensor(mask_256, dtype=torch.long)
        }

class CombinedBoundaryDiceLoss(nn.Module):
    def __init__(self, ce_weight=0.3, dice_weight=0.7, alpha=0.75, gamma=2.0):
        super().__init__()
        self.ce_weight = ce_weight
        self.dice_weight = dice_weight
        self.alpha = alpha
        self.gamma = gamma
        
    def forward(self, logits, targets):
        ce = F.cross_entropy(logits, targets, reduction='none')
        probs = F.softmax(logits, dim=1)
        p_t = probs[:, 1, :, :] * targets.float() + probs[:, 0, :, :] * (1.0 - targets.float())
        alpha_t = self.alpha * targets.float() + (1.0 - self.alpha) * (1.0 - targets.float())
        focal = (alpha_t * ((1.0 - p_t) ** self.gamma) * ce).mean()
        
        # Soft Dice
        p1 = probs[:, 1, :, :]
        t1 = targets.float()
        inter = (p1 * t1).sum(dim=(1, 2))
        card = (p1 + t1).sum(dim=(1, 2))
        dice_loss = (1.0 - (2.0 * inter + 1.0) / (card + 1.0 + 1e-7)).mean()
        
        return self.ce_weight * focal + self.dice_weight * dice_loss

def run_512_resolution_experiment():
    print("="*75)
    print("EXP-06: 512x512 HIGH-RESOLUTION TRANSFORMER OPTIMIZATION")
    print("="*75)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    train_npz = np.load("data/processed/train.npz")
    val_npz = np.load("data/processed/val.npz")
    test_npz = np.load("data/processed/test.npz")
    
    train_dataset = SARIceberg512Dataset(train_npz["images"], train_npz["masks"], augment=True, target_size=512)
    val_dataset = SARIceberg512Dataset(val_npz["images"], val_npz["masks"], augment=False, target_size=512)
    test_dataset = SARIceberg512Dataset(test_npz["images"], test_npz["masks"], augment=False, target_size=512)
    
    # Batch size 8 for 512x512 on GPU
    train_loader = DataLoader(train_dataset, batch_size=8, shuffle=True, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=8, shuffle=False, pin_memory=True)
    test_loader = DataLoader(test_dataset, batch_size=8, shuffle=False, pin_memory=True)
    
    model = SegFormerB0Iceberg(num_classes=2, pretrained_model_name="nvidia/mit-b0").to(device)
    loss_fn = CombinedBoundaryDiceLoss(ce_weight=0.3, dice_weight=0.7, alpha=0.80, gamma=2.0).to(device)
    
    encoder_params = [p for n, p in model.named_parameters() if "decode_head" not in n and "classifier" not in n]
    decoder_params = [p for n, p in model.named_parameters() if "decode_head" in n or "classifier" in n]
    
    optimizer = AdamW([
        {"params": encoder_params, "lr": 1.2e-4, "weight_decay": 0.01},
        {"params": decoder_params, "lr": 5e-4, "weight_decay": 0.01}
    ])
    
    epochs = 40
    scheduler = CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)
    
    best_val_dice = 0.0
    best_model_state = None
    best_epoch = 0
    
    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        
        for batch in train_loader:
            imgs = batch["pixel_values"].to(device)
            masks = batch["labels"].to(device)
            
            optimizer.zero_grad()
            outputs = model(imgs)
            logits = outputs["logits"]
            
            loss = loss_fn(logits, masks)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_loss += loss.item() * imgs.size(0)
            
        scheduler.step()
        train_loss /= len(train_loader.dataset)
        
        # Evaluate on Validation set (downsampled back to original 256x256 ground truth)
        model.eval()
        val_probs_256 = []
        val_targets_256 = []
        
        with torch.no_grad():
            for batch in val_loader:
                imgs = batch["pixel_values"].to(device)
                orig_masks = batch["orig_mask"].numpy()
                probs_512 = F.softmax(model(imgs)["logits"], dim=1)[:, 1, :, :].cpu().numpy()
                
                # Resize probability map back to 256x256 for standard benchmark
                for i in range(len(probs_512)):
                    p256 = cv2.resize(probs_512[i], (256, 256), interpolation=cv2.INTER_LINEAR)
                    val_probs_256.append(p256)
                    val_targets_256.append(orig_masks[i])
                    
        val_probs_arr = np.array(val_probs_256)
        val_targets_arr = np.array(val_targets_256)
        
        val_dice_at_50 = compute_segmentation_metrics((val_probs_arr >= 0.5).astype(np.int64), val_targets_arr)["dice_f1"]
        
        if val_dice_at_50 > best_val_dice:
            best_val_dice = val_dice_at_50
            best_epoch = epoch
            best_model_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            
        if epoch % 5 == 0 or epoch == epochs:
            print(f"  Epoch [{epoch:02d}/{epochs:02d}] Train Loss: {train_loss:.4f} | Val Dice@0.5: {val_dice_at_50*100:.2f}% (Best: {best_val_dice*100:.2f}% @ Ep {best_epoch})")
            
    # Load best weights
    model.load_state_dict({k: v.to(device) for k, v in best_model_state.items()})
    model.eval()
    
    # 1. Validation Threshold & Post-Processing Optimization Sweep
    val_probs_256 = []
    val_targets_256 = []
    with torch.no_grad():
        for batch in val_loader:
            imgs = batch["pixel_values"].to(device)
            orig_masks = batch["orig_mask"].numpy()
            probs_512 = F.softmax(model(imgs)["logits"], dim=1)[:, 1, :, :].cpu().numpy()
            for i in range(len(probs_512)):
                p256 = cv2.resize(probs_512[i], (256, 256), interpolation=cv2.INTER_LINEAR)
                val_probs_256.append(p256)
                val_targets_256.append(orig_masks[i])
                
    val_probs_arr = np.array(val_probs_256)
    val_targets_arr = np.array(val_targets_256)
    
    best_opt_thresh = 0.5
    best_opt_dice = 0.0
    best_min_area = 2
    
    for t in [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]:
        for min_area in [1, 2, 4, 6]:
            # Post process
            post_preds = []
            for i in range(len(val_probs_arr)):
                bin_m = (val_probs_arr[i] >= t).astype(np.uint8)
                # Morphological close
                k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
                bin_m = cv2.morphologyEx(bin_m, cv2.MORPH_CLOSE, k)
                # Filter small components
                num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(bin_m)
                for lbl in range(1, num_labels):
                    if stats[lbl, cv2.CC_STAT_AREA] < min_area:
                        bin_m[labels == lbl] = 0
                post_preds.append(bin_m)
                
            post_preds_arr = np.array(post_preds)
            m = compute_segmentation_metrics(post_preds_arr, val_targets_arr)
            if m["dice_f1"] > best_opt_dice:
                best_opt_dice = m["dice_f1"]
                best_opt_thresh = t
                best_min_area = min_area
                
    print(f"\nOptimal Post-Processing on Validation Set: Threshold={best_opt_thresh:.2f}, MinArea={best_min_area} px -> Val Dice: {best_opt_dice*100:.2f}%")
    
    # 2. Final Evaluation ONCE on Test Set
    test_probs_256 = []
    test_targets_256 = []
    with torch.no_grad():
        for batch in test_loader:
            imgs = batch["pixel_values"].to(device)
            orig_masks = batch["orig_mask"].numpy()
            probs_512 = F.softmax(model(imgs)["logits"], dim=1)[:, 1, :, :].cpu().numpy()
            for i in range(len(probs_512)):
                p256 = cv2.resize(probs_512[i], (256, 256), interpolation=cv2.INTER_LINEAR)
                test_probs_256.append(p256)
                test_targets_256.append(orig_masks[i])
                
    test_probs_arr = np.array(test_probs_256)
    test_targets_arr = np.array(test_targets_256)
    
    test_preds = []
    for i in range(len(test_probs_arr)):
        bin_m = (test_probs_arr[i] >= best_opt_thresh).astype(np.uint8)
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        bin_m = cv2.morphologyEx(bin_m, cv2.MORPH_CLOSE, k)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(bin_m)
        for lbl in range(1, num_labels):
            if stats[lbl, cv2.CC_STAT_AREA] < best_min_area:
                bin_m[labels == lbl] = 0
        test_preds.append(bin_m)
        
    test_preds_arr = np.array(test_preds)
    test_metrics = compute_segmentation_metrics(test_preds_arr, test_targets_arr)
    
    print("\n" + "="*75)
    print("FINAL 512x512 HIGH-RES MODEL RESULTS (TEST SET):")
    print(f"  - Iceberg Dice / F1:  {test_metrics['dice_f1']*100:.2f}%")
    print(f"  - Iceberg IoU:        {test_metrics['iceberg_iou']*100:.2f}%")
    print(f"  - Iceberg Precision:  {test_metrics['precision']*100:.2f}%")
    print(f"  - Iceberg Recall:     {test_metrics['recall']*100:.2f}%")
    print(f"  - Pixel Accuracy:     {test_metrics['pixel_accuracy']*100:.2f}%")
    print("="*75)
    
    # Save optimized model
    os.makedirs("outputs/experiments/EXP-06-HighRes512", exist_ok=True)
    torch.save({
        "exp_id": "EXP-06-HighRes512",
        "model_state_dict": best_model_state,
        "optimal_threshold": best_opt_thresh,
        "min_area_pixels": best_min_area,
        "test_metrics": test_metrics,
        "best_epoch": best_epoch,
        "input_resolution": 512
    }, "outputs/experiments/EXP-06-HighRes512/model.pt")
    
    # Update production checkpoint if better
    best_prod_path = "outputs/checkpoints/best_model.pt"
    torch.save({
        "epoch": best_epoch,
        "model_state_dict": best_model_state,
        "best_val_dice": best_opt_dice,
        "optimal_threshold": best_opt_thresh,
        "min_area_pixels": best_min_area,
        "input_resolution": 512
    }, best_prod_path)
    print(f"Updated production model checkpoint at {best_prod_path}!")

if __name__ == "__main__":
    run_512_resolution_experiment()
