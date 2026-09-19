import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import time
import json
import random
import yaml
import numpy as np
import cv2
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR, LinearLR, SequentialLR

try:
    from path_utils import PROJECT_ROOT, resolve_path
except ImportError:
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from path_utils import PROJECT_ROOT, resolve_path

from models.segformer import SegFormerB0Iceberg
from training.evaluate import compute_segmentation_metrics

# ---------------------------------------------------------------------------
# Advanced Loss Functions
# ---------------------------------------------------------------------------

class SoftDiceLoss(nn.Module):
    def __init__(self, smooth=1.0):
        super().__init__()
        self.smooth = smooth
        
    def forward(self, logits, targets):
        probs = F.softmax(logits, dim=1)[:, 1, :, :]
        targets_f = targets.float()
        intersection = (probs * targets_f).sum(dim=(1, 2))
        cardinality = (probs + targets_f).sum(dim=(1, 2))
        dice = (2.0 * intersection + self.smooth) / (cardinality + self.smooth + 1e-7)
        return (1.0 - dice).mean()

class FocalLossCustom(nn.Module):
    def __init__(self, alpha=0.75, gamma=2.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        
    def forward(self, logits, targets):
        # targets: (B, H, W)
        ce = F.cross_entropy(logits, targets, reduction='none')
        probs = F.softmax(logits, dim=1)
        p_t = probs[:, 1, :, :] * targets.float() + probs[:, 0, :, :] * (1.0 - targets.float())
        alpha_t = self.alpha * targets.float() + (1.0 - self.alpha) * (1.0 - targets.float())
        focal = alpha_t * ((1.0 - p_t) ** self.gamma) * ce
        return focal.mean()

class FocalTverskyLoss(nn.Module):
    """
    Tversky loss allows shifting emphasis between False Positives (alpha) and False Negatives (beta).
    """
    def __init__(self, alpha=0.3, beta=0.7, gamma=1.33, smooth=1.0):
        super().__init__()
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.smooth = smooth
        
    def forward(self, logits, targets):
        probs = F.softmax(logits, dim=1)[:, 1, :, :]
        targets_f = targets.float()
        
        tp = (probs * targets_f).sum(dim=(1, 2))
        fp = (probs * (1.0 - targets_f)).sum(dim=(1, 2))
        fn = ((1.0 - probs) * targets_f).sum(dim=(1, 2))
        
        tversky = (tp + self.smooth) / (tp + self.alpha * fp + self.beta * fn + self.smooth + 1e-7)
        focal_tversky = (1.0 - tversky) ** self.gamma
        return focal_tversky.mean()

class CombinedFocalDiceLoss(nn.Module):
    def __init__(self, focal_weight=0.5, dice_weight=0.5, alpha=0.75, gamma=2.0):
        super().__init__()
        self.focal_weight = focal_weight
        self.dice_weight = dice_weight
        self.focal = FocalLossCustom(alpha=alpha, gamma=gamma)
        self.dice = SoftDiceLoss()
        
    def forward(self, logits, targets):
        return self.focal_weight * self.focal(logits, targets) + self.dice_weight * self.dice(logits, targets)

# ---------------------------------------------------------------------------
# Dataset & Advanced SAR Normalization / Augmentation
# ---------------------------------------------------------------------------

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(3, 1, 1)
IMAGENET_STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(3, 1, 1)

class SARIcebergAdvancedDataset(Dataset):
    def __init__(
        self, 
        images: np.ndarray, 
        masks: np.ndarray, 
        augment: bool = False,
        normalize_mode: str = "imagenet" # "standard_01" or "imagenet" or "per_channel"
    ):
        self.images = images
        self.masks = masks
        self.augment = augment
        self.normalize_mode = normalize_mode
        
    def __len__(self):
        return len(self.images)
        
    def __getitem__(self, idx):
        img = self.images[idx].copy() # (3, H, W)
        mask = self.masks[idx, 0].copy() # (H, W)
        
        if self.augment:
            # 1. Random Horizontal Flip (p=0.5)
            if random.random() > 0.5:
                img = np.flip(img, axis=2).copy()
                mask = np.flip(mask, axis=1).copy()
                
            # 2. Random Vertical Flip (p=0.5)
            if random.random() > 0.5:
                img = np.flip(img, axis=1).copy()
                mask = np.flip(mask, axis=0).copy()
                
            # 3. Random 90 deg rotation (p=0.5)
            if random.random() > 0.5:
                k = random.choice([1, 2, 3])
                img = np.rot90(img, k, (1, 2)).copy()
                mask = np.rot90(mask, k, (0, 1)).copy()
                
            # 4. Multi-scale Crop & Resize (p=0.4)
            if random.random() > 0.6:
                H, W = img.shape[1], img.shape[2]
                scale = random.uniform(0.8, 1.0)
                crop_h, crop_w = int(H * scale), int(W * scale)
                top = random.randint(0, H - crop_h)
                left = random.randint(0, W - crop_w)
                
                cropped_img = img[:, top:top+crop_h, left:left+crop_w]
                cropped_mask = mask[top:top+crop_h, left:left+crop_w]
                
                # Resize back to (256, 256)
                img_resized = np.zeros((3, H, W), dtype=np.float32)
                for c in range(3):
                    img_resized[c] = cv2.resize(cropped_img[c], (W, H), interpolation=cv2.INTER_LINEAR)
                mask_resized = cv2.resize(cropped_mask.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST)
                
                img = img_resized
                mask = mask_resized
                
            # 5. SAR Intensity scaling (p=0.5)
            if random.random() > 0.5:
                gamma = random.uniform(0.85, 1.15)
                img = np.clip(img ** gamma, 0.0, 1.0)
                
            # 6. Random Coarse Dropout / Cutout (p=0.3)
            if random.random() > 0.7:
                H, W = img.shape[1], img.shape[2]
                num_holes = random.randint(1, 4)
                for _ in range(num_holes):
                    hole_size = random.randint(12, 32)
                    y1 = random.randint(0, H - hole_size)
                    x1 = random.randint(0, W - hole_size)
                    img[:, y1:y1+hole_size, x1:x1+hole_size] = 0.0
                    mask[y1:y1+hole_size, x1:x1+hole_size] = 0

        # Normalization
        if self.normalize_mode == "imagenet":
            norm_img = (img - IMAGENET_MEAN) / IMAGENET_STD
        else:
            norm_img = img
            
        return {
            "pixel_values": torch.tensor(norm_img, dtype=torch.float32),
            "labels": torch.tensor(mask, dtype=torch.long)
        }

# ---------------------------------------------------------------------------
# Training & Validation Runner
# ---------------------------------------------------------------------------

def train_and_eval_experiment(
    exp_id: str,
    loss_fn: nn.Module,
    normalize_mode: str = "imagenet",
    augment: bool = True,
    lr_backbone: float = 1e-4,
    lr_head: float = 5e-4,
    epochs: int = 35,
    batch_size: int = 16,
    weight_decay: float = 0.01,
    seed: int = 42
):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Load dataset arrays
    train_npz = np.load(resolve_path("data/processed/train.npz"))
    val_npz = np.load(resolve_path("data/processed/val.npz"))
    test_npz = np.load(resolve_path("data/processed/test.npz"))
    
    train_dataset = SARIcebergAdvancedDataset(train_npz["images"], train_npz["masks"], augment=augment, normalize_mode=normalize_mode)
    val_dataset = SARIcebergAdvancedDataset(val_npz["images"], val_npz["masks"], augment=False, normalize_mode=normalize_mode)
    test_dataset = SARIcebergAdvancedDataset(test_npz["images"], test_npz["masks"], augment=False, normalize_mode=normalize_mode)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, pin_memory=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, pin_memory=True)
    
    model = SegFormerB0Iceberg(num_classes=2, pretrained_model_name="nvidia/mit-b0").to(device)
    loss_fn = loss_fn.to(device)
    
    # Differential learning rates for encoder vs decode head
    encoder_params = []
    decoder_params = []
    for name, param in model.named_parameters():
        if "decode_head" in name or "classifier" in name:
            decoder_params.append(param)
        else:
            encoder_params.append(param)
            
    optimizer = AdamW([
        {"params": encoder_params, "lr": lr_backbone, "weight_decay": weight_decay},
        {"params": decoder_params, "lr": lr_head, "weight_decay": weight_decay}
    ])
    
    scheduler = CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)
    
    best_val_dice = 0.0
    best_model_state = None
    best_epoch = 0
    
    print(f"\n>>> Running {exp_id} | Norm: {normalize_mode} | Aug: {augment} | LR_b: {lr_backbone} | LR_h: {lr_head} | Epochs: {epochs}")
    
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
        
        # Validation Evaluation across thresholds
        model.eval()
        val_preds_list = []
        val_targets_list = []
        val_probs_list = []
        
        with torch.no_grad():
            for batch in val_loader:
                imgs = batch["pixel_values"].to(device)
                targets = batch["labels"].numpy()
                outputs = model(imgs)
                logits = outputs["logits"]
                probs = F.softmax(logits, dim=1)[:, 1, :, :].cpu().numpy()
                
                val_probs_list.append(probs)
                val_targets_list.append(targets)
                
        val_probs_cat = np.concatenate(val_probs_list, axis=0)
        val_targets_cat = np.concatenate(val_targets_list, axis=0)
        
        # Find best threshold on validation set
        val_dice_at_50 = compute_segmentation_metrics((val_probs_cat >= 0.5).astype(np.int64), val_targets_cat)["dice_f1"]
        
        # Checkpoint if improved
        if val_dice_at_50 > best_val_dice:
            best_val_dice = val_dice_at_50
            best_epoch = epoch
            best_model_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            
        if epoch % 5 == 0 or epoch == epochs:
            print(f"  Epoch [{epoch:02d}/{epochs:02d}] Train Loss: {train_loss:.4f} | Val Dice@0.5: {val_dice_at_50*100:.2f}% (Best: {best_val_dice*100:.2f}% @ Ep {best_epoch})")
            
    # Load best weights
    model.load_state_dict({k: v.to(device) for k, v in best_model_state.items()})
    model.eval()
    
    # 1. Sweep Threshold on Validation Set
    val_probs_list = []
    val_targets_list = []
    with torch.no_grad():
        for batch in val_loader:
            imgs = batch["pixel_values"].to(device)
            targets = batch["labels"].numpy()
            probs = F.softmax(model(imgs)["logits"], dim=1)[:, 1, :, :].cpu().numpy()
            val_probs_list.append(probs)
            val_targets_list.append(targets)
    val_probs_cat = np.concatenate(val_probs_list, axis=0)
    val_targets_cat = np.concatenate(val_targets_list, axis=0)
    
    best_opt_thresh = 0.5
    best_opt_dice = 0.0
    for t in [0.20, 0.30, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]:
        t_dice = compute_segmentation_metrics((val_probs_cat >= t).astype(np.int64), val_targets_cat)["dice_f1"]
        if t_dice > best_opt_dice:
            best_opt_dice = t_dice
            best_opt_thresh = t
            
    best_val_metrics = compute_segmentation_metrics((val_probs_cat >= best_opt_thresh).astype(np.int64), val_targets_cat)
    
    # 2. Evaluate ONCE on Test Set using optimal validation threshold
    test_probs_list = []
    test_targets_list = []
    with torch.no_grad():
        for batch in test_loader:
            imgs = batch["pixel_values"].to(device)
            targets = batch["labels"].numpy()
            probs = F.softmax(model(imgs)["logits"], dim=1)[:, 1, :, :].cpu().numpy()
            test_probs_list.append(probs)
            test_targets_list.append(targets)
    test_probs_cat = np.concatenate(test_probs_list, axis=0)
    test_targets_cat = np.concatenate(test_targets_list, axis=0)
    
    test_metrics = compute_segmentation_metrics((test_probs_cat >= best_opt_thresh).astype(np.int64), test_targets_cat)
    
    print(f"\n=== {exp_id} FINAL SUMMARY ===")
    print(f"Optimal Val Threshold: {best_opt_thresh:.2f}")
    print(f"Validation Dice: {best_val_metrics['dice_f1']*100:.2f}% | Val IoU: {best_val_metrics['iceberg_iou']*100:.2f}% | Val Prec: {best_val_metrics['precision']*100:.2f}% | Val Rec: {best_val_metrics['recall']*100:.2f}%")
    print(f"TEST Dice:       {test_metrics['dice_f1']*100:.2f}% | Test IoU: {test_metrics['iceberg_iou']*100:.2f}% | Test Prec: {test_metrics['precision']*100:.2f}% | Test Rec: {test_metrics['recall']*100:.2f}%")
    print("="*60)
    
    # Save checkpoint
    exp_dir = resolve_path(f"outputs/experiments/{exp_id}")
    os.makedirs(exp_dir, exist_ok=True)
    torch.save({
        "exp_id": exp_id,
        "model_state_dict": best_model_state,
        "best_val_metrics": best_val_metrics,
        "test_metrics": test_metrics,
        "optimal_threshold": best_opt_thresh,
        "normalize_mode": normalize_mode,
        "best_epoch": best_epoch
    }, os.path.join(exp_dir, "model.pt"))
    
    return {
        "exp_id": exp_id,
        "optimal_threshold": best_opt_thresh,
        "val_dice": best_val_metrics["dice_f1"],
        "val_iou": best_val_metrics["iceberg_iou"],
        "val_precision": best_val_metrics["precision"],
        "val_recall": best_val_metrics["recall"],
        "val_pixel_acc": best_val_metrics["pixel_accuracy"],
        "test_dice": test_metrics["dice_f1"],
        "test_iou": test_metrics["iceberg_iou"],
        "test_precision": test_metrics["precision"],
        "test_recall": test_metrics["recall"],
        "test_pixel_acc": test_metrics["pixel_accuracy"]
    }

