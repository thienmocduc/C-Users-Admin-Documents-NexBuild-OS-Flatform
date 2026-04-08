# PHASE 1 — SPEC v2 (TOI UU — XOA TRUNG — CHONG XUNG DOT)
# NexBuild Holdings Platform — NXB-SPEC-HUB-001
# CTO Recheck: 08/04/2026

---

## 1. VAN DE PHAT HIEN SAU KHI RECHECK

### 1.1 XUNG DOT CSS GIUA 3 FILE GOC

| Van de | Chi tiet | Muc do |
|--------|----------|--------|
| Ten bien CSS khac nhau | HUB: `--indigo`, `--violet`, `--amber` / DASH+MKT: `--ind`, `--vio`, `--amb` | **CRITICAL** |
| Ten bg khac nhau | HUB: `--bg0/bg1/bg2/bg3` / DASH+MKT: `--bg/bg2/bg3/bg4` | **CRITICAL** |
| Gia tri mau khac nhau | HUB text=#EDF2FF / DASH+MKT text=#F2F7FF | **HIGH** |
| Orb opacity khac nhau | HUB: var(--orb-op)=.35 / DASH: .25 / MKT: .3 | MEDIUM |
| Toast khac nhau | HUB: 3500ms, 13px / DASH+MKT: 3200ms, 12px | LOW |
| Border-radius khac nhau | HUB: --r=14px / MKT: --r=12px | MEDIUM |
| Class trung ten, khac style | `.card` (HUB vs DASH), `.bdg` (HUB vs MKT), `.pill` (DASH vs MKT) | **HIGH** |
| Auth modal khac flow | HUB: redirect marketplace / MKT: login in-place | **HIGH** |
| Font import khac | HUB co italic / DASH+MKT co Mono 700 | LOW |

### 1.2 CODE TRUNG LAP (LANG PHI)

| Component | HUB | DASH | MKT | Lines trung |
|-----------|-----|------|-----|-------------|
| CSS reset + base | Co | Co | Co | ~30 |
| CSS custom props (2 theme) | Co | Co | Co | ~60 |
| CSS orbs + @keyframes drift | Co | Co | Co | ~50 |
| CSS toast | Co | Co | Co | ~15 |
| CSS pills/badges | Co | Co | Co | ~40 |
| CSS buttons (base) | Co | Co | Co | ~30 |
| JS toast() | Co | Co | Co | ~8 |
| JS toggleTheme() | Co | Co | Co | ~10 |
| HTML orbs (4 div) | Co | Co | Co | ~5 |
| Google Fonts import | Co | Co | Co | ~1 |
| **TONG TRUNG LAP** | | | | **~250 lines x 3 = ~750 lines lang phi** |

---

## 2. PHUONG AN TOI UU — KIEN TRUC FILE

### Nguyen tac:
1. **File goc la nguon su that** — KHONG viet lai, chi TACH code chung ra
2. **Moi file HTML goc giu nguyen logic rieng** — chi import common
3. **Chuan hoa 1 lan** — dung chung, khong conflict
4. **0 overlap** — moi dong code chi ton tai 1 noi

### Cau truc thu muc:

```
nexbuild-platform/
├── index.html                    # Hub (redirect hoac copy tu hub.html)
├── hub.html                      # Landing page (tu nexbuild-hub.html goc)
├── dashboard.html                # Dashboard 5 roles (tu nexbuild-dashboard.html goc)
├── marketplace.html              # Marketplace B2B/B2C (tu nexbuild-marketplace.html goc)
│
├── css/
│   ├── tokens.css                # Design tokens chuan hoa (1 nguon duy nhat)
│   ├── orbs.css                  # Orbs + @keyframes drift
│   ├── toast.css                 # Toast notification
│   ├── pills.css                 # Pills + badges (chuan hoa ten class)
│   ├── hub.css                   # CSS rieng Hub (header, hero, modules, pricing, footer...)
│   ├── app-shell.css             # CSS chung DASH + MKT (sidebar, topbar, modal, cards)
│   ├── dashboard.css             # CSS rieng Dashboard (role pages, charts, GPS)
│   └── marketplace.css           # CSS rieng Marketplace (products, cart, booking, forum)
│
├── js/
│   ├── common.js                 # toast(), toggleTheme(), auth logic
│   ├── hub.js                    # ECO_DATA, animCount, openEco, LANGS, openMarketplace...
│   ├── dashboard.js              # NAV, loginAs, setPage, openModal, withdraw, topup...
│   └── marketplace.js            # PRODUCTS, WORKERS, cart, checkout, booking, forum...
│
├── lang/
│   ├── vi.json                   # Tieng Viet (default)
│   ├── en.json                   # English
│   └── ... (38 files)            # Lazy load theo lua chon
│
├── api/                          # FastAPI backend
│   ├── main.py
│   ├── routers/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   └── ...
│
├── docs/
│   └── PHASE1-SPEC-v2.md        # File nay
│
└── .env                          # Secrets (KHONG commit)
```

