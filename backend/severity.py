"""
Pavement Distress Index (PDI) Module
Calculates a transparent, multi-factor road damage priority score (0 to 100)
and classifies events into Low, Moderate, High, or Critical priority.

NOTE: This is a prototype prioritization index for crowdsourced academic
evaluation, combining kinematic intensity, event classification, crowdsourced
device consensus, and model confidence. It is not an officially certified
civil engineering pavement standard (such as ASTM D6433).
"""

import math
from typing import Dict, Any, Tuple
import config

# Base severity weights by anomaly classification
BASE_EVENT_WEIGHTS = {
    "Normal Road": 5.0,
    "Speed Breaker": 35.0,
    "Pothole": 70.0
}


def get_priority_level(pdi_score: float) -> str:
    """Map a 0-100 PDI score to human-readable priority levels."""
    score = max(0.0, min(100.0, float(pdi_score)))
    for level, (low, high) in config.PDI_THRESHOLDS.items():
        if low <= score < high:
            return level
    return "Critical" if score >= 80.0 else "Low"


def calculate_single_pdi(
    event_type: str,
    confidence: float,
    peak_accel: float = 9.8,
    accel_jerk: float = 0.0
) -> Tuple[float, str]:
    """
    Calculate PDI score for an individual detection event.
    
    Formula:
    BaseScore = BASE_EVENT_WEIGHTS[event_type]
    KinematicShock = min(20.0, ((peak_accel - 9.8) / 15.0) * 20.0) if peak > 9.8 else 0
    ConfidenceFactor = 0.8 + (0.2 * confidence)
    SingleScore = min(100.0, (BaseScore + KinematicShock) * ConfidenceFactor)
    """
    base = BASE_EVENT_WEIGHTS.get(event_type, 10.0)
    conf = max(0.0, min(1.0, float(confidence or 0.5)))
    peak = max(0.0, float(peak_accel or 9.8))

    # Kinematic shock adjustment from high impact G-force
    if peak > 9.8:
        shock_bonus = min(20.0, ((peak - 9.8) / 15.0) * 20.0)
    else:
        shock_bonus = 0.0

    conf_factor = 0.8 + (0.2 * conf)
    raw_score = (base + shock_bonus) * conf_factor
    final_score = round(max(0.0, min(100.0, raw_score)), 1)
    priority = get_priority_level(final_score)

    return final_score, priority


def calculate_cluster_pdi(
    base_scores: list,
    detection_count: int,
    unique_devices_count: int,
    dominant_event_type: str
) -> Tuple[float, str]:
    """
    Calculate composite PDI score for a geographic cluster of detections.
    
    Considers:
    - Average individual PDI scores of members
    - Repetition frequency (higher report count increases urgency)
    - Independent vehicle consensus (multiple distinct phones verifying same spot)
    """
    if not base_scores:
        avg_base = BASE_EVENT_WEIGHTS.get(dominant_event_type, 10.0)
    else:
        avg_base = sum(base_scores) / len(base_scores)

    # Frequency bonus: log scale up to +15 points
    freq_bonus = min(15.0, math.log(max(1, detection_count) + 1) * 4.5)

    # Independent crowdsource consensus bonus: +5 points per extra unique device, up to +15
    device_bonus = min(15.0, max(0, unique_devices_count - 1) * 5.0)

    composite_score = avg_base + freq_bonus + device_bonus
    final_score = round(max(0.0, min(100.0, composite_score)), 1)
    priority = get_priority_level(final_score)

    return final_score, priority
