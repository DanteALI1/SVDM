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
      <div className="compose">
        <h1 className="brand-hero">SVDB</h1>
        <p className="tagline">2FA enrollment</p>
        {qr && <img src={`data:image/png;base64,${qr}`} alt="QR" style={{ width: 200, height: 200 }} />}
        <p className="muted">Secret: {secret}</p>
        <input className="input" value={code} onChange={(e) => setCode(e.target.value)} placeholder="TOTP code" />
        {error && <p style={{ color: "var(--svdb-danger)" }}>{error}</p>}
        <button className="btn" onClick={confirm}>
          Confirm
        </button>
      </div>
    </div>
  );
}
