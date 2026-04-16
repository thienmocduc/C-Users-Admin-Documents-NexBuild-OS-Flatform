/**
 * NexBuild Common JS — Shared across all pages
 * AUTH object, toast(), toggleTheme(), apiFetch(), i18n
 * Spec: PHASE1-SPEC-v2.md Section 7.3
 */

// ─── Config ─────────────────────────────────────────────
const API_BASE = window.NXB_API_BASE || '/api/v1';
const WS_BASE = window.NXB_WS_BASE || (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host;

// ─── AUTH ────────────────────────────────────────────────
const AUTH = {
  user: null,
  isLoggedIn: false,
  role: null,
  token: null,

  async init() {
    // Try to restore from localStorage
    const savedToken = localStorage.getItem('nxb_token');
    if (savedToken) {
      this.token = savedToken;
      try {
        const resp = await apiFetch('/auth/me');
        if (resp.ok !== false) {
          this.user = resp;
          this.role = resp.role;
          this.isLoggedIn = true;
          this._emit('auth:ready');
          return;
        }
      } catch (e) {
        localStorage.removeItem('nxb_token');
      }
    }
    this.user = null;
    this.isLoggedIn = false;
    this.role = null;
    this.token = null;
    this._emit('auth:ready');
  },

  async login(emailOrPhone, password) {
    const resp = await apiFetch('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email_or_phone: emailOrPhone, password }),
    });

    if (resp.access_token) {
      this.token = resp.access_token;
      this.user = resp.user;
      this.role = resp.user.role;
      this.isLoggedIn = true;
      localStorage.setItem('nxb_token', resp.access_token);
      this._emit('auth:login');
      return { ok: true, user: resp.user };
    }
    return { ok: false, error: resp.detail || 'Đăng nhập thất bại' };
  },

  async register(data) {
    const resp = await apiFetch('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return resp;
  },

  async logout() {
    try {
      await apiFetch('/auth/logout', { method: 'POST' });
    } catch (e) { /* ignore */ }
    this.user = null;
    this.isLoggedIn = false;
    this.role = null;
    this.token = null;
    localStorage.removeItem('nxb_token');
    this._emit('auth:logout');
  },

  requireAuth(callback) {
    if (this.isLoggedIn) {
      callback(this.user);
    } else {
      showAuthModal(() => {
        if (this.isLoggedIn) callback(this.user);
      });
    }
  },

  // Event system
  _listeners: {},
  on(event, fn) {
    if (!this._listeners[event]) this._listeners[event] = [];
    this._listeners[event].push(fn);
  },
  _emit(event) {
    (this._listeners[event] || []).forEach(fn => fn(this.user));
  },
};

// ─── API FETCH ──────────────────────────────────────────
async function apiFetch(path, options = {}) {
  const url = path.startsWith('http') ? path : API_BASE + path;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };
  if (AUTH.token) {
    headers['Authorization'] = `Bearer ${AUTH.token}`;
  }

  try {
    const resp = await fetch(url, {
      credentials: 'include',
      ...options,
      headers,
    });

    // Handle 401 — token expired, try refresh
    if (resp.status === 401 && AUTH.token) {
      const refreshResp = await fetch(API_BASE + '/auth/refresh', {
        method: 'POST',
        credentials: 'include',
      });
      if (refreshResp.ok) {
        const data = await refreshResp.json();
        AUTH.token = data.access_token;
        localStorage.setItem('nxb_token', data.access_token);
        headers['Authorization'] = `Bearer ${data.access_token}`;
        const retry = await fetch(url, { credentials: 'include', ...options, headers });
        return await retry.json();
      }
      // Refresh failed — logout
      AUTH.logout();
      return { ok: false, detail: 'Phiên đăng nhập hết hạn' };
    }

    const data = await resp.json();
    if (!resp.ok) {
      data.ok = false;
      data._status = resp.status;
    }
    return data;
  } catch (e) {
    return { ok: false, detail: 'Lỗi kết nối server' };
  }
}

// ─── TOAST ──────────────────────────────────────────────
function toast(message, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = message;
  container.appendChild(el);

  setTimeout(() => el.remove(), 3500);
}

// ─── THEME ──────────────────────────────────────────────
let _isDark = true;

function toggleTheme() {
  _isDark = !_isDark;
  const theme = _isDark ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('nxb_theme', theme);

  // Update toggle button text if exists
  const btn = document.getElementById('themeToggle');
  if (btn) btn.textContent = _isDark ? '🌙' : '☀️';
}

