"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { useApp } from "@/components/AppProvider";

function severityClass(sev: string | undefined) {
  const s = String(sev || "").toLowerCase();
  if (s.includes("critical")) return "critical";
  if (s.includes("high")) return "high";
  if (s.includes("medium")) return "medium";
  if (s.includes("low")) return "low";
  return "";
}

export default function DashboardPage() {
  const { t } = useApp();
  const [data, setData] = useState<any>(null);
  const [updates, setUpdates] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/api/dashboard/")
      .then(setData)
      .catch((e) => setError(String(e.message || e)));
    api("/api/dashboard/updates/")
      .then(setUpdates)
      .catch(() => setUpdates(null));
  }, []);

  return (
    <Shell>
      <div className="page-header">
        <div>
          <h1>{t("dashboard")}</h1>
          <p className="subtitle">
            {t("dashboardWelcome")}
            {updates?.enabled
              ? ` · v${updates.current_version}${updates.update_available ? ` · ${updates.notes}` : " · up to date"}`
              : ""}
          </p>
        </div>
        <div className="page-actions">
          <Link className="btn secondary" href="/vulnerabilities">
            {t("vulnerabilities")}
          </Link>
          <Link className="btn" href="/tickets/new">
            + {t("create")}
          </Link>
        </div>
      </div>

      {error && <p style={{ color: "var(--svdb-danger)" }}>{error}</p>}

      {data && (
        <>
          <div className="grid-stats">
            <div className="stat tone-critical">
              <span className="stat-label">{t("critical")}</span>
              <strong>{data.critical_vulnerabilities}</strong>
              <div className="stat-meta up">{t("severityFocus")}</div>
            </div>
            <div className="stat tone-high" style={{ animationDelay: "0.05s" }}>
              <span className="stat-label">{t("high")}</span>
              <strong>{data.high_vulnerabilities}</strong>
              <div className="stat-meta up">{t("severityFocus")}</div>
            </div>
            <div className="stat" style={{ animationDelay: "0.1s" }}>
              <span className="stat-label">{t("kev")}</span>
              <strong>{data.kev_total}</strong>
              <div className="stat-meta neutral">CISA KEV</div>
            </div>
            <div className="stat" style={{ animationDelay: "0.15s" }}>
              <span className="stat-label">{t("openTickets")}</span>
              <strong>{data.open_tickets}</strong>
              <div className="stat-meta neutral">{t("tickets")}</div>
            </div>
            <div className="stat" style={{ animationDelay: "0.2s" }}>
              <span className="stat-label">{t("overdue")}</span>
              <strong>{data.overdue_sla}</strong>
              <div className="stat-meta up">SLA</div>
            </div>
          </div>

          <div className="dash-grid">
            <div className="dash-stack">
              <div className="panel">
                <div className="panel-head">
                  <h3>{t("topVulns")}</h3>
                  <Link className="link" href="/vulnerabilities">
                    {t("viewAll")}
                  </Link>
                </div>
                <table className="table">
                  <thead>
                    <tr>
                      <th>CVE / BDU</th>
                      <th>CVSS</th>
                      <th>{t("openTickets")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data.top_vulnerabilities_by_open_tickets || []).length === 0 && (
                      <tr>
                        <td colSpan={3} className="muted">
                          —
                        </td>
                      </tr>
                    )}
                    {(data.top_vulnerabilities_by_open_tickets || []).map((v: any) => (
                      <tr key={v.id}>
                        <td>
                          <Link href={`/vulnerabilities/${v.id}`}>{v.cve_id || v.bdu_id || `#${v.id}`}</Link>
                        </td>
                        <td>
                          <span className={`badge ${severityClass(String(v.max_cvss >= 9 ? "critical" : v.max_cvss >= 7 ? "high" : "medium"))}`}>
                            {v.max_cvss ?? "—"}
                          </span>
                        </td>
                        <td>{v.open_ticket_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="dash-stack">
              <div className="panel">
                <div className="panel-head">
                  <h3>{t("severityMix")}</h3>
                </div>
                <div style={{ display: "grid", gap: "0.75rem" }}>
                  {[
                    { label: t("critical"), value: data.critical_vulnerabilities, cls: "critical" },
                    { label: t("high"), value: data.high_vulnerabilities, cls: "high" },
                    { label: t("kev"), value: data.kev_total, cls: "info" },
                    { label: t("openTickets"), value: data.open_tickets, cls: "warn" },
                  ].map((row) => {
                    const total =
                      Number(data.critical_vulnerabilities || 0) +
                      Number(data.high_vulnerabilities || 0) +
                      Number(data.kev_total || 0) +
                      Number(data.open_tickets || 0) || 1;
                    const pct = Math.min(100, Math.round((Number(row.value || 0) / total) * 100));
                    return (
                      <div key={row.label}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                          <span className={`badge ${row.cls}`}>{row.label}</span>
                          <strong>{row.value}</strong>
                        </div>
                        <div
                          style={{
                            height: 8,
                            borderRadius: 999,
                            background: "var(--svdb-surface)",
                            overflow: "hidden",
                          }}
                        >
                          <div
                            style={{
                              width: `${pct}%`,
                              height: "100%",
                              borderRadius: 999,
                              background: "var(--svdb-primary)",
                              transition: "width 0.4s ease",
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="panel">
                <div className="panel-head">
                  <h3>{t("recentSyncs")}</h3>
                </div>
                <table className="table">
                  <thead>
                    <tr>
                      <th>Source</th>
                      <th>When</th>
                      <th>OK</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data.recent_syncs || []).slice(0, 6).map((s: any) => (
                      <tr key={s.id}>
                        <td>{s.source}</td>
                        <td className="muted" style={{ fontSize: "0.8rem" }}>
                          {s.started_at}
                        </td>
                        <td>
                          <span className={`badge ${s.success ? "ok" : "critical"}`}>
                            {s.success ? "OK" : "ERR"}
                          </span>
                        </td>
                      </tr>
                    ))}
                    {(data.recent_syncs || []).length === 0 && (
                      <tr>
                        <td colSpan={3} className="muted">
                          —
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </>
      )}
    </Shell>
  );
}
