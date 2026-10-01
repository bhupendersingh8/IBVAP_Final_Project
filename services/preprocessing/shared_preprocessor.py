"""
IBVAP Shared Preprocessor
=========================
Grand Finale Master Architecture - Section 4
Generates unified, normalized GPU tensors once in CUDA/VRAM memory.
Eliminates redundant BGR->RGB conversions, CPU->GPU uploads, and repeated resizing across all downstream models.
"""
from __future__ import annotations

import cv2
import numpy as np
from typing import Optional, Tuple, Dict, Any
import structlog

from services.ingestion.frame_packet import FramePacket

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

logger = structlog.get_logger()


class SharedPreprocessor:
    """
    Unified GPU Preprocessor for IBVAP.
    Transforms raw BGR frames into pre-allocated, normalized PyTorch device tensors once.
    """
    def __init__(
        self,
        target_size: Tuple[int, int] = (640, 640),
        device: Optional[str] = None,
        use_half: bool = False,
    ):
        self.target_width, self.target_height = target_size
        self.use_half = use_half

        if device is None:
            cuda_ok = False
            if HAS_TORCH and torch.cuda.is_available():
                try:
                    torch.zeros(1, device="cuda")
                    cuda_ok = True
                except Exception:
                    cuda_ok = False
            self.device = torch.device("cuda:0") if cuda_ok else (torch.device("cpu") if HAS_TORCH else "cpu")
        else:
            cand_dev = torch.device(device) if HAS_TORCH else "cpu"
            if HAS_TORCH and hasattr(cand_dev, "type") and cand_dev.type == "cuda":
                try:
                    torch.zeros(1, device=cand_dev)
                    self.device = cand_dev
                except Exception:
                    self.device = torch.device("cpu")
            else:
                self.device = cand_dev

        logger.info(
            "SharedPreprocessor initialized",
            target_size=target_size,
            device=str(self.device),
            use_half=self.use_half,
        )

    def letterbox(
        self,
        img: np.ndarray,
        new_shape: Tuple[int, int] = (640, 640),
        color: Tuple[int, int, int] = (114, 114, 114),
        auto: bool = False,
        scale_fill: bool = False,
        scaleup: bool = True,
        stride: int = 32,
    ) -> Tuple[np.ndarray, float, Tuple[float, float]]:
        """
        Resizes and pads image while preserving aspect ratio.
        Returns: (padded_image, ratio, (pad_left, pad_top))
        """
        shape = img.shape[:2]  # current shape [height, width]
        if isinstance(new_shape, int):
            new_shape = (new_shape, new_shape)

        # Scale ratio (new / old)
        r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
        if not scaleup:  # only scale down, do not scale up
            r = min(r, 1.0)

        # Compute padding
        ratio = r, r
        new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
        dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]  # wh padding

        if auto:  # minimum rectangle
            dw, dh = np.mod(dw, stride), np.mod(dh, stride)
        elif scale_fill:  # stretch
            dw, dh = 0.0, 0.0
            new_unpad = (new_shape[1], new_shape[0])
            ratio = new_shape[1] / shape[1], new_shape[0] / shape[0]

        dw /= 2  # divide padding into 2 sides
        dh /= 2

        if shape[::-1] != new_unpad:  # resize
            img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
        img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
        return img, r, (dw, dh)

    def preprocess(self, packet: FramePacket, target_size: Optional[Tuple[int, int]] = None) -> FramePacket:
        """
        Performs shared GPU preprocessing on the FramePacket.
        Attaches packet.gpu_tensor and metadata.
        """
        if packet.raw_bgr is None:
            return packet

        target_w, target_h = target_size or (self.target_width, self.target_height)

        # 1. Letterbox resize in BGR
        padded_bgr, ratio, (pad_w, pad_h) = self.letterbox(
            packet.raw_bgr,
            new_shape=(target_h, target_w),
            auto=False,
            scale_fill=False
        )

        # 2. Convert to RGB
        rgb_img = cv2.cvtColor(padded_bgr, cv2.COLOR_BGR2RGB)

        # 3. Create Tensor
        if HAS_TORCH:
            try:
                # Transfer numpy (H, W, C) -> torch (C, H, W)
                tensor = torch.from_numpy(rgb_img).to(self.device, non_blocking=True)
                # Permute from HWC to CHW and add batch dimension -> [1, C, H, W]
                tensor = tensor.permute(2, 0, 1).unsqueeze(0)
                # Convert uint8 -> float32/float16 in range [0.0, 1.0]
                if self.use_half and getattr(self.device, "type", None) == "cuda":
                    tensor = tensor.half() / 255.0
                else:
                    tensor = tensor.float() / 255.0
            except Exception as e:
                # Automatic zero-crash fallback to CPU
                self.device = torch.device("cpu")
                tensor = torch.from_numpy(rgb_img).to(self.device)
                tensor = tensor.permute(2, 0, 1).unsqueeze(0).float() / 255.0

            packet.gpu_tensor = tensor
        else:
            # CPU fallback array
            chw = np.transpose(rgb_img, (2, 0, 1))[np.newaxis, ...]
            packet.gpu_tensor = chw.astype(np.float32) / 255.0

        # 4. Attach metadata for downstream bounding-box coordinate reversal
        packet.preprocessing_metadata.update({
            "device": str(self.device),
            "target_size": (target_w, target_h),
            "ratio": ratio,
            "pad_w": pad_w,
            "pad_h": pad_h,
            "original_shape": (packet.height, packet.width),
            "letterbox_shape": (target_h, target_w),
            "dtype": "float16" if self.use_half else "float32",
        })

        return packet

    def scale_boxes_to_original(
        self,
        boxes: np.ndarray,
        packet: FramePacket,
    ) -> np.ndarray:
        """
        Rescales bounding boxes [x1, y1, x2, y2] from letterboxed coordinates back to original frame dimensions.
        """
        if len(boxes) == 0:
            return boxes

        meta = packet.preprocessing_metadata
        if not meta or "ratio" not in meta:
            return boxes

        ratio = meta["ratio"]
        pad_w = meta["pad_w"]
        pad_h = meta["pad_h"]
        orig_h, orig_w = meta["original_shape"]

        rescaled = boxes.copy()
        rescaled[:, [0, 2]] = (rescaled[:, [0, 2]] - pad_w) / ratio
        rescaled[:, [1, 3]] = (rescaled[:, [1, 3]] - pad_h) / ratio

        # Clip to image boundary
        rescaled[:, [0, 2]] = np.clip(rescaled[:, [0, 2]], 0, orig_w)
        rescaled[:, [1, 3]] = np.clip(rescaled[:, [1, 3]], 0, orig_h)

        return rescaled
