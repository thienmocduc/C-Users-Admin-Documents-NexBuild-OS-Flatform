"use client";

import Link from "next/link";

const modules = [
  {
    id: 12,
    name: "NexMarket",
    slug: "market",
    desc: "B2B · B2C · D2C · Tho · Vat lieu · Cong trinh · Dien dan",
    tag: "B2B/B2C/D2C",
    color: "#C9A84C",
    gradientFrom: "#C9A84C",
    gradientVia: "#F59E0B",
    gradientTo: "#0EA5E9",
    price: "Free — Pro tu 490K/thang",
    key: true,
    label: "KEY · 12",
    icon: (
      <svg width="20" height="20" viewBox="0 0 22 22" fill="none">
        <circle cx="11" cy="11" r="8.5" stroke="#C9A84C" strokeWidth="1.5" />
        <circle cx="11" cy="11" r="3" fill="#C9A84C" opacity=".7" />
        <path d="M11 2.5V4M11 18V19.5M19.5 11H18M4 11H2.5" stroke="#C9A84C" strokeWidth="1.3" strokeLinecap="round" />
        <path d="M17 5L15.8 6.2M6.2 15.8L5 17M17 17L15.8 15.8M6.2 6.2L5 5" stroke="#C9A84C" strokeWidth="1.1" strokeLinecap="round" opacity=".6" />
      </svg>
    ),
  },
  {
    id: 1,
    name: "NexDesign AI",
    slug: "design",
    desc: "Mo ta y tuong → AI render 3D → BOQ tu dong → 1-click dat tho",
    tag: "AI SaaS",
    color: "#00C9A7",
    gradientFrom: "#00C9A7",
    gradientTo: "#0EA5E9",
    price: "Free 5 render — Pro tu 299K/thang",
    label: "01",
    icon: (
      <svg width="20" height="20" viewBox="0 0 22 22" fill="none">
        <path d="M11 2L19 6.5V15.5L11 20L3 15.5V6.5L11 2Z" stroke="#00C9A7" strokeWidth="1.5" strokeLinejoin="round" />
        <circle cx="11" cy="11" r="2.5" fill="#00C9A7" opacity=".8" />
      </svg>
    ),
  },
  {
    id: 2,
    name: "NexTalent",
    slug: "talent",
    desc: "Tho verified · Escrow · Bao hiem tu dong · GPS realtime",
    tag: "Marketplace",
    color: "#0EA5E9",
    gradientFrom: "#0EA5E9",
    gradientTo: "#6366F1",
    price: "Free — Hoa hong 5%",
    label: "02",
    icon: (
      <svg width="20" height="20" viewBox="0 0 22 22" fill="none">
        <circle cx="11" cy="8" r="3.5" stroke="#0EA5E9" strokeWidth="1.5" />
        <path d="M4 20C4 16.5 7 13.5 11 13.5C15 13.5 18 16.5 18 20" stroke="#0EA5E9" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    id: 3,
    name: "NexSupply",
    slug: "supply",
    desc: "200+ nha cung cap · So sanh gia realtime · Mua truoc tra sau 60 ngay",
    tag: "B2B",
    color: "#F59E0B",
    gradientFrom: "#F59E0B",
    gradientTo: "#FB923C",
    price: "Free listing — Pro tu 390K/thang",
    label: "03",
    icon: (
      <svg width="20" height="20" viewBox="0 0 22 22" fill="none">
        <path d="M2 5H20L18 16H4L2 5Z" stroke="#F59E0B" strokeWidth="1.5" strokeLinejoin="round" />
        <circle cx="8" cy="19.5" r="1.5" fill="#F59E0B" />
        <circle cx="15" cy="19.5" r="1.5" fill="#F59E0B" />
      </svg>
    ),
  },
  {
    id: 4,
    name: "NexERP",
    slug: "erp",
    desc: "Voice command · AI nhan biet tien do tu anh · Canh bao tre som",
    tag: "SaaS",
    color: "#6366F1",
    gradientFrom: "#6366F1",
    gradientTo: "#0EA5E9",
    price: "Tu 690K/thang",
    label: "04",
    icon: (
      <svg width="20" height="20" viewBox="0 0 22 22" fill="none">
        <rect x="2" y="2" width="8" height="8" rx="2" stroke="#6366F1" strokeWidth="1.5" />
        <rect x="12" y="2" width="8" height="8" rx="2" stroke="#0EA5E9" strokeWidth="1.5" />
        <rect x="2" y="12" width="8" height="8" rx="2" stroke="#0EA5E9" strokeWidth="1.5" />
        <rect x="12" y="12" width="8" height="8" rx="2" stroke="#6366F1" strokeWidth="1.5" />
      </svg>
    ),
  },
  {
    id: 5,
    name: "NexMedia",
    slug: "media",
    desc: "In-render Ads · Attribution 100% · Khong bi ad blocker",
    tag: "AdTech",
    color: "#A855F7",
    gradientFrom: "#A855F7",
    gradientTo: "#6366F1",
    price: "Tu 1.5M/chien dich",
    label: "05",
    icon: (
      <svg width="20" height="20" viewBox="0 0 22 22" fill="none">
        <rect x="2" y="4" width="18" height="12" rx="2" stroke="#A855F7" strokeWidth="1.5" />
        <path d="M8 8L14 11L8 14V8Z" fill="#A855F7" opacity=".8" />
      </svg>
    ),
  },
  {
    id: 6,
    name: "NexFinance",
    slug: "finance",
    desc: "Vay khong the chap · Duyet 24h · Milestone disbursement · Bao hiem",
    tag: "Fintech",
    color: "#22C55E",
    gradientFrom: "#22C55E",
    gradientTo: "#00C9A7",
    price: "Phi tu van mien phi",
    label: "06",
    icon: (
      <svg width="20" height="20" viewBox="0 0 22 22" fill="none">
        <rect x="2" y="5" width="18" height="13" rx="2.5" stroke="#22C55E" strokeWidth="1.5" />
        <path d="M2 9H20" stroke="#22C55E" strokeWidth="1.5" />
        <circle cx="11" cy="13" r="2" stroke="#22C55E" strokeWidth="1.2" />
      </svg>
    ),
  },
  {
    id: 7,
    name: "NexAffiliates",
    slug: "affiliates",
    desc: "Share thiet ke → Earn 3-12% hoa hong · Payout 24h",
    tag: "Affiliate",
    color: "#FB923C",
    gradientFrom: "#FB923C",
    gradientTo: "#F59E0B",
    price: "Mien phi — Hoa hong 3-8%",
    label: "07",
    icon: (
      <svg width="20" height="20" viewBox="0 0 22 22" fill="none">
        <circle cx="11" cy="4" r="2.5" stroke="#FB923C" strokeWidth="1.5" />
        <circle cx="3" cy="17" r="2.5" stroke="#FB923C" strokeWidth="1.5" />
        <circle cx="19" cy="17" r="2.5" stroke="#FB923C" strokeWidth="1.5" />
        <path d="M11 6.5L5.5 14.5M11 6.5L16.5 14.5" stroke="#FB923C" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    id: 8,
    name: "NexAcademy",
    slug: "academy",
    desc: "Hoc → Cert → Badge NexTalent → Thu nhap tang +15-25%",
    tag: "EdTech",
    color: "#6366F1",
    gradientFrom: "#6366F1",
    gradientTo: "#A855F7",
    price: "Free — Premium tu 199K/thang",
    label: "08",
    icon: (
      <svg width="20" height="20" viewBox="0 0 22 22" fill="none">
        <path d="M11 2L21 7.5L11 13L1 7.5L11 2Z" stroke="#6366F1" strokeWidth="1.5" strokeLinejoin="round" />
        <path d="M5 10.5V16C5 16 7 19 11 19C15 19 17 16 17 16V10.5" stroke="#6366F1" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    id: 9,
    name: "NexAgent AI",
    slug: "agent",
    desc: "Cong trinh tu van hanh · Dat tho, order vat lieu tu dong",
    tag: "AI",
    color: "#6366F1",
    gradientFrom: "#6366F1",
    gradientTo: "#A855F7",
    price: "Tu 990K/thang",
    label: "09",
    icon: (
      <svg width="20" height="20" viewBox="0 0 22 22" fill="none">
        <circle cx="11" cy="11" r="8" stroke="#6366F1" strokeWidth="1.5" />
        <path d="M11 7V11L14 13" stroke="#A855F7" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    id: 10,
    name: "NexConnect",
    slug: "connect",
    desc: "MISA · Slack · Google · Zalo · 50+ app · Nhap 1 lan",
    tag: "Integration",
    color: "#0EA5E9",
    gradientFrom: "#0EA5E9",
    gradientTo: "#00C9A7",
    price: "Free 3 ket noi — Pro tu 290K/thang",
    label: "10",
    icon: (
      <svg width="20" height="20" viewBox="0 0 22 22" fill="none">
        <circle cx="4" cy="11" r="2.5" stroke="#0EA5E9" strokeWidth="1.5" />
        <circle cx="18" cy="5" r="2.5" stroke="#00C9A7" strokeWidth="1.5" />
        <circle cx="18" cy="17" r="2.5" stroke="#00C9A7" strokeWidth="1.5" />
        <path d="M6.5 11H11M11 11L15.5 5.8M11 11L15.5 16.2" stroke="#0EA5E9" strokeWidth="1.2" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    id: 11,
    name: "NexAccounting",
    slug: "accounting",
    desc: "Ket noi MISA · So sach tu ghi · Lai lo realtime · Quyet toan 5 phut",
    tag: "SaaS",
    color: "#22C55E",
    gradientFrom: "#22C55E",
    gradientTo: "#0EA5E9",
    price: "Tu 490K/thang",
    label: "11",
    icon: (
      <svg width="20" height="20" viewBox="0 0 22 22" fill="none">
        <rect x="3" y="3" width="16" height="16" rx="3" stroke="#22C55E" strokeWidth="1.5" />
        <path d="M7 11H15M7 7H15M7 15H11" stroke="#22C55E" strokeWidth="1.2" strokeLinecap="round" />
      </svg>
    ),
  },
];

export function Ecosystem() {
  return (
    <section className="section" id="ecosystem">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-14">
          <span
            className="inline-block rounded-full px-4 py-1.5 text-xs font-semibold uppercase tracking-widest mb-4"
            style={{
              border: "1px solid var(--bdr2)",
              color: "var(--c1)",
              background: "rgba(0,201,167,.08)",
            }}
          >
            HE SINH THAI
          </span>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-4" style={{ color: "var(--text)" }}>
            12 module.{" "}
            <span className="grad-text">1 nen tang.</span>{" "}
            Khong manh ghep.
          </h2>
          <p className="max-w-2xl mx-auto text-base leading-relaxed" style={{ color: "var(--text2)" }}>
            Moi module hoat dong doc lap nhung ket noi lien mach — du lieu chay
            xuyen suot, khong can tich hop thu cong.
          </p>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {modules.map((m) => {
            const gradient = m.gradientVia
              ? `linear-gradient(135deg, ${m.gradientFrom}, ${m.gradientVia}, ${m.gradientTo})`
              : `linear-gradient(135deg, ${m.gradientFrom}, ${m.gradientTo})`;

            return (
              <Link
                key={m.slug}
                href={`/ecosystem/${m.slug}`}
                className="card-hover group relative flex flex-col overflow-hidden rounded-2xl"
                style={{
                  background: "var(--card-bg)",
                  border: m.key
                    ? `1.5px solid ${m.color}44`
                    : "1px solid var(--card-bdr)",
                  backdropFilter: "blur(12px)",
                }}
              >
                {/* Colored gradient strip */}
                <div
                  className="h-[2px] w-full"
                  style={{ background: gradient }}
                />

                <div className="flex flex-col flex-1 p-5">
                  {/* Module number */}
                  <span
                    className="font-mono text-xs mb-3"
                    style={{ color: "var(--text3)" }}
                  >
                    {m.key ? (
                      <>
                        <span style={{ color: m.color }}>⬡</span> {m.label}
                      </>
                    ) : (
                      m.label
                    )}
                  </span>

                  {/* Icon in colored bg */}
                  <div
                    className="w-[38px] h-[38px] rounded-[10px] flex items-center justify-center mb-4"
                    style={{ background: `${m.color}1A` }}
                  >
                    {m.icon}
                  </div>

                  {/* Name */}
                  <h3
                    className="text-[16px] font-bold mb-1"
                    style={{ color: "var(--text)" }}
                  >
                    {m.name}
                  </h3>

                  {/* Description */}
                  <p
                    className="text-sm mb-3 flex-1 leading-relaxed"
                    style={{ color: "var(--text2)" }}
                  >
                    {m.desc}
                  </p>

                  {/* Tag */}
                  <span
                    className="inline-block self-start rounded-full px-2.5 py-0.5 text-[11px] font-medium mb-3"
                    style={{
                      background: `${m.color}18`,
                      color: m.color,
                      border: `1px solid ${m.color}33`,
                    }}
                  >
                    {m.tag}
                  </span>

                  {/* Price */}
                  <p
                    className="text-xs mb-4"
                    style={{ color: "var(--text3)" }}
                  >
                    {m.price}
                  </p>

                  {/* CTA */}
                  <span
                    className="inline-flex items-center justify-center w-full rounded-lg py-2 text-sm font-semibold transition-opacity duration-200 group-hover:opacity-90"
                    style={{
                      background: gradient,
                      color: "#fff",
                    }}
                  >
                    Tim hieu &rarr;
                  </span>
                </div>

                {/* KEY module highlight ring */}
                {m.key && (
                  <div
                    className="absolute -top-px -left-px -right-px -bottom-px rounded-2xl pointer-events-none"
                    style={{
                      boxShadow: `0 0 30px ${m.color}22, inset 0 0 30px ${m.color}08`,
                    }}
                  />
                )}
              </Link>
            );
          })}
        </div>
      </div>
    </section>
  );
}