function initTheme() {
  const saved = localStorage.getItem('nxb_theme');
  if (saved) {
    _isDark = saved === 'dark';
    document.documentElement.setAttribute('data-theme', saved);
  }
  const btn = document.getElementById('themeToggle');
  if (btn) {
    btn.textContent = _isDark ? '🌙' : '☀️';
    btn.addEventListener('click', toggleTheme);
  }
}

// ─── i18n ───────────────────────────────────────────────
let _i18n = {};
let _currentLang = 'vi';

async function loadLang(code) {
  try {
    const resp = await fetch(`/lang/${code}.json`);
    if (resp.ok) {
      _i18n = await resp.json();
      _currentLang = code;
      applyTranslations();
      localStorage.setItem('nxb_lang', code);
    }
  } catch (e) {
    console.warn('i18n load failed:', code);
  }
}

function t(key) {
  return _i18n[key] || key;
}

function applyTranslations() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (_i18n[key]) el.textContent = _i18n[key];
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    if (_i18n[key]) el.placeholder = _i18n[key];
  });
}

// ─── AUTH MODAL ─────────────────────────────────────────
let _authCallback = null;

function showAuthModal(callback) {
  _authCallback = callback;
  const modal = document.getElementById('authModal');
  if (modal) {
    modal.style.display = 'flex';
    return;
  }

  // Create auth modal dynamically
  const m = document.createElement('div');
  m.id = 'authModal';
  m.style.cssText = 'position:fixed;inset:0;z-index:9999;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.7);backdrop-filter:blur(8px)';
  m.innerHTML = `
    <div style="background:var(--bg2);border:1px solid var(--bdr);border-radius:var(--r);padding:32px;width:90%;max-width:400px;position:relative">
      <button onclick="closeAuthModal()" style="position:absolute;top:12px;right:12px;background:none;border:none;color:var(--text2);font-size:20px;cursor:pointer">&times;</button>
      <h2 style="margin-bottom:20px;background:var(--grad);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:22px" data-i18n="login_title">Đăng nhập NexBuild</h2>
      <div id="authTabs" style="display:flex;gap:0;margin-bottom:20px">
        <button onclick="showAuthTab('login')" id="tabLogin" class="btn" style="flex:1;border-radius:var(--r) 0 0 var(--r);background:var(--c1);color:#fff">Đăng nhập</button>
        <button onclick="showAuthTab('register')" id="tabRegister" class="btn" style="flex:1;border-radius:0 var(--r) var(--r) 0;background:var(--bg3);color:var(--text2)">Đăng ký</button>
      </div>
      <form id="loginForm" onsubmit="handleLogin(event)" style="display:flex;flex-direction:column;gap:12px">
        <input type="text" id="loginEmail" placeholder="Email hoặc SĐT" required style="padding:12px;border-radius:8px;border:1px solid var(--bdr);background:var(--bg3);color:var(--text);font-size:14px">
        <input type="password" id="loginPassword" placeholder="Mật khẩu" required style="padding:12px;border-radius:8px;border:1px solid var(--bdr);background:var(--bg3);color:var(--text);font-size:14px">
        <button type="submit" class="btn btn-primary" style="width:100%;justify-content:center">Đăng nhập</button>
        <p id="loginError" style="color:var(--red);font-size:13px;display:none"></p>
      </form>
      <form id="registerForm" onsubmit="handleRegister(event)" style="display:none;flex-direction:column;gap:12px">
        <input type="text" id="regName" placeholder="Họ và tên" required style="padding:12px;border-radius:8px;border:1px solid var(--bdr);background:var(--bg3);color:var(--text);font-size:14px">
        <input type="email" id="regEmail" placeholder="Email" required style="padding:12px;border-radius:8px;border:1px solid var(--bdr);background:var(--bg3);color:var(--text);font-size:14px">
        <input type="tel" id="regPhone" placeholder="Số điện thoại (tùy chọn)" pattern="^0\\d{9}$" style="padding:12px;border-radius:8px;border:1px solid var(--bdr);background:var(--bg3);color:var(--text);font-size:14px">
        <input type="password" id="regPassword" placeholder="Mật khẩu (tối thiểu 8 ký tự)" required minlength="8" style="padding:12px;border-radius:8px;border:1px solid var(--bdr);background:var(--bg3);color:var(--text);font-size:14px">
        <select id="regRole" required style="padding:12px;border-radius:8px;border:1px solid var(--bdr);background:var(--bg3);color:var(--text);font-size:14px">
          <option value="">Chọn vai trò</option>
          <option value="buyer">Chủ nhà / CĐT</option>
          <option value="worker">Thợ kỹ thuật</option>
          <option value="contractor">Nhà thầu</option>
          <option value="supplier">Nhà cung cấp</option>
        </select>
        <button type="submit" class="btn btn-primary" style="width:100%;justify-content:center">Đăng ký</button>
        <p id="regError" style="color:var(--red);font-size:13px;display:none"></p>
      </form>
    </div>
  `;
  document.body.appendChild(m);
}

