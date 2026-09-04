"use client";

import Link from "next/link";
import { FormEvent, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useApp } from "@/components/AppProvider";
import { getTenantId } from "@/lib/api";

function initials(name?: string | null) {
  const s = (name || "U").trim();
  const parts = s.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return s.slice(0, 2).toUpperCase();
}

export function Shell({ children }: { children: React.ReactNode }) {
  const { t, user, lang, theme, setLanguage, setThemeMode, logout, switchOrg } = useApp();
  const pathname = usePathname();
  const router = useRouter();
  const [navOpen, setNavOpen] = useState(false);
  const [q, setQ] = useState("");

  const mainLinks = [
    { href: "/dashboard", label: t("dashboard"), ico: "▣" },
    { href: "/vulnerabilities", label: t("vulnerabilities"), ico: "⚠" },
    { href: "/assets", label: t("assets"), ico: "⧉" },
    { href: "/tickets", label: t("tickets"), ico: "☰" },
  ];
  const manageLinks = [
    { href: "/wiki", label: t("wiki"), ico: "◈" },
    { href: "/admin", label: t("admin"), ico: "⚙" },
  ];
  if (user?.is_platform_admin) manageLinks.push({ href: "/platform", label: t("platform"), ico: "★" });

  const membership = useMemo(
    () => (user?.memberships || []).find((m) => String(m.tenant) === String(getTenantId())) || user?.memberships?.[0],
    [user]
  );
  const role = membership?.role || (user?.is_platform_admin ? "platform" : "user");

  function onSearch(e: FormEvent) {
    e.preventDefault();
    const term = q.trim();
    router.push(term ? `/vulnerabilities?search=${encodeURIComponent(term)}` : "/vulnerabilities");
    setNavOpen(false);
  }

  function NavItems({ items }: { items: { href: string; label: string; ico: string }[] }) {
    return (
      <>
        {items.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className={`nav-link ${pathname.startsWith(l.href) ? "active" : ""}`}
            onClick={() => setNavOpen(false)}
          >
            <span className="nav-ico" aria-hidden>
              {l.ico}
            </span>
            <span>{l.label}</span>
          </Link>
        ))}
      </>
    );
  }

  return (
    <div className={`app-shell ${navOpen ? "nav-open" : ""}`}>
      <button
        type="button"
        className="nav-toggle btn secondary"
        aria-label="Menu"
        aria-expanded={navOpen}
        onClick={() => setNavOpen((v) => !v)}
      >
        ☰ SVDB
      </button>
      {navOpen && <div className="nav-backdrop" onClick={() => setNavOpen(false)} />}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand">SVDB</div>
          <span className="plan-badge">SecOps</span>
        </div>
        <select
          className="select sidebar-org"
          value={getTenantId()}
          onChange={(e) => switchOrg(Number(e.target.value))}
          aria-label={t("org")}
        >
          {(user?.memberships || []).map((m) => (
            <option key={m.id} value={m.tenant}>
              {m.tenant_name}
            </option>
          ))}
        </select>
        <div className="nav-group">
          <div className="nav-group-label">{t("mainMenu")}</div>
          <NavItems items={mainLinks} />
        </div>
        <div className="nav-group">
          <div className="nav-group-label">{t("manageMenu")}</div>
          <NavItems items={manageLinks} />
        </div>
        <div className="sidebar-spacer" />
        <div className="sidebar-user">
          <div className="avatar">{initials(user?.username)}</div>
          <div className="meta">
            <div className="name">{user?.username || "—"}</div>
            <div className="role">{role}</div>
          </div>
        </div>
      </aside>
      <div className="content-col">
        <div className="topbar">
          <div className="topbar-left">
            <form onSubmit={onSearch} style={{ display: "contents" }}>
              <input
                className="input top-search"
                placeholder={t("searchPlaceholder")}
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
            </form>
          </div>
          <div className="topbar-right">
            <span className="status-chip">
              <span className="dot" />
              {t("liveStatus")}
            </span>
            <select className="select compact" value={lang} onChange={(e) => setLanguage(e.target.value as "ru" | "en")}>
              <option value="ru">RU</option>
              <option value="en">EN</option>
            </select>
            <select
              className="select compact"
              value={theme}
              onChange={(e) => setThemeMode(e.target.value as "light" | "dark")}
            >
              <option value="light">{t("light")}</option>
              <option value="dark">{t("dark")}</option>
            </select>
            <div className="avatar sm" title={user?.username || ""}>
              {initials(user?.username)}
            </div>
            <button className="btn ghost" onClick={() => logout()}>
              {t("logout")}
            </button>
          </div>
        </div>
        <div className="main">{children}</div>
      </div>
    </div>
  );
}
