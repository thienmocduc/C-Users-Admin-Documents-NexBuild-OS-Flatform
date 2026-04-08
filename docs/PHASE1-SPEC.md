# PHASE 1 — SPEC REVIEW + API INTERFACE
# NexBuild Holdings Platform — NXB-SPEC-HUB-001
# Ngay: 08/04/2026 | CTO Sign-off

---

## 1. TONG QUAN HE THONG

### 3 File HTML Goc (nguon su that duy nhat)
| File | Lines | Size | Chuc nang |
|------|-------|------|-----------|
| nexbuild-hub.html | 2,759 | 261KB | Trang chu he sinh thai - 16 tinh nang - 12 modules |
| nexbuild-dashboard.html | 2,018 | 184KB | Dashboard 5 roles - 30+ pages - 3 modals |
| nexbuild-marketplace.html | 2,602 | 224KB | Marketplace B2B/B2C/D2C - 7 tabs - 14+ modals |

### Tech Stack (KHONG thay the)
- **Frontend:** HTML5 + CSS3 + Vanilla JS (single-file, KHONG React/Vue)
- **Font:** Noto Sans + Noto Sans Mono (Google Fonts)
- **Backend:** Python FastAPI 0.104+ (async/await)
- **Database:** PostgreSQL 15+ (pgBouncer pool)
- **Cache:** Redis 7+ (TTL strategy)
- **Auth:** JWT RS256 (access 15min, refresh 7d HttpOnly)
- **Queue:** Celery 5.3+ (AI tasks)
- **Infra:** Docker + K8s (3 replicas min)

### Design System (KHONG doi)
```
Dark:  bg=#04080F  text=#EDF2FF  text2=#8898B8  text3=#3A4F6A
Light: bg=#F8F9FF  text=#0A1020  text2=#2A3A55  text3=#6A7A95
Colors: c1=#00C9A7  c2=#0EA5E9  indigo=#6366F1  violet=#A855F7  gold=#C9A84C
Gradient: linear-gradient(135deg,#00C9A7,#0EA5E9,#6366F1,#A855F7)
Orbs: 4 orb, blur 90px, drift 14s, opacity .35 dark / .18 light
Border-radius: 14px | Transition: .22s cubic-bezier(.4,0,.2,1)
```

---

## 2. DATABASE SCHEMA (PostgreSQL)

### 2.1 Core Tables

