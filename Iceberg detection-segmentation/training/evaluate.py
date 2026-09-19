import torch
import numpy as np
import time
from typing import Dict, Any, Tuple
import torch.nn.functional as F

def compute_segmentation_metrics(
    preds: np.ndarray, 
    targets: np.ndarray, 
    eps: float = 1e-7
) -> Dict[str, float]:
    """
    Computes rigorous binary segmentation metrics.
    preds: 2D or 3D binary numpy array (0 or 1)
    targets: 2D or 3D binary numpy array (0 or 1)
    """
    preds_bool = (preds > 0).astype(bool)
    targets_bool = (targets > 0).astype(bool)
    
    tp = float(np.logical_and(preds_bool, targets_bool).sum())
    fp = float(np.logical_and(preds_bool, ~targets_bool).sum())
    fn = float(np.logical_and(~preds_bool, targets_bool).sum())
    tn = float(np.logical_and(~preds_bool, ~targets_bool).sum())
    
    # Foreground Iceberg metrics
    precision = (tp + eps) / (tp + fp + eps)
    recall = (tp + eps) / (tp + fn + eps)
    dice = (2.0 * tp + eps) / (2.0 * tp + fp + fn + eps)
    iou = (tp + eps) / (tp + fp + fn + eps)
    
    # Background IoU
    bg_iou = (tn + eps) / (tn + fp + fn + eps)
    mean_iou = 0.5 * (iou + bg_iou)
    
    pixel_acc = (tp + tn) / (tp + tn + fp + fn + eps)
    
    return {
        "iceberg_iou": float(iou),
        "mean_iou": float(mean_iou),
        "dice_f1": float(dice),
        "precision": float(precision),
        "recall": float(recall),
        "pixel_accuracy": float(pixel_acc),
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "tn": int(tn)
    }

@torch.no_grad()
def evaluate_model(
    model: torch.nn.Module, 
    data_loader: torch.utils.data.DataLoader, 
    device: torch.device,
    threshold: float = 0.5
) -> Dict[str, Any]:
    """
    Evaluates model across an entire dataset DataLoader.
    Computes segmentation metrics, parameter count, and inference latency.
    """
    model.eval()
    all_preds = []
    all_targets = []
    total_time = 0.0
    total_samples = 0
    
    # Parameter count
    param_count = sum(p.numel() for p in model.parameters())
    trainable_param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
    
    for batch in data_loader:
        images = batch["pixel_values"].to(device)
        targets = batch["labels"].numpy()
        
        start_t = time.perf_counter()
        outputs = model(images)
        logits = outputs["logits"]
        probs = F.softmax(logits, dim=1)[:, 1, :, :].cpu().numpy()
        latency = time.perf_counter() - start_t
        
        total_time += latency
        total_samples += images.size(0)
        
        binary_preds = (probs >= threshold).astype(np.int64)
        all_preds.append(binary_preds)
        all_targets.append(targets)
        
    all_preds_cat = np.concatenate(all_preds, axis=0)
    all_targets_cat = np.concatenate(all_targets, axis=0)
    
    metrics = compute_segmentation_metrics(all_preds_cat, all_targets_cat)
    avg_latency_ms = (total_time / total_samples) * 1000.0 if total_samples > 0 else 0.0
    
    metrics["avg_inference_latency_ms"] = float(round(avg_latency_ms, 2))
    metrics["total_parameters"] = int(param_count)
    metrics["trainable_parameters"] = int(trainable_param_count)
    metrics["total_evaluated_samples"] = int(total_samples)
    
    return metrics