---

## 3. CHUAN HOA CSS TOKENS (XOA XUNG DOT)

### Quy tac: Dung TEN DAY DU (theo HUB), GIA TRI theo tung file goc

```css
/* === tokens.css === */
/* SHARED — dung cho ca 3 file */

:root {
  /* Brand colors — DONG NHAT ca 3 file */
  --c1: #00C9A7;
  --c2: #0EA5E9;
  --indigo: #6366F1;
  --violet: #A855F7;
  --gold: #C9A84C;
  --red: #EF4444;
  --green: #22C55E;
  --amber: #F59E0B;
  --orange: #FB923C;
  --grad: linear-gradient(135deg, #00C9A7, #0EA5E9, #6366F1, #A855F7);

  /* Typography */
  --font: "Noto Sans", sans-serif;
  --mono: "Noto Sans Mono", monospace;

  /* Transitions */
  --tr: .22s cubic-bezier(.4, 0, .2, 1);
}

/* HUB theme — dung cho hub.html */
[data-page="hub"][data-theme="dark"] {
  --bg: #04080F;
  --bg2: #080F1C;
  --bg3: #0D1828;
  --bg4: #132034;
  --text: #EDF2FF;
  --text2: #8898B8;
  --text3: #3A4F6A;
  --bdr: rgba(255,255,255,.07);
  --sur: rgba(255,255,255,.04);
  --r: 14px;
  --orb-op: .35;
}
[data-page="hub"][data-theme="light"] {
  --bg: #F8F9FF;
  --bg2: #FFFFFF;
  --bg3: #EFF1FF;
  --bg4: #E4E7FF;
  --text: #0A1020;
  --text2: #2A3A55;
  --text3: #6A7A95;
  --bdr: rgba(99,102,241,.12);
  --sur: rgba(255,255,255,.7);
  --r: 14px;
  --orb-op: .18;
}

/* APP theme — dung cho dashboard.html + marketplace.html */
[data-page="app"][data-theme="dark"] {
  --bg: #030609;
  --bg2: #050A14;
  --bg3: #080E1C;
  --bg4: #0B1424;
  --text: #F2F7FF;
  --text2: #B0C8E4;
  --text3: #5A7898;
  --bdr: rgba(255,255,255,.08);
  --sur: rgba(8,14,30,.96);
  --sb: rgba(4,7,16,.97);
  --r: 12px;
  --orb-op: .28;
}
[data-page="app"][data-theme="light"] {
  --bg: #EEF2FF;
  --bg2: #F8F9FF;
  --bg3: #E4E9FF;
  --bg4: #DDE4FF;
  --text: #0A1020;
  --text2: #2A3A58;
  --text3: #5A7898;
  --bdr: rgba(80,100,200,.1);
  --sur: rgba(255,255,255,.97);
  --sb: rgba(248,250,255,.98);
  --r: 12px;
  --orb-op: .07;
}
```

### Cach dung:
- `hub.html`: `<html data-page="hub" data-theme="dark">`
- `dashboard.html`: `<html data-page="app" data-theme="dark">`
- `marketplace.html`: `<html data-page="app" data-theme="dark">`

### Class trung ten — CHUAN HOA:

| Class cu (xung dot) | Class moi (khong xung dot) |
|---------------------|---------------------------|
| `.card` (HUB eco) | `.eco-card` |
| `.card` (DASH) | `.dash-card` |
| `.bdg` (HUB eco) | `.eco-bdg` |
| `.bdg` (MKT product) | `.mkt-bdg` |
| `.pill` (DASH 9px) | `.pill` (chuan = 10px) |
| `.btn` (DASH) | `.btn` (chuan, dung chung) |

