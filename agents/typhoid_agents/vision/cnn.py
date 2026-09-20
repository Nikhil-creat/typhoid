"""Spatial CNN feature extractor: perceptual diff that ignores anti-aliasing noise but catches layout shifts.
Uses ResNet-18 feature maps; cosine distance per spatial cell -> heatmap the dashboard overlays on the screenshot."""
import io
import numpy as np
import torch
import torchvision.models as tvm
import torchvision.transforms as T
from PIL import Image

_net = None
_prep = T.Compose([T.Resize((448, 448)), T.ToTensor(), T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])


def _backbone():
    global _net
    if _net is None:
        m = tvm.resnet18(weights=tvm.ResNet18_Weights.DEFAULT).eval()
        _net = torch.nn.Sequential(*list(m.children())[:-2])   # keep spatial map (512 x 14 x 14)
    return _net


@torch.no_grad()
def feature_map(png: bytes) -> torch.Tensor:
    x = _prep(Image.open(io.BytesIO(png)).convert("RGB")).unsqueeze(0)
    return torch.nn.functional.normalize(_backbone()(x)[0], dim=0)


@torch.no_grad()
def diff_heatmap(baseline: bytes, candidate: bytes) -> dict:
    a, b = feature_map(baseline), feature_map(candidate)
    dist = 1 - (a * b).sum(0)                                    # 14x14 cosine distance
    hm = dist.numpy()
    ys, xs = np.where(hm > max(0.15, hm.mean() + 2 * hm.std()))
    boxes = [{"x": int(x) / hm.shape[1], "y": int(y) / hm.shape[0], "w": 1 / hm.shape[1], "h": 1 / hm.shape[0]} for y, x in zip(ys, xs)]
    return {"score": float(hm.mean()), "max": float(hm.max()), "heatmap": hm.round(3).tolist(), "regions": boxes}
