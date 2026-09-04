"use client";

import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { useApp } from "@/components/AppProvider";

export default function PlatformPage() {
  const { t, user } = useApp();
  const [settings, setSettings] = useState<any>(null);
  const [tenants, setTenants] = useState<any[]>([]);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");

  useEffect(() => {
    if (!user?.is_platform_admin) return;
    api("/api/platform/settings/").then(setSettings).catch(console.error);
    api<any>("/api/platform/tenants/").then((d) => setTenants(d.results || d)).catch(console.error);
  }, [user]);

  if (!user?.is_platform_admin) {
    return (
      <Shell>
        <p>Forbidden</p>
      </Shell>
    );
  }

  async function saveSettings() {
    setSettings(await api("/api/platform/settings/", { method: "PATCH", json: settings }));
  }

  async function createTenant() {
    const tnt = await api("/api/platform/tenants/", { method: "POST", json: { name, slug } });
    setTenants((x) => [...x, tnt]);
    setName("");
    setSlug("");
  }

  return (
    <Shell>
      <h1 style={{ marginTop: 0 }}>SVDB — {t("platform")}</h1>
      {settings && (
        <div className="panel" style={{ marginBottom: "1rem", display: "grid", gap: "0.5rem", maxWidth: 640 }}>
          <h3>Global kill-switches</h3>
          {Object.keys(settings)
            .filter((k) => k.startsWith("kill_"))
            .map((k) => (
              <label key={k}>
                <input
                  type="checkbox"
                  checked={!!settings[k]}
                  onChange={() => setSettings({ ...settings, [k]: !settings[k] })}
                />{" "}
                {k}
              </label>
            ))}
          <button className="btn" onClick={saveSettings}>
            {t("save")}
          </button>
        </div>
      )}
      <div className="panel">
        <h3>Tenants</h3>
        <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.75rem" }}>
          <input className="input" placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
          <input className="input" placeholder="slug" value={slug} onChange={(e) => setSlug(e.target.value)} />
          <button className="btn" onClick={createTenant}>
            {t("create")}
          </button>
        </div>
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Slug</th>
              <th>Active</th>
            </tr>
          </thead>
          <tbody>
            {tenants.map((tn) => (
              <tr key={tn.id}>
                <td>{tn.name}</td>
                <td>{tn.slug}</td>
                <td>{tn.is_active ? "yes" : "no"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
