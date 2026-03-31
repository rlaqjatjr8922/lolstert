from __future__ import annotations

import json
from pathlib import Path

import numpy as np


class ColorChecker:
    def __init__(self):
        config_path = Path(__file__).resolve().parents[2] / "data" / "config.json"
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        th = config["thresholds"]
        self.red_min = float(th["red_mean_min"])
        self.red_margin = float(th["red_margin"])

    def check_red(self, roi) -> bool:
        if roi is None or getattr(roi, "size", 0) == 0:
            return False

        b_mean = float(np.mean(roi[:, :, 0]))
        g_mean = float(np.mean(roi[:, :, 1]))
        r_mean = float(np.mean(roi[:, :, 2]))

        return r_mean >= self.red_min and (r_mean - max(b_mean, g_mean)) >= self.red_margin
