import os
import torch
from torch.utils.data import Dataset, DataLoader
import numpy as np
import random
from typing import Optional, Dict, Any, Tuple

class SARIcebergDataset(Dataset):
    """
    PyTorch Dataset for Sentinel-1 SAR imagery and binary iceberg masks.
    Supports physical SAR-preserving augmentations (flips, rotations, scaling).
    """
    def __init__(
        self, 
        images: np.ndarray, 
        masks: np.ndarray, 
        augment: bool = False
    ):
        """
        images: (N, 3, H, W) float32 in [0, 1]
        masks: (N, 1, H, W) int64 in {0, 1}
        augment: bool
        """
        self.images = images
        self.masks = masks
        self.augment = augment
        
    def __len__(self) -> int:
        return len(self.images)
        
    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        img = self.images[idx].copy()  # (3, H, W)
        mask = self.masks[idx].copy()  # (1, H, W)
        
        if self.augment:
            # 1. Random Horizontal Flip
            if random.random() > 0.5:
                img = np.flip(img, axis=2).copy()
                mask = np.flip(mask, axis=2).copy()
                
            # 2. Random Vertical Flip
            if random.random() > 0.5:
                img = np.flip(img, axis=1).copy()
                mask = np.flip(mask, axis=1).copy()
                
            # 3. Random 90-degree rotations (k in [1, 2, 3])
            if random.random() > 0.5:
                k = random.choice([1, 2, 3])
                img = np.rot90(img, k, (1, 2)).copy()
                mask = np.rot90(mask, k, (1, 2)).copy()
                
            # 4. Subtle intensity jitter (+/- 8%) - preserves SAR backscatter relations
            if random.random() > 0.5:
                factor = random.uniform(0.92, 1.08)
                img = np.clip(img * factor, 0.0, 1.0)
                
        # Squeeze mask channel: (H, W) for CrossEntropy / SegFormer loss
        mask_2d = mask[0].astype(np.int64)
        
        return {
            "pixel_values": torch.tensor(img, dtype=torch.float32),
            "labels": torch.tensor(mask_2d, dtype=torch.long)
        }

try:
    from path_utils import resolve_path
except ImportError:
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from path_utils import resolve_path

def get_dataloaders(
    processed_dir: str = "data/processed",
    batch_size: int = 16,
    num_workers: int = 0
) -> Tuple[DataLoader, DataLoader, DataLoader]:
    """
    Constructs train, validation, and test DataLoader instances.
    """
    resolved_dir = resolve_path(processed_dir)
    train_data = np.load(os.path.join(resolved_dir, "train.npz"))
    val_data = np.load(os.path.join(resolved_dir, "val.npz"))
    test_data = np.load(os.path.join(resolved_dir, "test.npz"))
    
    train_dataset = SARIcebergDataset(train_data["images"], train_data["masks"], augment=True)
    val_dataset = SARIcebergDataset(val_data["images"], val_data["masks"], augment=False)
    test_dataset = SARIcebergDataset(test_data["images"], test_data["masks"], augment=False)
    
    train_loader = DataLoader(
        train_dataset, 
        batch_size=batch_size, 
        shuffle=True, 
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available()
    )
    
    val_loader = DataLoader(
        val_dataset, 
        batch_size=batch_size, 
        shuffle=False, 
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available()
    )
    
    test_loader = DataLoader(
        test_dataset, 
        batch_size=batch_size, 
        shuffle=False, 
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available()
    )
    
    return train_loader, val_loader, test_loader