```sql
-- ========================================
-- USERS & AUTH
-- ========================================

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
    lang VARCHAR(5) DEFAULT 'VI',
    theme VARCHAR(10) DEFAULT 'dark',
    daily_quota INT DEFAULT 3,
    quota_reset TIMESTAMPTZ,
    email_verified BOOLEAN DEFAULT FALSE,
    phone_verified BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE login_attempts (
    id SERIAL PRIMARY KEY,
    ip_address INET NOT NULL,
    email VARCHAR(255),
    success BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- MODULES & ECOSYSTEM
-- ========================================

CREATE TABLE modules (
    id VARCHAR(20) PRIMARY KEY,  -- 'design','talent','supply',...
    name VARCHAR(100) NOT NULL,
    num VARCHAR(5),              -- '01','02',...,'KEY'
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
    module_id VARCHAR(20) REFERENCES modules(id),
    before_title VARCHAR(200),
    before_desc TEXT,
    after_title VARCHAR(200),
    after_desc TEXT,
    sort_order INT DEFAULT 0
);

CREATE TABLE module_results (
    id SERIAL PRIMARY KEY,
    module_id VARCHAR(20) REFERENCES modules(id),
    emoji VARCHAR(10),
    title VARCHAR(200),
    kpi VARCHAR(100),
    sort_order INT DEFAULT 0
);

-- ========================================
-- PRODUCTS & MARKETPLACE
-- ========================================

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
    price BIGINT NOT NULL,           -- dong (VND), no decimal
    promo_price BIGINT,
    unit VARCHAR(20) NOT NULL,       -- 'bao','kg','tan','m2','m3','cai','bo','cuon'
    stock INT DEFAULT 0,
    min_order INT DEFAULT 1,
    delivery_time VARCHAR(50),
    sku VARCHAR(50),
    images TEXT[],                    -- array of S3 URLs, max 8
    badges TEXT[],                    -- 'd2c','sale','new','hot','bulk','vip'
    sale_label VARCHAR(50),
    rating NUMERIC(2,1) DEFAULT 0,
    rating_count INT DEFAULT 0,
    is_d2c BOOLEAN DEFAULT FALSE,
    allow_b2b_credit BOOLEAN DEFAULT FALSE,
    show_in_boq BOOLEAN DEFAULT TRUE,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending','published','rejected','archived')),
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- WORKERS & TALENT
-- ========================================

CREATE TABLE worker_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id),
    trade VARCHAR(50) NOT NULL,      -- 'tho_ho','tho_dien','tho_nuoc','tho_moc','tho_son','op_lat','chong_tham','kts','ks'
    experience_years INT,
    daily_rate BIGINT,               -- VND
    work_area VARCHAR(200),
    travel_radius_km INT DEFAULT 10,
    bio TEXT,
    skills TEXT[],
    certificates TEXT[],             -- S3 URLs
    portfolio_count INT DEFAULT 0,
    rating NUMERIC(2,1) DEFAULT 0,
    rating_count INT DEFAULT 0,
    is_online BOOLEAN DEFAULT FALSE,
    accept_escrow BOOLEAN DEFAULT TRUE,
    allow_gps BOOLEAN DEFAULT FALSE,
    accept_insurance BOOLEAN DEFAULT TRUE,
    ai_score INT,                    -- 0-100, admin review
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending','verified','basic_verified','rejected','suspended')),
    verified_by UUID REFERENCES users(id),
    verified_at TIMESTAMPTZ,
    location_lat NUMERIC(10,7),
    location_lng NUMERIC(10,7),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE worker_portfolio (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    worker_id UUID NOT NULL REFERENCES worker_profiles(id),
    title VARCHAR(255),
    description TEXT,
    images TEXT[],
    rating NUMERIC(2,1),
    tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- BOOKINGS (Worker)
-- ========================================

CREATE TABLE bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    buyer_id UUID NOT NULL REFERENCES users(id),
    worker_id UUID NOT NULL REFERENCES worker_profiles(id),
    job_description TEXT NOT NULL,
    work_address VARCHAR(500),
    num_days INT NOT NULL,
    start_date DATE NOT NULL,
    shift VARCHAR(20) CHECK (shift IN ('morning','afternoon','evening')),
    worker_fee BIGINT NOT NULL,      -- daily_rate * num_days
    service_fee BIGINT NOT NULL,     -- 8% of worker_fee
    insurance_fee BIGINT DEFAULT 0,
    total BIGINT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending','accepted','rejected','in_progress','completed','cancelled','disputed')),
    escrow_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- PROJECTS & BIDDING
-- ========================================

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    type VARCHAR(50),                -- 'nha_o','biet_thu','van_phong','shophouse','chung_cu','cong_nghiep','fnb'
    budget_min BIGINT,
    budget_max BIGINT,
    duration_days INT,
    address VARCHAR(500),
    floor_area_m2 NUMERIC(10,2),
    requirements TEXT,
    work_categories TEXT[],          -- 'xay_tho','hoan_thien','dien_nuoc','son','noi_that','op_lat','chong_tham','mai'
    bid_deadline DATE,
    payment_method VARCHAR(30),      -- 'escrow','milestone','post_completion'
    blueprints TEXT[],               -- S3 URLs
    status VARCHAR(20) DEFAULT 'open' CHECK (status IN ('open','bidding','in_progress','completed','cancelled')),
    view_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE bids (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id),
    contractor_id UUID NOT NULL REFERENCES users(id),
    bid_price BIGINT NOT NULL,
    price_unit VARCHAR(10) DEFAULT 'dong', -- 'dong','trieu'
    duration_value INT,
    duration_unit VARCHAR(10),        -- 'ngay','tuan','thang'
    capability TEXT,
    construction_plan TEXT,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending','reviewing','shortlisted','accepted','rejected','lost')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE project_milestones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id),
    contractor_id UUID REFERENCES users(id),
    name VARCHAR(255),
    percentage INT,                   -- % of contract
    amount BIGINT,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending','in_progress','completed','paid')),
    escrow_id UUID,
    due_date DATE,
    completed_at TIMESTAMPTZ
);

-- ========================================
-- SUPPLIERS & D2C STORES
-- ========================================

CREATE TABLE supplier_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id),
    store_name VARCHAR(255),
    supplier_type VARCHAR(50),       -- 'manufacturer_d2c','exclusive_distributor','official_agent','b2b_retailer'
    main_category VARCHAR(100),
    delivery_area VARCHAR(200),
    intro TEXT,
    delivery_time VARCHAR(50),
    b2b_credit_policy VARCHAR(20),   -- 'none','30','60','90'
    verification_docs TEXT[],        -- S3 URLs
    pricing_tier VARCHAR(20) DEFAULT 'free', -- 'free','growth','enterprise'
    product_count INT DEFAULT 0,
    rating NUMERIC(2,1) DEFAULT 0,
    rating_count INT DEFAULT 0,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- CART & ORDERS
-- ========================================

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
    order_number VARCHAR(30) UNIQUE NOT NULL,  -- 'NXM-2026-XXXX'
    buyer_id UUID NOT NULL REFERENCES users(id),
    supplier_id UUID REFERENCES users(id),
    shipping_address VARCHAR(500),
    receiver_name VARCHAR(255),
    receiver_phone VARCHAR(20),
    notes TEXT,
    payment_method VARCHAR(30),      -- 'card','vnpay','bank_transfer','b2b_credit'
    subtotal BIGINT NOT NULL,
    vat BIGINT NOT NULL,             -- 10%
    total BIGINT NOT NULL,
    status VARCHAR(20) DEFAULT 'processing' CHECK (status IN ('processing','shipping','received','cancelled','disputed','refunded')),
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

-- ========================================
-- ESCROW
-- ========================================

CREATE TABLE escrow (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idempotency_key VARCHAR(100) UNIQUE NOT NULL,
    buyer_id UUID NOT NULL REFERENCES users(id),
    seller_id UUID REFERENCES users(id),       -- supplier or worker
    entity_type VARCHAR(20) NOT NULL,           -- 'order','booking','milestone'
    entity_id UUID NOT NULL,
    amount BIGINT NOT NULL,
    service_fee BIGINT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'held' CHECK (status IN ('held','released','refunded','disputed','cancelled')),
    released_at TIMESTAMPTZ,
    auto_release_date DATE,                     -- 30 days after delivery
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- DISPUTES
-- ========================================

CREATE TABLE disputes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    escrow_id UUID NOT NULL REFERENCES escrow(id),
    reporter_id UUID NOT NULL REFERENCES users(id),
    reason VARCHAR(50) NOT NULL,                -- 'wrong_description','damaged','not_received','wrong_quantity','low_quality'
    description TEXT,
    evidence TEXT[],                             -- S3 URLs, max 5
    status VARCHAR(20) DEFAULT 'open' CHECK (status IN ('open','investigating','resolved_refund','resolved_release','closed')),
    resolution TEXT,
    resolved_by UUID REFERENCES users(id),
    deadline TIMESTAMPTZ,                       -- 24-48h
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

-- ========================================
-- REVIEWS & RATINGS
-- ========================================

CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reviewer_id UUID NOT NULL REFERENCES users(id),
    target_type VARCHAR(20) NOT NULL,           -- 'supplier','worker','product','order'
    target_id UUID NOT NULL,
    stars INT NOT NULL CHECK (stars BETWEEN 1 AND 5),
    criteria JSONB,                              -- {"correct_description":true,"on_time":true,...}
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- CONTRACTS (Digital)
-- ========================================

CREATE TABLE contracts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_number VARCHAR(30) UNIQUE NOT NULL, -- 'CTR-2026-XXXX'
    project_id UUID NOT NULL REFERENCES projects(id),
    investor_id UUID NOT NULL REFERENCES users(id),
    contractor_id UUID NOT NULL REFERENCES users(id),
    contract_value BIGINT NOT NULL,
    duration_days INT,
    warranty_months INT DEFAULT 12,
    late_penalty_pct NUMERIC(4,2) DEFAULT 0.1,  -- %/day
    milestone_count INT,
    signed_by_investor BOOLEAN DEFAULT FALSE,
    signed_by_contractor BOOLEAN DEFAULT FALSE,
    signed_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft','pending_signature','active','completed','terminated')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- WALLET & TRANSACTIONS
-- ========================================

CREATE TABLE wallets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id),
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
    type VARCHAR(30) NOT NULL,      -- 'escrow_activate','escrow_release','withdraw','topup','commission','booking_fee','refund'
    amount BIGINT NOT NULL,
    balance_after BIGINT,
    reference_type VARCHAR(20),     -- 'order','booking','milestone','dispute'
    reference_id UUID,
    description TEXT,
    status VARCHAR(20) DEFAULT 'completed' CHECK (status IN ('pending','completed','failed','cancelled')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE bank_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    bank_name VARCHAR(100),
    account_number VARCHAR(30),
    account_holder VARCHAR(255),
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- FORUM & NXT TOKEN
-- ========================================

CREATE TABLE forum_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    tags TEXT[],
    votes INT DEFAULT 0,
    comment_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE forum_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES forum_posts(id) ON DELETE CASCADE,
    author_id UUID NOT NULL REFERENCES users(id),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE forum_votes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES forum_posts(id),
    user_id UUID NOT NULL REFERENCES users(id),
    value INT CHECK (value IN (-1, 1)),
    UNIQUE(post_id, user_id)
);

CREATE TABLE nxt_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    balance INT DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- NOTIFICATIONS
-- ========================================

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

-- ========================================
-- CHAT
-- ========================================

CREATE TABLE chat_rooms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(20) DEFAULT 'direct', -- 'direct','dispute_3party'
    entity_type VARCHAR(20),           -- 'order','booking','dispute'
    entity_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE chat_participants (
    room_id UUID REFERENCES chat_rooms(id),
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

-- ========================================
-- ADMIN: AUDIT LOG & SETTINGS
-- ========================================

CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    event_type VARCHAR(50) NOT NULL,
    ip_address INET,
    details JSONB,
    severity VARCHAR(10) DEFAULT 'info', -- 'info','success','warn','action'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE system_settings (
    key VARCHAR(100) PRIMARY KEY,
    value VARCHAR(255) NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by UUID REFERENCES users(id)
);

-- Default settings
INSERT INTO system_settings (key, value, description) VALUES
('commission_ncc_d2c', '2.5', 'Commission NCC D2C (%)'),
('commission_booking_tho', '8', 'Commission Booking tho (%)'),
('phi_escrow', '0.5', 'Phi Escrow (%)'),
('phi_rut_tien_nhanh', '2', 'Phi rut tien nhanh (%)'),
('nexerp_monthly', '500000', 'NexERP co ban/thang (VND)'),
('rate_limit_api', '100', 'Rate limit API (req/min)'),
('max_file_upload_mb', '10', 'Max file upload (MB)'),
('session_timeout_min', '60', 'Session timeout (phut)'),
('escrow_auto_release_days', '30', 'Escrow auto-release (ngay)'),
('max_orders_per_day', '50', 'Max don hang/ngay/user');

-- ========================================
-- BOQ (Bill of Quantities)
-- ========================================

CREATE TABLE boq_imports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    file_url TEXT,
    manual_text TEXT,
    status VARCHAR(20) DEFAULT 'processing',
    result JSONB,                     -- parsed items
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- INDEXES
-- ========================================

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_products_supplier ON products(supplier_id);
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_status ON products(status);
CREATE INDEX idx_worker_profiles_trade ON worker_profiles(trade);
CREATE INDEX idx_worker_profiles_status ON worker_profiles(status);
CREATE INDEX idx_bookings_buyer ON bookings(buyer_id);
CREATE INDEX idx_bookings_worker ON bookings(worker_id);
CREATE INDEX idx_bookings_status ON bookings(status);
CREATE INDEX idx_projects_owner ON projects(owner_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_bids_project ON bids(project_id);
CREATE INDEX idx_bids_contractor ON bids(contractor_id);
CREATE INDEX idx_orders_buyer ON orders(buyer_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_escrow_buyer ON escrow(buyer_id);
CREATE INDEX idx_escrow_status ON escrow(status);
CREATE INDEX idx_escrow_entity ON escrow(entity_type, entity_id);
CREATE INDEX idx_transactions_user ON transactions(user_id);
CREATE INDEX idx_transactions_type ON transactions(type);
CREATE INDEX idx_notifications_user ON notifications(user_id, is_read);
CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_event ON audit_log(event_type);
CREATE INDEX idx_forum_posts_author ON forum_posts(author_id);
CREATE INDEX idx_cart_items_user ON cart_items(user_id);
CREATE INDEX idx_login_attempts_ip ON login_attempts(ip_address, created_at);
```

