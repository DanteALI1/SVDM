"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Shell } from "@/components/Shell";
import { api, getToken, getTenantId } from "@/lib/api";
import { useApp } from "@/components/AppProvider";

export default function TicketDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { t } = useApp();
  const [ticket, setTicket] = useState<any>(null);
  const [comment, setComment] = useState("");
  const [msg, setMsg] = useState("");

  async function load() {
    setTicket(await api(`/api/tickets/${id}/`));
  }

  useEffect(() => {
    load().catch(console.error);
  }, [id]);

  async function setStatus(status: string) {
    await api(`/api/tickets/${id}/`, { method: "PATCH", json: { status } });
    await load();
  }

  async function addComment() {
    await api(`/api/tickets/${id}/comments/`, { method: "POST", json: { body: comment } });
    setComment("");
    await load();
  }

  async function attach(file: File) {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`/api/tickets/${id}/attach/`, {
      method: "POST",
      headers: { Authorization: `Token ${getToken()}`, "X-Tenant-ID": getTenantId() },
      body: fd,
    });
    setMsg(res.ok ? "Attached" : await res.text());
    await load();
  }

  if (!ticket) {
    return (
      <Shell>
        <p>Loading…</p>
      </Shell>
    );
  }

  return (
    <Shell>
      <h1 style={{ marginTop: 0 }}>
        #{ticket.id} {ticket.title}
      </h1>
      <p className="muted">
        {ticket.ticket_type} · {ticket.goal} · {ticket.status} · {ticket.priority}
        {ticket.is_overdue ? " · OVERDUE" : ""}
        {ticket.sla_deadline ? ` · SLA ${ticket.sla_deadline}` : ""}
      </p>
      {msg && <p className="muted">{msg}</p>}
      {ticket.duplicate_warning?.length > 0 && (
        <div className="panel" style={{ borderColor: "var(--svdb-danger)", marginBottom: "1rem" }}>
          Duplicate warning: {JSON.stringify(ticket.duplicate_warning)}
        </div>
      )}
      <div className="panel" style={{ marginBottom: "1rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
        <button className="btn secondary" onClick={() => setStatus("in_progress")}>
          in_progress
        </button>
        <button className="btn secondary" onClick={() => setStatus("for_review")}>
          for_review
        </button>
        <button className="btn secondary" onClick={() => setStatus("on_check")}>
          on_check
        </button>
        <button className="btn secondary" onClick={() => setStatus("rework")}>
          rework
        </button>
        <button className="btn" onClick={() => setStatus("closed")}>
          closed
        </button>
      </div>
      <div className="panel" style={{ marginBottom: "1rem" }}>
        <h3>Attachments</h3>
        <label className="btn secondary">
          Upload
          <input hidden type="file" onChange={(e) => e.target.files?.[0] && attach(e.target.files[0])} />
        </label>
      </div>
      <div className="panel" style={{ marginBottom: "1rem" }}>
        <h3>{t("save")} comment</h3>
        <textarea className="input" rows={3} value={comment} onChange={(e) => setComment(e.target.value)} />
        <button className="btn" style={{ marginTop: "0.5rem" }} onClick={addComment}>
          Comment
        </button>
        <ul>
          {(ticket.comments || []).map((c: any) => (
            <li key={c.id}>
              <strong>{c.author_username}</strong>: {c.body}
            </li>
          ))}
        </ul>
      </div>
    </Shell>
  );
}
