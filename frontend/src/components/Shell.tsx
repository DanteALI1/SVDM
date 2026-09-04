"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useApp } from "@/components/AppProvider";
import { getTenantId } from "@/lib/api";

export function Shell({ children }: { children: React.ReactNode }) {
  const { t, user, lang, theme, setLanguage, setThemeMode, logout, switchOrg } = useApp();
  const pathname = usePathname();
  const links = [
    { href: "/dashboard", label: t("dashboard") },
    { href: "/vulnerabilities", label: t("vulnerabilities") },
    { href: "/assets", label: t("assets") },
    { href: "/tickets", label: t("tickets") },
    { href: "/wiki", label: t("wiki") },
    { href: "/admin", label: t("admin") },
  ];
  if (user?.is_platform_admin) links.push({ href: "/platform", label: t("platform") });

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">SVDB</div>
        {links.map((l) => (
          <Link key={l.href} href={l.href} className={`nav-link ${pathname.startsWith(l.href) ? "active" : ""}`}>
            {l.label}
          </Link>
        ))}
      </aside>
      <div className="main">
        <div className="topbar">
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>
            <span className="muted">{t("org")}:</span>
            <select
              className="select"
              style={{ width: "auto", minWidth: 160 }}
              value={getTenantId()}
              onChange={(e) => switchOrg(Number(e.target.value))}
            >
              {(user?.memberships || []).map((m) => (
                <option key={m.id} value={m.tenant}>
                  {m.tenant_name} ({m.role})
                </option>
              ))}
            </select>
          </div>
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <select className="select" style={{ width: "auto" }} value={lang} onChange={(e) => setLanguage(e.target.value as "ru" | "en")}>
              <option value="ru">RU</option>
              <option value="en">EN</option>
            </select>
            <select
              className="select"
              style={{ width: "auto" }}
              value={theme}
              onChange={(e) => setThemeMode(e.target.value as "light" | "dark")}
            >
              <option value="light">{t("light")}</option>
              <option value="dark">{t("dark")}</option>
            </select>
            <button className="btn ghost" onClick={() => logout()}>
              {t("logout")}
            </button>
          </div>
        </div>
        {children}
      </div>
    </div>
  );
}