**Tong: 32 tables | Quan he: FK cascading | Indexes: 28**

---

## 3. API ENDPOINTS

### Base URL: `/api/v1`

### 3.1 Auth (`/auth`)

| Method | Endpoint | Mo ta | Request | Response |
|--------|----------|-------|---------|----------|
| POST | `/auth/register` | Dang ky | `{full_name, email, phone, password, role}` | `{user_id, message}` |
| POST | `/auth/login` | Dang nhap | `{email_or_phone, password}` | `{access_token, user}` + Set-Cookie refresh |
| POST | `/auth/refresh` | Refresh token | Cookie refresh_token | `{access_token}` |
| POST | `/auth/logout` | Dang xuat | Cookie refresh_token | `{ok}` |
| POST | `/auth/forgot-password` | Quen MK | `{email}` | `{message}` |
| POST | `/auth/reset-password` | Dat lai MK | `{token, new_password}` | `{ok}` |
| POST | `/auth/verify-email` | Xac minh email | `{token}` | `{ok}` |
| POST | `/auth/verify-otp` | Xac minh OTP | `{phone, otp}` | `{ok}` |
| GET | `/auth/me` | User hien tai | Bearer token | `{user}` |
| PATCH | `/auth/preferences` | Cap nhat lang/theme | `{lang?, theme?}` | `{ok}` |

