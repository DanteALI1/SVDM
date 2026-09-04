export type Membership = {
  id: number;
  tenant: number;
  tenant_name: string;
  tenant_slug: string;
  role: string;
};

export type User = {
  id: number;
  username: string;
  email: string;
  is_platform_admin: boolean;
  preferred_language: "ru" | "en";
  preferred_theme: "light" | "dark";
  totp_confirmed: boolean;
  must_enroll_2fa: boolean;
  memberships: Membership[];
};

const TOKEN_KEY = "svdb_token";
const TENANT_KEY = "svdb_tenant";
const LANG_KEY = "svdb_lang";
const THEME_KEY = "svdb_theme";

export function getToken() {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(TOKEN_KEY) || "";
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(TENANT_KEY);
}

export function getTenantId() {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(TENANT_KEY) || "";
}

export function setTenantId(id: string | number) {
  localStorage.setItem(TENANT_KEY, String(id));
}

export function getLang(): "ru" | "en" {
  if (typeof window === "undefined") return "ru";
  return (localStorage.getItem(LANG_KEY) as "ru" | "en") || "ru";
}

export function setLang(lang: "ru" | "en") {
  localStorage.setItem(LANG_KEY, lang);
}

export function getTheme(): "light" | "dark" {
  if (typeof window === "undefined") return "light";
  return (localStorage.getItem(THEME_KEY) as "light" | "dark") || "light";
}

export function setTheme(theme: "light" | "dark") {
  localStorage.setItem(THEME_KEY, theme);
  document.documentElement.setAttribute("data-theme", theme);
}

export async function api<T = any>(
  path: string,
  options: RequestInit & { json?: unknown } = {}
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  const token = getToken();
  if (token) headers.Authorization = `Token ${token}`;
  const tenant = getTenantId();
  if (tenant) headers["X-Tenant-ID"] = tenant;
  let body = options.body;
  if (options.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.json);
  }
  const res = await fetch(
    (() => {
      let p = path.startsWith("/api") ? path : `/api${path.startsWith("/") ? path : `/${path}`}`;
      // Keep trailing slash for Django/DRF; Next skipTrailingSlashRedirect avoids POST 308 drops.
      if (!p.includes("?") && !p.endsWith("/")) p = `${p}/`;
      return p;
    })(),
    {
      ...options,
      headers,
      body,
      credentials: "include",
    }
  );
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || JSON.stringify(data);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res as unknown as T;
}
