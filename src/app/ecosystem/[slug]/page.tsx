import { ecosystems, getEcosystem } from "@/data/ecosystems";
import { notFound } from "next/navigation";
import Link from "next/link";
import { EcoIcon } from "@/components/EcoIcons";

export function generateStaticParams() {
  return ecosystems.map((e) => ({ slug: e.slug }));
}

export function generateMetadata({ params }: { params: { slug: string } }) {
  const eco = getEcosystem(params.slug);
  if (!eco) return { title: "Not Found" };
  return {
    title: `${eco.name} — NexBuild Holdings`,
    description: eco.desc,
  };
}

export default function EcosystemPage({ params }: { params: { slug: string } }) {
  const eco = getEcosystem(params.slug);
  if (!eco) notFound();

  return (
    <div className="min-h-screen relative z-10">
      {/* Back nav */}
      <div
        className="sticky top-0 z-20 h-14 flex items-center justify-between px-6 md:px-12 border-b backdrop-blur-2xl"
        style={{ background: "var(--hdr-bg)", borderColor: `${eco.color}33` }}
      >
        <Link
          href="/#ecosystem"
          className="flex items-center gap-2 text-sm font-semibold px-3 py-1.5 rounded-lg border transition-colors hover:border-[var(--c1)] hover:text-[var(--c1)]"
          style={{ color: "var(--text2)", borderColor: "var(--bdr)" }}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M10 3L5 8L10 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          Quay lai
        </Link>
        <span className="text-sm font-bold grad-text">NexBuild Ecosystem</span>
        <div className="w-[90px]" />
      </div>

      <div className="max-w-5xl mx-auto px-6 md:px-12 pb-20">
        {/* Header */}
        <div className="flex items-start gap-5 py-8 border-b mb-7" style={{ borderColor: "var(--bdr)" }}>
          <div
            className="w-14 h-14 rounded-2xl flex items-center justify-center flex-shrink-0"
            style={{ background: eco.colorBg, border: `1px solid ${eco.color}40` }}
          >
            <EcoIcon slug={eco.slug} size={28} />
          </div>
          <div>
            <h1
              className="text-3xl font-black mb-1"
              style={{
                background: `linear-gradient(135deg, ${eco.gradientFrom}, ${eco.gradientTo})`,
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              {eco.name}
            </h1>
            <div className="text-xs font-semibold tracking-wider uppercase" style={{ color: "var(--text3)" }}>
              {eco.model}
            </div>
            <p className="text-sm mt-1.5 leading-relaxed max-w-xl" style={{ color: "var(--text2)" }}>
              {eco.desc}
            </p>
          </div>
        </div>

        {/* KPIs */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          {eco.kpis.map((kpi) => (
            <div
              key={kpi.label}
              className="p-4 rounded-nex border transition-transform hover:-translate-y-0.5"
              style={{
                background: kpi.highlight
                  ? `linear-gradient(135deg, ${eco.color}18, ${eco.gradientTo}10)`
                  : "var(--card-bg)",
                borderColor: kpi.highlight ? `${eco.color}35` : "var(--card-bdr)",
              }}
            >
              <div className="text-[10px] uppercase tracking-wider font-semibold mb-1.5" style={{ color: "var(--text3)" }}>
                {kpi.label}
              </div>
              <div
                className="font-mono text-2xl font-bold leading-none"
                style={{
                  background: kpi.highlight
                    ? `linear-gradient(135deg, ${eco.gradientFrom}, ${eco.gradientTo})`
                    : undefined,
                  WebkitBackgroundClip: kpi.highlight ? "text" : undefined,
                  WebkitTextFillColor: kpi.highlight ? "transparent" : undefined,
                  color: kpi.highlight ? undefined : "var(--text)",
                }}
              >
                {kpi.value}
              </div>
              <div className="text-[11px] mt-1" style={{ color: "var(--text3)" }}>
                {kpi.note}
              </div>
            </div>
          ))}
        </div>

        {/* Pain → Solution */}
        <h3 className="font-bold text-base mb-3">Noi dau → Giai phap</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
          {eco.pains.map((pain, i) => (
            <div
              key={i}
              className="rounded-nex border p-5 transition-all hover:shadow-lg"
              style={{
                background: "var(--card-bg)",
                borderColor: "var(--card-bdr)",
                borderLeft: "3px solid #EF4444",
              }}
            >
              <div className="text-[10px] font-bold text-red-500 mb-1 tracking-wider">TRUOC DAY</div>
              <div className="text-sm font-semibold mb-1" style={{ color: "var(--text)" }}>
                {pain.before}
              </div>
              <div className="text-xs mb-3 leading-relaxed" style={{ color: "var(--text2)" }}>
                {pain.beforeDesc}
              </div>
              <div className="text-[10px] font-bold mb-1 tracking-wider" style={{ color: eco.color }}>
                VOI {eco.name.toUpperCase()}
              </div>
              <div className="text-sm font-semibold mb-1" style={{ color: eco.color }}>
                {pain.after}
              </div>
              <div className="text-xs leading-relaxed" style={{ color: "var(--text2)" }}>
                {pain.afterDesc}
              </div>
            </div>
          ))}
        </div>

        {/* Features */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
          {eco.features.map((feat) => (
            <div
              key={feat.title}
              className="rounded-nex border p-5 relative overflow-hidden transition-all hover:shadow-lg"
              style={{ background: "var(--card-bg)", borderColor: "var(--card-bdr)" }}
            >
              <div
                className="absolute top-0 left-0 right-0 h-0.5"
                style={{ background: `linear-gradient(90deg, ${eco.gradientFrom}, ${eco.gradientTo})` }}
              />
              <div className="text-xl mb-2">{feat.icon}</div>
              <div className="font-bold text-sm mb-1" style={{ color: "var(--text)" }}>
                {feat.title}
              </div>
              <div className="text-xs leading-relaxed" style={{ color: "var(--text2)" }}>
                {feat.desc}
              </div>
            </div>
          ))}
        </div>

        {/* Pricing */}
        <div className="h-px mb-6" style={{ background: "var(--bdr)" }} />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-8">
          {eco.pricing.map((p) => (
            <div
              key={p.label}
              className="p-4 rounded-nex border text-center"
              style={{
                background: p.highlight
                  ? `linear-gradient(135deg, ${eco.color}15, ${eco.gradientTo}08)`
                  : "var(--card-bg)",
                borderColor: p.highlight ? `${eco.color}30` : "var(--card-bdr)",
              }}
            >
              <div className="text-[10px] uppercase tracking-wider font-semibold mb-1" style={{ color: "var(--text3)" }}>
                {p.label}
              </div>
              <div
                className="font-mono text-xl font-bold"
                style={{
                  background: `linear-gradient(135deg, ${eco.gradientFrom}, ${eco.gradientTo})`,
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                }}
              >
                {p.value}
              </div>
              <div className="text-[11px] mt-1" style={{ color: "var(--text3)" }}>
                {p.note}
              </div>
            </div>
          ))}
        </div>

        {/* CTA */}
        <div className="flex gap-3 justify-center">
          <button
            className="h-11 px-7 rounded-xl text-white text-sm font-bold border-none cursor-pointer transition-opacity hover:opacity-85"
            style={{ background: `linear-gradient(135deg, ${eco.gradientFrom}, ${eco.gradientTo})` }}
          >
            Dung thu {eco.name}
          </button>
          <Link
            href="/#ecosystem"
            className="h-11 px-5 rounded-xl text-sm font-semibold border flex items-center transition-colors hover:border-[var(--c1)] hover:text-[var(--c1)]"
            style={{ color: "var(--text)", borderColor: "var(--bdr2)", background: "var(--sur2)" }}
          >
            Xem tat ca modules
          </Link>
        </div>
      </div>
    </div>
  );
}