function closeAuthModal() {
  const modal = document.getElementById('authModal');
  if (modal) modal.style.display = 'none';
}

function showAuthTab(tab) {
  const loginForm = document.getElementById('loginForm');
  const registerForm = document.getElementById('registerForm');
  const tabLogin = document.getElementById('tabLogin');
  const tabRegister = document.getElementById('tabRegister');

  if (tab === 'login') {
    loginForm.style.display = 'flex';
    registerForm.style.display = 'none';
    tabLogin.style.background = 'var(--c1)'; tabLogin.style.color = '#fff';
    tabRegister.style.background = 'var(--bg3)'; tabRegister.style.color = 'var(--text2)';
  } else {
    loginForm.style.display = 'none';
    registerForm.style.display = 'flex';
    tabRegister.style.background = 'var(--c1)'; tabRegister.style.color = '#fff';
    tabLogin.style.background = 'var(--bg3)'; tabLogin.style.color = 'var(--text2)';
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const email = document.getElementById('loginEmail').value;
  const password = document.getElementById('loginPassword').value;
  const errEl = document.getElementById('loginError');

  const result = await AUTH.login(email, password);
  if (result.ok) {
    closeAuthModal();
    toast('Đăng nhập thành công!', 'success');
    if (_authCallback) _authCallback(AUTH.user);
  } else {
    errEl.textContent = result.error;
    errEl.style.display = 'block';
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const data = {
    full_name: document.getElementById('regName').value,
    email: document.getElementById('regEmail').value,
    phone: document.getElementById('regPhone').value || undefined,
    password: document.getElementById('regPassword').value,
    role: document.getElementById('regRole').value,
  };
  const errEl = document.getElementById('regError');

  if (!data.role) {
    errEl.textContent = 'Vui lòng chọn vai trò';
    errEl.style.display = 'block';
    return;
  }

  const result = await AUTH.register(data);
  if (result.ok !== false) {
    toast('Đăng ký thành công! Vui lòng đăng nhập.', 'success');
    showAuthTab('login');
  } else {
    errEl.textContent = result.detail || 'Đăng ký thất bại';
    errEl.style.display = 'block';
  }
}

// ─── WebSocket Helpers ──────────────────────────────────
function connectWS(path, onMessage, onOpen, onClose) {
  // SECURITY: Send token in first message, NOT in URL query string
  // URL query params appear in server logs, browser history, proxy logs
  const url = WS_BASE + path;
  const ws = new WebSocket(url);

  ws.onopen = () => {
    // Authenticate via first message
    ws.send(JSON.stringify({ type: 'auth', token: AUTH.token || '' }));
    if (onOpen) onOpen(ws);
  };
  ws.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      if (onMessage) onMessage(data, ws);
    } catch (err) {
      if (onMessage) onMessage(e.data, ws);
    }
  };
  ws.onclose = (e) => { if (onClose) onClose(e); };
  ws.onerror = (e) => { console.warn('WebSocket error:', path, e); };

  return ws;
}

// ─── Format Helpers ─────────────────────────────────────
function formatVND(amount) {
  if (amount == null) return '0đ';
  return new Intl.NumberFormat('vi-VN').format(amount) + 'đ';
}

function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function timeAgo(iso) {
  if (!iso) return '';
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Vừa xong';
  if (mins < 60) return `${mins} phút trước`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} giờ trước`;
  const days = Math.floor(hours / 24);
  return `${days} ngày trước`;
}

// ─── Init ───────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initTheme();

  // Load saved language
  const savedLang = localStorage.getItem('nxb_lang');
  if (savedLang && savedLang !== 'vi') loadLang(savedLang);

  // Initialize auth
  AUTH.init();
});
