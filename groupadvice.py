from typing import List, Sequence, Tuple

Box = Tuple[float, float, float, float]  # x, y, width, height in pixels

# All thresholds are fractions of the live picture, which is already cut to the frame's opening.
EDGE_MARGIN = 0.02        # a face this close to a side counts as cut off or about to be
TOO_FAR_WIDTH = 0.28      # the group is narrower than this share of the picture: come closer
TOO_NEAR_WIDTH = 0.92     # the group is wider than this: step back
TOO_FAR_FACE = 0.07       # a single face smaller than this share of the picture width: come closer
TOO_NEAR_FACE = 0.40      # a single face larger than this: step back
# People shoulder to shoulder have gaps of about one face width between their faces, so only clearly
# wider gaps count as loose.
LOOSE_GAP = 1.6           # gaps between neighbours wider than this many face widths: stand closer together


def advice(boxes: Sequence[Box], width: int, height: int) -> Tuple[str, str]:
    """
    One short hint for the people in front of the camera, as (code, German text). The code is stable for the
    browser (it only shows a hint that stays the same for a moment); "ok" means nothing to improve.
    The order matters: being in the picture beats distance, distance beats spacing.
    """
    if not boxes:
        return ("nobody", "Tretet vor die Kamera")

    count = len(boxes)
    left = min(b[0] for b in boxes)
    right = max(b[0] + b[2] for b in boxes)
    top = min(b[1] for b in boxes)
    bottom = max(b[1] + b[3] for b in boxes)

    if left < width * EDGE_MARGIN or right > width * (1 - EDGE_MARGIN) or top < height * EDGE_MARGIN:
        return ("edge", "Rückt in die Mitte, nicht alle sind im Bild" if count > 1 else "Rück in die Mitte")

    group_width = (right - left) / width
    average_face = sum(b[2] for b in boxes) / count / width
    if group_width > TOO_NEAR_WIDTH or (count == 1 and average_face > TOO_NEAR_FACE):
        return ("back", "Einen Schritt zurück")
    if (count > 1 and group_width < TOO_FAR_WIDTH) or (count == 1 and average_face < TOO_FAR_FACE):
        return ("closer", "Ein Stück näher ran")

    if count > 1:
        ordered = sorted(boxes, key=lambda b: b[0])
        gaps = [
            max(0.0, nxt[0] - (cur[0] + cur[2])) / ((cur[2] + nxt[2]) / 2)
            for cur, nxt in zip(ordered, ordered[1:])
        ]
        if max(gaps) > LOOSE_GAP:
            return ("together", "Enger zusammenrücken")

    return ("ok", "Perfekt, so bleiben")
