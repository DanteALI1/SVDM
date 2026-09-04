"use client";

import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { api, getToken, getTenantId } from "@/lib/api";
import { useApp } from "@/components/AppProvider";

export default function AdminPage() {
  const { t } = useApp();
  const [tenant, setTenant] = useState<any>(null);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api("/api/tenants/current/").then(setTenant).catch((e) => setMsg(String(e.message || e)));
  }, []);

  async function save() {
    const updated = await api("/api/tenants/current/", { method: "PATCH", json: tenant });
    setTenant(updated);
    setMsg("Saved");
  }

  async function backup() {
    const res = await fetch("/api/backup/export/", {
      method: "POST",
      headers: { Authorization: `Token ${getToken()}`, "X-Tenant-ID": getTenantId() },
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "svdb-backup.zip";
    a.click();
  }

  async function restore(file: File) {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch("/api/backup/restore/", {
      method: "POST",
      headers: { Authorization: `Token ${getToken()}`, "X-Tenant-ID": getTenantId() },
      body: fd,
    });
    setMsg(JSON.stringify(await res.json()));
  }

  if (!tenant) {
    return (
      <Shell>
        <p>{msg || "Loading…"}</p>
      </Shell>
    );
  }

  function toggle(key: string) {
    setTenant({ ...tenant, [key]: !tenant[key] });
  }

  return (
    <Shell>
      <h1 style={{ marginTop: 0 }}>
        SVDB — {t("admin")}
      </h1>
      {msg && <p className="muted">{msg}</p>}
      <div className="panel" style={{ display: "grid", gap: "0.65rem", maxWidth: 720 }}>
        <h3>Branding</h3>
        <input className="input" value={tenant.primary_color} onChange={(e) => setTenant({ ...tenant, primary_color: e.target.value })} />
        <input className="input" value={tenant.accent_color} onChange={(e) => setTenant({ ...tenant, accent_color: e.target.value })} />
        <h3>Feature flags</h3>
        {[
          "feature_sync_nvd",
          "feature_sync_kev",
          "feature_sync_bdu",
          "feature_outbound_mail",
          "feature_sso",
          "feature_product_updates",
          "feature_2fa_totp",
          "offline_mode",
        ].map((k) => (
          <label key={k} style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <input type="checkbox" checked={!!tenant[k]} onChange={() => toggle(k)} /> {k}
          </label>
        ))}
        <h3>SMTP</h3>
        <input className="input" placeholder="host" value={tenant.smtp_host || ""} onChange={(e) => setTenant({ ...tenant, smtp_host: e.target.value })} />
        <input className="input" placeholder="from" value={tenant.smtp_from || ""} onChange={(e) => setTenant({ ...tenant, smtp_from: e.target.value })} />
        <input className="input" placeholder="NVD API key" value={tenant.nvd_api_key || ""} onChange={(e) => setTenant({ ...tenant, nvd_api_key: e.target.value })} />
        <button className="btn" onClick={save}>
          {t("save")}
        </button>
        <h3>Backup / Restore</h3>
        <button className="btn secondary" onClick={backup}>
          Backup tenant
        </button>
        <label className="btn secondary">
          Restore
          <input hidden type="file" accept=".zip" onChange={(e) => e.target.files?.[0] && restore(e.target.files[0])} />
        </label>
      </div>
    </Shell>
  );
}