### 3.2 Modules & Hub (`/modules`)

| Method | Endpoint | Mo ta | Response |
|--------|----------|-------|----------|
| GET | `/modules` | Tat ca modules (12) | `[{id, name, num, tag, model, hook, desc, icon, color, pricing, ...}]` |
| GET | `/modules/:id` | Chi tiet 1 module | `{module, pains[], results[]}` |
| GET | `/modules/:id/pricing` | Gia module | `{tiers[]}` |

### 3.3 Platform Stats (`/stats`)

| Method | Endpoint | Mo ta | Response |
|--------|----------|-------|----------|
| GET | `/stats/platform` | Stats trang chu | `{workers, suppliers, projects, designs, transactions}` |
| GET | `/stats/admin` | Stats admin overview | `{total_users, gmv, escrow_held, revenue, user_breakdown}` |
| GET | `/stats/admin/analytics` | Analytics chi tiet | `{gmv, revenue, dau, nps, breakdown, top_cities}` |

### 3.4 Products (`/products`)

| Method | Endpoint | Mo ta | Request/Params |
|--------|----------|-------|----------------|
| GET | `/products` | Danh sach SP | `?category=&search=&sort=&location=&page=&limit=` |
| GET | `/products/:id` | Chi tiet SP | — |
| POST | `/products` | Tao SP (supplier) | `{name, category_id, price, unit, stock, ...}` |
| PUT | `/products/:id` | Sua SP | `{...fields}` |
| DELETE | `/products/:id` | Xoa SP | — |
| PATCH | `/products/:id/status` | Admin duyet/reject | `{status, reason?}` |