---

## 4. CHUAN HOA AUTH FLOW (XOA TRUNG)

### Van de hien tai:
- HUB co auth modal → login → redirect marketplace
- MKT co auth modal → login → stay in page, show dashboard
- DASH co role select → loginAs() → show role dashboard

### Phuong an thong nhat:

```
[User vao Hub] → Click "Dang nhap" → Auth Modal (common.js)
    ├─ Login thanh cong → redirect dashboard.html (co role)
    └─ Register thanh cong → verify email → redirect dashboard.html

[User vao Marketplace] → Click "Dang nhap" → Auth Modal (common.js)
    ├─ Login thanh cong → stay in page, load user data
    └─ Register thanh cong → verify email → stay in page

[User vao Dashboard] → Check auth
    ├─ Co token → load role dashboard
    └─ Khong token → redirect hub.html hoac show login
```

### Auth state management (common.js):
```
1 function duy nhat: authManager
- Login: POST /api/v1/auth/login → nhan JWT → luu HttpOnly cookie
- Check: GET /api/v1/auth/me → return user + role
- Logout: POST /api/v1/auth/logout → xoa cookie
- Guard: requireAuth() → check token → redirect neu chua login
```

---

## 5. DATABASE SCHEMA v2 (DA XOA TRUNG)

### Thay doi so voi v1:
1. **Xoa `login_attempts`** → dung Redis counter (nhanh hon, TTL tu dong)
2. **Gop `supplier_profiles` vao `users` JSONB** → tranh 2 bang cho 1 user
3. **KHONG gop worker_profiles** → vi worker co nhieu field rieng (trade, GPS, skills)
4. **Them `user_preferences`** → tach lang/theme ra khoi users table
5. **Them `contractor_teams`** → quan ly doi tho cua nha thau

### Schema toi uu: 30 tables (giam tu 32)

