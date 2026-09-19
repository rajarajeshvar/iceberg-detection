import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, List

class DiceLoss(nn.Module):
    """
    Differentiable Soft Dice Loss for binary semantic segmentation.
    Focuses gradient optimization directly on the iceberg foreground region.
    """
    def __init__(self, smooth: float = 1.0, eps: float = 1e-7):
        super().__init__()
        self.smooth = smooth
        self.eps = eps
        
    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """
        logits: (B, 2, H, W)
        targets: (B, H, W) binary {0, 1}
        """
        probs = F.softmax(logits, dim=1)[:, 1, :, :]  # (B, H, W) iceberg probability
        targets_f = targets.float()
        
        intersection = torch.sum(probs * targets_f, dim=(1, 2))
        cardinality = torch.sum(probs + targets_f, dim=(1, 2))
        
        dice_score = (2.0 * intersection + self.smooth) / (cardinality + self.smooth + self.eps)
        dice_loss = 1.0 - dice_score
        return dice_loss.mean()

class FocalLoss(nn.Module):
    """
    Focal Loss to counter severe class imbalance in satellite segmentation.
    FL(p_t) = -alpha_t * (1 - p_t)^gamma * log(p_t)
    """
    def __init__(self, alpha: Optional[torch.Tensor] = None, gamma: float = 2.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        
    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        ce_loss = F.cross_entropy(logits, targets, weight=self.alpha, reduction='none')
        pt = torch.exp(-ce_loss)
        focal_loss = ((1.0 - pt) ** self.gamma) * ce_loss
        return focal_loss.mean()

class CombinedLoss(nn.Module):
    """
    Weighted combination of Cross Entropy (or Focal) Loss and Soft Dice Loss.
    """
    def __init__(
        self, 
        class_weights: Optional[List[float]] = None,
        ce_weight: float = 0.5,
        dice_weight: float = 0.5
    ):
        super().__init__()
        self.ce_weight = ce_weight
        self.dice_weight = dice_weight
        
        if class_weights is not None:
            weights_tensor = torch.tensor(class_weights, dtype=torch.float32)
        else:
            weights_tensor = torch.tensor([1.0, 10.0], dtype=torch.float32)
            
        self.register_buffer("weights_tensor", weights_tensor)
        self.dice_loss_fn = DiceLoss()
        
    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        ce = F.cross_entropy(logits, targets, weight=self.weights_tensor)
        dice = self.dice_loss_fn(logits, targets)
        total = self.ce_weight * ce + self.dice_weight * dice
        return total
