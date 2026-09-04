"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { useApp } from "@/components/AppProvider";

export default function TicketsPage() {
  const { t } = useApp();
  const [items, setItems] = useState<any[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [count, setCount] = useState(0);

  useEffect(() => {
    api<any>(`/api/tickets/?page=${page}&page_size=${pageSize}`)
      .then((d) => {
        setItems(d.results || []);
        setCount(d.count || 0);
      })
      .catch(console.error);
  }, [page, pageSize]);

  return (
    <Shell>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <h1 style={{ marginTop: 0 }}>{t("tickets")}</h1>
        <Link className="btn" href="/tickets/new">
          {t("create")}
        </Link>
      </div>
      <div className="panel">
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Title</th>
              <th>Type</th>
              <th>Goal</th>
              <th>Status</th>
              <th>Priority</th>
              <th>SLA</th>
            </tr>
          </thead>
          <tbody>
            {items.map((tkt) => (
              <tr key={tkt.id}>
                <td>
                  <Link href={`/tickets/${tkt.id}`}>#{tkt.id}</Link>
                </td>
                <td>{tkt.title}</td>
                <td>{tkt.ticket_type}</td>
                <td>{tkt.goal}</td>
                <td>{tkt.status}</td>
                <td>{tkt.priority}</td>
                <td style={{ color: tkt.is_overdue ? "var(--svdb-danger)" : undefined }}>
                  {tkt.sla_deadline || "—"}
                  {tkt.is_overdue ? " ⚠" : ""}
                </td>
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
          <span>{page}</span>
          <button className="btn secondary" disabled={page * pageSize >= count} onClick={() => setPage((p) => p + 1)}>
            ›
          </button>
        </div>
      </div>
    </Shell>
  );
}
