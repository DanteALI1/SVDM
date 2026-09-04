"use client";

import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { api, getToken, getTenantId } from "@/lib/api";
import { useApp } from "@/components/AppProvider";

type Tab = "flags" | "users" | "calendar" | "sso" | "sync" | "audit" | "branding" | "backup" | "policy";

export default function AdminPage() {
  const { t } = useApp();
  const [tab, setTab] = useState<Tab>("flags");
  const [tenant, setTenant] = useState<any>(null);
  const [members, setMembers] = useState<any[]>([]);
  const [calendar, setCalendar] = useState<any>(null);
  const [schedules, setSchedules] = useState<any[]>([]);
  const [audit, setAudit] = useState<any[]>([]);
  const [errors, setErrors] = useState<any[]>([]);
  const [policy, setPolicy] = useState<any>(null);
  const [msg, setMsg] = useState("");
  const [invite, setInvite] = useState({ username: "", email: "", password: "SecurePass1!", role: "reader" });

  async function load() {
    const tn = await api("/api/tenants/current/");
    setTenant(tn);
    setMembers((await api<any>("/api/tenants/memberships/")).results || []);
    setCalendar(await api("/api/tenants/calendar/"));
    setPolicy(await api("/api/tenants/password-policy/"));
    try {
      setSchedules((await api<any>("/api/vulnerabilities/sync/schedules/")).results || []);
    } catch {
      setSchedules([]);
    }
    try {
      setAudit((await api<any>("/api/audit/logs/")).results || []);
    } catch {
      setAudit([]);
    }
    try {
      setErrors((await api<any>("/api/core/errors/")).results || []);
    } catch {
      setErrors([]);
    }
  }

  useEffect(() => {
    load().catch((e) => setMsg(String(e.message || e)));
  }, []);

  async function saveTenant() {
    setTenant(await api("/api/tenants/current/", { method: "PATCH", json: tenant }));
    setMsg("Saved");
  }

  async function inviteUser() {
    await api("/api/tenants/memberships/invite/", { method: "POST", json: invite });
    setMsg("User invited");
    await load();
  }

  async function saveCalendar() {
    setCalendar(await api("/api/tenants/calendar/", { method: "PATCH", json: calendar }));
    setMsg("Calendar saved");
  }

  async function uploadBrand(kind: "logo" | "favicon", file: File) {
    const fd = new FormData();
    fd.append(kind, file);
    const res = await fetch("/api/tenants/branding/", {
      method: "POST",
      headers: { Authorization: `Token ${getToken()}`, "X-Tenant-ID": getTenantId() },
      body: fd,
    });
    setTenant(await res.json());
    setMsg(`${kind} uploaded`);
  }

  async function upsertSchedule(source: string) {
    const existing = schedules.find((s) => s.source === source);
    if (existing) {
      await api(`/api/vulnerabilities/sync/schedules/${existing.id}/`, {
        method: "PATCH",
        json: { enabled: !existing.enabled, interval_hours: existing.interval_hours || 24 },
      });
    } else {
      await api("/api/vulnerabilities/sync/schedules/", {
        method: "POST",
        json: { source, enabled: true, interval_hours: 24, days_of_week: [0, 1, 2, 3, 4] },
      });
    }
    await load();
  }

  async function testSso() {
    const r = await api<any>("/api/auth/sso/test/", { method: "POST", json: {} });
    setMsg(JSON.stringify(r));
  }

  async function backup() {
    const res = await fetch("/api/backup/export/", {
      method: "POST",
      headers: { Authorization: `Token ${getToken()}`, "X-Tenant-ID": getTenantId() },
    });
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
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

  const tabs: { id: Tab; label: string }[] = [
    { id: "flags", label: "Flags" },
    { id: "users", label: "Users" },
    { id: "policy", label: "Password" },
    { id: "calendar", label: "SLA calendar" },
    { id: "sso", label: "SSO" },
    { id: "sync", label: "Sync" },
    { id: "audit", label: "Audit" },
    { id: "branding", label: "Branding" },
    { id: "backup", label: "Backup" },
  ];

  return (
    <Shell>
      <div className="page-header">
        <div>
          <h1>{t("admin")}</h1>
          <p className="subtitle">Tenant configuration & security controls</p>
        </div>
      </div>
      {msg && <p className="muted">{msg}</p>}
      <div className="page-actions" style={{ marginBottom: "1rem" }}>
        {tabs.map((x) => (
          <button key={x.id} className={`btn ${tab === x.id ? "" : "secondary"}`} onClick={() => setTab(x.id)}>
            {x.label}
          </button>
        ))}
      </div>

      {tab === "flags" && (
        <div className="panel" style={{ display: "grid", gap: "0.55rem", maxWidth: 720 }}>
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
            <label key={k}>
              <input type="checkbox" checked={!!tenant[k]} onChange={() => setTenant({ ...tenant, [k]: !tenant[k] })} /> {k}
            </label>
          ))}
          <input className="input" placeholder="SMTP host" value={tenant.smtp_host || ""} onChange={(e) => setTenant({ ...tenant, smtp_host: e.target.value })} />
          <input className="input" placeholder="SMTP from" value={tenant.smtp_from || ""} onChange={(e) => setTenant({ ...tenant, smtp_from: e.target.value })} />
          <input className="input" placeholder="NVD API key" value={tenant.nvd_api_key || ""} onChange={(e) => setTenant({ ...tenant, nvd_api_key: e.target.value })} />
          <button className="btn" onClick={saveTenant}>
            {t("save")}
          </button>
        </div>
      )}

      {tab === "users" && (
        <div className="panel">
          <h3>Invite / create user</h3>
          <div style={{ display: "grid", gap: "0.5rem", maxWidth: 480, marginBottom: "1rem" }}>
            <input className="input" placeholder="username" value={invite.username} onChange={(e) => setInvite({ ...invite, username: e.target.value })} />
            <input className="input" placeholder="email" value={invite.email} onChange={(e) => setInvite({ ...invite, email: e.target.value })} />
            <input className="input" type="password" placeholder="password" value={invite.password} onChange={(e) => setInvite({ ...invite, password: e.target.value })} />
            <select className="select" value={invite.role} onChange={(e) => setInvite({ ...invite, role: e.target.value })}>
              <option value="admin">admin</option>
              <option value="analyst">analyst</option>
              <option value="wiki_editor">wiki_editor</option>
              <option value="asset_owner">asset_owner</option>
              <option value="reader">reader</option>
            </select>
            <button className="btn" onClick={inviteUser}>
              Invite
            </button>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>User</th>
                <th>Role</th>
                <th>Active</th>
              </tr>
            </thead>
            <tbody>
              {members.map((m) => (
                <tr key={m.id}>
                  <td>{m.username}</td>
                  <td>{m.role}</td>
                  <td>{m.is_active ? "yes" : "no"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "policy" && policy && (
        <div className="panel" style={{ display: "grid", gap: "0.5rem", maxWidth: 480 }}>
          <label>Min length</label>
          <input
            className="input"
            type="number"
            value={policy.min_length}
            onChange={(e) => setPolicy({ ...policy, min_length: Number(e.target.value) })}
          />
          {(["require_upper", "require_lower", "require_digit", "require_special"] as const).map((k) => (
            <label key={k}>
              <input type="checkbox" checked={!!policy[k]} onChange={() => setPolicy({ ...policy, [k]: !policy[k] })} /> {k}
            </label>
          ))}
          <label>Max failed attempts</label>
          <input
            className="input"
            type="number"
            value={policy.max_failed_attempts}
            onChange={(e) => setPolicy({ ...policy, max_failed_attempts: Number(e.target.value) })}
          />
          <label>Lockout minutes</label>
          <input
            className="input"
            type="number"
            value={policy.lockout_minutes}
            onChange={(e) => setPolicy({ ...policy, lockout_minutes: Number(e.target.value) })}
          />
          <label>Session idle minutes</label>
          <input
            className="input"
            type="number"
            value={tenant.session_idle_minutes}
            onChange={(e) => setTenant({ ...tenant, session_idle_minutes: Number(e.target.value) })}
          />
          <label>Audit retention days</label>
          <input
            className="input"
            type="number"
            value={tenant.audit_retention_days}
            onChange={(e) => setTenant({ ...tenant, audit_retention_days: Number(e.target.value) })}
          />
          <button
            className="btn"
            onClick={async () => {
              setPolicy(await api("/api/tenants/password-policy/", { method: "PATCH", json: policy }));
              await saveTenant();
              setMsg("Policy saved");
            }}
          >
            {t("save")}
          </button>
        </div>
      )}

      {tab === "calendar" && calendar && (
        <div className="panel" style={{ display: "grid", gap: "0.5rem", maxWidth: 520 }}>
          <label>Workday start</label>
          <input className="input" value={String(calendar.workday_start).slice(0, 5)} onChange={(e) => setCalendar({ ...calendar, workday_start: e.target.value })} />
          <label>Workday end</label>
          <input className="input" value={String(calendar.workday_end).slice(0, 5)} onChange={(e) => setCalendar({ ...calendar, workday_end: e.target.value })} />
          <label>Workdays (0=Mon … 6=Sun), comma-separated</label>
          <input
            className="input"
            value={(calendar.workdays || []).join(",")}
            onChange={(e) =>
              setCalendar({
                ...calendar,
                workdays: e.target.value
                  .split(",")
                  .map((x: string) => Number(x.trim()))
                  .filter((n: number) => !Number.isNaN(n)),
              })
            }
          />
          <label>Exceptions JSON [{"{"}date, is_working{"}"}]</label>
          <textarea
            className="input"
            rows={4}
            value={JSON.stringify(calendar.exceptions || [], null, 2)}
            onChange={(e) => {
              try {
                setCalendar({ ...calendar, exceptions: JSON.parse(e.target.value) });
              } catch {
                /* ignore while typing */
              }
            }}
          />
          <button className="btn" onClick={saveCalendar}>
            {t("save")}
          </button>
        </div>
      )}

      {tab === "sso" && (
        <div className="panel" style={{ display: "grid", gap: "0.5rem", maxWidth: 640 }}>
          <label>
            <input type="checkbox" checked={!!tenant.feature_sso} onChange={() => setTenant({ ...tenant, feature_sso: !tenant.feature_sso })} /> feature_sso
          </label>
          <select className="select" value={tenant.sso_provider || ""} onChange={(e) => setTenant({ ...tenant, sso_provider: e.target.value })}>
            <option value="">None</option>
            <option value="oidc">OIDC</option>
            <option value="saml">SAML</option>
            <option value="ldap">LDAP</option>
            <option value="ad">Active Directory</option>
          </select>
          <textarea
            className="input"
            rows={10}
            value={JSON.stringify(tenant.sso_config || {}, null, 2)}
            onChange={(e) => {
              try {
                setTenant({ ...tenant, sso_config: JSON.parse(e.target.value) });
              } catch {
                /* typing */
              }
            }}
          />
          <p className="muted">OIDC: client_id, client_secret, authorize_url, token_url, userinfo_url. LDAP/AD: server, base_dn, domain. SAML: idp_sso_url, idp_x509_cert.</p>
          <button className="btn" onClick={saveTenant}>
            {t("save")}
          </button>
          <button className="btn secondary" onClick={testSso}>
            Test config
          </button>
        </div>
      )}

      {tab === "sync" && (
        <div className="panel">
          <p className="muted">Celery Beat runs schedules every 15 minutes.</p>
          {["nvd", "kev"].map((src) => {
            const s = schedules.find((x) => x.source === src);
            return (
              <div key={src} style={{ display: "flex", gap: "0.75rem", alignItems: "center", marginBottom: "0.5rem" }}>
                <strong>{src.toUpperCase()}</strong>
                <span className="muted">{s ? `enabled=${s.enabled} every ${s.interval_hours || 24}h` : "not configured"}</span>
                <button className="btn secondary" onClick={() => upsertSchedule(src)}>
                  {s?.enabled ? "Disable" : "Enable 24h"}
                </button>
              </div>
            );
          })}
        </div>
      )}

      {tab === "audit" && (
        <div className="panel">
          <h3>Audit log</h3>
          <table className="table">
            <thead>
              <tr>
                <th>When</th>
                <th>User</th>
                <th>Action</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {audit.slice(0, 50).map((a) => (
                <tr key={a.id}>
                  <td>{a.created_at}</td>
                  <td>{a.username || "—"}</td>
                  <td>{a.action}</td>
                  <td>{a.status_code}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <h3>Error journal</h3>
          <table className="table">
            <thead>
              <tr>
                <th>When</th>
                <th>Category</th>
                <th>Message</th>
              </tr>
            </thead>
            <tbody>
              {errors.slice(0, 50).map((e) => (
                <tr key={e.id}>
                  <td>{e.created_at}</td>
                  <td>{e.category}</td>
                  <td>{e.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "branding" && (
        <div className="panel" style={{ display: "grid", gap: "0.5rem", maxWidth: 480 }}>
          <input className="input" value={tenant.primary_color} onChange={(e) => setTenant({ ...tenant, primary_color: e.target.value })} />
          <input className="input" value={tenant.accent_color} onChange={(e) => setTenant({ ...tenant, accent_color: e.target.value })} />
          <button className="btn" onClick={saveTenant}>
            {t("save")} colors
          </button>
          <label className="btn secondary">
            Upload logo
            <input hidden type="file" accept="image/*" onChange={(e) => e.target.files?.[0] && uploadBrand("logo", e.target.files[0])} />
          </label>
          <label className="btn secondary">
            Upload favicon
            <input hidden type="file" accept="image/*,.ico" onChange={(e) => e.target.files?.[0] && uploadBrand("favicon", e.target.files[0])} />
          </label>
        </div>
      )}

      {tab === "backup" && (
        <div className="panel" style={{ display: "flex", gap: "0.5rem" }}>
          <button className="btn" onClick={backup}>
            Backup tenant
          </button>
          <label className="btn secondary">
            Restore
            <input hidden type="file" accept=".zip" onChange={(e) => e.target.files?.[0] && restore(e.target.files[0])} />
          </label>
        </div>
      )}
    </Shell>
  );
}
