"use client";

import Link from "next/link";
import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Shell } from "@/components/Shell";
import { api, getToken, getTenantId } from "@/lib/api";
import { useApp } from "@/components/AppProvider";

function VulnerabilitiesInner() {
  const { t } = useApp();
  const sp = useSearchParams();
  const [items, setItems] = useState<any[]>([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [expanded, setExpanded] = useState(false);
  const [filters, setFilters] = useState({ search: sp.get("search") || "", severity: "", is_kev: "", min_cvss: "" });
  const [msg, setMsg] = useState("");

  async function load() {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (filters.search) params.set("search", filters.search);
    if (filters.severity) params.set("severity", filters.severity);
    if (filters.is_kev) params.set("is_kev", filters.is_kev);
    if (filters.min_cvss) params.set("min_cvss", filters.min_cvss);
    const data = await api<any>(`/api/vulnerabilities/items/?${params}`);
    setItems(data.results || []);
    setCount(data.count || 0);
  }

  useEffect(() => {
    const q = sp.get("search");
    if (q) setFilters((f) => ({ ...f, search: q }));
  }, [sp]);

  useEffect(() => {
    load().catch((e) => setMsg(String(e.message || e)));
  }, [page, pageSize]);

  async function sync(source: string) {
    setMsg("...");
    try {
      const j = await api<any>("/api/vulnerabilities/sync/trigger/", { method: "POST", json: { source } });
      setMsg(`${source}: ${j.records_processed} records, ok=${j.success}`);
      await load();
    } catch (e: any) {
      setMsg(String(e.message || e));
    }
  }

  async function uploadBdu(file: File) {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch("/api/vulnerabilities/sync/bdu-upload/", {
      method: "POST",
      headers: {
        Authorization: `Token ${getToken()}`,
        "X-Tenant-ID": getTenantId(),
      },
      body: fd,
    });
    const data = await res.json();
    setMsg(res.ok ? `BDU: ${data.records_processed}` : JSON.stringify(data));
    await load();
  }

  return (
    <Shell>
      <div className="page-header">
        <div>
          <h1>{t("vulnerabilities")}</h1>
          <p className="subtitle">{count} records</p>
        </div>
        <div className="page-actions">
          <button className="btn secondary" onClick={() => sync("nvd")}>
            {t("sync")} NVD
          </button>
          <button className="btn secondary" onClick={() => sync("kev")}>
            {t("sync")} KEV
          </button>
          <label className="btn secondary" style={{ cursor: "pointer" }}>
            {t("uploadBdu")}
            <input
              type="file"
              accept=".json,.xml,.xlsx,.xls"
              hidden
              onChange={(e) => e.target.files?.[0] && uploadBdu(e.target.files[0])}
            />
          </label>
          <a className="btn" href={`/api/vulnerabilities/items/export_csv/?page_size=50`} target="_blank">
            {t("exportCsv")}
          </a>
        </div>
      </div>
      {msg && <p className="muted">{msg}</p>}
      <div className={`panel filters ${expanded ? "" : "collapsed"}`} style={{ marginBottom: "1rem" }}>
        <div className="panel-head">
          <h3>{t("filters")}</h3>
          <button className="btn ghost" onClick={() => setExpanded((v) => !v)}>
            {expanded ? t("collapse") : t("expand")}
          </button>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))", gap: "0.5rem" }}>
          <input className="input" placeholder={t("search")} value={filters.search} onChange={(e) => setFilters({ ...filters, search: e.target.value })} />
          <select className="select" value={filters.severity} onChange={(e) => setFilters({ ...filters, severity: e.target.value })}>
            <option value="">Severity</option>
            <option>Critical</option>
            <option>High</option>
            <option>Medium</option>
            <option>Low</option>
          </select>
          <div className="extra">
            <select className="select" value={filters.is_kev} onChange={(e) => setFilters({ ...filters, is_kev: e.target.value })}>
              <option value="">KEV</option>
              <option value="true">Yes</option>
              <option value="false">No</option>
            </select>
          </div>
          <div className="extra">
            <input className="input" placeholder="min CVSS" value={filters.min_cvss} onChange={(e) => setFilters({ ...filters, min_cvss: e.target.value })} />
          </div>
        </div>
        <button className="btn" style={{ marginTop: "0.6rem" }} onClick={() => { setPage(1); load(); }}>
          Apply
        </button>
      </div>
      <div className="panel">
        <table className="table">
          <thead>
            <tr>
              <th>CVE</th>
              <th>BDU</th>
              <th>max CVSS</th>
              <th>Severity</th>
              <th>KEV</th>
              <th>Coverage</th>
            </tr>
          </thead>
          <tbody>
            {items.map((v) => (
              <tr key={v.id}>
                <td>
                  <Link href={`/vulnerabilities/${v.id}`}>{v.cve_id || "—"}</Link>
                </td>
                <td>{v.bdu_id || "—"}</td>
                <td>{v.max_cvss ?? "—"}</td>
                <td>
                  <span className={`badge ${String(v.severity).toLowerCase()}`}>{v.severity}</span>
                </td>
                <td>{v.is_kev ? "✓" : ""}</td>
                <td>{v.coverage_status}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="pager">
          <span className="muted">
            {count} · {t("pageSize")}
          </span>
          <select className="select" style={{ width: 80 }} value={pageSize} onChange={(e) => setPageSize(Number(e.target.value))}>
            <option value={25}>25</option>
            <option value={50}>50</option>
          </select>
          <button className="btn secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            ‹
          </button>
          <span>{page}</span>
          <button className="btn secondary" disabled={page * pageSize >= count} onClick={() => setPage((p) => p + 1)}>
            ›
          </button>
        </div>
      </div>
    </Shell>
  );
}

export default function VulnerabilitiesPage() {
  return (
    <Suspense
      fallback={
        <Shell>
          <p className="muted">Loading…</p>
        </Shell>
      }
    >
      <VulnerabilitiesInner />
    </Suspense>
  );
}
