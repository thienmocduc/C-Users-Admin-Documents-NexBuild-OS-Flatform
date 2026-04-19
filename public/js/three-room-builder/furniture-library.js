/**
 * NexBuild 3D Furniture Library
 * Primitive geometry furniture items (Phase 1 — no GLTF models needed)
 * Each item built from Three.js BoxGeometry/CylinderGeometry compositions
 */

const FURNITURE_CATEGORIES = {
  living: { label: 'Phòng khách', icon: '🛋️' },
  bedroom: { label: 'Phòng ngủ', icon: '🛏️' },
  dining: { label: 'Bàn ăn', icon: '🍽️' },
  office: { label: 'Văn phòng', icon: '💼' },
  bathroom: { label: 'Phòng tắm', icon: '🚿' },
  decor: { label: 'Trang trí', icon: '🌿' },
};

const FURNITURE_CATALOG = [
  // ── Living Room ──
  { id: 'sofa', name: 'Sofa 3 chỗ', category: 'living', dimensions: { width: 2.2, height: 0.85, depth: 0.9 }, price: 15000000 },
  { id: 'sofa_l', name: 'Sofa chữ L', category: 'living', dimensions: { width: 2.8, height: 0.85, depth: 1.8 }, price: 22000000 },
  { id: 'armchair', name: 'Ghế bành', category: 'living', dimensions: { width: 0.9, height: 0.9, depth: 0.85 }, price: 5000000 },
  { id: 'table', name: 'Bàn trà', category: 'living', dimensions: { width: 1.2, height: 0.45, depth: 0.6 }, price: 5000000 },
  { id: 'tv_stand', name: 'Kệ TV', category: 'living', dimensions: { width: 1.8, height: 0.5, depth: 0.4 }, price: 4000000 },
  { id: 'bookshelf', name: 'Kệ sách', category: 'living', dimensions: { width: 0.8, height: 1.8, depth: 0.3 }, price: 3500000 },

  // ── Bedroom ──
  { id: 'bed_single', name: 'Giường đơn', category: 'bedroom', dimensions: { width: 1.0, height: 0.5, depth: 2.0 }, price: 8000000 },
  { id: 'bed_double', name: 'Giường đôi', category: 'bedroom', dimensions: { width: 1.8, height: 0.5, depth: 2.0 }, price: 12000000 },
  { id: 'wardrobe', name: 'Tủ quần áo', category: 'bedroom', dimensions: { width: 1.6, height: 2.0, depth: 0.6 }, price: 10000000 },
  { id: 'nightstand', name: 'Tủ đầu giường', category: 'bedroom', dimensions: { width: 0.5, height: 0.55, depth: 0.4 }, price: 2500000 },
  { id: 'dresser', name: 'Bàn trang điểm', category: 'bedroom', dimensions: { width: 1.0, height: 0.75, depth: 0.45 }, price: 4000000 },

  // ── Dining ──
  { id: 'dining_table', name: 'Bàn ăn 6 người', category: 'dining', dimensions: { width: 1.6, height: 0.75, depth: 0.9 }, price: 8000000 },
  { id: 'dining_chair', name: 'Ghế ăn', category: 'dining', dimensions: { width: 0.45, height: 0.9, depth: 0.5 }, price: 1500000 },
  { id: 'cabinet', name: 'Tủ bếp treo', category: 'dining', dimensions: { width: 1.2, height: 0.7, depth: 0.35 }, price: 5000000 },

  // ── Office ──
  { id: 'desk', name: 'Bàn làm việc', category: 'office', dimensions: { width: 1.4, height: 0.75, depth: 0.7 }, price: 6000000 },
  { id: 'office_chair', name: 'Ghế văn phòng', category: 'office', dimensions: { width: 0.6, height: 1.1, depth: 0.6 }, price: 3000000 },
  { id: 'filing_cabinet', name: 'Tủ hồ sơ', category: 'office', dimensions: { width: 0.4, height: 0.7, depth: 0.5 }, price: 2000000 },

  // ── Bathroom ──
  { id: 'toilet', name: 'Bồn cầu TOTO', category: 'bathroom', dimensions: { width: 0.4, height: 0.4, depth: 0.65 }, price: 8500000 },
  { id: 'sink', name: 'Lavabo TOTO', category: 'bathroom', dimensions: { width: 0.6, height: 0.85, depth: 0.45 }, price: 3200000 },
  { id: 'bathtub', name: 'Bồn tắm', category: 'bathroom', dimensions: { width: 0.7, height: 0.5, depth: 1.5 }, price: 12000000 },

  // ── Decor ──
  { id: 'plant', name: 'Cây cảnh', category: 'decor', dimensions: { width: 0.4, height: 1.2, depth: 0.4 }, price: 500000 },
  { id: 'plant_small', name: 'Cây nhỏ', category: 'decor', dimensions: { width: 0.25, height: 0.4, depth: 0.25 }, price: 200000 },
  { id: 'lamp_floor', name: 'Đèn đứng', category: 'decor', dimensions: { width: 0.3, height: 1.6, depth: 0.3 }, price: 1200000 },
  { id: 'lamp_table', name: 'Đèn bàn', category: 'decor', dimensions: { width: 0.25, height: 0.45, depth: 0.25 }, price: 800000 },
  { id: 'rug', name: 'Thảm trải', category: 'decor', dimensions: { width: 2.0, height: 0.02, depth: 1.4 }, price: 2000000 },
  { id: 'shelf', name: 'Kệ treo tường', category: 'decor', dimensions: { width: 0.8, height: 0.3, depth: 0.25 }, price: 850000 },
  { id: 'mirror', name: 'Gương trang trí', category: 'decor', dimensions: { width: 0.6, height: 0.8, depth: 0.05 }, price: 1500000 },
];

