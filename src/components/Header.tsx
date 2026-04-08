"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useTheme } from "@/components/ThemeProvider";

const NAV_LINKS = [
  { label: "He sinh thai", href: "#ecosystem" },
  { label: "Giai phap", href: "#solutions" },
  { label: "Bang gia", href: "#pricing" },
  { label: "Ve chung toi", href: "#about" },
];

const ECOSYSTEM_MODULES = [
  { tag: "KEY", name: "NexMarket", slug: "market", color: "#C9A84C" },
  { tag: "01", name: "NexDesign AI", slug: "design", color: "#00C9A7" },
  { tag: "02", name: "NexTalent", slug: "talent", color: "#0EA5E9" },
  { tag: "03", name: "NexSupply", slug: "supply", color: "#F59E0B" },
  { tag: "04", name: "NexERP", slug: "erp", color: "#6366F1" },
  { tag: "05", name: "NexMedia", slug: "media", color: "#A855F7" },
  { tag: "06", name: "NexFinance", slug: "finance", color: "#22C55E" },
  { tag: "07", name: "NexAffiliates", slug: "affiliates", color: "#FB923C" },
  { tag: "08", name: "NexAcademy", slug: "academy", color: "#6366F1" },
  { tag: "09", name: "NexAgent AI", slug: "agent", color: "#6366F1" },
  { tag: "10", name: "NexConnect", slug: "connect", color: "#0EA5E9" },
  { tag: "11", name: "NexAccounting", slug: "accounting", color: "#22C55E" },
];

