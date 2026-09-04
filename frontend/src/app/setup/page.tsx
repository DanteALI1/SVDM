"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useApp } from "@/components/AppProvider";

const steps = ["platform_admin", "database", "tenant", "tenant_admin"] as const;

export default function SetupPage() {
  const { t } = useApp();
  const router = useRouter();
  const [stepIdx, setStepIdx] = useState(0);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    username: "platform",
    email: "platform@svdb.local",
    password: "SecurePass1!",
    host: "127.0.0.1",
    port: 5432,
    name: "svdb",
    user: "svdb",
    db_password: "",
    tenant_name: "Default",
    tenant_slug: "default",
    tadmin_username: "admin",
    tadmin_email: "admin@svdb.local",
    tadmin_password: "SecurePass1!",
  });

  const step = steps[stepIdx];

  async function next() {
    setError("");
    try {
      let payload: Record<string, unknown> = { step };
      if (step === "platform_admin") {
        payload = { step, username: form.username, email: form.email, password: form.password };
      } else if (step === "database") {
        payload = {
          step,
          host: form.host,
          port: form.port,
          name: form.name,
          user: form.user,
          password: form.db_password,
          confirm: true,
        };
      } else if (step === "tenant") {
        payload = { step, name: form.tenant_name, slug: form.tenant_slug };
      } else {
        payload = {
          step,
          tenant_slug: form.tenant_slug,
          username: form.tadmin_username,
          email: form.tadmin_email,
          password: form.tadmin_password,
        };
      }
      const res = await api<any>("/api/setup/first-run/", { method: "POST", json: payload });
      if (res.setup_completed) {
        router.push("/login");
        return;
      }
      setStepIdx((i) => Math.min(i + 1, steps.length - 1));
    } catch (e: any) {
      setError(String(e.message || e));
    }
  }

  function set(k: string, v: string | number) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  return (
    <div className="hero-login">
      <aside className="login-brand-pane">
        <div>
          <h1 className="brand-hero">SVDB</h1>
          <p className="tagline">{t("setup")}</p>
        </div>
        <div className="brand-foot">Step {stepIdx + 1} / 4 — {step}</div>
      </aside>
      <div className="login-form-pane">
        <div className="login-card" style={{ width: "min(520px, 100%)" }}>
          <h2>{t("setup")}</h2>
          <p className="lead">
            Step {stepIdx + 1}/4 — {step}
          </p>
          {step === "platform_admin" && (
            <div style={{ display: "grid", gap: "0.6rem" }}>
              <input className="input" placeholder="Platform admin username" value={form.username} onChange={(e) => set("username", e.target.value)} />
              <input className="input" placeholder="Email" value={form.email} onChange={(e) => set("email", e.target.value)} />
              <input className="input" type="password" placeholder="Password" value={form.password} onChange={(e) => set("password", e.target.value)} />
            </div>
          )}
          {step === "database" && (
            <div style={{ display: "grid", gap: "0.6rem" }}>
              <input className="input" placeholder="DB host" value={form.host} onChange={(e) => set("host", e.target.value)} />
              <input className="input" placeholder="Port" value={form.port} onChange={(e) => set("port", Number(e.target.value))} />
              <input className="input" placeholder="Database" value={form.name} onChange={(e) => set("name", e.target.value)} />
              <input className="input" placeholder="User" value={form.user} onChange={(e) => set("user", e.target.value)} />
              <input className="input" type="password" placeholder="Password (optional confirm)" value={form.db_password} onChange={(e) => set("db_password", e.target.value)} />
            </div>
          )}
          {step === "tenant" && (
            <div style={{ display: "grid", gap: "0.6rem" }}>
              <input className="input" placeholder="Tenant name" value={form.tenant_name} onChange={(e) => set("tenant_name", e.target.value)} />
              <input className="input" placeholder="Slug" value={form.tenant_slug} onChange={(e) => set("tenant_slug", e.target.value)} />
            </div>
          )}
          {step === "tenant_admin" && (
            <div style={{ display: "grid", gap: "0.6rem" }}>
              <input className="input" placeholder="Tenant admin" value={form.tadmin_username} onChange={(e) => set("tadmin_username", e.target.value)} />
              <input className="input" placeholder="Email" value={form.tadmin_email} onChange={(e) => set("tadmin_email", e.target.value)} />
              <input className="input" type="password" placeholder="Password" value={form.tadmin_password} onChange={(e) => set("tadmin_password", e.target.value)} />
            </div>
          )}
          {error && <p style={{ color: "var(--svdb-danger)" }}>{error}</p>}
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "1rem" }}>
            <button className="btn secondary" disabled={stepIdx === 0} onClick={() => setStepIdx((i) => i - 1)}>
              {t("back")}
            </button>
            <button className="btn" onClick={next}>
              {stepIdx === steps.length - 1 ? t("finish") : t("next")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
