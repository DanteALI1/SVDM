"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function Enroll2FAPage() {
  const router = useRouter();
  const [qr, setQr] = useState("");
  const [secret, setSecret] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api<any>("/api/auth/2fa/enroll/")
      .then((d) => {
        setQr(d.qr_png_base64);
        setSecret(d.secret);
      })
      .catch((e) => setError(String(e.message || e)));
  }, []);

  async function confirm() {
    try {
      await api("/api/auth/2fa/enroll/", { method: "POST", json: { code } });
      router.push("/dashboard");
    } catch (e: any) {
      setError(String(e.message || e));
    }
  }

  return (
    <div className="hero-login">
      <aside className="login-brand-pane">
        <div>
          <h1 className="brand-hero">SVDB</h1>
          <p className="tagline">Enable two-factor authentication</p>
        </div>
        <div className="brand-foot">Required for this account</div>
      </aside>
      <div className="login-form-pane">
        <div className="login-card">
          <h2>2FA enrollment</h2>
          <p className="lead">Scan the QR code, then enter a TOTP code.</p>
          {qr && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={`data:image/png;base64,${qr}`} alt="QR" style={{ width: 180, height: 180, margin: "0 auto 0.75rem", display: "block" }} />
          )}
          <p className="muted" style={{ wordBreak: "break-all" }}>
            Secret: {secret}
          </p>
          <input className="input" value={code} onChange={(e) => setCode(e.target.value)} placeholder="TOTP code" />
          {error && <p style={{ color: "var(--svdb-danger)" }}>{error}</p>}
          <button className="btn" style={{ marginTop: 8, width: "100%" }} onClick={confirm}>
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
}
