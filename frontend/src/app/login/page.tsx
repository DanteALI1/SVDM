"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { api, setToken, setTenantId, getToken } from "@/lib/api";
import { useApp } from "@/components/AppProvider";

function LoginForm() {
  const { t, refreshUser } = useApp();
  const router = useRouter();
  const sp = useSearchParams();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const [needTotp, setNeedTotp] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [tenantSlug, setTenantSlug] = useState("default");
  const [sso, setSso] = useState<{ sso_enabled: boolean; provider: string } | null>(null);

  useEffect(() => {
    const token = sp.get("token");
    const tenant = sp.get("tenant");
    if (token) {
      setToken(token);
      if (tenant) setTenantId(tenant);
      refreshUser().then(() => router.replace("/dashboard"));
      return;
    }
    api<{ setup_completed: boolean }>("/api/setup/status/")
      .then((s) => {
        if (!s.setup_completed) router.replace("/setup");
      })
      .catch(() => {});
    if (getToken()) router.replace("/dashboard");
  }, [router, sp, refreshUser]);

  useEffect(() => {
    api<{ sso_enabled: boolean; provider: string }>(`/api/auth/sso/providers/?tenant=${encodeURIComponent(tenantSlug)}`)
      .then(setSso)
      .catch(() => setSso(null));
  }, [tenantSlug]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      if (sso?.sso_enabled && (sso.provider === "ldap" || sso.provider === "ad")) {
        const data = await api<{ token: string; user: any; tenant_id: number }>("/api/auth/sso/ldap/", {
          method: "POST",
          json: { tenant: tenantSlug, username, password },
        });
        setToken(data.token);
        setTenantId(data.tenant_id);
        await refreshUser();
        router.push("/dashboard");
        return;
      }
      const data = await api<{ token: string; user: any }>("/api/auth/login/", {
        method: "POST",
        json: { username, password, totp_code: totp },
      });
      setToken(data.token);
      if (data.user.memberships?.[0]) setTenantId(data.user.memberships[0].tenant);
      await refreshUser();
      if (data.user.must_enroll_2fa) router.push("/enroll-2fa");
      else router.push("/dashboard");
    } catch (err: any) {
      const msg = String(err.message || err);
      if (msg.toLowerCase().includes("totp")) setNeedTotp(true);
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  async function startExternalSso() {
    try {
      const data = await api<{ authorize_url?: string; provider: string; mode?: string }>(
        `/api/auth/sso/start/?tenant=${encodeURIComponent(tenantSlug)}`
      );
      if (data.authorize_url) {
        window.location.href = data.authorize_url;
        return;
      }
      setError(data.mode === "form" ? "Enter LDAP/AD credentials above" : "SSO start failed");
    } catch (e: any) {
      setError(String(e.message || e));
    }
  }

  return (
    <div className="hero-login">
      <div className="compose">
        <h1 className="brand-hero">SVDB</h1>
        <p className="tagline">{t("tagline")}</p>
        <form onSubmit={onSubmit}>
          <label className="muted">Tenant</label>
          <input className="input" value={tenantSlug} onChange={(e) => setTenantSlug(e.target.value)} />
          <label className="muted">{t("username")}</label>
          <input className="input" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
          <label className="muted">{t("password")}</label>
          <input
            className="input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
          {(needTotp || totp) && (
            <>
              <label className="muted">{t("totp")}</label>
              <input className="input" value={totp} onChange={(e) => setTotp(e.target.value)} />
            </>
          )}
          {error && <p style={{ color: "var(--svdb-danger)", margin: 0 }}>{error}</p>}
          <button className="btn" disabled={loading} type="submit">
            {t("login")}
          </button>
          {sso?.sso_enabled && (
            <button className="btn secondary" type="button" onClick={startExternalSso}>
              SSO ({sso.provider})
            </button>
          )}
        </form>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="hero-login"><p>Loading…</p></div>}>
      <LoginForm />
    </Suspense>
  );
}
