"""Image generation service — proxies to ZeniCloud Imagen 3.

NOTE: Filename kept for backward-compat with existing imports
(`from api.services.fal_service import generate_design_images`).
The implementation is now ZeniCloud-backed (Imagen 3, $0.04/image).
Fal.ai integration deprecated 2026-04-27 due to credit exhaustion.

Returns base64 data URIs (data:image/png;base64,...) — frontend renders directly
in <img src="..."/> without needing public URLs.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from api.services import zenicloud_service as zc

logger = logging.getLogger(__name__)

# Style → English keyword pack for the image generator
STYLE_PROMPTS = {
    "modern": "modern luxury interior design, clean lines, neutral tones with bold accents, minimalist furniture, marble and glass surfaces",
    "scandinavian": "scandinavian warm interior design, light wood floors, white walls, natural light, linen textiles, hygge atmosphere",
    "japandi": "japandi zen interior design, japanese-nordic fusion, natural materials, low furniture, muted earth tones, wabi-sabi aesthetics",
    "industrial": "industrial raw interior design, exposed brick walls, metal pipes, concrete floors, edison bulbs, vintage leather",
    "mediterranean": "mediterranean interior design, warm terracotta, arched doorways, natural stone, ceramic tiles, olive and cream palette",
    "biophilic": "biophilic green interior design, indoor plants, natural light, organic materials, living walls, wood and stone",
    "indochine": "Indochine interior, French colonial Vietnamese fusion, rattan furniture, ceramic patterned tiles, silk fabric, brass accents",
    "tropical_modern": "tropical modern interior, lush plants, teak wood, travertine stone, indoor-outdoor flow, large glazing",
    "wabi_sabi": "wabi-sabi interior, lime plaster walls, raw wood, hand-thrown ceramics, soft diffused light, imperfect beauty",
    "neo_classical": "neo-classical interior, symmetric layout, plaster moldings, marble flooring, crystal chandeliers, champagne and navy palette",
}

NEGATIVE_PROMPT = (
    "blurry, distorted perspective, oversaturated colors, AI artifacts, "
    "deformed objects, extra limbs, mannequin people, plastic textures, "
    "cartoonish, generic stock photo, low resolution, watermark"
)


async def generate_image(
    prompt: str,
    *,
    style: str = "modern",
    area_m2: float = 30,
    room_type: str = "living room",
    aspect_ratio: str = "16:9",
) -> Optional[str]:
    """Generate a single interior image via ZeniCloud Imagen 3.

    Returns base64 data URI or None on failure.
    """
    if not zc.is_configured():
        return None

    style_desc = STYLE_PROMPTS.get(style, STYLE_PROMPTS["modern"])
    full_prompt = (
        f"professional interior design photograph, 8K, photorealistic, "
        f"beautiful natural lighting, {style_desc}, {prompt}, {area_m2}m² {room_type}, "
        f"high ceiling, architectural visualization, award winning interior photography, "
        f"Vietnam premium residential project"
    )

    images = await zc.generate_image(
        prompt=full_prompt,
        aspect_ratio=aspect_ratio,
        n=1,
        negative_prompt=NEGATIVE_PROMPT,
    )
    return images[0] if images else None


async def generate_design_images(
    prompt: str,
    *,
    style: str = "modern",
    area_m2: float = 30,
    room_type: str = "living room",
    variant_descriptions: list[str] | None = None,
    count: int = 4,
) -> list[Optional[str]]:
    """Generate `count` design variant images in parallel.

    Strategy: 1 ZeniCloud call with n=count if all variants share the same style,
    otherwise N parallel calls (one per variant). For 4 different style variants
    we go parallel to keep prompts distinct.

    Returns list of `count` items, each is a base64 data URI or None.
    """
    if not zc.is_configured() or count <= 0:
        return [None] * count

    styles_for_variants = ["modern", "scandinavian", "japandi", "industrial"]
    descriptions = (variant_descriptions or [])[:count]
    while len(descriptions) < count:
        descriptions.append("")

    tasks = []
    for i in range(count):
        s = styles_for_variants[i % len(styles_for_variants)]
        desc = descriptions[i] or prompt
        # Combine variant description with base prompt
        variant_prompt = f"{prompt}, {desc}" if desc and desc != prompt else prompt
        tasks.append(
            generate_image(
                variant_prompt,
                style=s,
                area_m2=area_m2,
                room_type=room_type,
                aspect_ratio="16:9",
            )
        )

    results = await asyncio.gather(*tasks, return_exceptions=True)
    out: list[Optional[str]] = []
    for r in results:
        if isinstance(r, Exception):
            logger.warning("variant image failed: %s", r)
            out.append(None)
        else:
            out.append(r)
    return out
