"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, setToken, setTenantId, getToken } from "@/lib/api";
import { useApp } from "@/components/AppProvider";

export default function LoginPage() {
  const { t, refreshUser } = useApp();
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const [needTotp, setNeedTotp] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api<{ setup_completed: boolean }>("/api/setup/status/")
      .then((s) => {
        if (!s.setup_completed) router.replace("/setup");
      })
      .catch(() => {});
    if (getToken()) router.replace("/dashboard");
  }, [router]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
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

  return (
    <div className="hero-login">
      <div className="compose">
        <h1 className="brand-hero">SVDB</h1>
        <p className="tagline">{t("tagline")}</p>
        <form onSubmit={onSubmit}>
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
        </form>
      </div>
    </div>
  );
}
