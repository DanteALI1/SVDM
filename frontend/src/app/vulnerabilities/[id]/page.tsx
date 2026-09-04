"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { useApp } from "@/components/AppProvider";

export default function VulnDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { t } = useApp();
  const router = useRouter();
  const [v, setV] = useState<any>(null);
  const [tab, setTab] = useState<"ru" | "en">("ru");

  useEffect(() => {
    api(`/api/vulnerabilities/items/${id}/`).then(setV).catch(console.error);
  }, [id]);

  if (!v) {
    return (
      <Shell>
        <p className="muted">Loading…</p>
      </Shell>
    );
  }

  return (
    <Shell>
      <h1 style={{ marginTop: 0 }}>{v.cve_id || v.bdu_id || `Vuln #${v.id}`}</h1>
      <p className="muted">
        max CVSS <strong>{v.max_cvss ?? "—"}</strong> · {v.severity} · sources: {(v.sources || []).join(", ")}
        {v.is_kev ? " · KEV" : ""}
      </p>
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.75rem" }}>
        <button className={`btn ${tab === "ru" ? "" : "secondary"}`} onClick={() => setTab("ru")}>
          RU (BDU)
        </button>
        <button className={`btn ${tab === "en" ? "" : "secondary"}`} onClick={() => setTab("en")}>
          EN (NVD)
        </button>
        <button
          className="btn"
          onClick={() =>
            router.push(
              `/tickets/new?cve=${encodeURIComponent(v.cve_id || "")}&vuln=${v.id}&title=${encodeURIComponent(
                `CVE ${v.cve_id || v.id}`
              )}`
            )
          }
        >
          {t("create")} ticket
        </button>
      </div>
      <div className="panel" style={{ marginBottom: "1rem", whiteSpace: "pre-wrap" }}>
        {tab === "ru" ? v.description_ru || v.description_en || "—" : v.description_en || "—"}
      </div>
      <div className="panel">
        <h3>CVSS</h3>
        <table className="table">
          <tbody>
            <tr>
              <td>v2</td>
              <td>{v.cvss_v2_score}</td>
              <td>{v.cvss_v2_vector}</td>
            </tr>
            <tr>
              <td>v3.0</td>
              <td>{v.cvss_v3_score}</td>
              <td>{v.cvss_v3_vector}</td>
            </tr>
            <tr>
              <td>v3.1</td>
              <td>{v.cvss_v31_score}</td>
              <td>{v.cvss_v31_vector}</td>
            </tr>
            <tr>
              <td>v4</td>
              <td>{v.cvss_v4_score}</td>
              <td>{v.cvss_v4_vector}</td>
            </tr>
          </tbody>
        </table>
        <p>
          Matching: CVE={v.cve_id || "—"} · BDU={v.bdu_id || "—"} · KEV={v.is_kev ? "yes" : "no"}
        </p>
        <p>
          Coverage: <strong>{v.coverage_status}</strong> · open tickets: {v.open_ticket_count}
        </p>
      </div>
    </Shell>
  );
}