### 3.5 Categories (`/categories`)

| Method | Endpoint | Mo ta |
|--------|----------|-------|
| GET | `/categories` | Tat ca danh muc |
| GET | `/categories/:slug/products` | SP theo danh muc |

### 3.6 Workers (`/workers`)

| Method | Endpoint | Mo ta | Params |
|--------|----------|-------|--------|
| GET | `/workers` | Danh sach tho | `?trade=&sort=&distance=&price_range=&page=` |
| GET | `/workers/:id` | Profile tho | — |
| POST | `/workers/profile` | Tao ho so tho | `{trade, experience, daily_rate, skills[], ...}` |
| PUT | `/workers/profile` | Sua ho so | `{...fields}` |
| PATCH | `/workers/:id/status` | Admin duyet | `{status}` |
| PATCH | `/workers/:id/online` | Cap nhat online | `{is_online}` |
| GET | `/workers/:id/portfolio` | Portfolio | — |
| POST | `/workers/:id/portfolio` | Them portfolio | `{title, description, images[]}` |
| GET | `/workers/:id/reviews` | Danh gia | — |

### 3.7 Bookings (`/bookings`)

| Method | Endpoint | Mo ta | Request |
|--------|----------|-------|---------|
| POST | `/bookings` | Dat tho | `{worker_id, job_description, work_address, num_days, start_date, shift}` |
| GET | `/bookings` | Danh sach booking | `?status=&role=` |
| GET | `/bookings/:id` | Chi tiet | — |
| PATCH | `/bookings/:id/accept` | Tho chap nhan | — |
| PATCH | `/bookings/:id/reject` | Tho tu choi | `{reason?}` |
| PATCH | `/bookings/:id/complete` | Xac nhan hoan thanh | — |
| PATCH | `/bookings/:id/checkin` | Check-in GPS | `{lat, lng}` |
| PATCH | `/bookings/:id/checkout` | Check-out | — |

