export function EcoIcon({ slug, size = 20 }: { slug: string; size?: number }) {
  const icons: Record<string, React.ReactNode> = {
    market: (
      <svg width={size} height={size} viewBox="0 0 22 22" fill="none">
        <circle cx="11" cy="11" r="8.5" stroke="#C9A84C" strokeWidth="1.5" />
        <circle cx="11" cy="11" r="3" fill="#C9A84C" opacity=".7" />
        <path d="M11 2.5V4M11 18V19.5M19.5 11H18M4 11H2.5" stroke="#C9A84C" strokeWidth="1.3" strokeLinecap="round" />
        <path d="M17 5L15.8 6.2M6.2 15.8L5 17M17 17L15.8 15.8M6.2 6.2L5 5" stroke="#C9A84C" strokeWidth="1.1" strokeLinecap="round" opacity=".6" />
      </svg>
    ),
    design: (
      <svg width={size} height={size} viewBox="0 0 22 22" fill="none">
        <path d="M11 2L19 6.5V15.5L11 20L3 15.5V6.5L11 2Z" stroke="#00C9A7" strokeWidth="1.5" strokeLinejoin="round" />
        <circle cx="11" cy="11" r="2.5" fill="#00C9A7" opacity=".8" />
      </svg>
    ),
    talent: (
      <svg width={size} height={size} viewBox="0 0 22 22" fill="none">
        <circle cx="11" cy="8" r="3.5" stroke="#0EA5E9" strokeWidth="1.5" />
        <path d="M4 20C4 16.5 7 13.5 11 13.5C15 13.5 18 16.5 18 20" stroke="#0EA5E9" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
    supply: (
      <svg width={size} height={size} viewBox="0 0 22 22" fill="none">
        <path d="M2 5H20L18 16H4L2 5Z" stroke="#F59E0B" strokeWidth="1.5" strokeLinejoin="round" />
        <circle cx="8" cy="19.5" r="1.5" fill="#F59E0B" />
        <circle cx="15" cy="19.5" r="1.5" fill="#F59E0B" />
      </svg>
    ),
    erp: (
      <svg width={size} height={size} viewBox="0 0 22 22" fill="none">
        <rect x="2" y="2" width="8" height="8" rx="2" stroke="#6366F1" strokeWidth="1.5" />
        <rect x="12" y="2" width="8" height="8" rx="2" stroke="#0EA5E9" strokeWidth="1.5" />
        <rect x="2" y="12" width="8" height="8" rx="2" stroke="#0EA5E9" strokeWidth="1.5" />
        <rect x="12" y="12" width="8" height="8" rx="2" stroke="#6366F1" strokeWidth="1.5" />
      </svg>
    ),
    media: (
      <svg width={size} height={size} viewBox="0 0 22 22" fill="none">
        <rect x="2" y="4" width="18" height="12" rx="2" stroke="#A855F7" strokeWidth="1.5" />
        <path d="M8 8L14 11L8 14V8Z" fill="#A855F7" opacity=".8" />
      </svg>
    ),
    finance: (
      <svg width={size} height={size} viewBox="0 0 22 22" fill="none">
        <rect x="2" y="5" width="18" height="13" rx="2.5" stroke="#22C55E" strokeWidth="1.5" />
        <path d="M2 9H20" stroke="#22C55E" strokeWidth="1.5" />
        <circle cx="11" cy="13" r="2" stroke="#22C55E" strokeWidth="1.2" />
      </svg>
    ),
    affiliates: (
      <svg width={size} height={size} viewBox="0 0 22 22" fill="none">
        <circle cx="11" cy="4" r="2.5" stroke="#FB923C" strokeWidth="1.5" />
        <circle cx="3" cy="17" r="2.5" stroke="#FB923C" strokeWidth="1.5" />
        <circle cx="19" cy="17" r="2.5" stroke="#FB923C" strokeWidth="1.5" />
        <path d="M11 6.5L5.5 14.5M11 6.5L16.5 14.5" stroke="#FB923C" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
    academy: (
      <svg width={size} height={size} viewBox="0 0 22 22" fill="none">
        <path d="M11 2L21 7.5L11 13L1 7.5L11 2Z" stroke="#6366F1" strokeWidth="1.5" strokeLinejoin="round" />
        <path d="M5 10.5V16C5 16 7 19 11 19C15 19 17 16 17 16V10.5" stroke="#6366F1" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
    agent: (
      <svg width={size} height={size} viewBox="0 0 22 22" fill="none">
        <circle cx="11" cy="11" r="8" stroke="#6366F1" strokeWidth="1.5" />
        <path d="M11 7V11L14 13" stroke="#A855F7" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
    connect: (
      <svg width={size} height={size} viewBox="0 0 22 22" fill="none">
        <circle cx="4" cy="11" r="2.5" stroke="#0EA5E9" strokeWidth="1.5" />
        <circle cx="18" cy="5" r="2.5" stroke="#00C9A7" strokeWidth="1.5" />
        <circle cx="18" cy="17" r="2.5" stroke="#00C9A7" strokeWidth="1.5" />
        <path d="M6.5 11H11M11 11L15.5 5.8M11 11L15.5 16.2" stroke="#0EA5E9" strokeWidth="1.2" strokeLinecap="round" />
      </svg>
    ),
    accounting: (
      <svg width={size} height={size} viewBox="0 0 22 22" fill="none">
        <rect x="3" y="3" width="16" height="16" rx="3" stroke="#22C55E" strokeWidth="1.5" />
        <path d="M7 11H15M7 7H15M7 15H11" stroke="#22C55E" strokeWidth="1.2" strokeLinecap="round" />
      </svg>
    ),
  };

  return <>{icons[slug] || null}</>;
}
