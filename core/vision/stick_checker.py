from pathlib import Path

import cv2
import numpy as np

class StickChecker:
    def __init__(self, debug=False, slot_count=5):
        self.debug = debug
        self.slot_count = slot_count
        self.last_info = {}

        self.turn_slot_centers = [1, 2, 3, 4, 5]

        self.inner_top_ratio = 0.06
        self.inner_bottom_ratio = 0.94
        self.color_ratio_threshold = 0.90

        self.my_pick_slot = 5

    def _open_mask(self, mask):
        kernel = np.ones((3, 3), np.uint8)
        return cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    def _calc_mask_ratio(self, mask):
        total = mask.size
        if total <= 0:
            return 0.0
        return float(np.count_nonzero(mask)) / float(total)

    def _build_slot_ranges(self, height):
        ranges = []
        step = height / float(self.slot_count)

        for i in range(self.slot_count):
            raw_y1 = int(round(i * step))
            raw_y2 = int(round((i + 1) * step)) - 1

            if i == self.slot_count - 1:
                raw_y2 = height - 1

            seg_h = max(1, raw_y2 - raw_y1 + 1)

            inner_y1 = raw_y1 + int(round(seg_h * self.inner_top_ratio))
            inner_y2 = raw_y1 + int(round(seg_h * self.inner_bottom_ratio)) - 1

            inner_y1 = max(raw_y1, min(raw_y2, inner_y1))
            inner_y2 = max(inner_y1, min(raw_y2, inner_y2))

            center_y = (raw_y1 + raw_y2) // 2
            ranges.append((i + 1, inner_y1, inner_y2, center_y))

        return ranges

    def _pick_primary_slot(self, active_slots, slot_ratios):
        if not active_slots:
            return None

        best_slot = None
        best_ratio = -1.0

        for s in active_slots:
            r = slot_ratios.get(s, 0.0)
            if r > best_ratio:
                best_ratio = r
                best_slot = s

        return best_slot

    def normalize_slots(self, slots):
        return tuple(sorted(set(slots)))

    def get_pattern_a_stage(self, slots):
        slots = self.normalize_slots(slots)

        if slots == (1, 2):
            return 0
        if slots == (3, 4):
            return 1
        if slots == (5,):
            return 2
        if slots == ():
            return 3
        return None

    def get_pattern_b_stage(self, slots):
        slots = self.normalize_slots(slots)

        if slots == (1,):
            return 0
        if slots == (2, 3):
            return 1
        if slots == (4, 5):
            return 2
        if slots == ():
            return 3
        return None

    def detect_team_pattern(self, slots):
        slots = self.normalize_slots(slots)
        a_stage = self.get_pattern_a_stage(slots)
        b_stage = self.get_pattern_b_stage(slots)

        if slots == ():
            return (None, 3)

        if a_stage is not None and b_stage is None:
            return ("A", a_stage)

        if b_stage is not None and a_stage is None:
            return ("B", b_stage)

        return (None, None)

    def infer_patterns(self, ally_slots, enemy_slots):
        ally_slots = self.normalize_slots(ally_slots)
        enemy_slots = self.normalize_slots(enemy_slots)

        ally_pattern, ally_stage = self.detect_team_pattern(ally_slots)
        enemy_pattern, enemy_stage = self.detect_team_pattern(enemy_slots)

        if ally_pattern == "A" and enemy_pattern is None:
            enemy_pattern = "B"
            enemy_stage = self.get_pattern_b_stage(enemy_slots)
        elif ally_pattern == "B" and enemy_pattern is None:
            enemy_pattern = "A"
            enemy_stage = self.get_pattern_a_stage(enemy_slots)

        if enemy_pattern == "A" and ally_pattern is None:
            ally_pattern = "B"
            ally_stage = self.get_pattern_b_stage(ally_slots)
        elif enemy_pattern == "B" and ally_pattern is None:
            ally_pattern = "A"
            ally_stage = self.get_pattern_a_stage(ally_slots)

        return {
            "ally_pattern": ally_pattern,
            "ally_stage": ally_stage,
            "enemy_pattern": enemy_pattern,
            "enemy_stage": enemy_stage,
        }

    def detect_pick_turn_from_patterns(self, ally_slots, enemy_slots):
        info = self.infer_patterns(ally_slots, enemy_slots)

        ally_pattern = info["ally_pattern"]
        ally_stage = info["ally_stage"]
        enemy_pattern = info["enemy_pattern"]
        enemy_stage = info["enemy_stage"]

        if ally_pattern is None or enemy_pattern is None:
            return {
                **info,
                "pick_turn_team": None,
                "is_ally_pick_turn": False,
                "is_enemy_pick_turn": False,
            }

        if ally_pattern == "A":
            a_stage = ally_stage
            b_stage = enemy_stage
            a_owner = "ally"
            b_owner = "enemy"
        else:
            a_stage = enemy_stage
            b_stage = ally_stage
            a_owner = "enemy"
            b_owner = "ally"

        pick_turn_team = None

        if b_stage == a_stage:
            pick_turn_team = b_owner
        elif b_stage == a_stage + 1:
            pick_turn_team = a_owner

        return {
            **info,
            "pick_turn_team": pick_turn_team,
            "is_ally_pick_turn": pick_turn_team == "ally",
            "is_enemy_pick_turn": pick_turn_team == "enemy",
        }

    def _ranges_from_config(self, items):
        ranges = []
        for pair in items:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                continue
            lower, upper = pair
            ranges.append(
                (np.array(lower, dtype=np.uint8), np.array(upper, dtype=np.uint8))
            )
        return ranges

    def _segment_color_presence(self, roi_img, hsv_ranges):
        if roi_img is None or roi_img.size == 0:
            return {
                "slot_ranges": [],
                "active_slots": [],
                "slot_ratios": {},
            }

        h, _w = roi_img.shape[:2]
        hsv = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)

        slot_ranges = self._build_slot_ranges(h)

        active_slots = []
        slot_ratios = {}

        for slot_idx, y1, y2, _center_y in slot_ranges:
            patch = hsv[y1:y2 + 1, :]
            if patch.size == 0:
                slot_ratios[slot_idx] = 0.0
                continue

            merged_mask = None
            for lower, upper in hsv_ranges:
                m = cv2.inRange(patch, lower, upper)
                merged_mask = m if merged_mask is None else cv2.bitwise_or(merged_mask, m)

            if merged_mask is None:
                slot_ratios[slot_idx] = 0.0
                continue

            merged_mask = self._open_mask(merged_mask)
            ratio = self._calc_mask_ratio(merged_mask)
            slot_ratios[slot_idx] = ratio

            if ratio >= self.color_ratio_threshold:
                active_slots.append(slot_idx)

        return {
            "slot_ranges": slot_ranges,
            "active_slots": active_slots,
            "slot_ratios": slot_ratios,
        }

    def _calc_pick_order(self, ally_slot, enemy_slot, pick_turn_team, is_my_turn):
        if is_my_turn and ally_slot is not None:
            return ally_slot

        if pick_turn_team == "ally" and ally_slot is not None:
            return ally_slot

        if pick_turn_team == "enemy" and enemy_slot is not None:
            return enemy_slot

        if ally_slot is not None:
            return ally_slot

        return enemy_slot

    def check(self, ally_roi, enemy_roi, stage_config):
        if ally_roi is None or enemy_roi is None:
            self.last_info = {}
            return False, None, 0.0

        self.slot_count = int(stage_config.get("slot_count", 5))
        self.my_pick_slot = int(stage_config.get("my_pick_slot", 5))
        self.color_ratio_threshold = float(stage_config.get("color_ratio_threshold", 0.90))
        self.inner_top_ratio = float(stage_config.get("inner_top_ratio", 0.06))
        self.inner_bottom_ratio = float(stage_config.get("inner_bottom_ratio", 0.94))

        ally_hsv_ranges = self._ranges_from_config(stage_config.get("ally_hsv_ranges", []))
        enemy_hsv_ranges = self._ranges_from_config(stage_config.get("enemy_hsv_ranges", []))

        if not ally_hsv_ranges:
            self.last_info = {}
            return False, None, 0.0

        if not enemy_hsv_ranges:
            self.last_info = {}
            return False, None, 0.0

        ally_all = self._segment_color_presence(ally_roi, ally_hsv_ranges)
        enemy_red = self._segment_color_presence(enemy_roi, enemy_hsv_ranges)

        ally_active_slots = ally_all["active_slots"]
        enemy_active_slots = enemy_red["active_slots"]

        pick_info = self.detect_pick_turn_from_patterns(
            ally_active_slots,
            enemy_active_slots,
        )

        ally_slot = self._pick_primary_slot(ally_active_slots, ally_all["slot_ratios"])
        enemy_slot = self._pick_primary_slot(enemy_active_slots, enemy_red["slot_ratios"])

        # 현재 config는 ally_hsv_ranges가 파랑+노랑 합본이라
        # 내 차례 여부는 정확히 분리 판정 불가
        is_my_turn = False

        pick_order = self._calc_pick_order(
            ally_slot=ally_slot,
            enemy_slot=enemy_slot,
            pick_turn_team=pick_info["pick_turn_team"],
            is_my_turn=is_my_turn,
        )

        self.last_info = {
            "is_my_turn": is_my_turn,
            "ally_slot": ally_slot,
            "enemy_slot": enemy_slot,
            "turn_slot": ally_slot,

            "ally_slot_ratios": ally_all["slot_ratios"],
            "enemy_slot_ratios": enemy_red["slot_ratios"],

            "ally_slot_ranges": ally_all["slot_ranges"],
            "enemy_slot_ranges": enemy_red["slot_ranges"],

            "ally_active_slots": ally_active_slots,
            "enemy_active_slots": enemy_active_slots,

            "ally_pattern": pick_info["ally_pattern"],
            "enemy_pattern": pick_info["enemy_pattern"],
            "ally_stage": pick_info["ally_stage"],
            "enemy_stage": pick_info["enemy_stage"],

            "pick_turn_team": pick_info["pick_turn_team"],
            "is_ally_pick_turn": pick_info["is_ally_pick_turn"],
            "is_enemy_pick_turn": pick_info["is_enemy_pick_turn"],

            "pick_order": pick_order,
        }

        has_any_signal = (
            len(ally_active_slots) > 0 or
            len(enemy_active_slots) > 0
        )

        if not has_any_signal:
            return False, None, 0.0

        matched_name = f"turn_{pick_info['pick_turn_team']}" if pick_info["pick_turn_team"] else "turn_detected"
        best_score = max(
            [0.0]
            + list(ally_all["slot_ratios"].values())
            + list(enemy_red["slot_ratios"].values())
        )

        return True, matched_name, float(best_score)