### 3.8 Projects (`/projects`)

| Method | Endpoint | Mo ta |
|--------|----------|-------|
| GET | `/projects` | Danh sach cong trinh | `?type=&location=&budget=&page=` |
| GET | `/projects/:id` | Chi tiet | |
| POST | `/projects` | Dang cong trinh | |
| PUT | `/projects/:id` | Sua | |
| POST | `/projects/:id/bids` | Gui thau | `{bid_price, duration, capability, plan}` |
| GET | `/projects/:id/bids` | Xem cac bid | |
| PATCH | `/projects/:id/bids/:bid_id` | Duyet bid | `{status}` |

### 3.9 Suppliers (`/suppliers`)

| Method | Endpoint | Mo ta |
|--------|----------|-------|
| GET | `/suppliers` | Danh sach NCC | `?category=&type=&page=` |
| GET | `/suppliers/:id` | Chi tiet gian hang | |
| POST | `/suppliers/store` | Dang ky gian hang | `{store_name, type, category, ...}` |
| PUT | `/suppliers/store` | Sua thong tin | |
| GET | `/suppliers/:id/products` | SP cua NCC | |

### 3.10 Cart (`/cart`)

| Method | Endpoint | Mo ta |
|--------|----------|-------|
| GET | `/cart` | Gio hang hien tai | |
| POST | `/cart/items` | Them SP | `{product_id, quantity}` |
| PUT | `/cart/items/:id` | Sua SL | `{quantity}` |
| DELETE | `/cart/items/:id` | Xoa SP | |
| DELETE | `/cart` | Xoa toan bo | |

### 3.11 Orders (`/orders`)

| Method | Endpoint | Mo ta |
|--------|----------|-------|
| POST | `/orders/checkout` | Dat hang + Escrow | `{shipping_address, receiver, phone, notes, payment_method}` |
| POST | `/orders/verify-otp` | Xac minh OTP | `{order_id, otp}` |
| GET | `/orders` | Danh sach don | `?status=&page=` |
| GET | `/orders/:id` | Chi tiet don | |
| PATCH | `/orders/:id/confirm` | Xac nhan nhan | `{quality: 'correct'/'minor'/'serious'}` |
| POST | `/orders/:id/reorder` | Mua lai | |
| GET | `/orders/:id/invoice` | Tai hoa don | |

### 3.12 Escrow (`/escrow`)

| Method | Endpoint | Mo ta |
|--------|----------|-------|
| GET | `/escrow` | Danh sach escrow cua user | |
| GET | `/escrow/:id` | Chi tiet | |
| POST | `/escrow/:id/release` | Giai phong tien | |
| POST | `/escrow/:id/dispute` | Mo khieu nai | `{reason, description, evidence[]}` |

### 3.13 Disputes (`/disputes`)