// Color palettes for materials
const MATERIAL_COLORS = {
  fabric: ['#6B7B8D', '#A0522D', '#DEB887', '#BC8F8F', '#708090', '#556B2F', '#8B4513', '#CD853F'],
  leather: ['#3C1414', '#654321', '#8B4513', '#000000', '#2F4F4F'],
  wood: ['#DEB887', '#D2B48C', '#A0845C', '#8B6F47', '#6B4226', '#4A3728', '#3E2723'],
  metal: ['#C0C0C0', '#808080', '#2A2A2A', '#B87333', '#CFB53B'],
  glass: ['#E0F7FA', '#B2EBF2', '#80DEEA'],
  organic: ['#4A7C59', '#2E7D32', '#558B2F', '#33691E'],
  paint: ['#FFFFFF', '#F5F5DC', '#FFF8DC', '#FAF0E6', '#FAEBD7', '#E8D5B7', '#D4C5B2', '#B0A090'],
};

/**
 * Create a Three.js mesh for a furniture item
 */
function createFurnitureMesh(itemDef, color, THREE) {
  const { id, dimensions: d } = itemDef;
  const group = new THREE.Group();
  group.userData = { ...itemDef, furnitureColor: color };

  const mat = (c, roughness = 0.7) => new THREE.MeshStandardMaterial({
    color: new THREE.Color(c),
    roughness,
    metalness: roughness < 0.3 ? 0.5 : 0.1,
  });

  switch (id) {
    case 'sofa':
    case 'sofa_l': {
      // Seat
      const seat = new THREE.Mesh(new THREE.BoxGeometry(d.width, 0.2, d.depth * 0.7), mat(color));
      seat.position.set(0, 0.2, 0);
      seat.castShadow = true;
      group.add(seat);
      // Back
      const back = new THREE.Mesh(new THREE.BoxGeometry(d.width, 0.45, 0.12), mat(color));
      back.position.set(0, 0.5, -d.depth * 0.35 + 0.06);
      back.castShadow = true;
      group.add(back);
      // Arms
      for (const side of [-1, 1]) {
        const arm = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.3, d.depth * 0.7), mat(color));
        arm.position.set(side * (d.width / 2 - 0.06), 0.35, 0);
        arm.castShadow = true;
        group.add(arm);
      }
      // Legs
      for (const x of [-1, 1]) {
        for (const z of [-1, 1]) {
          const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.1), mat('#333'));
          leg.position.set(x * (d.width / 2 - 0.1), 0.05, z * (d.depth * 0.35 - 0.1));
          group.add(leg);
        }
      }
      break;
    }

    case 'armchair': {
      const seat = new THREE.Mesh(new THREE.BoxGeometry(d.width * 0.8, 0.15, d.depth * 0.7), mat(color));
      seat.position.set(0, 0.25, 0.05);
      seat.castShadow = true;
      group.add(seat);
      const back = new THREE.Mesh(new THREE.BoxGeometry(d.width * 0.8, 0.5, 0.1), mat(color));
      back.position.set(0, 0.55, -d.depth * 0.35);
      back.castShadow = true;
      group.add(back);
      for (const side of [-1, 1]) {
        const arm = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.25, d.depth * 0.6), mat(color));
        arm.position.set(side * (d.width / 2 - 0.05), 0.35, 0);
        group.add(arm);
      }
      break;
    }

    case 'table':
    case 'dining_table': {
      // Top
      const top = new THREE.Mesh(new THREE.BoxGeometry(d.width, 0.04, d.depth), mat(color, 0.4));
      top.position.set(0, d.height, 0);
      top.castShadow = true;
      group.add(top);
      // Legs
      for (const x of [-1, 1]) {
        for (const z of [-1, 1]) {
          const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, d.height), mat(color, 0.4));
          leg.position.set(x * (d.width / 2 - 0.08), d.height / 2, z * (d.depth / 2 - 0.08));
          leg.castShadow = true;
          group.add(leg);
        }
      }
      break;
    }

    case 'tv_stand':
    case 'cabinet':
    case 'filing_cabinet':
    case 'dresser': {
      const body = new THREE.Mesh(new THREE.BoxGeometry(d.width, d.height, d.depth), mat(color, 0.5));
      body.position.set(0, d.height / 2, 0);
      body.castShadow = true;
      group.add(body);
      break;
    }

    case 'bed_single':
    case 'bed_double': {
      // Mattress
      const mattress = new THREE.Mesh(new THREE.BoxGeometry(d.width, 0.2, d.depth), mat('#F5F5DC', 0.9));
      mattress.position.set(0, d.height, 0);
      mattress.castShadow = true;
      group.add(mattress);
      // Frame
      const frame = new THREE.Mesh(new THREE.BoxGeometry(d.width + 0.1, d.height - 0.1, d.depth + 0.05), mat(color, 0.5));
      frame.position.set(0, (d.height - 0.1) / 2, 0);
      frame.castShadow = true;
      group.add(frame);
      // Headboard
      const headboard = new THREE.Mesh(new THREE.BoxGeometry(d.width + 0.1, 0.6, 0.08), mat(color, 0.5));
      headboard.position.set(0, d.height + 0.3, -d.depth / 2);
      headboard.castShadow = true;
      group.add(headboard);
      // Pillow(s)
      const pillowCount = d.width > 1.2 ? 2 : 1;
      for (let i = 0; i < pillowCount; i++) {
        const px = pillowCount > 1 ? (i - 0.5) * 0.5 : 0;
        const pillow = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.1, 0.3), mat('#FFFFFF', 0.95));
        pillow.position.set(px, d.height + 0.15, -d.depth * 0.35);
        group.add(pillow);
      }
      break;
    }

    case 'wardrobe': {
      const body = new THREE.Mesh(new THREE.BoxGeometry(d.width, d.height, d.depth), mat(color, 0.5));
      body.position.set(0, d.height / 2, 0);
      body.castShadow = true;
      group.add(body);
      // Door line
      const line = new THREE.Mesh(new THREE.BoxGeometry(0.01, d.height * 0.9, 0.01), mat('#888'));
      line.position.set(0, d.height / 2, d.depth / 2 + 0.005);
      group.add(line);
      // Handles
      for (const side of [-0.08, 0.08]) {
        const handle = new THREE.Mesh(new THREE.CylinderGeometry(0.008, 0.008, 0.15), mat('#AAA', 0.2));
        handle.rotation.x = Math.PI / 2;
        handle.position.set(side, d.height * 0.55, d.depth / 2 + 0.01);
        group.add(handle);
      }
      break;
    }

    case 'nightstand': {
      const body = new THREE.Mesh(new THREE.BoxGeometry(d.width, d.height, d.depth), mat(color, 0.5));
      body.position.set(0, d.height / 2, 0);
      body.castShadow = true;
      group.add(body);
      break;
    }

    case 'dining_chair':
    case 'office_chair': {
      // Seat
      const cSeat = new THREE.Mesh(new THREE.BoxGeometry(d.width, 0.05, d.depth * 0.7), mat(color));
      cSeat.position.set(0, d.height * 0.5, 0.05);
      cSeat.castShadow = true;
      group.add(cSeat);
      // Back
      const cBack = new THREE.Mesh(new THREE.BoxGeometry(d.width * 0.9, d.height * 0.45, 0.04), mat(color));
      cBack.position.set(0, d.height * 0.75, -d.depth * 0.3);
      cBack.castShadow = true;
      group.add(cBack);
      // Legs
      for (const x of [-1, 1]) {
        for (const z of [-1, 1]) {
          const cLeg = new THREE.Mesh(new THREE.CylinderGeometry(0.015, 0.015, d.height * 0.5), mat('#666', 0.3));
          cLeg.position.set(x * (d.width / 2 - 0.05), d.height * 0.25, z * (d.depth * 0.25));
          group.add(cLeg);
        }
      }
      break;
    }

    case 'desk': {
      const dTop = new THREE.Mesh(new THREE.BoxGeometry(d.width, 0.04, d.depth), mat(color, 0.4));
      dTop.position.set(0, d.height, 0);
      dTop.castShadow = true;
      group.add(dTop);
      // Two side panels
      for (const side of [-1, 1]) {
        const panel = new THREE.Mesh(new THREE.BoxGeometry(0.04, d.height, d.depth), mat(color, 0.4));
        panel.position.set(side * (d.width / 2 - 0.02), d.height / 2, 0);
        group.add(panel);
      }
      break;
    }

    case 'bookshelf': {
      // Back panel
      const bBack = new THREE.Mesh(new THREE.BoxGeometry(d.width, d.height, 0.02), mat(color, 0.5));
      bBack.position.set(0, d.height / 2, -d.depth / 2 + 0.01);
      bBack.castShadow = true;
      group.add(bBack);
      // Shelves (5 levels)
      for (let i = 0; i < 5; i++) {
        const shelf = new THREE.Mesh(new THREE.BoxGeometry(d.width, 0.02, d.depth), mat(color, 0.5));
        shelf.position.set(0, i * (d.height / 4), 0);
        group.add(shelf);
      }
      // Sides
      for (const side of [-1, 1]) {
        const bSide = new THREE.Mesh(new THREE.BoxGeometry(0.02, d.height, d.depth), mat(color, 0.5));
        bSide.position.set(side * (d.width / 2), d.height / 2, 0);
        group.add(bSide);
      }
      break;
    }

    case 'plant':
    case 'plant_small': {
      // Pot
      const pot = new THREE.Mesh(new THREE.CylinderGeometry(d.width * 0.35, d.width * 0.3, d.height * 0.25, 8), mat('#8B4513', 0.8));
      pot.position.set(0, d.height * 0.125, 0);
      group.add(pot);
      // Foliage
      const foliage = new THREE.Mesh(new THREE.SphereGeometry(d.width * 0.45, 8, 6), mat(color, 0.9));
      foliage.position.set(0, d.height * 0.6, 0);
      foliage.scale.y = 1.3;
      group.add(foliage);
      break;
    }

    case 'lamp_floor': {
      // Base
      const base = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.15, 0.03, 16), mat('#333', 0.3));
      base.position.set(0, 0.015, 0);
      group.add(base);
      // Pole
      const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.015, 0.015, d.height * 0.8, 8), mat('#333', 0.3));
      pole.position.set(0, d.height * 0.4, 0);
      group.add(pole);
      // Shade
      const shade = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.18, 0.25, 16, 1, true), mat('#FFF8E7', 0.95));
      shade.position.set(0, d.height * 0.85, 0);
      group.add(shade);
      // Light bulb glow
      const glow = new THREE.Mesh(new THREE.SphereGeometry(0.04, 8, 8), new THREE.MeshBasicMaterial({ color: 0xFFF5E6 }));
      glow.position.set(0, d.height * 0.8, 0);
      group.add(glow);
      break;
    }

    case 'lamp_table': {
      const tBase = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.1, 0.02, 12), mat('#888', 0.3));
      tBase.position.set(0, 0.01, 0);
      group.add(tBase);
      const tPole = new THREE.Mesh(new THREE.CylinderGeometry(0.01, 0.01, d.height * 0.6, 8), mat('#888', 0.3));
      tPole.position.set(0, d.height * 0.3, 0);
      group.add(tPole);
      const tShade = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.12, 0.15, 12, 1, true), mat('#FFF8E7', 0.95));
      tShade.position.set(0, d.height * 0.7, 0);
      group.add(tShade);
      break;
    }

    case 'rug': {
      const rugMesh = new THREE.Mesh(new THREE.BoxGeometry(d.width, d.height, d.depth), mat(color, 0.95));
      rugMesh.position.set(0, d.height / 2, 0);
      rugMesh.receiveShadow = true;
      group.add(rugMesh);
      break;
    }

    case 'shelf': {
      const shelfBoard = new THREE.Mesh(new THREE.BoxGeometry(d.width, 0.03, d.depth), mat(color, 0.5));
      shelfBoard.position.set(0, 0, 0);
      shelfBoard.castShadow = true;
      group.add(shelfBoard);
      // Brackets
      for (const side of [-0.3, 0.3]) {
        const bracket = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.12, d.depth), mat('#666', 0.3));
        bracket.position.set(side, -0.06, 0);
        group.add(bracket);
      }
      break;
    }

    case 'mirror': {
      const mFrame = new THREE.Mesh(new THREE.BoxGeometry(d.width + 0.04, d.height + 0.04, 0.03), mat(color || '#8B6F47', 0.4));
      mFrame.position.set(0, 0, 0);
      group.add(mFrame);
      const mGlass = new THREE.Mesh(
        new THREE.BoxGeometry(d.width, d.height, 0.01),
        new THREE.MeshStandardMaterial({ color: 0xE0E8F0, roughness: 0.05, metalness: 0.9 })
      );
      mGlass.position.set(0, 0, 0.02);
      group.add(mGlass);
      break;
    }

    case 'toilet': {
      const bowl = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.15, 0.35, 12), mat('#FFFFFF', 0.3));
      bowl.position.set(0, 0.175, 0.05);
      group.add(bowl);
      const tank = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.3, 0.15), mat('#FFFFFF', 0.3));
      tank.position.set(0, 0.35, -d.depth / 2 + 0.08);
      group.add(tank);
      break;
    }

    case 'sink': {
      const basin = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.18, 0.12, 16), mat('#FFFFFF', 0.2));
      basin.position.set(0, d.height, 0);
      group.add(basin);
      const pedestal = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.1, d.height - 0.1, 8), mat('#FFFFFF', 0.3));
      pedestal.position.set(0, (d.height - 0.1) / 2, 0);
      group.add(pedestal);
      break;
    }

    case 'bathtub': {
      const tub = new THREE.Mesh(new THREE.BoxGeometry(d.width, d.height, d.depth), mat('#FFFFFF', 0.2));
      tub.position.set(0, d.height / 2, 0);
      group.add(tub);
      break;
    }

    default: {
      // Generic box fallback
      const box = new THREE.Mesh(new THREE.BoxGeometry(d.width, d.height, d.depth), mat(color || '#888'));
      box.position.set(0, d.height / 2, 0);
      box.castShadow = true;
      group.add(box);
    }
  }

  return group;
}

// Export for module use
if (typeof window !== 'undefined') {
  window.FURNITURE_CATEGORIES = FURNITURE_CATEGORIES;
  window.FURNITURE_CATALOG = FURNITURE_CATALOG;
  window.MATERIAL_COLORS = MATERIAL_COLORS;
  window.createFurnitureMesh = createFurnitureMesh;
}