export function Header() {
  const { theme, toggle } = useTheme();
  const [scrolled, setScrolled] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Lock body scroll when drawer is open
  useEffect(() => {
    document.body.style.overflow = drawerOpen ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [drawerOpen]);

  return (
    <>
      <header
        className={`fixed top-0 left-0 right-0 z-50 transition-shadow duration-300 ${
          scrolled ? "shadow-lg" : ""
        }`}
        style={{
          background: "var(--hdr-bg)",
          borderBottom: "1px solid var(--bdr)",
        }}
      >
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 shrink-0">
            <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
              <path d="M16 2L28 9V23L16 30L4 23V9L16 2Z" stroke="url(#logoGrad)" strokeWidth="2" strokeLinejoin="round"/>
              <circle cx="16" cy="16" r="4" fill="url(#logoGrad)" opacity="0.8"/>
              <defs>
                <linearGradient id="logoGrad" x1="4" y1="2" x2="28" y2="30">
                  <stop stopColor="#00C9A7"/>
                  <stop offset="1" stopColor="#0EA5E9"/>
                </linearGradient>
              </defs>
            </svg>
            <div className="flex flex-col leading-tight">
              <span
                className="bg-clip-text text-transparent"
                style={{
                  fontSize: "16px",
                  fontWeight: 900,
                  backgroundImage: "linear-gradient(135deg, #00C9A7, #0EA5E9)",
                }}
              >
                NexBuild
              </span>
              <span
                style={{
                  fontSize: "9px",
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "0.15em",
                  color: "var(--text3)",
                }}
              >
                Holdings
              </span>
            </div>
          </Link>

          {/* Center nav — hidden on mobile */}
          <nav className="hidden md:flex items-center gap-8">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="text-sm font-medium transition-colors hover:opacity-80"
                style={{ color: "var(--text2)" }}
              >
                {link.label}
              </Link>
            ))}
          </nav>

          {/* Right side */}
          <div className="flex items-center gap-3">
            {/* Theme toggle */}
            <button
              onClick={toggle}
              className="flex h-9 w-9 items-center justify-center rounded-lg transition-colors hover:opacity-80"
              style={{ background: "var(--bdr)" }}
              aria-label="Toggle theme"
            >
              {theme === "dark" ? "\u2600\uFE0F" : "\uD83C\uDF19"}
            </button>

            {/* Login */}
            <Link
              href="/login"
              className="hidden sm:inline-flex items-center px-4 py-2 text-sm font-medium rounded-lg transition-colors hover:opacity-80"
              style={{ color: "var(--text)", border: "1px solid var(--bdr)" }}
            >
              Login
            </Link>

            {/* CTA */}
            <Link
              href="/signup"
              className="hidden sm:inline-flex items-center px-4 py-2 text-sm font-semibold text-white rounded-lg transition-opacity hover:opacity-90"
              style={{
                backgroundImage: "linear-gradient(135deg, var(--c1), var(--c2, #6366f1))",
              }}
            >
              Dung thu
            </Link>

            {/* Hamburger — mobile only */}
            <button
              onClick={() => setDrawerOpen(true)}
              className="flex md:hidden h-9 w-9 items-center justify-center rounded-lg transition-colors hover:opacity-80"
              style={{ background: "var(--bdr)" }}
              aria-label="Open menu"
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 20 20"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                style={{ color: "var(--text)" }}
              >
                <line x1="3" y1="5" x2="17" y2="5" />
                <line x1="3" y1="10" x2="17" y2="10" />
                <line x1="3" y1="15" x2="17" y2="15" />
              </svg>
            </button>
          </div>
        </div>
      </header>

      {/* Spacer so content isn't hidden behind fixed header */}
      <div className="h-16" />

      {/* ── Ecosystem Drawer (mobile) ── */}
      {drawerOpen && (
        <div className="fixed inset-0 z-[60] md:hidden">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => setDrawerOpen(false)}
          />

          {/* Drawer panel */}
          <aside
            className="absolute top-0 right-0 h-full w-80 max-w-[85vw] overflow-y-auto animate-slide-in"
            style={{ background: "var(--hdr-bg)", borderLeft: "1px solid var(--bdr)" }}
          >
            {/* Drawer header */}
            <div
              className="flex items-center justify-between px-5 py-4"
              style={{ borderBottom: "1px solid var(--bdr)" }}
            >
              <span className="text-base font-semibold" style={{ color: "var(--text)" }}>
                He sinh thai
              </span>
              <button
                onClick={() => setDrawerOpen(false)}
                className="flex h-8 w-8 items-center justify-center rounded-lg hover:opacity-80"
                style={{ background: "var(--bdr)", color: "var(--text)" }}
                aria-label="Close menu"
              >
                ✕
              </button>
            </div>

            {/* Nav links (mobile) */}
            <div className="px-5 py-3" style={{ borderBottom: "1px solid var(--bdr)" }}>
              {NAV_LINKS.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setDrawerOpen(false)}
                  className="block py-2 text-sm font-medium transition-colors hover:opacity-80"
                  style={{ color: "var(--text2)" }}
                >
                  {link.label}
                </Link>
              ))}
            </div>

            {/* Ecosystem modules */}
            <div className="px-5 py-4 space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--text2)" }}>
                12 Modules
              </p>
              {ECOSYSTEM_MODULES.map((mod) => (
                <Link
                  key={mod.slug}
                  href={`/ecosystem/${mod.slug}`}
                  onClick={() => setDrawerOpen(false)}
                  className="flex items-center gap-3 rounded-lg px-3 py-2.5 transition-colors hover:opacity-80"
                  style={{ background: `${mod.color}10` }}
                >
                  <span
                    className="flex h-8 w-8 items-center justify-center rounded-md text-[10px] font-bold text-white shrink-0"
                    style={{ background: mod.color }}
                  >
                    {mod.tag}
                  </span>
                  <span className="text-sm font-medium" style={{ color: "var(--text)" }}>
                    {mod.name}
                  </span>
                </Link>
              ))}
            </div>

            {/* Mobile CTA buttons */}
            <div className="px-5 py-4 space-y-2 sm:hidden" style={{ borderTop: "1px solid var(--bdr)" }}>
              <Link
                href="/login"
                onClick={() => setDrawerOpen(false)}
                className="block w-full text-center px-4 py-2.5 text-sm font-medium rounded-lg transition-colors"
                style={{ color: "var(--text)", border: "1px solid var(--bdr)" }}
              >
                Login
              </Link>
              <Link
                href="/signup"
                onClick={() => setDrawerOpen(false)}
                className="block w-full text-center px-4 py-2.5 text-sm font-semibold text-white rounded-lg"
                style={{
                  backgroundImage: "linear-gradient(135deg, var(--c1), var(--c2, #6366f1))",
                }}
              >
                Dung thu
              </Link>
            </div>
          </aside>
        </div>
      )}

      {/* Slide-in animation */}
      <style jsx global>{`
        @keyframes slide-in {
          from { transform: translateX(100%); }
          to   { transform: translateX(0); }
        }
        .animate-slide-in {
          animation: slide-in 0.25s ease-out;
        }
      `}</style>
    </>
  );
}
