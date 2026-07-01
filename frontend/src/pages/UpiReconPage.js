import React, { useEffect, useRef, useState } from "react";
import { Upload, Save, X, Link2 } from "lucide-react";
import { toast } from "sonner";
import api from "../lib/api";
import { Card, Button, Input, Label, Badge } from "../components/ui/primitives";
import { fmtINR, fmtDate, todayISO } from "../lib/utils";

const EMPTY = {
  payer_name: "", upi_id: "", amount: 0, date: todayISO(), ref_number: "",
  matched_invoice_id: null, notes: "", image_url: null,
};

export default function UpiReconPage() {
  const [txns, setTxns] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [suggested, setSuggested] = useState(null);
  const fileRef = useRef(null);

  const load = async () => {
    setLoading(true);
    try { const res = await api.get("/upi/transactions"); setTxns(res.data); }
    catch { toast.error("UPI transactions load nahi ho paye"); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const set = (k) => (e) => {
    const val = k === "amount" ? Number(e.target.value || 0) : e.target.value;
    setForm({ ...form, [k]: val });
  };

  const onFile = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setParsing(true);
    try {
      const fd = new FormData(); fd.append("file", f);
      const res = await api.post("/upi/parse", fd, { headers: { "Content-Type": "multipart/form-data" } });
      const d = res.data || {};
      setForm({
        ...EMPTY,
        payer_name: d.payer_name || "",
        upi_id: d.upi_id || "",
        amount: Number(d.amount || 0),
        date: d.date || todayISO(),
        ref_number: d.ref_number || "",
        image_url: d.image_url || null,
      });
      if (d.suggested_match) {
        setSuggested(d.suggested_match);
        setForm((f) => ({ ...f, matched_invoice_id: d.suggested_match.invoice_id }));
        toast.success("Ek matching invoice mila!");
      } else {
        setSuggested(null);
      }
      setShowForm(true);
    } catch (err) { toast.error(err.response?.data?.detail || "UPI parse fail"); }
    finally {
      setParsing(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const save = async () => {
    try {
      await api.post("/upi/transactions", form);
      toast.success("UPI transaction save ho gaya");
      setShowForm(false); setForm(EMPTY); setSuggested(null);
      load();
    } catch (err) { toast.error(err.response?.data?.detail || "Save fail"); }
  };

  return (
    <div className="space-y-6" data-testid="upi-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-ochre">UPI RECONCILIATION</div>
          <h1 className="font-heading text-4xl font-black text-ink mt-1">UPI payments match karein</h1>
          <p className="text-stone-600 mt-1">GPay / PhonePe / Paytm ki screenshot upload karo — AI amount, UPI ID, ref number extract karega aur sales invoice ke saath match karega.</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => fileRef.current?.click()} disabled={parsing} data-testid="upi-upload-btn">
            {parsing ? "Parse ho raha…" : (<><Upload className="w-4 h-4 mr-2"/>Screenshot upload</>)}
          </Button>
          <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={onFile}/>
          <Button variant="outline" onClick={() => { setForm(EMPTY); setSuggested(null); setShowForm(true); }} data-testid="upi-manual-btn">
            Manual entry
          </Button>
        </div>
      </div>

      {showForm && (
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-heading text-2xl font-bold text-ink">UPI transaction confirm karein</h2>
            <button onClick={() => setShowForm(false)}><X className="w-5 h-5"/></button>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div><Label>Payer name</Label><Input value={form.payer_name} onChange={set("payer_name")} data-testid="upi-payer"/></div>
            <div><Label>UPI ID</Label><Input value={form.upi_id} onChange={set("upi_id")} data-testid="upi-id"/></div>
            <div><Label>Amount (₹)</Label><Input type="number" value={form.amount} onChange={set("amount")} data-testid="upi-amount"/></div>
            <div><Label>Date</Label><Input type="date" value={form.date} onChange={set("date")} data-testid="upi-date"/></div>
            <div><Label>Ref number</Label><Input value={form.ref_number} onChange={set("ref_number")} data-testid="upi-ref"/></div>
          </div>
          {suggested && (
            <div className="mt-4 p-4 rounded-lg bg-green-50 border border-green-200 flex items-center gap-3">
              <Link2 className="w-5 h-5 text-green-700"/>
              <div className="flex-1 text-sm">
                <div className="font-semibold text-green-900">Match mila:</div>
                <div className="text-green-900">{suggested.counterparty_name} · {suggested.invoice_number} · {fmtINR(suggested.total_amount)}</div>
              </div>
            </div>
          )}
          <div className="mt-5 flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
            <Button onClick={save} data-testid="upi-save"><Save className="w-4 h-4 mr-2"/> Save</Button>
          </div>
        </Card>
      )}

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-parchment/70 text-left text-stone-700">
              <tr>
                <th className="p-4 font-semibold">Date</th>
                <th className="p-4 font-semibold">Payer</th>
                <th className="p-4 font-semibold">UPI ID</th>
                <th className="p-4 font-semibold">Ref</th>
                <th className="p-4 font-semibold text-right">Amount</th>
                <th className="p-4 font-semibold">Match</th>
              </tr>
            </thead>
            <tbody>
              {loading && <tr><td colSpan={6} className="p-6 text-center text-stone-500">Loading…</td></tr>}
              {!loading && txns.length === 0 && (
                <tr><td colSpan={6} className="p-8 text-center text-stone-500">Koi UPI transaction nahi. Screenshot upload karein.</td></tr>
              )}
              {txns.map((t) => (
                <tr key={t._id} className="border-t border-[#E7E5E4] hover:bg-parchment/30">
                  <td className="p-4 whitespace-nowrap">{fmtDate(t.date)}</td>
                  <td className="p-4">{t.payer_name || "—"}</td>
                  <td className="p-4 font-mono text-xs">{t.upi_id || "—"}</td>
                  <td className="p-4 font-mono text-xs">{t.ref_number || "—"}</td>
                  <td className="p-4 text-right font-mono font-semibold">{fmtINR(t.amount)}</td>
                  <td className="p-4">
                    {t.matched_invoice_id
                      ? <Badge tone="success">Matched</Badge>
                      : <Badge tone="warning">Unmatched</Badge>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
