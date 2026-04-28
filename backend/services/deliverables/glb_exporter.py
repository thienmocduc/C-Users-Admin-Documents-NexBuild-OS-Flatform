"""GLB exporter — convert scene_3d JSON → glTF 2.0 binary (.glb).

GLB is the binary glTF format consumable by:
- Three.js (frontend WebGL viewer)
- Blender, SketchUp, AutoCAD, Revit
- WebXR / AR.js / model-viewer.dev

We synthesize simple box meshes for each furniture item + room walls.
Output is a SINGLE .glb file (header + JSON chunk + binary chunk).
"""
from __future__ import annotations

import json
import math
import struct
from typing import Any


# ─── glTF 2.0 spec constants ──────────────────────────────────
# https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html
COMPONENT_FLOAT = 5126
COMPONENT_USHORT = 5123
COMPONENT_UINT = 5125
PRIMITIVE_TRIANGLES = 4
TARGET_ARRAY_BUFFER = 34962        # vertices
TARGET_ELEMENT_ARRAY_BUFFER = 34963  # indices

GLB_MAGIC = 0x46546C67  # "glTF"
GLB_VERSION = 2
GLB_CHUNK_JSON = 0x4E4F534A  # "JSON"
GLB_CHUNK_BIN = 0x004E4942   # "BIN\0"


def _box_mesh(w: float, h: float, d: float) -> tuple[list[float], list[int]]:
    """Generate vertices + indices for a box centered at origin.

    Returns (positions: 24 verts × 3 floats, indices: 12 triangles × 3).
    """
    hw, hh, hd = w / 2, h / 2, d / 2
    # 8 corners
    corners = [
        (-hw, -hh, -hd), (hw, -hh, -hd), (hw, hh, -hd), (-hw, hh, -hd),  # back
        (-hw, -hh, hd), (hw, -hh, hd), (hw, hh, hd), (-hw, hh, hd),     # front
    ]
    # Faces (each face has 4 vertices, 2 triangles, separate copies for flat normals)
    # Face order: -Z, +Z, -X, +X, -Y, +Y
    faces = [
        [0, 1, 2, 3],  # back -Z
        [5, 4, 7, 6],  # front +Z
        [4, 0, 3, 7],  # left -X
        [1, 5, 6, 2],  # right +X
        [4, 5, 1, 0],  # bottom -Y
        [3, 2, 6, 7],  # top +Y
    ]
    positions = []
    indices = []
    for face_idx, face in enumerate(faces):
        base = face_idx * 4
        for vi in face:
            positions.extend(corners[vi])
        indices.extend([base, base + 1, base + 2, base, base + 2, base + 3])
    return positions, indices


