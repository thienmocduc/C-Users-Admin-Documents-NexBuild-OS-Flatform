const nodemailer = require('nodemailer');
const crypto = require('crypto');

// In-memory token store (production: use Redis/DB)
const tokens = new Map();

const transporter = nodemailer.createTransport({
  service: 'gmail',
  auth: {
    user: process.env.SMTP_USER,
    pass: process.env.SMTP_PASS,
  },
});

module.exports = async (req, res) => {
  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  try {
    const { email, full_name } = req.body;
    if (!email || !full_name) {
      return res.status(400).json({ error: 'Email và tên là bắt buộc' });
    }

    // Generate verification token
    const token = crypto.randomBytes(32).toString('hex');
    const verifyUrl = `https://nexbuild.holdings/api/verify-email?token=${token}&email=${encodeURIComponent(email)}`;

    // Store token (expires 24h)
    tokens.set(token, { email, full_name, created: Date.now() });

    // Send email
    await transporter.sendMail({
      from: '"NexBuild Holdings" <doanhnhancaotuan@gmail.com>',
      to: email,
      subject: '🔐 Xác nhận tài khoản NexBuild Holdings',
      html: `
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#04080F;font-family:'Segoe UI',Arial,sans-serif">
<div style="max-width:560px;margin:0 auto;padding:40px 24px">

  <!-- Header -->
  <div style="text-align:center;margin-bottom:32px">
    <div style="display:inline-block;background:linear-gradient(135deg,rgba(0,201,167,.15),rgba(14,165,233,.1));border:1px solid rgba(0,201,167,.3);border-radius:14px;padding:12px 16px;margin-bottom:16px">
      <span style="font-size:28px;font-weight:900;background:linear-gradient(135deg,#00C9A7,#0EA5E9);-webkit-background-clip:text;-webkit-text-fill-color:transparent">NEXBUILD</span>
      <span style="font-size:10px;color:#8898B8;display:block;letter-spacing:2px;font-weight:700">HOLDINGS</span>
    </div>
    <h1 style="color:#EDF2FF;font-size:24px;font-weight:800;margin:0">Xin chào ${full_name}!</h1>
    <p style="color:#8898B8;font-size:14px;margin-top:8px">Cảm ơn bạn đã đăng ký tài khoản NexBuild Holdings</p>
  </div>

  <!-- Card -->
  <div style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:32px;text-align:center">
    <div style="font-size:48px;margin-bottom:16px">🔐</div>
    <h2 style="color:#EDF2FF;font-size:18px;font-weight:700;margin:0 0 12px">Xác nhận email của bạn</h2>
    <p style="color:#8898B8;font-size:13px;line-height:1.6;margin:0 0 24px">
      Nhấn nút bên dưới để kích hoạt tài khoản và bắt đầu sử dụng hệ sinh thái xây dựng thông minh NexBuild.
    </p>

    <!-- CTA Button -->
    <a href="${verifyUrl}" style="display:inline-block;padding:14px 40px;background:linear-gradient(135deg,#00C9A7,#0EA5E9,#6366F1);color:#fff;text-decoration:none;border-radius:12px;font-size:15px;font-weight:700;letter-spacing:.5px">
      Kích hoạt tài khoản →
    </a>

    <p style="color:#3A4F6A;font-size:11px;margin-top:20px">
      Link này có hiệu lực trong 24 giờ.
    </p>
  </div>

  <!-- Features -->
  <div style="margin-top:24px;display:flex;gap:8px;justify-content:center;flex-wrap:wrap">
    <span style="background:rgba(0,201,167,.08);border:1px solid rgba(0,201,167,.2);color:#00C9A7;padding:6px 12px;border-radius:8px;font-size:11px;font-weight:600">NexDesign AI</span>
    <span style="background:rgba(14,165,233,.08);border:1px solid rgba(14,165,233,.2);color:#0EA5E9;padding:6px 12px;border-radius:8px;font-size:11px;font-weight:600">NexMarket</span>
    <span style="background:rgba(99,102,241,.08);border:1px solid rgba(99,102,241,.2);color:#6366F1;padding:6px 12px;border-radius:8px;font-size:11px;font-weight:600">NexTalent</span>
    <span style="background:rgba(168,85,247,.08);border:1px solid rgba(168,85,247,.2);color:#A855F7;padding:6px 12px;border-radius:8px;font-size:11px;font-weight:600">11 Modules</span>
  </div>

  <!-- Footer -->
  <div style="text-align:center;margin-top:32px;padding-top:24px;border-top:1px solid rgba(255,255,255,.06)">
    <p style="color:#3A4F6A;font-size:11px;margin:0">
      NexBuild Holdings — Hệ sinh thái xây dựng thông minh<br>
      <a href="https://nexbuild.holdings" style="color:#00C9A7;text-decoration:none">nexbuild.holdings</a> ·
      Hotline: 0988 766 686
    </p>
    <p style="color:#3A4F6A;font-size:10px;margin-top:12px">
      Nếu bạn không đăng ký tài khoản này, vui lòng bỏ qua email này.
    </p>
  </div>

</div>
</body>
</html>
      `,
    });

    return res.status(200).json({
      ok: true,
      message: 'Email xác nhận đã được gửi tới ' + email,
    });
  } catch (error) {
    console.error('Email error:', error);
    return res.status(500).json({
      error: 'Không thể gửi email. Vui lòng thử lại.',
      detail: error.message,
    });
  }
};
