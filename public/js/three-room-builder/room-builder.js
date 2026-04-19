/**
 * NexBuild 3D Room Builder — Main Controller
 * Three.js interactive room with furniture drag-drop, materials, camera, export
 * Dependencies: Three.js r162+, OrbitControls, TransformControls
 */

class RoomBuilder {
  constructor(container) {
    this.container = container;
    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.controls = null;
    this.transformControls = null;
    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2();
    this.selected = null;
    this.roomGroup = null;
    this.furnitureGroup = null;
    this.lightsGroup = null;
    this.sceneData = null;
    this.gridHelper = null;
    this.undoStack = [];
    this.redoStack = [];
    this.mode = 'orbit'; // orbit | place | walkthrough
    this.placingItem = null;
    this.ghostMesh = null;
    this.onSelectionChange = null;
    this.onFurnitureChange = null;

    this._init();
  }

  _init() {
    const w = this.container.clientWidth;
    const h = this.container.clientHeight;

    // Scene
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x1a1a2e);
    this.scene.fog = new THREE.Fog(0x1a1a2e, 20, 50);

    // Camera
    this.camera = new THREE.PerspectiveCamera(50, w / h, 0.1, 100);
    this.camera.position.set(6, 5, 8);

    // Renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setSize(w, h);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.2;
    this.container.appendChild(this.renderer.domElement);

    // Groups
    this.roomGroup = new THREE.Group();
    this.roomGroup.name = 'room';
    this.scene.add(this.roomGroup);

    this.furnitureGroup = new THREE.Group();
    this.furnitureGroup.name = 'furniture';
    this.scene.add(this.furnitureGroup);

    this.lightsGroup = new THREE.Group();
    this.lightsGroup.name = 'lights';
    this.scene.add(this.lightsGroup);

    // Default lighting
    this._setupDefaultLights();

    // Controls
    this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.maxPolarAngle = Math.PI * 0.49;
    this.controls.minDistance = 1;
    this.controls.maxDistance = 25;

    // Transform controls for selected furniture
    this.transformControls = new THREE.TransformControls(this.camera, this.renderer.domElement);
    this.transformControls.addEventListener('dragging-changed', (e) => {
      this.controls.enabled = !e.value;
    });
    this.transformControls.addEventListener('objectChange', () => {
      if (this.onFurnitureChange) this.onFurnitureChange();
    });
    this.scene.add(this.transformControls);

    // Events
    this.renderer.domElement.addEventListener('click', (e) => this._onClick(e));
    this.renderer.domElement.addEventListener('mousemove', (e) => this._onMouseMove(e));
    window.addEventListener('keydown', (e) => this._onKeyDown(e));
    window.addEventListener('resize', () => this._onResize());

