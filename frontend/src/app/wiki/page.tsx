"use client";

import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { useApp } from "@/components/AppProvider";
import { marked } from "marked";

export default function WikiPage() {
  const { t } = useApp();
  const [spaces, setSpaces] = useState<any[]>([]);
  const [spaceId, setSpaceId] = useState<number | null>(null);
  const [tree, setTree] = useState<any[]>([]);
  const [view, setView] = useState<"spaces" | "tree">("spaces");
  const [page, setPage] = useState<any>(null);
  const [draft, setDraft] = useState({ title: "", slug: "", content_md: "" });
  const [wysiwyg, setWysiwyg] = useState(false);

  useEffect(() => {
    api<any>("/api/wiki/spaces/").then((d) => setSpaces(d.results || d || [])).catch(console.error);
  }, []);

  async function openSpace(id: number) {
    setSpaceId(id);
    setView("tree");
    const d = await api<any>(`/api/wiki/spaces/${id}/tree/`);
    setTree(d.tree || []);
  }

  async function openPage(id: number) {
    const p = await api(`/api/wiki/pages/${id}/`);
    setPage(p);
    setDraft({ title: p.title, slug: p.slug, content_md: p.content_md });
  }

  async function createSpace() {
    const name = prompt("Space name");
    if (!name) return;
    const slug = name.toLowerCase().replace(/\s+/g, "-");
    const s = await api("/api/wiki/spaces/", { method: "POST", json: { name, slug } });
    setSpaces((x) => [...x, s]);
  }

  async function createPage() {
    if (!spaceId) return;
    const p = await api("/api/wiki/pages/", {
      method: "POST",
      json: { space: spaceId, title: draft.title || "New page", slug: draft.slug || `page-${Date.now()}`, content_md: draft.content_md, is_draft: true },
    });
    setPage(p);
    await openSpace(spaceId);
  }

  async function savePage() {
    if (!page) return;
    const p = await api(`/api/wiki/pages/${page.id}/`, {
      method: "PATCH",
      json: { ...draft, content_html: marked.parse(draft.content_md) as string, is_draft: false },
    });
    setPage(p);
  }

  return (
    <Shell>
      <div className="page-header">
        <div>
          <h1>{t("wiki")}</h1>
          <p className="subtitle">Spaces & knowledge base</p>
        </div>
        <div className="page-actions">
          <button className={`btn ${view === "spaces" ? "" : "secondary"}`} onClick={() => setView("spaces")}>
            Spaces
          </button>
          <button className={`btn ${view === "tree" ? "" : "secondary"}`} onClick={() => setView("tree")} disabled={!spaceId}>
            Tree
          </button>
          <button className="btn secondary" onClick={createSpace}>
            + Space
          </button>
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "240px 1fr", gap: "1rem" }}>
        <div className="panel">
          {view === "spaces"
            ? spaces.map((s) => (
                <button key={s.id} className="btn ghost" style={{ display: "block", width: "100%", textAlign: "left" }} onClick={() => openSpace(s.id)}>
                  {s.name}
                </button>
              ))
            : tree.map((n) => (
                <button key={n.id} className="btn ghost" style={{ display: "block", width: "100%", textAlign: "left" }} onClick={() => openPage(n.id)}>
                  {n.title}
                  {n.is_draft ? " *" : ""}
                </button>
              ))}
        </div>
        <div className="panel">
          <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.75rem" }}>
            <button className={`btn ${!wysiwyg ? "" : "secondary"}`} onClick={() => setWysiwyg(false)}>
              Markdown
            </button>
            <button className={`btn ${wysiwyg ? "" : "secondary"}`} onClick={() => setWysiwyg(true)}>
              WYSIWYG
            </button>
            <button className="btn secondary" onClick={createPage}>
              New page
            </button>
            <button className="btn" onClick={savePage} disabled={!page}>
              {t("save")}
            </button>
          </div>
          <input className="input" style={{ marginBottom: "0.5rem" }} value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} placeholder="Title" />
          <input className="input" style={{ marginBottom: "0.5rem" }} value={draft.slug} onChange={(e) => setDraft({ ...draft, slug: e.target.value })} placeholder="slug" />
          {!wysiwyg ? (
            <textarea className="input" rows={16} value={draft.content_md} onChange={(e) => setDraft({ ...draft, content_md: e.target.value })} />
          ) : (
            <div
              className="input"
              style={{ minHeight: 280 }}
              contentEditable
              suppressContentEditableWarning
              onBlur={(e) => setDraft({ ...draft, content_md: e.currentTarget.innerText })}
              dangerouslySetInnerHTML={{ __html: marked.parse(draft.content_md) as string }}
            />
          )}
        </div>
      </div>
    </Shell>
  );
}
