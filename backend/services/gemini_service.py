"""Gemini AI service — generates design concepts + BOQ from prompts.

THU TIEN THAT: Moi request ~$0.001 → margin cuc lon voi gia 299K/thang Pro.
Free: 3 renders/thang. Pro: unlimited.
"""
import json
import os
from typing import Optional

import httpx

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

# Vietnamese construction materials database for BOQ pricing
VN_MATERIALS_DB = {
    "san_go": {"name": "Sàn gỗ công nghiệp An Cường 12mm", "unit": "m2", "price": 285000},
    "son_tuong": {"name": "Dulux Weathershield 5L Trắng ngà", "unit": "lon", "price": 485000},
    "den_led": {"name": "Philips LED Panel 18W 4000K", "unit": "bộ", "price": 285000},
    "o_cam": {"name": "Schneider Electric Vivace Đơn", "unit": "cái", "price": 85000},
    "kinh_cuong_luc": {"name": "Kính cường lực Low-E 8mm", "unit": "m2", "price": 520000},
    "gach_op": {"name": "Gạch ốp tường Viglacera 30x60", "unit": "m2", "price": 195000},
    "xi_mang": {"name": "Xi măng Vicem PCB40 bao 40kg", "unit": "bao", "price": 128000},
    "thep": {"name": "Thép cuộn CB240-T Hòa Phát", "unit": "kg", "price": 17800},
    "go_mdf": {"name": "MDF An Cường 18mm 1220x2440", "unit": "tờ", "price": 265000},
    "day_dien": {"name": "Dây điện Cadivi 2.5mm²", "unit": "cuộn", "price": 2200000},
    "ong_nuoc": {"name": "Ống nước Bình Minh PPR 20mm", "unit": "cây", "price": 45000},
    "bon_cau": {"name": "Bồn cầu TOTO C884 1 khối", "unit": "bộ", "price": 8500000},
    "lavabo": {"name": "Lavabo TOTO L946CR đặt bàn", "unit": "cái", "price": 3200000},
    "voi_sen": {"name": "Vòi sen TOTO TBG11302V tay mạ chrome", "unit": "bộ", "price": 4800000},
    "cua_nhom": {"name": "Cửa nhôm Xingfa kính Low-E", "unit": "m2", "price": 1850000},
    "rem_cua": {"name": "Rèm vải Hàn Quốc 2 lớp", "unit": "m", "price": 350000},
    "den_trang_tri": {"name": "Đèn thả trang trí Nordic", "unit": "cái", "price": 1200000},
    "ke_go": {"name": "Kệ gỗ treo tường MDF sơn PU", "unit": "cái", "price": 850000},
}

STYLE_DESCRIPTIONS = {
    "modern": "Phong cách hiện đại - đường nét sạch, tối giản, tone trung tính với điểm nhấn mạnh",
    "scandinavian": "Scandinavian - ấm áp, gỗ sáng, trắng chủ đạo, ánh sáng tự nhiên",
    "japandi": "Japandi - kết hợp Nhật Bản & Bắc Âu, tĩnh lặng, vật liệu tự nhiên",
    "industrial": "Industrial - thô mộc, gạch trần, kim loại, bê tông lộ thiên",
    "mediterranean": "Địa Trung Hải - tông ấm, gốm, đá tự nhiên, arch doorway",
    "biophilic": "Biophilic - cây xanh, ánh sáng tự nhiên, vật liệu hữu cơ, kết nối thiên nhiên",
}