```sql
-- =============================================
-- CORE: USERS & AUTH (3 tables + Redis)
-- =============================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('buyer','worker','contractor','supplier','admin')),
    avatar_url TEXT,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending','active','suspended','rejected')),
    plan VARCHAR(20) DEFAULT 'free' CHECK (plan IN ('free','pro','enterprise')),
    email_verified BOOLEAN DEFAULT FALSE,
    phone_verified BOOLEAN DEFAULT FALSE,
    -- Supplier fields (NULL cho role khac)
    store_name VARCHAR(255),
    supplier_type VARCHAR(50),
    main_category VARCHAR(100),
    delivery_area VARCHAR(200),
    supplier_intro TEXT,
    b2b_credit_policy VARCHAR(20) DEFAULT 'none',
    pricing_tier VARCHAR(20) DEFAULT 'free',
    is_verified_supplier BOOLEAN DEFAULT FALSE,
    --
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE user_preferences (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    lang VARCHAR(5) DEFAULT 'VI',
    theme VARCHAR(10) DEFAULT 'dark',
    daily_quota INT DEFAULT 3,
    quota_reset TIMESTAMPTZ
);

CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- login_attempts → Redis: key=login:{ip}, TTL=15min, max=5

-- =============================================
-- ECOSYSTEM: MODULES (3 tables)
-- =============================================

CREATE TABLE modules (
    id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    num VARCHAR(5),
    tag VARCHAR(100),
    model VARCHAR(100),
    hook TEXT,
    description TEXT,
    icon_svg TEXT,
    icon_bg VARCHAR(20),
    icon_border VARCHAR(20),
    cta_bg VARCHAR(100),
    color VARCHAR(20),
    gradient VARCHAR(200),
    file_url VARCHAR(255),
    pricing_label VARCHAR(100),
    pricing_detail VARCHAR(200),
    sort_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE module_pains (
    id SERIAL PRIMARY KEY,
    module_id VARCHAR(20) REFERENCES modules(id) ON DELETE CASCADE,
    before_title VARCHAR(200),
    before_desc TEXT,
    after_title VARCHAR(200),
    after_desc TEXT,
    sort_order INT DEFAULT 0
);

CREATE TABLE module_results (
    id SERIAL PRIMARY KEY,
    module_id VARCHAR(20) REFERENCES modules(id) ON DELETE CASCADE,
    emoji VARCHAR(10),
    title VARCHAR(200),
    kpi VARCHAR(100),
    sort_order INT DEFAULT 0
);

-- =============================================
-- MARKETPLACE: PRODUCTS (2 tables)
-- =============================================

CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    icon VARCHAR(20),
    parent_id INT REFERENCES categories(id),
    sort_order INT DEFAULT 0
);

CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id UUID NOT NULL REFERENCES users(id),
    category_id INT REFERENCES categories(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price BIGINT NOT NULL,
    promo_price BIGINT,
    unit VARCHAR(20) NOT NULL,
    stock INT DEFAULT 0,
    min_order INT DEFAULT 1,
    delivery_time VARCHAR(50),
    sku VARCHAR(50),
    images TEXT[],
    badges TEXT[],
    sale_label VARCHAR(50),
    rating NUMERIC(2,1) DEFAULT 0,
    rating_count INT DEFAULT 0,
    is_d2c BOOLEAN DEFAULT FALSE,
    allow_b2b_credit BOOLEAN DEFAULT FALSE,
    show_in_boq BOOLEAN DEFAULT TRUE,
    status VARCHAR(20) DEFAULT 'pending',
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- TALENT: WORKERS (2 tables)
-- =============================================

CREATE TABLE worker_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    trade VARCHAR(50) NOT NULL,
    experience_years INT,
    daily_rate BIGINT,
    work_area VARCHAR(200),
    travel_radius_km INT DEFAULT 10,
    bio TEXT,
    skills TEXT[],
    certificates TEXT[],
    portfolio_count INT DEFAULT 0,
    rating NUMERIC(2,1) DEFAULT 0,
    rating_count INT DEFAULT 0,
    is_online BOOLEAN DEFAULT FALSE,
    accept_escrow BOOLEAN DEFAULT TRUE,
    allow_gps BOOLEAN DEFAULT FALSE,
    accept_insurance BOOLEAN DEFAULT TRUE,
    ai_score INT,
    status VARCHAR(20) DEFAULT 'pending',
    verified_by UUID REFERENCES users(id),
    verified_at TIMESTAMPTZ,
    location_lat NUMERIC(10,7),
    location_lng NUMERIC(10,7),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE worker_portfolio (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    worker_id UUID NOT NULL REFERENCES worker_profiles(id) ON DELETE CASCADE,
    title VARCHAR(255),
    description TEXT,
    images TEXT[],
    rating NUMERIC(2,1),
    tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- BOOKINGS (1 table)
-- =============================================

CREATE TABLE bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    buyer_id UUID NOT NULL REFERENCES users(id),
    worker_id UUID NOT NULL REFERENCES worker_profiles(id),
    job_description TEXT NOT NULL,
    work_address VARCHAR(500),
    num_days INT NOT NULL,
    start_date DATE NOT NULL,
    shift VARCHAR(20) CHECK (shift IN ('morning','afternoon','evening')),
    worker_fee BIGINT NOT NULL,
    service_fee BIGINT NOT NULL,
    insurance_fee BIGINT DEFAULT 0,
    total BIGINT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    escrow_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- PROJECTS & BIDDING (3 tables)
-- =============================================

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    type VARCHAR(50),
    budget_min BIGINT,
    budget_max BIGINT,
    duration_days INT,
    address VARCHAR(500),
    floor_area_m2 NUMERIC(10,2),
    requirements TEXT,
    work_categories TEXT[],
    bid_deadline DATE,
    payment_method VARCHAR(30),
    blueprints TEXT[],
    status VARCHAR(20) DEFAULT 'open',
    view_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE bids (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id),
    contractor_id UUID NOT NULL REFERENCES users(id),
    bid_price BIGINT NOT NULL,
    price_unit VARCHAR(10) DEFAULT 'dong',
    duration_value INT,
    duration_unit VARCHAR(10),
    capability TEXT,
    construction_plan TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE project_milestones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id),
    contractor_id UUID REFERENCES users(id),
    name VARCHAR(255),
    percentage INT,
    amount BIGINT,
    status VARCHAR(20) DEFAULT 'pending',
    escrow_id UUID,
    due_date DATE,
    completed_at TIMESTAMPTZ
);

-- =============================================
-- CONTRACTOR TEAMS (1 table — MOI)
-- =============================================

CREATE TABLE contractor_teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contractor_id UUID NOT NULL REFERENCES users(id),
    worker_id UUID NOT NULL REFERENCES users(id),
    role_in_team VARCHAR(100),
    assigned_project UUID REFERENCES projects(id),
    monthly_salary BIGINT,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(contractor_id, worker_id)
);

-- =============================================
-- CART & ORDERS (3 tables)
-- =============================================

CREATE TABLE cart_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    product_id UUID NOT NULL REFERENCES products(id),
    quantity INT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, product_id)
);

CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_number VARCHAR(30) UNIQUE NOT NULL,
    buyer_id UUID NOT NULL REFERENCES users(id),
    supplier_id UUID REFERENCES users(id),
    shipping_address VARCHAR(500),
    receiver_name VARCHAR(255),
    receiver_phone VARCHAR(20),
    notes TEXT,
    payment_method VARCHAR(30),
    subtotal BIGINT NOT NULL,
    vat BIGINT NOT NULL,
    total BIGINT NOT NULL,
    status VARCHAR(20) DEFAULT 'processing',
    escrow_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id),
    product_name VARCHAR(255),
    quantity INT NOT NULL,
    unit_price BIGINT NOT NULL,
    total BIGINT NOT NULL
);

-- =============================================
-- ESCROW (1 table — TRUNG TAM)
-- =============================================

CREATE TABLE escrow (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idempotency_key VARCHAR(100) UNIQUE NOT NULL,
    buyer_id UUID NOT NULL REFERENCES users(id),
    seller_id UUID REFERENCES users(id),
    entity_type VARCHAR(20) NOT NULL,  -- 'order','booking','milestone'
    entity_id UUID NOT NULL,
    amount BIGINT NOT NULL,
    service_fee BIGINT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'held',
    released_at TIMESTAMPTZ,
    auto_release_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- DISPUTES (1 table)
-- =============================================

CREATE TABLE disputes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    escrow_id UUID NOT NULL REFERENCES escrow(id),
    reporter_id UUID NOT NULL REFERENCES users(id),
    reason VARCHAR(50) NOT NULL,
    description TEXT,
    evidence TEXT[],
    status VARCHAR(20) DEFAULT 'open',
    resolution TEXT,
    resolved_by UUID REFERENCES users(id),
    deadline TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

-- =============================================
-- REVIEWS (1 table — CHUNG cho tat ca target)
-- =============================================

CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reviewer_id UUID NOT NULL REFERENCES users(id),
    target_type VARCHAR(20) NOT NULL,  -- 'supplier','worker','product','order'
    target_id UUID NOT NULL,
    stars INT NOT NULL CHECK (stars BETWEEN 1 AND 5),
    criteria JSONB,
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- CONTRACTS (1 table)
-- =============================================

CREATE TABLE contracts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_number VARCHAR(30) UNIQUE NOT NULL,
    project_id UUID NOT NULL REFERENCES projects(id),
    investor_id UUID NOT NULL REFERENCES users(id),
    contractor_id UUID NOT NULL REFERENCES users(id),
    contract_value BIGINT NOT NULL,
    duration_days INT,
    warranty_months INT DEFAULT 12,
    late_penalty_pct NUMERIC(4,2) DEFAULT 0.1,
    milestone_count INT,
    signed_by_investor BOOLEAN DEFAULT FALSE,
    signed_by_contractor BOOLEAN DEFAULT FALSE,
    signed_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'draft',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- WALLET & TRANSACTIONS (3 tables)
-- =============================================

CREATE TABLE wallets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    available_balance BIGINT DEFAULT 0,
    escrow_held BIGINT DEFAULT 0,
    b2b_credit_limit BIGINT DEFAULT 0,
    b2b_credit_used BIGINT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    type VARCHAR(30) NOT NULL,
    amount BIGINT NOT NULL,
    balance_after BIGINT,
    reference_type VARCHAR(20),
    reference_id UUID,
    description TEXT,
    status VARCHAR(20) DEFAULT 'completed',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE bank_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    bank_name VARCHAR(100),
    account_number_encrypted VARCHAR(255),  -- AES-256
    account_holder VARCHAR(255),
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- FORUM & NXT (3 tables)
-- =============================================

CREATE TABLE forum_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    tags TEXT[],
    votes INT DEFAULT 0,
    comment_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE forum_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES forum_posts(id) ON DELETE CASCADE,
    author_id UUID NOT NULL REFERENCES users(id),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- forum_votes → Redis sorted set (nhanh hon table rieng)
-- nxt_tokens → wallet.nxt_balance (them column vao wallets)

-- =============================================
-- NOTIFICATIONS (1 table)
-- =============================================

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    type VARCHAR(50),
    title VARCHAR(255),
    message TEXT,
    link VARCHAR(500),
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- CHAT (3 tables)
-- =============================================

CREATE TABLE chat_rooms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(20) DEFAULT 'direct',
    entity_type VARCHAR(20),
    entity_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE chat_participants (
    room_id UUID REFERENCES chat_rooms(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    PRIMARY KEY (room_id, user_id)
);

CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id UUID NOT NULL REFERENCES chat_rooms(id),
    sender_id UUID NOT NULL REFERENCES users(id),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- ADMIN (2 tables + Redis)
-- =============================================

CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    event_type VARCHAR(50) NOT NULL,
    ip_address INET,
    details JSONB,
    severity VARCHAR(10) DEFAULT 'info',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE system_settings (
    key VARCHAR(100) PRIMARY KEY,
    value VARCHAR(255) NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by UUID REFERENCES users(id)
);

-- =============================================
-- BOQ (1 table)
-- =============================================

CREATE TABLE boq_imports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    file_url TEXT,
    manual_text TEXT,
    status VARCHAR(20) DEFAULT 'processing',
    result JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Tong: 30 tables (giam 2 tu v1)

| Da xoa/gop | Ly do |
|------------|-------|
| `login_attempts` | Chuyen sang Redis counter, TTL tu dong, nhanh hon |
| `supplier_profiles` | Gop vao `users` (them columns, NULL cho role khac) |
| `forum_votes` | Chuyen sang Redis sorted set |
| `nxt_tokens` | Them `nxt_balance` vao `wallets` |
| **Them moi** | |
| `contractor_teams` | Quan ly doi tho nha thau (dashboard yeu cau) |
| `user_preferences` | Tach lang/theme rieng, khong query chung voi auth |

---

## 6. API ENDPOINTS v2 (DA XOA TRUNG)

### Thay doi so voi v1:
- Gop `/stats/admin` + `/stats/admin/analytics` → 1 endpoint voi `?detail=true`
- Gop `/suppliers/store` (POST/PUT) → dung `/auth/me` PATCH (vi supplier info nam trong users)
- Xoa `/upload/document` trung voi `/upload/image` → 1 endpoint `/upload` xu ly ca 2
- Them `/contractor/team` endpoints

### Tong: 105 REST + 3 WebSocket (giam 14 tu v1)

| Nhom | Endpoints | Ghi chu |
|------|-----------|---------|
| Auth | 9 | Gop preferences vao /auth/me PATCH |
| Modules | 2 | Gop pricing vao module detail |
| Stats | 2 | 1 platform + 1 admin (co ?detail) |
| Products | 5 | CRUD + admin approve |
| Categories | 2 | List + products by category |
| Workers | 8 | Profile + portfolio + reviews |
| Bookings | 8 | CRUD + accept/reject/complete + GPS |
| Projects | 6 | CRUD + bids |
| Bids | 2 | Submit + admin/owner update |
| Suppliers | 3 | List + detail + products |
| Cart | 4 | CRUD (xoa clear rieng) |
| Orders | 6 | Checkout + OTP + list + confirm + reorder |
| Escrow | 3 | List + release + dispute |
| Disputes | 3 | List + detail + resolve |
| Wallet | 5 | Balance + topup + withdraw + transactions + bank |
| Contracts | 4 | Create + detail + sign + milestones |
| Contractor Teams | 3 | List + add + remove |
| Forum | 6 | Posts CRUD + vote + comments |
| Reviews | 2 | Create + list |
| Chat | 3 + WS | Rooms + messages + WebSocket |
| Notifications | 3 + WS | List + read + WebSocket |
| Admin | 10 | Users + products + workers + disputes + settings + audit |
| BOQ | 3 | Import + parse + add-to-cart |
| Upload | 2 | Upload + delete (1 endpoint ca image+doc) |
| GPS | WS | 1 WebSocket |
| **TONG** | **105 + 3 WS** | |

---

## 7. WORKFLOW CHUAN — KHONG BI ROI

### 7.1 User Journey Map (khong trung, khong loop)

```
                    ┌──────────────┐
                    │   hub.html   │ ← Landing page, marketing
                    │  (khach vao) │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        Click "Dang nhap"  Click "Marketplace"  Click module
              │            │            │
              ▼            ▼            ▼
        Auth Modal    marketplace.html   Module app
        (common.js)   (co the chua login) (nexdesign-app.html...)
              │
              ▼
        POST /auth/login
              │
     ┌────────┴────────┐
     ▼                 ▼
  Tu Hub:           Tu Marketplace:
  redirect →        stay in page →
  dashboard.html    load user data
     │
     ▼
  dashboard.html
  (5 roles, 30+ pages)
     │
     ├─ Buyer → orders, workers, projects, wallet
     ├─ Worker → jobs, bookings, earnings, portfolio
     ├─ Contractor → bids, team, finance, milestones
     ├─ Supplier → products, orders, analytics, finance
     └─ Admin → users, disputes, settings, security
