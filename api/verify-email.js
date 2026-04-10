module.exports = async (req, res) => {
  const { token, email } = req.query;

  // In production: validate token against DB/Redis
  // For now: redirect to success page
  if (!token || !email) {
    return res.status(400).send(`
      <html><head><meta charset="utf-8"><title>Lỗi</title></head>
      <body style="background:#04080F;color:#EDF2FF;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
        <div style="text-align:center">
          <div style="font-size:48px;margin-bottom:16px">❌</div>
          <h1>Link không hợp lệ</h1>
          <p style="color:#8898B8">Token xác nhận không tồn tại hoặc đã hết hạn.</p>
          <a href="https://nexbuild.holdings" style="color:#00C9A7">← Về trang chủ</a>
        </div>
      </body></html>
    `);
  }

  // Success page
  res.status(200).send(`
    <!DOCTYPE html>
    <html lang="vi">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width,initial-scale=1">
      <title>Tài khoản đã kích hoạt — NexBuild Holdings</title>
    </head>
    <body style="background:#04080F;color:#EDF2FF;font-family:'Segoe UI',Arial,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
      <div style="text-align:center;max-width:480px;padding:24px">
        <div style="font-size:64px;margin-bottom:16px">✅</div>
        <h1 style="font-size:28px;font-weight:800;margin:0">
          <span style="background:linear-gradient(135deg,#00C9A7,#0EA5E9);-webkit-background-clip:text;-webkit-text-fill-color:transparent">Tài khoản đã kích hoạt!</span>
        </h1>
        <p style="color:#8898B8;font-size:14px;margin-top:12px;line-height:1.6">
          Email <strong style="color:#EDF2FF">${decodeURIComponent(email)}</strong> đã được xác nhận thành công.<br>
          Bạn có thể đăng nhập và sử dụng toàn bộ hệ sinh thái NexBuild.
        </p>
        <div style="margin-top:24px;display:flex;gap:10px;justify-content:center;flex-wrap:wrap">
          <a href="https://nexbuild.holdings/nexdesign-app" style="display:inline-block;padding:12px 24px;background:linear-gradient(135deg,#00C9A7,#0EA5E9);color:#fff;text-decoration:none;border-radius:10px;font-size:13px;font-weight:700">🎨 Mở NexDesign AI</a>
          <a href="https://nexbuild.holdings/marketplace" style="display:inline-block;padding:12px 24px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);color:#EDF2FF;text-decoration:none;border-radius:10px;font-size:13px;font-weight:600">🏪 Mở Marketplace</a>
        </div>
        <p style="color:#3A4F6A;font-size:11px;margin-top:32px">
          NexBuild Holdings — Hệ sinh thái xây dựng thông minh<br>
          <a href="https://nexbuild.holdings" style="color:#00C9A7;text-decoration:none">nexbuild.holdings</a>
        </p>
      </div>
    </body>
    </html>
  `);
};
