"use client";

import { FormEvent, useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { api, getToken, getTenantId } from "@/lib/api";
import { useApp } from "@/components/AppProvider";

export default function AssetsPage() {
  const { t, user } = useApp();
  const [items, setItems] = useState<any[]>([]);
  const [groupBy, setGroupBy] = useState("business_system");
  const [grouped, setGrouped] = useState<any>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [count, setCount] = useState(0);
  const [types, setTypes] = useState<any[]>([]);
  const [systems, setSystems] = useState<any[]>([]);
  const [contours, setContours] = useState<any[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    name: "",
    asset_type: "",
    status: "in_service",
    ip_address: "",
    fqdn: "",
    os_platform: "Linux",
    environment: "prod",
    criticality: "Medium",
    business_system: "",
    inventory_number: "",
    location: "",
    contour: "",
    commissioned_at: new Date().toISOString().slice(0, 10),
    description: "",
  });
  const [msg, setMsg] = useState("");

  async function reload() {
    const d = await api<any>(`/api/assets/?page=${page}&page_size=${pageSize}`);
    setItems(d.results || []);
    setCount(d.count || 0);
    setGrouped(await api(`/api/assets/grouped/?by=${groupBy}`));
  }

  useEffect(() => {
    reload().catch(console.error);
    api<any>("/api/assets/types/").then((d) => setTypes(d.results || [])).catch(console.error);
    api<any>("/api/assets/systems/").then((d) => setSystems(d.results || [])).catch(console.error);
    api<any>("/api/tenants/contours/").then((d) => setContours(d.results || [])).catch(console.error);
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
    await reload();
  }

  async function createAsset(e: FormEvent) {
    e.preventDefault();
    try {
      const ownerId = user?.id;
      await api("/api/assets/", {
        method: "POST",
        json: {
          ...form,
          asset_type: Number(form.asset_type),
          business_system: Number(form.business_system),
          contour: Number(form.contour),
          owner: ownerId,
          security_officer: ownerId,
        },
      });
      setShowForm(false);
      setMsg("Created");
      await reload();
    } catch (err: any) {
      setMsg(String(err.message || err));
    }
  }

  return (
    <Shell>
      <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "0.75rem" }}>
        <h1 style={{ marginTop: 0 }}>{t("assets")}</h1>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <button className="btn" onClick={() => setShowForm((v) => !v)}>
            {t("create")}
          </button>
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
      {msg && <p className="muted">{msg}</p>}
      {showForm && (
        <form className="panel" onSubmit={createAsset} style={{ display: "grid", gap: "0.5rem", marginBottom: "1rem", gridTemplateColumns: "repeat(auto-fit,minmax(200px,1fr))" }}>
          {(["name", "ip_address", "fqdn", "os_platform", "inventory_number", "location"] as const).map((k) => (
            <input key={k} className="input" required placeholder={k} value={(form as any)[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} />
          ))}
          <select className="select" required value={form.asset_type} onChange={(e) => setForm({ ...form, asset_type: e.target.value })}>
            <option value="">Type</option>
            {types.map((x) => (
              <option key={x.id} value={x.id}>
                {x.name}
              </option>
            ))}
          </select>
          <select className="select" required value={form.business_system} onChange={(e) => setForm({ ...form, business_system: e.target.value })}>
            <option value="">System</option>
            {systems.map((x) => (
              <option key={x.id} value={x.id}>
                {x.name}
              </option>
            ))}
          </select>
          <select className="select" required value={form.contour} onChange={(e) => setForm({ ...form, contour: e.target.value })}>
            <option value="">Contour</option>
            {contours.map((x) => (
              <option key={x.id} value={x.id}>
                {x.name}
              </option>
            ))}
          </select>
          <select className="select" value={form.environment} onChange={(e) => setForm({ ...form, environment: e.target.value })}>
            <option value="prod">prod</option>
            <option value="stage">stage</option>
            <option value="dev">dev</option>
            <option value="test">test</option>
          </select>
          <select className="select" value={form.criticality} onChange={(e) => setForm({ ...form, criticality: e.target.value })}>
            <option>Critical</option>
            <option>High</option>
            <option>Medium</option>
            <option>Low</option>
            <option>Info</option>
          </select>
          <input className="input" type="date" value={form.commissioned_at} onChange={(e) => setForm({ ...form, commissioned_at: e.target.value })} />
          <button className="btn" type="submit">
            {t("save")}
          </button>
        </form>
      )}
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