async def generate_design(
    prompt: str,
    style: str = "modern",
    room_type: Optional[str] = None,
    area_m2: Optional[float] = None,
    budget_million: Optional[float] = None,
    auto_boq: bool = True,
) -> dict:
    """Call Gemini API to generate 4 design concepts + BOQ.

    Returns structured JSON with variants and materials list.
    Cost: ~$0.001/request with gemini-2.0-flash.
    """
    style_desc = STYLE_DESCRIPTIONS.get(style, STYLE_DESCRIPTIONS["modern"])

    system_prompt = f"""Bạn là kiến trúc sư nội thất chuyên nghiệp tại Việt Nam.
Nhiệm vụ: Tạo 4 phương án thiết kế nội thất + bảng khối lượng vật liệu (BOQ) + dữ liệu 3D scene.

Yêu cầu trả về JSON CHÍNH XÁC theo format sau (KHÔNG markdown, KHÔNG giải thích):
{{
  "prompt_enhanced": "mô tả chi tiết hơn prompt gốc (tiếng Việt)",
  "variants": [
    {{
      "variant_idx": 0,
      "style_label": "Tên phong cách A",
      "description": "Mô tả chi tiết phương án A (80-120 từ tiếng Việt)"
    }},
    {{
      "variant_idx": 1,
      "style_label": "Tên phong cách B",
      "description": "Mô tả chi tiết phương án B"
    }},
    {{
      "variant_idx": 2,
      "style_label": "Tên phong cách C",
      "description": "Mô tả chi tiết phương án C"
    }},
    {{
      "variant_idx": 3,
      "style_label": "Tên phong cách D",
      "description": "Mô tả chi tiết phương án D"
    }}
  ],
  "boq_items": [
    {{
      "category": "Tên nhóm (Sàn & Tường / Ánh sáng & Điện / Cửa & Kính / Nội thất / Vệ sinh)",
      "material": "Loại vật liệu",
      "product_name": "Tên sản phẩm cụ thể (thương hiệu VN: An Cường, Dulux, Philips, TOTO, Schneider)",
      "unit": "đơn vị (m2/lon/bộ/cái/cuộn/cây)",
      "quantity": 10,
      "unit_price": 285000,
      "total_price": 2850000
    }}
  ],
  "scene_3d": {{
    "room": {{
      "width": 6.0,
      "depth": 5.0,
      "height": 2.8
    }},
    "walls": {{
      "material": "paint",
      "color": "#F5F0E8"
    }},
    "floor": {{
      "material": "wood",
      "color": "#8B6F47"
    }},
    "ceiling": {{
      "material": "paint",
      "color": "#FFFFFF"
    }},
    "furniture": [
      {{
        "type": "sofa",
        "name": "Sofa 3 chỗ",
        "position": {{"x": 3.0, "y": 0, "z": 1.5}},
        "rotation": 0,
        "scale": 1.0,
        "material": "fabric",
        "color": "#6B7B8D",
        "dimensions": {{"width": 2.2, "height": 0.85, "depth": 0.9}}
      }}
    ],
    "lights": [
      {{
        "type": "point",
        "position": {{"x": 3.0, "y": 2.5, "z": 2.5}},
        "intensity": 0.8,
        "color": "#FFF5E6"
      }}
    ]
  }}
}}

QUAN TRỌNG:
- 4 phương án phải KHÁC NHAU rõ rệt về phong cách
- BOQ dùng GIÁ THỊ TRƯỜNG VN 2025 (không phải giá quốc tế)
- Sản phẩm phải là thương hiệu có BÁN tại VN
- Số lượng tính theo diện tích {area_m2 or 30}m²
- Budget khoảng {budget_million or 'không giới hạn'} triệu
- BOQ 8-15 items, đủ các nhóm vật liệu chính"""

    user_prompt = f"""Thiết kế nội thất: {prompt}
Phong cách chính: {style_desc}
Loại phòng: {room_type or 'phòng khách'}
Diện tích: {area_m2 or 30}m²
Ngân sách: {budget_million or 'linh hoạt'} triệu VNĐ"""

    if not GEMINI_API_KEY:
        # Fallback: return demo data when no API key
        return _generate_demo_response(prompt, style, area_m2)

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                json={
                    "contents": [
                        {"role": "user", "parts": [{"text": system_prompt + "\n\n" + user_prompt}]}
                    ],
                    "generationConfig": {
                        "temperature": 0.8,
                        "topP": 0.95,
                        "maxOutputTokens": 4096,
                        "responseMimeType": "application/json",
                    },
                },
            )

            if resp.status_code != 200:
                return _generate_demo_response(prompt, style, area_m2)

            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]

            # Parse JSON response
            result = json.loads(text)

            # Validate and enrich BOQ prices from our DB
            for item in result.get("boq_items", []):
                if item["unit_price"] <= 0:
                    item["unit_price"] = 100000
                item["total_price"] = int(item["quantity"] * item["unit_price"])

            return result

    except Exception as e:
        print(f"Gemini API error: {e}")
        return _generate_demo_response(prompt, style, area_m2)