def _hex_to_rgba(hex_color: str, alpha: float = 1.0) -> list[float]:
    """Convert #RRGGBB to [r, g, b, a] floats."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return [0.7, 0.7, 0.75, alpha]
    try:
        r = int(h[0:2], 16) / 255.0
        g = int(h[2:4], 16) / 255.0
        b = int(h[4:6], 16) / 255.0
        return [r, g, b, alpha]
    except ValueError:
        return [0.7, 0.7, 0.75, alpha]


# ─── Furniture color palette (PBR baseColor) ───────────────────
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
    "kitchen": "#D4C8B8",
    "rug": "#E8D4B8",
    "plant": "#7DA982",
    "lamp": "#F0C674",
}

# Floor + walls color
FLOOR_COLOR = "#E8DDC8"
WALL_COLOR = "#F5F1EA"


def _color_for(furniture_type: str) -> str:
    if not furniture_type:
        return "#C0C0C8"
    t = furniture_type.lower()
    for k, c in FURNITURE_COLORS.items():
        if k in t:
            return c
    return "#C0C0C8"


# ─── Main entrypoint ──────────────────────────────────────────
def generate_scene_glb(design: dict) -> bytes:
    """Convert a design's scene_3d into a binary .glb file.

    Returns: GLB bytes (~5-50 KB depending on furniture count).
    """
    ao = design.get("agent_output", {}) or {}
    scene = ao.get("scene_3d") or design.get("scene_3d") or {}
    room = scene.get("room") or {}

    # Defaults
    area_m2 = float(design.get("area_m2") or 30)
    width_m = float(room.get("width_m") or 0)
    depth_m = float(room.get("depth_m") or 0)
    height_m = float(room.get("height_m") or 3.0)
    if width_m <= 0 or depth_m <= 0:
        width_m = round(math.sqrt(area_m2 * 1.2), 1)
        depth_m = round(area_m2 / width_m, 1)

    furniture = scene.get("furniture", []) or []

    # ─── Build meshes ──────────────────────────────────────
    meshes_data: list[dict] = []  # {positions, indices, color, transform}

    # 1. Floor (thin box)
    fp, fi = _box_mesh(width_m, 0.05, depth_m)
    meshes_data.append({
        "positions": fp,
        "indices": fi,
        "color": _hex_to_rgba(FLOOR_COLOR),
        "translation": [0, -0.025, 0],
        "name": "Floor",
    })

    # 2. Walls (4 thin boxes)
    wt = 0.15  # wall thickness
    walls = [
        # Back wall
        {"size": (width_m, height_m, wt), "pos": (0, height_m / 2, -depth_m / 2 - wt / 2)},
        # Front wall
        {"size": (width_m, height_m, wt), "pos": (0, height_m / 2, depth_m / 2 + wt / 2)},
        # Left wall
        {"size": (wt, height_m, depth_m), "pos": (-width_m / 2 - wt / 2, height_m / 2, 0)},
        # Right wall
        {"size": (wt, height_m, depth_m), "pos": (width_m / 2 + wt / 2, height_m / 2, 0)},
    ]
    for i, w in enumerate(walls):
        wp, wi = _box_mesh(*w["size"])
        meshes_data.append({
            "positions": wp,
            "indices": wi,
            "color": _hex_to_rgba(WALL_COLOR),
            "translation": list(w["pos"]),
            "name": f"Wall_{i}",
        })

    # 3. Furniture
    for idx, item in enumerate(furniture[:32]):  # cap at 32 items
        try:
            ftype = str(item.get("type") or item.get("name") or "")
            name = str(item.get("name") or ftype or f"item_{idx}")
            pos = item.get("position") or {}
            size = item.get("size") or item.get("dimensions") or {}

            fw = max(0.1, float(size.get("width", size.get("w", 1.0))))
            fh = max(0.1, float(size.get("height", size.get("h", 0.8))))
            fd = max(0.1, float(size.get("depth", size.get("d", 0.6))))

            fx = float(pos.get("x", 0))
            fy = float(pos.get("y", fh / 2))  # default sitting on floor
            fz = float(pos.get("z", 0))

            mp, mi = _box_mesh(fw, fh, fd)
            meshes_data.append({
                "positions": mp,
                "indices": mi,
                "color": _hex_to_rgba(_color_for(ftype)),
                "translation": [fx, fy, fz],
                "name": name[:60],
            })
        except (ValueError, TypeError):
            continue

    # ─── Pack binary buffer ──────────────────────────────
    # Each mesh contributes: positions (24 verts × 3 × 4 bytes = 288) +
    # indices (36 × 2 bytes = 72) → 360 bytes per box
    bin_chunks: list[bytes] = []
    accessors: list[dict] = []
    buffer_views: list[dict] = []
    meshes: list[dict] = []
    materials: list[dict] = []
    nodes: list[dict] = []

    bin_offset = 0

    for mi, mesh in enumerate(meshes_data):
        positions = mesh["positions"]
        indices = mesh["indices"]

        # Pack positions (Float32)
        pos_bytes = struct.pack(f"<{len(positions)}f", *positions)
        # Pad to 4-byte alignment
        if len(pos_bytes) % 4 != 0:
            pos_bytes += b"\x00" * (4 - len(pos_bytes) % 4)
        bin_chunks.append(pos_bytes)

        pos_view_idx = len(buffer_views)
        buffer_views.append({
            "buffer": 0,
            "byteOffset": bin_offset,
            "byteLength": len(pos_bytes),
            "target": TARGET_ARRAY_BUFFER,
        })
        bin_offset += len(pos_bytes)

        pos_acc_idx = len(accessors)
        # Compute min/max for positions (required by spec)
        xs = positions[0::3]; ys = positions[1::3]; zs = positions[2::3]
        accessors.append({
            "bufferView": pos_view_idx,
            "componentType": COMPONENT_FLOAT,
            "count": len(positions) // 3,
            "type": "VEC3",
            "min": [min(xs), min(ys), min(zs)],
            "max": [max(xs), max(ys), max(zs)],
        })

        # Pack indices (UInt16)
        idx_bytes = struct.pack(f"<{len(indices)}H", *indices)
        if len(idx_bytes) % 4 != 0:
            idx_bytes += b"\x00" * (4 - len(idx_bytes) % 4)
        bin_chunks.append(idx_bytes)

        idx_view_idx = len(buffer_views)
        buffer_views.append({
            "buffer": 0,
            "byteOffset": bin_offset,
            "byteLength": len(idx_bytes),
            "target": TARGET_ELEMENT_ARRAY_BUFFER,
        })
        bin_offset += len(idx_bytes)

        idx_acc_idx = len(accessors)
        accessors.append({
            "bufferView": idx_view_idx,
            "componentType": COMPONENT_USHORT,
            "count": len(indices),
            "type": "SCALAR",
        })

        # Material with PBR baseColor
        mat_idx = len(materials)
        materials.append({
            "name": f"mat_{mi}",
            "pbrMetallicRoughness": {
                "baseColorFactor": mesh["color"],
                "metallicFactor": 0.0,
                "roughnessFactor": 0.85,
            },
            "doubleSided": True,
        })

        # Mesh
        mesh_idx = len(meshes)
        meshes.append({
            "name": mesh["name"],
            "primitives": [{
                "attributes": {"POSITION": pos_acc_idx},
                "indices": idx_acc_idx,
                "material": mat_idx,
                "mode": PRIMITIVE_TRIANGLES,
            }],
        })

        # Node
        nodes.append({
            "name": mesh["name"],
            "mesh": mesh_idx,
            "translation": mesh["translation"],
        })

    # Concatenate all binary chunks
    bin_data = b"".join(bin_chunks)

    # ─── Build glTF JSON ────────────────────────────────
    gltf_json: dict[str, Any] = {
        "asset": {
            "version": "2.0",
            "generator": "NexDesign AI · NexBuild Holdings",
        },
        "scene": 0,
        "scenes": [{
            "name": "NexDesign Room",
            "nodes": list(range(len(nodes))),
        }],
        "nodes": nodes,
        "meshes": meshes,
        "materials": materials,
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(bin_data)}],
    }

    json_str = json.dumps(gltf_json, separators=(",", ":"))
    json_bytes = json_str.encode("utf-8")
    # Pad JSON chunk to 4-byte alignment with spaces
    if len(json_bytes) % 4 != 0:
        json_bytes += b" " * (4 - len(json_bytes) % 4)
    # Pad BIN chunk to 4-byte alignment with zeros
    if len(bin_data) % 4 != 0:
        bin_data += b"\x00" * (4 - len(bin_data) % 4)

    # ─── Pack GLB header ────────────────────────────────
    # Header: magic (4) + version (4) + total length (4) = 12 bytes
    # JSON chunk: length (4) + type (4) + data
    # BIN chunk: length (4) + type (4) + data
    total_length = (
        12  # header
        + 8 + len(json_bytes)  # JSON chunk header + data
        + 8 + len(bin_data)    # BIN chunk header + data
    )
    out = bytearray()
    out += struct.pack("<III", GLB_MAGIC, GLB_VERSION, total_length)
    # JSON chunk
    out += struct.pack("<II", len(json_bytes), GLB_CHUNK_JSON)
    out += json_bytes
    # BIN chunk
    out += struct.pack("<II", len(bin_data), GLB_CHUNK_BIN)
    out += bin_data

    return bytes(out)