    // Animate
    this._animate();
  }

  _setupDefaultLights() {
    // Ambient
    const ambient = new THREE.HemisphereLight(0xffffff, 0x444444, 0.4);
    ambient.name = 'ambient';
    this.lightsGroup.add(ambient);

    // Directional (sun from window)
    const sun = new THREE.DirectionalLight(0xFFF8E7, 0.8);
    sun.name = 'sun';
    sun.position.set(3, 5, -2);
    sun.castShadow = true;
    sun.shadow.mapSize.width = 2048;
    sun.shadow.mapSize.height = 2048;
    sun.shadow.camera.near = 0.5;
    sun.shadow.camera.far = 30;
    sun.shadow.camera.left = -10;
    sun.shadow.camera.right = 10;
    sun.shadow.camera.top = 10;
    sun.shadow.camera.bottom = -10;
    this.lightsGroup.add(sun);
  }

  // ─── Room Creation ────────────────────────────────
  buildRoom(width, depth, height) {
    // Clear existing room
    while (this.roomGroup.children.length) {
      this.roomGroup.remove(this.roomGroup.children[0]);
    }

    const wallMat = new THREE.MeshStandardMaterial({
      color: 0xF5F0E8, roughness: 0.9, metalness: 0, side: THREE.DoubleSide,
    });
    const floorMat = new THREE.MeshStandardMaterial({
      color: 0x8B6F47, roughness: 0.6, metalness: 0.05,
    });
    const ceilMat = new THREE.MeshStandardMaterial({
      color: 0xFFFFFF, roughness: 0.95, metalness: 0,
    });

    // Floor
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(width, depth), floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.position.set(width / 2, 0, depth / 2);
    floor.receiveShadow = true;
    floor.name = 'floor';
    this.roomGroup.add(floor);

    // Ceiling
    const ceiling = new THREE.Mesh(new THREE.PlaneGeometry(width, depth), ceilMat);
    ceiling.rotation.x = Math.PI / 2;
    ceiling.position.set(width / 2, height, depth / 2);
    ceiling.name = 'ceiling';
    this.roomGroup.add(ceiling);

    // Walls
    const wallConfigs = [
      { w: width, h: height, pos: [width / 2, height / 2, 0], rot: [0, 0, 0], name: 'wall_back' },
      { w: width, h: height, pos: [width / 2, height / 2, depth], rot: [0, Math.PI, 0], name: 'wall_front' },
      { w: depth, h: height, pos: [0, height / 2, depth / 2], rot: [0, Math.PI / 2, 0], name: 'wall_left' },
      { w: depth, h: height, pos: [width, height / 2, depth / 2], rot: [0, -Math.PI / 2, 0], name: 'wall_right' },
    ];

    wallConfigs.forEach(cfg => {
      const wall = new THREE.Mesh(new THREE.PlaneGeometry(cfg.w, cfg.h), wallMat.clone());
      wall.position.set(...cfg.pos);
      wall.rotation.set(...cfg.rot);
      wall.name = cfg.name;
      wall.receiveShadow = true;
      this.roomGroup.add(wall);
    });

    // Grid
    if (this.gridHelper) this.scene.remove(this.gridHelper);
    this.gridHelper = new THREE.GridHelper(Math.max(width, depth) + 2, Math.max(width, depth) * 5 + 10, 0x444466, 0x222244);
    this.gridHelper.position.set(width / 2, 0.001, depth / 2);
    this.scene.add(this.gridHelper);

    // Adjust camera
    const maxDim = Math.max(width, depth);
    this.camera.position.set(width / 2 + maxDim * 0.5, height * 1.5, depth + maxDim * 0.5);
    this.controls.target.set(width / 2, height * 0.3, depth / 2);
    this.controls.update();
  }

  // ─── Load Scene from Backend Data ─────────────────
  loadScene(data) {
    this.sceneData = data;
    const room = data.room || { width: 6, depth: 5, height: 2.8 };

    this.buildRoom(room.width, room.depth, room.height);

    // Apply materials
    if (data.walls) this.setWallMaterial(data.walls.material, data.walls.color);
    if (data.floor) this.setFloorMaterial(data.floor.material, data.floor.color);

    // Clear furniture
    while (this.furnitureGroup.children.length) {
      this.furnitureGroup.remove(this.furnitureGroup.children[0]);
    }

    // Add furniture
    (data.furniture || []).forEach(f => {
      const catalogItem = FURNITURE_CATALOG.find(c => c.id === f.type) || {
        id: f.type, name: f.name || f.type, category: 'decor',
        dimensions: f.dimensions || { width: 1, height: 1, depth: 1 },
        price: 1000000,
      };

      const mesh = createFurnitureMesh(catalogItem, f.color || '#888888', THREE);
      mesh.position.set(f.position?.x || 0, f.position?.y || 0, f.position?.z || 0);
      mesh.rotation.y = f.rotation || 0;
      if (f.scale && f.scale !== 1) mesh.scale.setScalar(f.scale);
      mesh.userData.furnitureName = f.name || catalogItem.name;
      mesh.userData.furnitureType = f.type;
      this.furnitureGroup.add(mesh);
    });

    // Add lights from scene data
    (data.lights || []).forEach(l => {
      if (l.type === 'point') {
        const pointLight = new THREE.PointLight(
          new THREE.Color(l.color || '#FFF5E6'),
          l.intensity || 0.5,
          10
        );
        pointLight.position.set(l.position?.x || 0, l.position?.y || 2.5, l.position?.z || 0);
        pointLight.castShadow = true;
        this.lightsGroup.add(pointLight);
      }
    });
  }

  // ─── Furniture Placement ──────────────────────────
  startPlacing(catalogItem, color) {
    this.mode = 'place';
    this.placingItem = catalogItem;

    // Create ghost preview
    if (this.ghostMesh) this.scene.remove(this.ghostMesh);
    this.ghostMesh = createFurnitureMesh(catalogItem, color || '#888888', THREE);
    this.ghostMesh.traverse(child => {
      if (child.isMesh) {
        child.material = child.material.clone();
        child.material.transparent = true;
        child.material.opacity = 0.5;
      }
    });
    this.scene.add(this.ghostMesh);
  }

  cancelPlacing() {
    this.mode = 'orbit';
    this.placingItem = null;
    if (this.ghostMesh) {
      this.scene.remove(this.ghostMesh);
      this.ghostMesh = null;
    }
  }

  _placeFurniture(position, catalogItem, color) {
    this._pushUndo();

    const mesh = createFurnitureMesh(catalogItem, color || '#888888', THREE);
    mesh.position.copy(position);
    mesh.userData.furnitureName = catalogItem.name;
    mesh.userData.furnitureType = catalogItem.id;
    this.furnitureGroup.add(mesh);

    this.cancelPlacing();
    this.selectObject(mesh);

    if (this.onFurnitureChange) this.onFurnitureChange();
  }

  removeFurniture(obj) {
    if (!obj) return;
    this._pushUndo();
    this.transformControls.detach();
    this.furnitureGroup.remove(obj);
    this.selected = null;
    if (this.onSelectionChange) this.onSelectionChange(null);
    if (this.onFurnitureChange) this.onFurnitureChange();
  }

  // ─── Selection ────────────────────────────────────
  selectObject(obj) {
    this.selected = obj;
    if (obj) {
      this.transformControls.attach(obj);
      this.transformControls.setMode('translate');
    } else {
      this.transformControls.detach();
    }
    if (this.onSelectionChange) this.onSelectionChange(obj);
  }

  // ─── Materials ────────────────────────────────────
  setWallMaterial(material, color) {
    this.roomGroup.children.forEach(child => {
      if (child.name?.startsWith('wall_')) {
        child.material.color.set(color || '#F5F0E8');
      }
    });
  }

  setFloorMaterial(material, color) {
    const floor = this.roomGroup.getObjectByName('floor');
    if (floor) {
      floor.material.color.set(color || '#8B6F47');
    }
  }

  setFurnitureColor(obj, color) {
    if (!obj) return;
    obj.traverse(child => {
      if (child.isMesh && child.material && !child.material.name?.includes('fixed')) {
        child.material.color.set(color);
      }
    });
  }

  // ─── Camera Presets ───────────────────────────────
  setCameraPreset(preset) {
    const room = this.sceneData?.room || { width: 6, depth: 5, height: 2.8 };
    const cx = room.width / 2, cz = room.depth / 2, ch = room.height;

    switch (preset) {
      case 'top':
        this.camera.position.set(cx, ch * 3.5, cz);
        this.controls.target.set(cx, 0, cz);
        break;
      case 'front':
        this.camera.position.set(cx, ch * 0.5, room.depth + 3);
        this.controls.target.set(cx, ch * 0.4, cz);
        break;
      case 'side':
        this.camera.position.set(-3, ch * 0.5, cz);
        this.controls.target.set(cx, ch * 0.4, cz);
        break;
      case 'perspective':
      default:
        this.camera.position.set(cx + room.width * 0.6, ch * 1.2, cz + room.depth * 0.8);
        this.controls.target.set(cx, ch * 0.3, cz);
        break;
    }
    this.controls.update();
  }

  // ─── Grid & Helpers ───────────────────────────────
  toggleGrid() {
    if (this.gridHelper) this.gridHelper.visible = !this.gridHelper.visible;
  }

  // ─── Export ───────────────────────────────────────
  exportScreenshot() {
    this.renderer.render(this.scene, this.camera);
    return this.renderer.domElement.toDataURL('image/png');
  }

  exportSceneData() {
    const room = this.sceneData?.room || { width: 6, depth: 5, height: 2.8 };

    const furniture = [];
    this.furnitureGroup.children.forEach(child => {
      furniture.push({
        type: child.userData.furnitureType || child.userData.id || 'unknown',
        name: child.userData.furnitureName || child.userData.name || 'Unknown',
        position: { x: child.position.x, y: child.position.y, z: child.position.z },
        rotation: child.rotation.y,
        scale: child.scale.x,
        material: child.userData.material || '',
        color: child.userData.furnitureColor || '#888888',
        dimensions: child.userData.dimensions || {},
      });
    });

    return {
      room,
      walls: this.sceneData?.walls || { material: 'paint', color: '#F5F0E8' },
      floor: this.sceneData?.floor || { material: 'wood', color: '#8B6F47' },
      ceiling: this.sceneData?.ceiling || { material: 'paint', color: '#FFFFFF' },
      furniture,
      lights: this.sceneData?.lights || [],
    };
  }

  getMeasurements() {
    const room = this.sceneData?.room || { width: 6, depth: 5, height: 2.8 };
    const area = room.width * room.depth;
    const items = [];

    this.furnitureGroup.children.forEach(child => {
      items.push({
        name: child.userData.furnitureName || 'Unknown',
        type: child.userData.furnitureType || 'unknown',
        position: `(${child.position.x.toFixed(1)}, ${child.position.z.toFixed(1)})`,
        dimensions: child.userData.dimensions || {},
      });
    });

    return {
      room: { ...room, area: Math.round(area * 10) / 10 },
      furniture: items,
      totalItems: items.length,
    };
  }

  getBOQFromScene() {
    const items = [];
    const priceMap = {
      sofa: 15000000, sofa_l: 22000000, armchair: 5000000,
      table: 5000000, dining_table: 8000000, tv_stand: 4000000,
      bookshelf: 3500000, bed_single: 8000000, bed_double: 12000000,
      wardrobe: 10000000, nightstand: 2500000, dresser: 4000000,
      dining_chair: 1500000, cabinet: 5000000, desk: 6000000,
      office_chair: 3000000, filing_cabinet: 2000000,
      toilet: 8500000, sink: 3200000, bathtub: 12000000,
      plant: 500000, plant_small: 200000, lamp_floor: 1200000,
      lamp_table: 800000, rug: 2000000, shelf: 850000, mirror: 1500000,
    };

    this.furnitureGroup.children.forEach(child => {
      const type = child.userData.furnitureType || child.userData.id || 'unknown';
      const price = priceMap[type] || 1000000;
      items.push({
        category: 'Nội thất',
        name: child.userData.furnitureName || child.userData.name || type,
        unit: 'cái',
        quantity: 1,
        unit_price: price,
        total_price: price,
      });
    });

    // Room materials
    const room = this.sceneData?.room || { width: 6, depth: 5, height: 2.8 };
    const floorArea = room.width * room.depth;
    const wallArea = 2 * (room.width + room.depth) * room.height;
    items.push(
      { category: 'Sàn', name: 'Sàn gỗ công nghiệp 12mm', unit: 'm²', quantity: Math.round(floorArea * 10) / 10, unit_price: 285000, total_price: Math.round(floorArea * 285000) },
      { category: 'Tường', name: 'Sơn nội thất Dulux', unit: 'm²', quantity: Math.round(wallArea * 10) / 10, unit_price: 45000, total_price: Math.round(wallArea * 45000) },
    );

    const total = items.reduce((s, i) => s + i.total_price, 0);
    return { items, total };
  }

  // ─── Undo / Redo ──────────────────────────────────
  _pushUndo() {
    this.undoStack.push(this.exportSceneData());
    this.redoStack = [];
    if (this.undoStack.length > 30) this.undoStack.shift();
  }

  undo() {
    if (!this.undoStack.length) return;
    this.redoStack.push(this.exportSceneData());
    const state = this.undoStack.pop();
    this.loadScene(state);
  }

  redo() {
    if (!this.redoStack.length) return;
    this.undoStack.push(this.exportSceneData());
    const state = this.redoStack.pop();
    this.loadScene(state);
  }

  // ─── Event Handlers ───────────────────────────────
  _onClick(event) {
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    this.raycaster.setFromCamera(this.mouse, this.camera);

    if (this.mode === 'place' && this.placingItem) {
      // Place furniture on floor
      const floor = this.roomGroup.getObjectByName('floor');
      if (floor) {
        const intersects = this.raycaster.intersectObject(floor);
        if (intersects.length) {
          const point = intersects[0].point;
          // Snap to 0.1m grid
          point.x = Math.round(point.x * 10) / 10;
          point.z = Math.round(point.z * 10) / 10;
          point.y = 0;
          this._placeFurniture(point, this.placingItem, this.placingItem._color || '#888888');
        }
      }
      return;
    }

    // Select furniture
    const intersects = this.raycaster.intersectObjects(this.furnitureGroup.children, true);
    if (intersects.length) {
      let obj = intersects[0].object;
      while (obj.parent && obj.parent !== this.furnitureGroup) {
        obj = obj.parent;
      }
      if (obj.parent === this.furnitureGroup) {
        this.selectObject(obj);
        return;
      }
    }

    // Deselect
    this.selectObject(null);
  }

  _onMouseMove(event) {
    if (this.mode !== 'place' || !this.ghostMesh) return;

    const rect = this.renderer.domElement.getBoundingClientRect();
    this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    this.raycaster.setFromCamera(this.mouse, this.camera);
    const floor = this.roomGroup.getObjectByName('floor');
    if (floor) {
      const intersects = this.raycaster.intersectObject(floor);
      if (intersects.length) {
        const p = intersects[0].point;
        this.ghostMesh.position.set(
          Math.round(p.x * 10) / 10,
          0,
          Math.round(p.z * 10) / 10
        );
      }
    }
  }

  _onKeyDown(event) {
    if (event.key === 'Delete' || event.key === 'Backspace') {
      if (this.selected) this.removeFurniture(this.selected);
    }
    if (event.key === 'Escape') {
      if (this.mode === 'place') this.cancelPlacing();
      else this.selectObject(null);
    }
    if (event.key === 'r' || event.key === 'R') {
      // Rotate selected 45 degrees
      if (this.selected) {
        this._pushUndo();
        this.selected.rotation.y += Math.PI / 4;
      }
    }
    if (event.ctrlKey && event.key === 'z') {
      event.preventDefault();
      this.undo();
    }
    if (event.ctrlKey && event.key === 'y') {
      event.preventDefault();
      this.redo();
    }
    // Transform mode shortcuts
    if (event.key === 'g') this.transformControls.setMode('translate');
    if (event.key === 's' && !event.ctrlKey) this.transformControls.setMode('scale');
  }

  _onResize() {
    const w = this.container.clientWidth;
    const h = this.container.clientHeight;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
  }

  _animate() {
    requestAnimationFrame(() => this._animate());
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }

  // ─── Cleanup ──────────────────────────────────────
  dispose() {
    this.renderer.dispose();
    this.controls.dispose();
    this.transformControls.dispose();
    if (this.container.contains(this.renderer.domElement)) {
      this.container.removeChild(this.renderer.domElement);
    }
  }
}

// Export
if (typeof window !== 'undefined') {
  window.RoomBuilder = RoomBuilder;
}