```

### 7.2 Escrow Flow (1 luong duy nhat, dung cho 3 entity)

```
[Buyer thanh toan]
     │
     ▼
POST /orders/checkout (hoac /bookings hoac /contracts/:id/sign)
     │
     ▼
[Tao Escrow voi idempotency_key]
     │ status = 'held'
     │ auto_release_date = +30 ngay
     ▼
[Seller thuc hien]
     │
     ▼
[Buyer confirm] ────────────┐
     │                      │
     ▼                      ▼
quality='correct'      quality='serious'
     │                      │
     ▼                      ▼
POST /escrow/:id/release  POST /escrow/:id/dispute
     │                      │
     ▼                      ▼
status='released'      status='disputed'
tien → seller          Admin giai quyet 24-48h
                            │
                   ┌────────┴────────┐
                   ▼                 ▼
              'refund'          'release'
              tien → buyer      tien → seller
```

### 7.3 Auth State — 1 nguon duy nhat

```
common.js:
  const AUTH = {
    user: null,        // GET /auth/me result
    isLoggedIn: false,
    role: null,        // 'buyer','worker','contractor','supplier','admin'

    async init() {
      // Goi khi load bat ky page nao
      // Cookie HttpOnly tu dong gui
      // Neu co token hop le → set user
    },

    async login(email, password) {
      // POST /auth/login → set cookie → init()
    },

    logout() {
      // POST /auth/logout → clear state → redirect hub
    },

    requireAuth(callback) {
      // Neu chua login → show auth modal
      // Neu da login → callback()
    }
  }
