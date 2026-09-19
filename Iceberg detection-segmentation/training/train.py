import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import yaml
import json
import random
import numpy as np
import torch
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
import torch.nn.functional as F

try:
    from path_utils import PROJECT_ROOT, resolve_path
except ImportError:
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from path_utils import PROJECT_ROOT, resolve_path

from models.segformer import SegFormerB0Iceberg
from training.dataset import get_dataloaders
from training.losses import CombinedLoss
from training.evaluate import evaluate_model

def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

def train_pipeline(config_path: str = "config.yaml"):
    resolved_config_path = resolve_path(config_path)
    with open(resolved_config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        
    set_seed(config["training"]["seed"])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")
    
    # 1. Dataloaders
    train_loader, val_loader, test_loader = get_dataloaders(
        processed_dir=resolve_path(config["data"]["processed_dir"]),
        batch_size=config["training"]["batch_size"],
        num_workers=config["training"]["num_workers"]
    )
    print(f"DataLoaders initialized: {len(train_loader.dataset)} train, {len(val_loader.dataset)} val, {len(test_loader.dataset)} test samples.")
    
    # 2. Model
    model = SegFormerB0Iceberg(
        num_classes=config["model"]["num_classes"],
        pretrained_model_name=config["model"]["backbone"],
        drop_rate=config["model"]["drop_rate"]
    ).to(device)
    
    # 3. Loss & Optimizer
    loss_cfg = config["training"]["loss"]
    criterion = CombinedLoss(
        class_weights=loss_cfg["class_weights"],
        ce_weight=loss_cfg["bce_weight"],
        dice_weight=loss_cfg["dice_weight"]
    ).to(device)
    
    optimizer = AdamW(
        model.parameters(), 
        lr=config["training"]["learning_rate"], 
        weight_decay=config["training"]["weight_decay"]
    )
    
    epochs = config["training"]["epochs"]
    scheduler = CosineAnnealingLR(
        optimizer, 
        T_max=epochs, 
        eta_min=config["training"]["min_lr"]
    )
    
    checkpoint_dir = resolve_path(config["training"]["checkpoint_dir"])
    os.makedirs(checkpoint_dir, exist_ok=True)
    
    best_val_dice = 0.0
    history = []
    
    print("\n" + "="*70)
    print("STARTING SEGFORMER-B0 TRAINING PIPELINE")
    print("="*70)
    
    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        
        for batch in train_loader:
            images = batch["pixel_values"].to(device)
            labels = batch["labels"].to(device)
            
            optimizer.zero_grad()
            outputs = model(images)
            logits = outputs["logits"]
            
            loss = criterion(logits, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            
            train_loss += loss.item() * images.size(0)
            
        scheduler.step()
        train_loss /= len(train_loader.dataset)
        
        # Validation
        val_metrics = evaluate_model(model, val_loader, device, threshold=config["inference"]["confidence_threshold"])
        val_dice = val_metrics["dice_f1"]
        val_iou = val_metrics["iceberg_iou"]
        val_prec = val_metrics["precision"]
        val_rec = val_metrics["recall"]
        
        epoch_info = {
            "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "lr": round(scheduler.get_last_lr()[0], 6),
            "val_dice": round(val_dice, 4),
            "val_iou": round(val_iou, 4),
            "val_precision": round(val_prec, 4),
            "val_recall": round(val_rec, 4),
            "val_pixel_acc": round(val_metrics["pixel_accuracy"], 4)
        }
        history.append(epoch_info)
        
        print(f"Epoch [{epoch:02d}/{epochs:02d}] - Train Loss: {train_loss:.4f} | Val Dice: {val_dice:.4f} | Val IoU: {val_iou:.4f} | Val Prec: {val_prec:.4f} | Val Rec: {val_rec:.4f} | LR: {scheduler.get_last_lr()[0]:.6f}")
        
        # Save best model checkpoint
        if val_dice > best_val_dice:
            best_val_dice = val_dice
            best_ckpt_path = os.path.join(checkpoint_dir, "best_model.pt")
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "best_val_dice": best_val_dice,
                "config": config
            }, best_ckpt_path)
            print(f"  --> Saved new BEST model checkpoint to {best_ckpt_path} (Val Dice: {val_dice:.4f})")
            
    # Save latest model checkpoint
    latest_ckpt_path = os.path.join(checkpoint_dir, "latest_model.pt")
    torch.save({
        "epoch": epochs,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "final_val_dice": val_dice,
        "config": config
    }, latest_ckpt_path)
    
    # Save training history
    with open(os.path.join(checkpoint_dir, "training_history.json"), "w") as f:
        json.dump(history, f, indent=2)
        
    print("\n" + "="*70)
    print("TRAINING COMPLETE! EVALUATING ON UNTOUCHED TEST SET")
    print("="*70)
    
    # Load best model for test set evaluation
    best_checkpoint = torch.load(os.path.join(checkpoint_dir, "best_model.pt"), map_location=device)
    model.load_state_dict(best_checkpoint["model_state_dict"])
    
    test_metrics = evaluate_model(model, test_loader, device, threshold=config["inference"]["confidence_threshold"])
    
    print("TEST SET EVALUATION RESULTS:")
    print(f"  - Iceberg IoU: {test_metrics['iceberg_iou']:.4f}")
    print(f"  - Mean IoU: {test_metrics['mean_iou']:.4f}")
    print(f"  - Dice / F1 Score: {test_metrics['dice_f1']:.4f}")
    print(f"  - Precision: {test_metrics['precision']:.4f}")
    print(f"  - Recall: {test_metrics['recall']:.4f}")
    print(f"  - Pixel Accuracy: {test_metrics['pixel_accuracy']:.4f}")
    print(f"  - Model Parameter Count: {test_metrics['total_parameters']:,}")
    print(f"  - Average Inference Latency: {test_metrics['avg_inference_latency_ms']:.2f} ms / tile")
    print("="*70)
    
    # Save test results
    with open(os.path.join(checkpoint_dir, "test_metrics.json"), "w") as f:
        json.dump(test_metrics, f, indent=2)
        
    return test_metrics, history

if __name__ == "__main__":
    train_pipeline()
