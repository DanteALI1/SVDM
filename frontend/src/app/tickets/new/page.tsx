"use client";

import { FormEvent, Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { useApp } from "@/components/AppProvider";

function NewTicketForm() {
  const { t } = useApp();
  const router = useRouter();
  const sp = useSearchParams();
  const [title, setTitle] = useState(sp.get("title") || "");
  const [ticketType, setTicketType] = useState("vulnerability");
  const [goal, setGoal] = useState("resolve");
  const [vulnId, setVulnId] = useState(sp.get("vuln") || "");
  const [assets, setAssets] = useState<any[]>([]);
  const [assetIds, setAssetIds] = useState<number[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api<any>("/api/assets/?page_size=50").then((d) => setAssets(d.results || []));
  }, []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    try {
      const data = await api<any>("/api/tickets/", {
        method: "POST",
        json: {
          title,
          ticket_type: ticketType,
          goal,
          vulnerability_ids: vulnId ? [Number(vulnId)] : [],
          asset_ids: assetIds,
        },
      });
      router.push(`/tickets/${data.id}`);
    } catch (err: any) {
      setError(String(err.message || err));
    }
  }

  return (
    <>
      <h1 style={{ marginTop: 0 }}>
        {t("create")} — {t("tickets")}
      </h1>
      <form className="panel" onSubmit={submit} style={{ display: "grid", gap: "0.65rem", maxWidth: 640 }}>
        <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Title" required />
        <select className="select" value={ticketType} onChange={(e) => setTicketType(e.target.value)}>
          <option value="vulnerability">vulnerability</option>
          <option value="incident">incident</option>
          <option value="change">change</option>
          <option value="general">general</option>
        </select>
        <select className="select" value={goal} onChange={(e) => setGoal(e.target.value)}>
          <option value="resolve">resolve</option>
          <option value="inform">inform</option>
        </select>
        <input className="input" value={vulnId} onChange={(e) => setVulnId(e.target.value)} placeholder="Vulnerability ID" />
        <select
          className="select"
          multiple
          value={assetIds.map(String)}
          onChange={(e) => setAssetIds(Array.from(e.target.selectedOptions).map((o) => Number(o.value)))}
          style={{ minHeight: 120 }}
        >
          {assets.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name} ({a.fqdn})
            </option>
          ))}
        </select>
        {error && <p style={{ color: "var(--svdb-danger)" }}>{error}</p>}
        <button className="btn" type="submit">
          {t("save")}
        </button>
      </form>
    </>
  );
}

export default function NewTicketPage() {
  return (
    <Shell>
      <Suspense fallback={<p>Loading…</p>}>
        <NewTicketForm />
      </Suspense>
    </Shell>
  );
}