| Method | Endpoint | Mo ta |
|--------|----------|-------|
| GET | `/disputes` | Danh sach (admin) | |
| GET | `/disputes/:id` | Chi tiet | |
| PATCH | `/disputes/:id/resolve` | Giai quyet (admin) | `{resolution: 'refund'/'release'/'partial', amount?, notes}` |

### 3.14 Wallet (`/wallet`)

| Method | Endpoint | Mo ta |
|--------|----------|-------|
| GET | `/wallet` | So du + thong ke | |
| POST | `/wallet/topup` | Nap tien | `{amount, payment_method}` |
| POST | `/wallet/withdraw` | Rut tien | `{amount, bank_account_id, note?}` |
| GET | `/wallet/transactions` | Lich su GD | `?type=&page=` |
| GET | `/wallet/bank-accounts` | DS tai khoan NH | |
| POST | `/wallet/bank-accounts` | Them TK NH | `{bank_name, account_number, holder}` |

### 3.15 Contracts (`/contracts`)

| Method | Endpoint | Mo ta |
|--------|----------|-------|
| POST | `/contracts` | Tao hop dong | `{project_id, contractor_id, value, milestones[]}` |
| GET | `/contracts/:id` | Chi tiet | |
| POST | `/contracts/:id/sign` | Ky so (OTP) | `{otp}` |
| GET | `/contracts/:id/milestones` | Tien do | |
| PATCH | `/contracts/:id/milestones/:mid` | Cap nhat milestone | `{status}` |

### 3.16 Forum (`/forum`)

| Method | Endpoint | Mo ta |
|--------|----------|-------|
| GET | `/forum/posts` | Danh sach bai viet | `?sort=hot/new&tags=&page=` |
| GET | `/forum/posts/:id` | Chi tiet | |
| POST | `/forum/posts` | Viet bai | `{title, content, tags[]}` |
| POST | `/forum/posts/:id/vote` | Vote | `{value: 1/-1}` |
| GET | `/forum/posts/:id/comments` | Comments | |
| POST | `/forum/posts/:id/comments` | Binh luan | `{content}` |
| GET | `/forum/top-contributors` | Top nguoi dong gop | |

### 3.17 Reviews (`/reviews`)

| Method | Endpoint | Mo ta |
|--------|----------|-------|
| POST | `/reviews` | Danh gia | `{target_type, target_id, stars, criteria, comment}` |
| GET | `/reviews` | DS danh gia | `?target_type=&target_id=` |

### 3.18 Chat (`/chat`)

| Method | Endpoint | Mo ta |
|--------|----------|-------|
| GET | `/chat/rooms` | DS phong chat | |
| POST | `/chat/rooms` | Tao phong | `{participant_ids[], entity_type?, entity_id?}` |
| GET | `/chat/rooms/:id/messages` | Tin nhan | `?before=&limit=` |
| WS | `/ws/chat/:room_id` | Realtime chat | |

### 3.19 Notifications (`/notifications`)

| Method | Endpoint | Mo ta |
|--------|----------|-------|
| GET | `/notifications` | DS thong bao | `?page=` |
| PATCH | `/notifications/:id/read` | Danh dau da doc | |
| PATCH | `/notifications/read-all` | Doc het | |
| GET | `/notifications/unread-count` | So chua doc | |

### 3.20 Admin (`/admin`)

| Method | Endpoint | Mo ta |
|--------|----------|-------|
| GET | `/admin/users` | DS users | `?role=&status=&search=&page=` |
| PATCH | `/admin/users/:id` | Cap nhat user | `{status}` |
| GET | `/admin/products/pending` | SP cho duyet | |
| PATCH | `/admin/products/:id` | Duyet SP | `{status}` |
| GET | `/admin/workers/pending` | Tho cho duyet | |
| PATCH | `/admin/workers/:id` | Duyet tho | `{status}` |
| GET | `/admin/disputes` | DS khieu nai | |
| GET | `/admin/transactions` | Tat ca GD | `?type=&page=` |
| GET | `/admin/settings` | Cau hinh | |
| PUT | `/admin/settings/:key` | Sua cau hinh | `{value}` |
| GET | `/admin/audit-log` | Nhat ky | `?event=&severity=&page=` |
| GET | `/admin/security` | Security dashboard | |

### 3.21 BOQ (`/boq`)