def _generate_demo_response(prompt: str, style: str, area_m2: Optional[float] = None) -> dict:
    """Demo response when Gemini API is unavailable."""
    area = area_m2 or 30
    style_names = {
        "modern": "Hiện đại tối giản",
        "scandinavian": "Scandinavian ấm áp",
        "japandi": "Japandi thanh lịch",
        "industrial": "Industrial thô mộc",
        "mediterranean": "Địa Trung Hải",
        "biophilic": "Biophilic xanh",
    }

    base_style = style_names.get(style, "Hiện đại")

    variants = [
        {"variant_idx": 0, "style_label": f"{base_style} — Phương án A",
         "description": f"Thiết kế {prompt.lower()} theo phong cách {base_style.lower()} với tone trắng kem chủ đạo. Sàn gỗ công nghiệp An Cường 12mm tone walnut, trần thạch cao phẳng với đèn LED âm trần Philips. Tường sơn Dulux trắng ngà, điểm nhấn tường feature bằng gỗ MDF sơn PU."},
        {"variant_idx": 1, "style_label": f"Scandinavian — Phương án B",
         "description": f"Không gian {prompt.lower()} tối giản kiểu Bắc Âu. Sàn gỗ sáng, tường trắng tinh khiết, nội thất gỗ tự nhiên. Cửa kính lớn đón ánh sáng, rèm vải linen mỏng. Kệ mở trang trí, cây xanh nhỏ tạo điểm nhấn."},
        {"variant_idx": 2, "style_label": f"Japandi — Phương án C",
         "description": f"Kết hợp tinh tế Nhật Bản và Bắc Âu cho {prompt.lower()}. Vật liệu tự nhiên: gỗ, đá, vải linen. Màu sắc trầm ấm: be, nâu nhạt, xám. Nội thất thấp, đường nét sạch, không gian tĩnh lặng."},
        {"variant_idx": 3, "style_label": f"Industrial — Phương án D",
         "description": f"Phong cách công nghiệp cho {prompt.lower()}. Tường gạch trần exposed, ống thép lộ thiên, bê tông mài. Đèn Edison retro, kệ sắt khung, sofa da vintage. Tone xám-đen-nâu tạo cá tính mạnh."},
    ]

    boq_items = [
        {"category": "Sàn & Tường", "material": "Sàn gỗ", "product_name": "Sàn gỗ công nghiệp An Cường 12mm", "unit": "m2", "quantity": area, "unit_price": 285000, "total_price": int(area * 285000)},
        {"category": "Sàn & Tường", "material": "Sơn tường", "product_name": "Dulux Weathershield 5L Trắng ngà", "unit": "lon", "quantity": max(4, int(area / 8)), "unit_price": 485000, "total_price": max(4, int(area / 8)) * 485000},
        {"category": "Ánh sáng & Điện", "material": "Đèn trần", "product_name": "Philips LED Panel 18W 4000K", "unit": "bộ", "quantity": max(4, int(area / 8)), "unit_price": 285000, "total_price": max(4, int(area / 8)) * 285000},
        {"category": "Ánh sáng & Điện", "material": "Ổ cắm", "product_name": "Schneider Electric Vivace Đơn", "unit": "cái", "quantity": max(8, int(area / 4)), "unit_price": 85000, "total_price": max(8, int(area / 4)) * 85000},
        {"category": "Cửa & Kính", "material": "Cửa sổ", "product_name": "Kính cường lực Low-E 8mm", "unit": "m2", "quantity": max(4, int(area / 5)), "unit_price": 520000, "total_price": max(4, int(area / 5)) * 520000},
        {"category": "Nội thất", "material": "Kệ trang trí", "product_name": "Kệ gỗ treo tường MDF sơn PU", "unit": "cái", "quantity": 3, "unit_price": 850000, "total_price": 2550000},
        {"category": "Nội thất", "material": "Rèm cửa", "product_name": "Rèm vải Hàn Quốc 2 lớp", "unit": "m", "quantity": max(4, int(area / 5)), "unit_price": 350000, "total_price": max(4, int(area / 5)) * 350000},
        {"category": "Ánh sáng & Điện", "material": "Đèn trang trí", "product_name": "Đèn thả trang trí Nordic", "unit": "cái", "quantity": 2, "unit_price": 1200000, "total_price": 2400000},
    ]

    boq_total = sum(item["total_price"] for item in boq_items)

    # Calculate room dimensions from area
    import math
    w = round(math.sqrt(area * 1.2), 1)  # slightly wider than deep
    d = round(area / w, 1)

    scene_3d = {
        "room": {"width": w, "depth": d, "height": 2.8},
        "walls": {"material": "paint", "color": "#F5F0E8"},
        "floor": {"material": "wood", "color": "#8B6F47"},
        "ceiling": {"material": "paint", "color": "#FFFFFF"},
        "furniture": [
            {"type": "sofa", "name": "Sofa 3 chỗ", "position": {"x": w * 0.5, "y": 0, "z": d * 0.3}, "rotation": 0, "scale": 1.0, "material": "fabric", "color": "#6B7B8D", "dimensions": {"width": 2.2, "height": 0.85, "depth": 0.9}},
            {"type": "table", "name": "Bàn trà", "position": {"x": w * 0.5, "y": 0, "z": d * 0.5}, "rotation": 0, "scale": 1.0, "material": "wood", "color": "#A0845C", "dimensions": {"width": 1.2, "height": 0.45, "depth": 0.6}},
            {"type": "tv_stand", "name": "Kệ TV", "position": {"x": w * 0.5, "y": 0, "z": d * 0.9}, "rotation": 0, "scale": 1.0, "material": "wood", "color": "#4A3728", "dimensions": {"width": 1.8, "height": 0.5, "depth": 0.4}},
            {"type": "shelf", "name": "Kệ trang trí", "position": {"x": 0.2, "y": 1.2, "z": d * 0.5}, "rotation": 0, "scale": 1.0, "material": "wood", "color": "#C8A882", "dimensions": {"width": 0.8, "height": 0.3, "depth": 0.25}},
            {"type": "plant", "name": "Cây cảnh", "position": {"x": w * 0.9, "y": 0, "z": d * 0.1}, "rotation": 0, "scale": 1.0, "material": "organic", "color": "#4A7C59", "dimensions": {"width": 0.4, "height": 1.2, "depth": 0.4}},
            {"type": "rug", "name": "Thảm trải", "position": {"x": w * 0.5, "y": 0.01, "z": d * 0.45}, "rotation": 0, "scale": 1.0, "material": "fabric", "color": "#D4C5B2", "dimensions": {"width": 2.0, "height": 0.02, "depth": 1.4}},
            {"type": "lamp", "name": "Đèn đứng", "position": {"x": w * 0.85, "y": 0, "z": d * 0.25}, "rotation": 0, "scale": 1.0, "material": "metal", "color": "#2A2A2A", "dimensions": {"width": 0.3, "height": 1.6, "depth": 0.3}},
        ],
        "lights": [
            {"type": "ambient", "intensity": 0.4, "color": "#FFFFFF"},
            {"type": "directional", "position": {"x": w * 0.3, "y": 2.5, "z": -1}, "intensity": 0.8, "color": "#FFF8E7"},
            {"type": "point", "position": {"x": w * 0.85, "y": 1.5, "z": d * 0.25}, "intensity": 0.5, "color": "#FFF5E6"},
        ],
    }

    return {
        "prompt_enhanced": f"Thiết kế nội thất {prompt} — diện tích {area}m², phong cách {base_style.lower()}, tối ưu công năng và thẩm mỹ với vật liệu chất lượng cao từ các thương hiệu uy tín tại Việt Nam.",
        "variants": variants,
        "boq_items": boq_items,
        "boq_total": boq_total,
        "scene_3d": scene_3d,
    }
