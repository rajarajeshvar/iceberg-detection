import torch
import torch.nn as nn
from transformers import SegformerForSemanticSegmentation, SegformerConfig
from typing import Optional, Union

class SegFormerB0Iceberg(nn.Module):
    """
    SegFormer-B0 architecture customized for binary SAR iceberg segmentation.
    Hierarchical Transformer Encoder with Lightweight All-MLP Decoder.
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
            self.model = SegformerForSemanticSegmentation.from_pretrained(
                pretrained_model_name,
                num_labels=num_classes,
                ignore_mismatched_sizes=True
            )
        except Exception:
            # Offline / Fallback config initialization
            config = SegformerConfig(
                num_labels=num_classes,
                classifier_dropout_prob=drop_rate
            )
            self.model = SegformerForSemanticSegmentation(config)
            
        self.sigmoid = nn.Sigmoid()

    def forward(self, pixel_values: torch.Tensor, labels: Optional[torch.Tensor] = None) -> Union[torch.Tensor, dict]:
        outputs = self.model(pixel_values=pixel_values, labels=labels)
        return outputs

    @torch.no_grad()
    def predict_probability(self, pixel_values: torch.Tensor) -> torch.Tensor:
        """
        Calculates normalized binary iceberg confidence map in [0, 1].
        """
        self.eval()
        outputs = self.model(pixel_values=pixel_values)
        logits = outputs.logits  # shape: (B, num_classes, H/4, W/4)
        
        # Upsample logits to match input image spatial resolution
        upsampled_logits = nn.functional.interpolate(
            logits,
            size=pixel_values.shape[-2:],
            mode="bilinear",
            align_corners=False
        )
        
        # Softmax over classes; return class 1 (iceberg) probability
        probs = torch.softmax(upsampled_logits, dim=1)
        iceberg_prob = probs[:, 1, :, :]  # (B, H, W)
        return iceberg_prob