| Method | Endpoint | Mo ta |
|--------|----------|-------|
| POST | `/boq/import` | Upload BOQ file | multipart: file (xlsx/csv/pdf) |
| POST | `/boq/parse-text` | Nhap thu cong | `{text}` |
| GET | `/boq/:id/result` | Ket qua phan tich | |
| POST | `/boq/:id/add-to-cart` | Them tat ca vao gio | |

### 3.22 Upload (`/upload`)

| Method | Endpoint | Mo ta |
|--------|----------|-------|
| POST | `/upload/image` | Upload anh | multipart, max 5MB, whitelist type |
| POST | `/upload/document` | Upload tai lieu | multipart, max 10MB |
| DELETE | `/upload/:key` | Xoa file | |

---

## 4. WEBSOCKET ENDPOINTS

| WS | Path | Muc dich |
|----|------|----------|
| 1 | `/ws/chat/:room_id` | Realtime chat |
| 2 | `/ws/notifications/:user_id` | Push thong bao |
| 3 | `/ws/gps/:booking_id` | Theo doi GPS tho |

---

## 5. SECURITY REQUIREMENTS (Tu Task Order)

### Auth & Session
- JWT RS256: access 15min, refresh 7d HttpOnly Secure cookie
- Refresh token rotation (moi lan refresh → token cu bi revoke)
- Rate limit login: 5 lan/15min/IP → lockout 30 min
- 2FA OTP cho checkout + escrow release + contract signing
- CSRF token moi form
- KHONG luu token trong localStorage

### Headers
- HTTPS + HSTS max-age 1 nam
- CSP: script-src 'self'
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- Referrer-Policy: strict-origin

### Rate Limiting
- Login: 5 req/15min/IP
- API: 100 req/min/IP
- User: 1000 req/hour
- Orders: 50/ngay/user

### File Upload
- Whitelist: jpg, jpeg, png, gif, webp, pdf, xlsx, xls, csv, dwg
- Max 10MB
- Virus scan truoc khi luu S3
- S3 private, signed URLs 1h

### Data Protection
- bcrypt cost >= 12
- AES-256 cho sensitive data
- TLS 1.3
- KHONG log PII/passwords/tokens

---

## 6. TONG KET API

| Nhom | So endpoints |
|------|-------------|
| Auth | 10 |
| Modules | 3 |
| Stats | 3 |
| Products | 6 |
| Categories | 2 |
| Workers | 9 |
| Bookings | 8 |
| Projects | 7 |
| Suppliers | 5 |
| Cart | 5 |
| Orders | 7 |
| Escrow | 4 |
| Disputes | 3 |
| Wallet | 6 |
| Contracts | 5 |
| Forum | 7 |
| Reviews | 2 |
| Chat | 4 + 1 WS |
| Notifications | 4 + 1 WS |
| Admin | 12 |
| BOQ | 4 |
| Upload | 3 |
| GPS | 1 WS |
| **TONG** | **~119 REST + 3 WS** |

---

## 7. KNOWN ISSUES TU FILE GOC

1. **Dashboard HTML structure bug:** Admin pages (9 pages) nam SAU the `</html>` → khong render. Can fix khi code Phase 3.
2. **Hub language array:** "VI" xuat hien 2 lan (index 0 va 36). Can de-dup.
3. **Hub auth modal:** Login form khong validate password (chi check email). Backend phai enforce.
4. **Marketplace pagination:** UI only, chua co logic. Backend phai implement cursor-based pagination.
5. **Marketplace search:** Chi search products, chua search workers/suppliers. Can mo rong.

---

## 8. GATE PASS PHASE 1

- [x] File goc doc xong: 3/3 files (7,379 lines / 669KB)
- [x] Task Order doc xong: NXB-SPEC-HUB-001
- [x] Design system xac nhan: colors/fonts/orbs/spacing
- [x] DB schema: 32 tables + 28 indexes
- [x] API interface chot: 119 REST endpoints + 3 WebSocket
- [x] Security requirements documented
- [x] Known issues documented
- [ ] **Cho Chairman confirm truoc khi bat dau Phase 2**

---

*CTO · NexBuild Holdings · 08/04/2026*
