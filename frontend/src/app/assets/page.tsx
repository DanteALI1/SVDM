"use client";

import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { api, getToken, getTenantId } from "@/lib/api";
import { useApp } from "@/components/AppProvider";

export default function AssetsPage() {
  const { t } = useApp();
  const [items, setItems] = useState<any[]>([]);
  const [groupBy, setGroupBy] = useState("business_system");
  const [grouped, setGrouped] = useState<any>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [count, setCount] = useState(0);

  useEffect(() => {
    api<any>(`/api/assets/?page=${page}&page_size=${pageSize}`)
      .then((d) => {
        setItems(d.results || []);
        setCount(d.count || 0);
      })
      .catch(console.error);
    api(`/api/assets/grouped/?by=${groupBy}`).then(setGrouped).catch(console.error);
  }, [page, pageSize, groupBy]);

  async function importFile(file: File, kind: "csv" | "excel") {
    const fd = new FormData();
    fd.append("file", file);
    await fetch(`/api/assets/${kind === "csv" ? "import_csv" : "import_excel"}/`, {
      method: "POST",
      headers: { Authorization: `Token ${getToken()}`, "X-Tenant-ID": getTenantId() },
      body: fd,
    });
    setPage(1);
    const d = await api<any>(`/api/assets/?page=1&page_size=${pageSize}`);
    setItems(d.results || []);
    setCount(d.count || 0);
  }

  return (
    <Shell>
      <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "0.75rem" }}>
        <h1 style={{ marginTop: 0 }}>{t("assets")}</h1>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <select className="select" style={{ width: "auto" }} value={groupBy} onChange={(e) => setGroupBy(e.target.value)}>
            <option value="business_system">System</option>
            <option value="type">Type</option>
            <option value="owner">Owner</option>
            <option value="environment">Environment</option>
          </select>
          <label className="btn secondary">
            Import CSV
            <input hidden type="file" accept=".csv" onChange={(e) => e.target.files?.[0] && importFile(e.target.files[0], "csv")} />
          </label>
          <label className="btn secondary">
            Import Excel
            <input hidden type="file" accept=".xlsx,.xls" onChange={(e) => e.target.files?.[0] && importFile(e.target.files[0], "excel")} />
          </label>
        </div>
      </div>
      {grouped && (
        <div className="panel" style={{ marginBottom: "1rem" }}>
          <h3 style={{ marginTop: 0 }}>
            {grouped.tenant} → {groupBy}
          </h3>
          {Object.entries(grouped.groups || {}).map(([k, arr]: any) => (
            <div key={k} style={{ marginBottom: "0.5rem" }}>
              <strong>{k}</strong> <span className="muted">({arr.length})</span>
            </div>
          ))}
        </div>
      )}
      <div className="panel">
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>IP</th>
              <th>FQDN</th>
              <th>Type</th>
              <th>Env</th>
              <th>Criticality</th>
              <th>System</th>
            </tr>
          </thead>
          <tbody>
            {items.map((a) => (
              <tr key={a.id}>
                <td>{a.name}</td>
                <td>{a.ip_address}</td>
                <td>{a.fqdn}</td>
                <td>{a.asset_type_name}</td>
                <td>{a.environment}</td>
                <td>{a.criticality}</td>
                <td>{a.business_system_name}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="pager">
          <select className="select" style={{ width: 80 }} value={pageSize} onChange={(e) => setPageSize(Number(e.target.value))}>
            <option value={25}>25</option>
            <option value={50}>50</option>
          </select>
          <button className="btn secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            ‹
          </button>
          <span>
            {page} / {Math.max(1, Math.ceil(count / pageSize))}
          </span>
          <button className="btn secondary" disabled={page * pageSize >= count} onClick={() => setPage((p) => p + 1)}>
            ›
          </button>
        </div>
      </div>
    </Shell>
  );
}
