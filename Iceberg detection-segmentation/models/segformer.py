import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import SegformerForSemanticSegmentation, SegformerConfig
from typing import Dict, Any, Optional

class SegFormerB0Iceberg(nn.Module):
    """
    SegFormer-B0 binary semantic segmentation model for Sentinel-1 SAR Iceberg Detection.
    
    Architecture:
    - Mix Transformer (MiT-B0) hierarchical encoder
    - All-MLP lightweight decoder aggregating multi-level feature maps
    - Binary classification head (num_classes = 2: 0=background, 1=iceberg)
    """
    def __init__(
        self, 
        num_classes: int = 2, 
        pretrained_model_name: str = "nvidia/mit-b0",
        drop_rate: float = 0.1
    ):
        super().__init__()
        self.num_classes = num_classes
        
        try:
            # Load pretrained Segformer with custom num_labels
            self.segformer = SegformerForSemanticSegmentation.from_pretrained(
                pretrained_model_name,
                num_labels=num_classes,
                ignore_mismatched_sizes=True,
                hidden_dropout_prob=drop_rate,
                attention_probs_dropout_prob=drop_rate
            )
        except Exception as e:
            print(f"Warning: Could not download/load '{pretrained_model_name}' ({e}). Initializing SegformerConfig from scratch.")
            config = SegformerConfig(
                num_labels=num_classes,
                num_channels=3,
                depths=[2, 2, 2, 2],
                hidden_sizes=[32, 64, 160, 256],
                decoder_hidden_size=256,
                classifier_dropout_prob=drop_rate
            )
            self.segformer = SegformerForSemanticSegmentation(config)
            
    def forward(self, pixel_values: torch.Tensor, labels: Optional[torch.Tensor] = None):
        """
        Forward pass.
        pixel_values: (B, 3, H, W) normalized SAR input tensor
        labels: Optional (B, H, W) ground truth binary mask tensor
        """
        outputs = self.segformer(pixel_values=pixel_values, labels=labels)
        
        # Segformer outputs logits at 1/4 resolution (B, num_classes, H/4, W/4)
        logits_low_res = outputs.logits
        
        # Upsample logits to original image resolution (B, num_classes, H, W)
        H, W = pixel_values.shape[2], pixel_values.shape[3]
        logits = F.interpolate(
            logits_low_res, 
            size=(H, W), 
            mode="bilinear", 
            align_corners=False
        )
        
        loss = outputs.loss if labels is not None else None
        
        return {
            "logits": logits,
            "loss": loss
        }
        
    @torch.no_grad()
    def predict_probability(self, pixel_values: torch.Tensor) -> torch.Tensor:
        """
        Inference helper: returns probability of iceberg class (B, H, W) in [0, 1].
        """
        self.eval()
        outputs = self.forward(pixel_values)
        logits = outputs["logits"]  # (B, 2, H, W)
        probs = F.softmax(logits, dim=1)[:, 1, :, :]  # class 1: iceberg probability
        return probs

def get_model(config: Optional[Dict[str, Any]] = None) -> SegFormerB0Iceberg:
    num_classes = config.get("model", {}).get("num_classes", 2) if config else 2
    backbone = config.get("model", {}).get("backbone", "nvidia/mit-b0") if config else "nvidia/mit-b0"
    drop_rate = config.get("model", {}).get("drop_rate", 0.1) if config else 0.1
    return SegFormerB0Iceberg(num_classes=num_classes, pretrained_model_name=backbone, drop_rate=drop_rate)

if __name__ == "__main__":
    model = SegFormerB0Iceberg(num_classes=2)
    dummy_input = torch.randn(2, 3, 256, 256)
    dummy_labels = torch.randint(0, 2, (2, 256, 256))
    out = model(dummy_input, dummy_labels)
    print("Logits shape:", out["logits"].shape)
    probs = model.predict_probability(dummy_input)
    print("Probs shape:", probs.shape, "min:", probs.min().item(), "max:", probs.max().item())