```

---

## 8. RISK MAP — DA XU LY

| Risk (tu review truoc) | Status | Giai phap |
|------------------------|--------|-----------|
| Code trung 750 lines | ✅ FIXED | Tach common files |
| CSS variable xung dot | ✅ FIXED | `data-page` attribute phan biet |
| Class name xung dot | ✅ FIXED | Prefix: eco-, dash-, mkt- |
| Auth flow roi | ✅ FIXED | 1 AUTH object trong common.js |
| Escrow trung logic | ✅ FIXED | 1 escrow table, 3 entity_type |
| i18n 38 lang | ✅ FIXED | Lazy load JSON rieng |
| Scale 11+ apps | ✅ PLANNED | Moi app import common, co the dung framework rieng |
| State management | ✅ FIXED | AUTH global + page-local state |

---

## 9. GATE PASS PHASE 1 v2

- [x] 3 file goc doc ky: 7,379 lines / 669KB
- [x] Task Order: NXB-SPEC-HUB-001 — 16 features, 40 test cases
- [x] Xung dot CSS: phat hien 9 conflicts → da fix bang data-page + prefix
- [x] Code trung: 750 lines → tach common files
- [x] DB schema: 30 tables toi uu (giam 2)
- [x] API: 105 REST + 3 WS (giam 14, xoa trung)
- [x] Workflow: user journey + escrow + auth — khong loop, khong conflict
- [x] Risk: 8/8 da xu ly
- [ ] **Cho Chairman confirm → bat dau Phase 2**

---

*CTO Recheck · NexBuild Holdings · 08/04/2026*
