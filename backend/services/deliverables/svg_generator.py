"""SVG floor plan generator — mặt bằng 2D dimensioned từ scene_3d.

Reads `agent_output.scene_3d.room.{width_m, depth_m}` + `furniture[]` and
draws a top-view floor plan with:
- Walls (thick lines) + dimension lines
- Furniture rectangles labeled with name
- Door/window markers
- Title block (project info + scale)
- 1m grid + scale ruler

Output is plain SVG text (no external deps beyond `svgwrite`).
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any

import svgwrite


# ─── Theme ────────────────────────────────────────────────────
TEAL = "#00C9A7"
DARK = "#0A1020"
GREY = "#5A7898"
LIGHT_GREY = "#CDD8E5"
ACCENT = "#0EA5E9"
WALL_COLOR = "#2A3A55"

# Default dimensions if scene_3d missing
DEFAULT_ROOM = {"width_m": 6.0, "depth_m": 5.0, "height_m": 3.0}


# ─── Furniture color map (top-view fill) ─────────────────────
FURNITURE_COLORS = {
    "sofa": "#A8B4C8",
    "armchair": "#9BAEC4",
    "chair": "#9BAEC4",
    "bed": "#B8A89C",
    "wardrobe": "#8B7C6E",
    "tv": "#3A3A3A",
    "tv_unit": "#4A4A4A",
    "cabinet": "#8B7C6E",
    "table": "#C0A875",
    "coffee_table": "#C0A875",
    "dining_table": "#C0A875",
    "kitchen": "#D4C8B8",
    "rug": "#E8D4B8",
    "plant": "#7DA982",
    "lamp": "#F0C674",
    "default": "#B8C5D6",
}


def _safe(v: Any, d: str = "") -> str:
    if v is None:
        return d
    return str(v).strip() or d


def _color_for(furniture_type: str) -> str:
    if not furniture_type:
        return FURNITURE_COLORS["default"]
    t = furniture_type.lower()
    for key, color in FURNITURE_COLORS.items():
        if key in t:
            return color
    return FURNITURE_COLORS["default"]


# ─── Main entrypoint ─────────────────────────────────────────
def generate_floor_plan_svg(design: dict) -> str:
    """Generate SVG floor plan from design's scene_3d data.

    Returns SVG as string (UTF-8). If scene_3d missing, returns a placeholder
    floor plan based on area_m2.
    """
    ao = design.get("agent_output", {}) or {}
    scene = ao.get("scene_3d") or design.get("scene_3d") or {}
    room = scene.get("room") or {}

    # Determine room dimensions
    area_m2 = float(design.get("area_m2") or 30)
    width_m = float(room.get("width_m") or 0)
    depth_m = float(room.get("depth_m") or 0)
    if width_m <= 0 or depth_m <= 0:
        # Derive from area_m2 (rectangular ~1.2:1)
        width_m = round(math.sqrt(area_m2 * 1.2), 1)
        depth_m = round(area_m2 / width_m, 1)

    # SVG canvas — 50px = 1m scale
    SCALE = 50  # px per meter
    PADDING = 80
    W_px = int(width_m * SCALE) + 2 * PADDING
    H_px = int(depth_m * SCALE) + 2 * PADDING + 120  # extra for title

    dwg = svgwrite.Drawing(
        size=(f"{W_px}px", f"{H_px}px"),
        viewBox=f"0 0 {W_px} {H_px}",
        profile="tiny",
    )

    # ─── Background ────────────────────────────────────────
    dwg.add(dwg.rect(insert=(0, 0), size=(W_px, H_px), fill="#FAFBFD"))

    # ─── Title block ──────────────────────────────────────
    title_y = 30
    dwg.add(dwg.text(
        "MẶT BẰNG THIẾT KẾ — NexBuild",
        insert=(PADDING, title_y),
        font_family="Helvetica, sans-serif",
        font_size="18px",
        font_weight="bold",
        fill=DARK,
    ))
    subtitle = (
        f"{_safe(design.get('style'))} · "
        f"{_safe(design.get('room_type'))} · "
        f"{width_m}m × {depth_m}m = {width_m * depth_m:.1f}m² · "
        f"Tỷ lệ 1:50"
    )
    dwg.add(dwg.text(
        subtitle,
        insert=(PADDING, title_y + 18),
        font_family="Helvetica, sans-serif",
        font_size="11px",
        fill=GREY,
    ))

    # ─── Grid (1m squares) ────────────────────────────────
    grid_g = dwg.g(stroke=LIGHT_GREY, stroke_width=0.5, fill="none", opacity=0.4)
    floor_x0 = PADDING
    floor_y0 = PADDING + 40
    floor_x1 = floor_x0 + width_m * SCALE
    floor_y1 = floor_y0 + depth_m * SCALE
    for i in range(int(width_m) + 1):
        x = floor_x0 + i * SCALE
        grid_g.add(dwg.line(start=(x, floor_y0), end=(x, floor_y1)))
    for i in range(int(depth_m) + 1):
        y = floor_y0 + i * SCALE
        grid_g.add(dwg.line(start=(floor_x0, y), end=(floor_x1, y)))
    dwg.add(grid_g)

    # ─── Walls (thick outer rect) ────────────────────────
    WALL_THICKNESS = 8
    # Outer wall (slightly larger)
    dwg.add(dwg.rect(
        insert=(floor_x0 - WALL_THICKNESS / 2, floor_y0 - WALL_THICKNESS / 2),
        size=(width_m * SCALE + WALL_THICKNESS, depth_m * SCALE + WALL_THICKNESS),
        fill="none",
        stroke=WALL_COLOR,
        stroke_width=WALL_THICKNESS,
    ))

    # ─── Furniture ──────────────────────────────────────
    furniture = scene.get("furniture", []) or []
    for f in furniture:
        try:
            ftype = _safe(f.get("type") or f.get("name"))
            name = _safe(f.get("name") or ftype, "Item")
            position = f.get("position") or {}
            size = f.get("size") or f.get("dimensions") or {}

            fx = float(position.get("x", 0))
            fz = float(position.get("z", position.get("y", 0)))  # z in 3D = y in 2D top-view
            fw = float(size.get("width", size.get("w", 1.0)))
            fd = float(size.get("depth", size.get("d", 0.6)))

            # Convert from meters to px (origin top-left of floor)
            # Assume position is room-center origin → convert
            px = floor_x0 + (fx + width_m / 2 - fw / 2) * SCALE
            py = floor_y0 + (fz + depth_m / 2 - fd / 2) * SCALE
            pw = fw * SCALE
            pd = fd * SCALE

            color = _color_for(ftype)
            dwg.add(dwg.rect(
                insert=(px, py), size=(pw, pd),
                fill=color, stroke=DARK, stroke_width=1, opacity=0.85,
                rx=2, ry=2,
            ))
            # Label inside if large enough
            if pw >= 40 and pd >= 20:
                dwg.add(dwg.text(
                    name[:12],
                    insert=(px + pw / 2, py + pd / 2 + 3),
                    font_family="Helvetica, sans-serif",
                    font_size="9px",
                    fill=DARK,
                    text_anchor="middle",
                ))
        except (ValueError, TypeError, KeyError):
            continue

    # ─── Dimension lines ────────────────────────────────
    dim_offset = 30
    dim_color = ACCENT

    # Top dimension (width)
    top_y = floor_y0 - dim_offset
    dwg.add(dwg.line(
        start=(floor_x0, top_y), end=(floor_x1, top_y),
        stroke=dim_color, stroke_width=1,
    ))
    # Tick marks
    dwg.add(dwg.line(start=(floor_x0, top_y - 5), end=(floor_x0, top_y + 5),
                     stroke=dim_color, stroke_width=1))
    dwg.add(dwg.line(start=(floor_x1, top_y - 5), end=(floor_x1, top_y + 5),
                     stroke=dim_color, stroke_width=1))
    dwg.add(dwg.text(
        f"{width_m:.1f}m",
        insert=((floor_x0 + floor_x1) / 2, top_y - 8),
        font_family="Helvetica, sans-serif",
        font_size="11px",
        font_weight="bold",
        fill=dim_color,
        text_anchor="middle",
    ))

    # Left dimension (depth)
    left_x = floor_x0 - dim_offset
    dwg.add(dwg.line(
        start=(left_x, floor_y0), end=(left_x, floor_y1),
        stroke=dim_color, stroke_width=1,
    ))
    dwg.add(dwg.line(start=(left_x - 5, floor_y0), end=(left_x + 5, floor_y0),
                     stroke=dim_color, stroke_width=1))
    dwg.add(dwg.line(start=(left_x - 5, floor_y1), end=(left_x + 5, floor_y1),
                     stroke=dim_color, stroke_width=1))
    dwg.add(dwg.text(
        f"{depth_m:.1f}m",
        insert=(left_x - 8, (floor_y0 + floor_y1) / 2),
        font_family="Helvetica, sans-serif",
        font_size="11px",
        font_weight="bold",
        fill=dim_color,
        text_anchor="middle",
        transform=f"rotate(-90 {left_x - 8} {(floor_y0 + floor_y1) / 2})",
    ))

    # ─── North arrow ───────────────────────────────────
    north_cx = floor_x1 + 30
    north_cy = floor_y0 + 20
    arrow_pts = [
        (north_cx, north_cy - 12),
        (north_cx - 6, north_cy + 8),
        (north_cx, north_cy + 4),
        (north_cx + 6, north_cy + 8),
    ]
    dwg.add(dwg.polygon(
        points=arrow_pts, fill=DARK, stroke=DARK, stroke_width=1,
    ))
    dwg.add(dwg.text(
        "N", insert=(north_cx, north_cy - 16),
        font_family="Helvetica, sans-serif", font_size="11px",
        font_weight="bold", fill=DARK, text_anchor="middle",
    ))

    # ─── Footer (legend) ──────────────────────────────
    footer_y = floor_y1 + 50
    dwg.add(dwg.text(
        f"Generated by NexDesign AI · {datetime.now().strftime('%d/%m/%Y %H:%M')} · "
        f"{len(furniture)} furniture items",
        insert=(PADDING, footer_y),
        font_family="Helvetica, sans-serif",
        font_size="9px",
        fill=GREY,
    ))

    # Brand strip
    dwg.add(dwg.rect(
        insert=(0, H_px - 8), size=(W_px, 8),
        fill=TEAL,
    ))

    return dwg.tostring()
