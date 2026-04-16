"""Fal.ai image generation service — server-side (API key in .env, NOT client).

Replaces the exposed FAL_KEY in nexdesign-app.html.
Uses Fal.ai Flux Schnell for fast interior design renders.
"""
import asyncio
import os
from typing import Optional

import httpx

FAL_API_KEY = os.getenv("FAL_API_KEY", "")
FAL_ENDPOINT = "https://fal.run/fal-ai/flux/schnell"


STYLE_PROMPTS = {
    "modern": "modern luxury interior design, clean lines, neutral tones with bold accents, minimalist furniture, marble and glass surfaces",
    "scandinavian": "scandinavian warm interior design, light wood floors, white walls, natural light, linen textiles, hygge atmosphere",
    "japandi": "japandi zen interior design, japanese-nordic fusion, natural materials, low furniture, muted earth tones, wabi-sabi aesthetics",
    "industrial": "industrial raw interior design, exposed brick walls, metal pipes, concrete floors, edison bulbs, vintage leather",
    "mediterranean": "mediterranean interior design, warm terracotta, arched doorways, natural stone, ceramic tiles, olive and cream palette",
    "biophilic": "biophilic green interior design, indoor plants, natural light, organic materials, living walls, wood and stone",
}


async def generate_image(
    prompt: str,
    style: str = "modern",
    area_m2: float = 30,
    room_type: str = "living room",
    image_size: str = "landscape_16_9",
    num_inference_steps: int = 8,
) -> Optional[str]:
    """Generate a single interior design image via Fal.ai Flux.

    Returns image URL or None on failure.
    """
    if not FAL_API_KEY:
        return None

    style_desc = STYLE_PROMPTS.get(style, STYLE_PROMPTS["modern"])

    full_prompt = (
        f"professional interior design photograph, 8k, photorealistic, beautiful natural lighting, "
        f"{style_desc}, {prompt}, {area_m2}m² {room_type}, high ceiling, "
        f"architectural visualization, award winning interior photography"
    )

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                FAL_ENDPOINT,
                headers={"Authorization": f"Key {FAL_API_KEY}"},
                json={
                    "prompt": full_prompt,
                    "image_size": image_size,
                    "num_inference_steps": num_inference_steps,
                    "seed": None,  # random
                    "enable_safety_checker": True,
                },
            )

            if resp.status_code == 200:
                data = resp.json()
                images = data.get("images", [])
                if images:
                    return images[0].get("url")
    except Exception as e:
        print(f"Fal.ai error: {e}")

    return None


async def generate_design_images(
    prompt: str,
    style: str = "modern",
    area_m2: float = 30,
    room_type: str = "living room",
    variant_descriptions: list[str] = None,
    count: int = 4,
) -> list[Optional[str]]:
    """Generate multiple design variant images in parallel.

    Returns list of image URLs (None for failures).
    """
    if not FAL_API_KEY:
        return [None] * count

    styles_for_variants = ["modern", "scandinavian", "japandi", "industrial"]
    if variant_descriptions:
        # Use variant-specific prompts
        tasks = [
            generate_image(
                prompt=f"{prompt}, {desc}",
                style=styles_for_variants[i % len(styles_for_variants)],
                area_m2=area_m2,
                room_type=room_type,
            )
            for i, desc in enumerate(variant_descriptions[:count])
        ]
    else:
        # Default 4 style variants
        tasks = [
            generate_image(
                prompt=prompt,
                style=s,
                area_m2=area_m2,
                room_type=room_type,
            )
            for s in styles_for_variants[:count]
        ]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r if isinstance(r, str) else None for r in results]
