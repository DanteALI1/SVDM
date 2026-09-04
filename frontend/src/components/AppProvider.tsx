"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { dict, Lang, Msg } from "@/lib/i18n";
import {
  User,
  api,
  clearAuth,
  getLang,
  getTheme,
  getToken,
  setLang as persistLang,
  setTheme as persistTheme,
  setTenantId,
  getTenantId,
} from "@/lib/api";

type Ctx = {
  user: User | null;
  lang: Lang;
  theme: "light" | "dark";
  t: (k: Msg) => string;
  setLanguage: (l: Lang) => void;
  setThemeMode: (t: "light" | "dark") => void;
  refreshUser: () => Promise<void>;
  logout: () => Promise<void>;
  switchOrg: (tenantId: number) => Promise<void>;
};

const AppCtx = createContext<Ctx | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [lang, setLangState] = useState<Lang>("ru");
  const [theme, setThemeState] = useState<"light" | "dark">("light");

  useEffect(() => {
    setLangState(getLang());
    const th = getTheme();
    setThemeState(th);
    persistTheme(th);
    if (getToken()) {
      api<User>("/api/auth/me/")
        .then((u) => {
          setUser(u);
          if (!getTenantId() && u.memberships[0]) setTenantId(u.memberships[0].tenant);
        })
        .catch(() => clearAuth());
    }
  }, []);

  const value: Ctx = {
    user,
    lang,
    theme,
    t: (k) => dict[lang][k],
    setLanguage: (l) => {
      setLangState(l);
      persistLang(l);
      if (user) api("/api/auth/me/", { method: "PATCH", json: { preferred_language: l } }).catch(() => {});
    },
    setThemeMode: (th) => {
      setThemeState(th);
      persistTheme(th);
      if (user) api("/api/auth/me/", { method: "PATCH", json: { preferred_theme: th } }).catch(() => {});
    },
    refreshUser: async () => {
      const u = await api<User>("/api/auth/me/");
      setUser(u);
    },
    logout: async () => {
      try {
        await api("/api/auth/logout/", { method: "POST" });
      } catch {
        /* ignore */
      }
      clearAuth();
      setUser(null);
      window.location.href = "/login";
    },
    switchOrg: async (tenantId) => {
      await api("/api/tenants/switch/", { method: "POST", json: { tenant_id: tenantId } });
      setTenantId(tenantId);
      window.location.reload();
    },
  };

  return <AppCtx.Provider value={value}>{children}</AppCtx.Provider>;
}

export function useApp() {
  const ctx = useContext(AppCtx);
  if (!ctx) throw new Error("AppProvider missing");
  return ctx;
}