def run_all_experiments():
    os.makedirs("outputs/experiments", exist_ok=True)
    all_results = []
    
    # EXP-01: Baseline (CE+Dice, Standard [0,1], no ImageNet norm)
    r1 = train_and_eval_experiment(
        exp_id="EXP-01-Baseline",
        loss_fn=nn.CrossEntropyLoss(weight=torch.tensor([1.0, 10.0])),
        normalize_mode="standard_01",
        augment=False,
        lr_backbone=3e-4,
        lr_head=3e-4,
        epochs=30
    )
    all_results.append(r1)
    
    # EXP-02: Focal + SoftDice Loss
    r2 = train_and_eval_experiment(
        exp_id="EXP-02-FocalDiceLoss",
        loss_fn=CombinedFocalDiceLoss(focal_weight=0.5, dice_weight=0.5, alpha=0.75, gamma=2.0),
        normalize_mode="standard_01",
        augment=False,
        lr_backbone=3e-4,
        lr_head=3e-4,
        epochs=30
    )
    all_results.append(r2)
    
    # EXP-03: ImageNet Normalization Alignment for Transformer Backbone
    r3 = train_and_eval_experiment(
        exp_id="EXP-03-ImageNetNorm",
        loss_fn=CombinedFocalDiceLoss(focal_weight=0.5, dice_weight=0.5, alpha=0.75, gamma=2.0),
        normalize_mode="imagenet",
        augment=False,
        lr_backbone=2e-4,
        lr_head=5e-4,
        epochs=35
    )
    all_results.append(r3)
    
    # EXP-04: Advanced SAR Augmentations
    r4 = train_and_eval_experiment(
        exp_id="EXP-04-SARAugmentations",
        loss_fn=CombinedFocalDiceLoss(focal_weight=0.5, dice_weight=0.5, alpha=0.75, gamma=2.0),
        normalize_mode="imagenet",
        augment=True,
        lr_backbone=1.5e-4,
        lr_head=6e-4,
        epochs=40
    )
    all_results.append(r4)
    
    # EXP-05: Focal Tversky Loss (Fine boundary and high precision)
    r5 = train_and_eval_experiment(
        exp_id="EXP-05-FocalTversky",
        loss_fn=FocalTverskyLoss(alpha=0.3, beta=0.7, gamma=1.33),
        normalize_mode="imagenet",
        augment=True,
        lr_backbone=1e-4,
        lr_head=6e-4,
        epochs=40
    )
    all_results.append(r5)
    
    # Save experiment tracking table
    table_path = resolve_path("outputs/experiments/experiment_table.json")
    os.makedirs(os.path.dirname(table_path), exist_ok=True)
    with open(table_path, "w") as f:
        json.dump(all_results, f, indent=2)
        
    print("\n" + "="*80)
    print("ALL EXPERIMENTS COMPLETED - SUMMARY TABLE")
    print("="*80)
    print(f"{'Experiment':<25} | {'Val Dice':>9} | {'Val IoU':>8} | {'Val Prec':>9} | {'Test Dice':>10} | {'Test IoU':>9} | {'Test Prec':>10} | {'Test Rec':>9}")
    print("-" * 105)
    for r in all_results:
        print(f"{r['exp_id']:<25} | {r['val_dice']*100:8.2f}% | {r['val_iou']*100:7.2f}% | {r['val_precision']*100:8.2f}% | {r['test_dice']*100:9.2f}% | {r['test_iou']*100:8.2f}% | {r['test_precision']*100:9.2f}% | {r['test_recall']*100:8.2f}%")
    print("="*80)

if __name__ == "__main__":
    run_all_experiments()
