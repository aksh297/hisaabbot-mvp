import React, { useState } from "react";
import { ShieldCheck, RefreshCcw } from "lucide-react";
import api from "../lib/api";
import { Card, Button, Input, Label, Badge } from "../components/ui/primitives";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";

export default function SettingsPage() {
  const { user } = useAuth();
  const [gstin, setGstin] = useState(user?.gstin || "");
  const [verifying, setVerifying] = useState(false);
  const [result, setResult] = useState(null);

  const verify = async () => {
    setVerifying(true);
    try {
      const res = await api.post("/gstin/verify", { gstin });
      setResult(res.data);
      if (res.data.valid) toast.success("GSTIN valid!");
      else toast.error(res.data.error || "Invalid GSTIN");
    } catch (err) {
      toast.error("Verify fail");
    } finally { setVerifying(false); }
  };

  return (
    <div className="space-y-6 max-w-3xl" data-testid="settings-page">
      <div>
        <div className="text-xs font-bold uppercase tracking-widest text-ochre">SETTINGS</div>
        <h1 className="font-heading text-4xl font-black text-ink mt-1">Aapki profile</h1>
      </div>

      <Card className="p-6">
        <div className="grid sm:grid-cols-2 gap-4">
          <KV label="Naam" value={user?.name}/>
          <KV label="Email" value={user?.email}/>
          <KV label="Business" value={user?.business_name || "—"}/>
          <KV label="Phone" value={user?.phone || "—"}/>
          <KV label="City" value={user?.city || "—"}/>
          <KV label="GSTIN" value={user?.gstin || "Not set"}/>
          <KV label="Language" value={user?.language}/>
          <KV label="Role" value={user?.role}/>
        </div>
      </Card>

      <Card className="p-6">
        <div className="flex items-center gap-2 mb-2">
          <ShieldCheck className="w-5 h-5 text-ink"/>
          <h2 className="font-heading text-2xl font-bold text-ink">GSTIN verify karein</h2>
        </div>
        <p className="text-stone-600 text-sm">15-character GSTIN daalein — hum format check karke state, PAN aur entity type extract karenge. Real GSTN portal integration production launch pe hoga (needs paid GSP).</p>
        <div className="mt-4 flex gap-2">
          <Input value={gstin} onChange={(e) => setGstin(e.target.value.toUpperCase())} placeholder="08AABCU9603R1ZM" style={{textTransform:"uppercase"}} data-testid="settings-gstin-input"/>
          <Button onClick={verify} disabled={verifying} data-testid="settings-gstin-verify">
            {verifying ? "Verifying…" : (<><RefreshCcw className="w-4 h-4 mr-2"/>Verify</>)}
          </Button>
        </div>
        {result && (
          <div className="mt-4 p-4 rounded-lg bg-parchment/60 border border-[#E7E5E4]" data-testid="settings-gstin-result">
            {result.valid ? (
              <div className="space-y-1 text-sm">
                <div className="flex items-center gap-2"><Badge tone="success">VALID</Badge> <span className="font-mono">{result.gstin}</span></div>
                <div><b>State:</b> {result.state} ({result.state_code})</div>
                <div><b>PAN:</b> <span className="font-mono">{result.pan}</span></div>
                <div><b>Entity type:</b> {result.entity_type}</div>
                <div><b>Status:</b> {result.status}</div>
                <div className="text-xs text-stone-500 mt-2">{result.note}</div>
              </div>
            ) : (
              <div className="text-terracotta"><Badge tone="danger">INVALID</Badge> {result.error}</div>
            )}
          </div>
        )}
      </Card>

      <Card className="p-6 bg-parchment/40">
        <h2 className="font-heading text-xl font-bold text-ink">WhatsApp Business Integration (Gupshup)</h2>
        <p className="text-stone-600 text-sm mt-1">Live WhatsApp connect karne ke liye Gupshup pe BSP account chahiye. Setup steps:</p>
        <ol className="mt-3 list-decimal list-inside space-y-1 text-sm text-stone-700">
          <li>Gupshup pe register karein → <a href="https://www.gupshup.io" target="_blank" rel="noreferrer" className="underline">gupshup.io</a></li>
          <li>WhatsApp Business number apply karein (Meta verified).</li>
          <li>Webhook URL set karein: <code className="bg-white px-1.5 py-0.5 rounded font-mono text-xs">{`${process.env.REACT_APP_BACKEND_URL}/api/whatsapp/webhook`}</code></li>
          <li>Template messages approve karvaayein (welcome, reminder).</li>
        </ol>
        <Badge tone="warning" className="mt-3">Production launch pe activate hoga</Badge>
      </Card>
    </div>
  );
}

function KV({ label, value }) {
  return (
    <div>
      <div className="text-xs font-bold uppercase tracking-widest text-stone-500">{label}</div>
      <div className="font-semibold text-ink mt-0.5">{value || "—"}</div>
    </div>
  );
}
