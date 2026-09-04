"use client";

import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { useApp } from "@/components/AppProvider";

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
      <h1 style={{ marginTop: 0 }}>SVDB — {t("dashboard")}</h1>
      {error && <p style={{ color: "var(--svdb-danger)" }}>{error}</p>}
      {updates?.enabled && (
        <p className="muted" style={{ marginTop: 0 }}>
          v{updates.current_version}
          {updates.update_available ? ` · ${updates.notes}` : " · up to date"}
        </p>
      )}
      {data && (
        <>
          <div className="grid-stats" style={{ marginBottom: "1rem" }}>
            <div className="stat">
              <span className="muted">{t("critical")}</span>
              <strong>{data.critical_vulnerabilities}</strong>
            </div>
            <div className="stat" style={{ animationDelay: "0.05s" }}>
              <span className="muted">{t("high")}</span>
              <strong>{data.high_vulnerabilities}</strong>
            </div>
            <div className="stat" style={{ animationDelay: "0.1s" }}>
              <span className="muted">{t("kev")}</span>
              <strong>{data.kev_total}</strong>
            </div>
            <div className="stat" style={{ animationDelay: "0.15s" }}>
              <span className="muted">{t("openTickets")}</span>
              <strong>{data.open_tickets}</strong>
            </div>
            <div className="stat" style={{ animationDelay: "0.2s" }}>
              <span className="muted">{t("overdue")}</span>
              <strong>{data.overdue_sla}</strong>
            </div>
          </div>
          <div className="panel" style={{ marginBottom: "1rem" }}>
            <h3 style={{ marginTop: 0 }}>{t("recentSyncs")}</h3>
            <table className="table">
              <thead>
                <tr>
                  <th>Source</th>
                  <th>When</th>
                  <th>Records</th>
                  <th>OK</th>
                </tr>
              </thead>
              <tbody>
                {(data.recent_syncs || []).map((s: any) => (
                  <tr key={s.id}>
                    <td>{s.source}</td>
                    <td>{s.started_at}</td>
                    <td>{s.records_processed}</td>
                    <td>{s.success ? "✓" : s.error_message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="panel">
            <h3 style={{ marginTop: 0 }}>{t("topVulns")}</h3>
            <table className="table">
              <thead>
                <tr>
                  <th>CVE</th>
                  <th>max CVSS</th>
                  <th>Open tickets</th>
                </tr>
              </thead>
              <tbody>
                {(data.top_vulnerabilities_by_open_tickets || []).map((v: any) => (
                  <tr key={v.id}>
                    <td>{v.cve_id || v.bdu_id}</td>
                    <td>{v.max_cvss}</td>
                    <td>{v.open_ticket_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Shell>
  );
}
