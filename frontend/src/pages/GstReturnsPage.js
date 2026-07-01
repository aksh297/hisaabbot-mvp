import React, { useEffect, useState } from "react";
import { Download, RefreshCcw, Send, Check } from "lucide-react";
import api from "../lib/api";
import { Card, Button, Badge, Select, Input, Label } from "../components/ui/primitives";
import { fmtINR, currentMonthISO } from "../lib/utils";
import { toast } from "sonner";

export default function GstReturnsPage() {
  const [month, setMonth] = useState(currentMonthISO());
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [filings, setFilings] = useState([]);
  const [otpModal, setOtpModal] = useState(null); // {filing_id, return_type}
  const [otp, setOtp] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [res, fRes] = await Promise.all([
        api.get("/gst/summary", { params: { month } }),
        api.get("/gst/filings").catch(() => ({ data: [] })),
      ]);
      setData(res.data);
      setFilings(fRes.data || []);
    } catch { toast.error("GST summary load nahi ho paya"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [month]); // eslint-disable-line

  const fileReturn = async (return_type) => {
    setBusy(true);
    try {
      const res = await api.post("/gst/file", { return_type, period: month });
      toast.success(`${return_type.toUpperCase()} uploaded — ACK ${res.data.ack_number}`);
      if (res.data.otp_required) {
        setOtpModal({ filing_id: res.data.filing_id, return_type });
      }
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "File failed");
    } finally { setBusy(false); }
  };

  const submitOtp = async () => {
    if (!/^\d{6}$/.test(otp)) { toast.error("6-digit OTP dijiye"); return; }
    setBusy(true);
    try {
      const res = await api.post("/gst/file/submit-otp", { filing_id: otpModal.filing_id, otp });
      toast.success(`Submitted! ARN: ${res.data.arn}`);
      setOtpModal(null); setOtp("");
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Submit failed");
    } finally { setBusy(false); }
  };

  const exportJson = () => {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `hisaabbot-gst-${month}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const gstr1 = data?.gstr1;
  const gstr3b = data?.gstr3b;

  return (
    <div className="space-y-6" data-testid="gst-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-ochre">GST RETURNS</div>
          <h1 className="font-heading text-4xl font-black text-ink mt-1">GSTR-1 & GSTR-3B</h1>
          <p className="text-stone-600 mt-1">Aapke saved invoices se automatically calculate hota hai. JSON export kar sakte hain.</p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={month} onChange={(e) => setMonth(e.target.value)} data-testid="gst-month" className="w-auto">
            {generateMonths().map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </Select>
          <Button variant="outline" onClick={load} data-testid="gst-refresh"><RefreshCcw className="w-4 h-4 mr-2"/>Refresh</Button>
          <Button onClick={exportJson} data-testid="gst-export"><Download className="w-4 h-4 mr-2"/>Export JSON</Button>
        </div>
      </div>

      <Card className="p-4 border-l-4 border-l-ochre">
        <div className="text-xs font-mono text-stone-600">
          <b>Note:</b> GSTR calculations local hain. "File via GSP" button real Masters India GSP integration ke liye wire-ready hai — jab tak GSP creds set nahi hote, simulated ACK/ARN return karega.
        </div>
      </Card>

      {/* Existing filings history */}
      {filings.length > 0 && (
        <Card className="p-4">
          <div className="text-xs font-bold uppercase tracking-widest text-stone-500 mb-2">FILING HISTORY</div>
          <div className="space-y-2">
            {filings.slice(0, 5).map((f) => (
              <div key={f._id} className="flex items-center justify-between p-3 rounded-lg bg-parchment/50 border border-[#E7E5E4] text-sm">
                <div>
                  <span className="font-semibold uppercase">{f.return_type}</span> · {f.period} · <span className="font-mono">{f.ack_number}</span>
                  {f.arn && <span className="ml-2 font-mono text-green-700">ARN {f.arn}</span>}
                </div>
                <Badge tone={f.status === "submitted" ? "success" : "warning"}>{f.status}</Badge>
              </div>
            ))}
          </div>
        </Card>
      )}

      {loading && <div className="text-stone-500">Loading…</div>}

      {gstr3b && (
        <>
          {/* GSTR-3B summary */}
          <Card className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-xs font-bold uppercase tracking-widest text-stone-500">GSTR-3B</div>
                <h2 className="font-heading text-2xl font-bold text-ink">Tax liability summary — {gstr3b.period}</h2>
              </div>
              <Badge tone={gstr3b.net_payable > 0 ? "warning" : "success"}>
                Net payable: {fmtINR(gstr3b.net_payable)}
              </Badge>
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <KV label="Outward taxable" value={fmtINR(gstr3b.outward_taxable)} sub={`${gstr3b.sales_count} sales`}/>
              <KV label="Output tax" value={fmtINR(gstr3b.output_tax_total)} sub={`CGST ${fmtINR(gstr3b.output_cgst)} · SGST ${fmtINR(gstr3b.output_sgst)} · IGST ${fmtINR(gstr3b.output_igst)}`}/>
              <KV label="Inward taxable" value={fmtINR(gstr3b.inward_taxable)} sub={`${gstr3b.purchase_count} purchases`}/>
              <KV label="ITC available" value={fmtINR(gstr3b.itc_total)} sub={`CGST ${fmtINR(gstr3b.itc_cgst)} · SGST ${fmtINR(gstr3b.itc_sgst)} · IGST ${fmtINR(gstr3b.itc_igst)}`}/>
            </div>
            <div className="mt-6 flex flex-wrap items-center justify-end gap-3">
              <div className="bg-ink text-paper rounded-lg px-6 py-4 text-right">
                <div className="text-xs uppercase tracking-widest text-ochre">NET GST PAYABLE</div>
                <div className="font-heading text-3xl font-black">{fmtINR(gstr3b.net_payable)}</div>
              </div>
              <div className="flex flex-col gap-2">
                <Button onClick={() => fileReturn("gstr1")} disabled={busy} data-testid="file-gstr1-btn"><Send className="w-4 h-4 mr-2"/>File GSTR-1 via GSP</Button>
                <Button variant="outline" onClick={() => fileReturn("gstr3b")} disabled={busy} data-testid="file-gstr3b-btn"><Send className="w-4 h-4 mr-2"/>File GSTR-3B via GSP</Button>
              </div>
            </div>
          </Card>

          {/* GSTR-1 breakdown */}
          <Card className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-xs font-bold uppercase tracking-widest text-stone-500">GSTR-1</div>
                <h2 className="font-heading text-2xl font-bold text-ink">Outward supplies — {gstr1.period}</h2>
              </div>
              <div className="text-sm text-stone-600">{gstr1.count} invoices · {fmtINR(gstr1.total_amount)}</div>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-parchment/60 text-stone-700">
                  <tr>
                    <th className="p-3 text-left">Date</th>
                    <th className="p-3 text-left">Customer</th>
                    <th className="p-3 text-left">GSTIN</th>
                    <th className="p-3 text-left">Inv #</th>
                    <th className="p-3 text-left">HSN</th>
                    <th className="p-3 text-right">Taxable</th>
                    <th className="p-3 text-right">CGST</th>
                    <th className="p-3 text-right">SGST</th>
                    <th className="p-3 text-right">IGST</th>
                    <th className="p-3 text-right">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {gstr1.invoices.length === 0 && (
                    <tr><td colSpan={10} className="p-6 text-center text-stone-500">Is mahine koi sales invoice nahi.</td></tr>
                  )}
                  {gstr1.invoices.map((i) => (
                    <tr key={i.id} className="border-t border-[#E7E5E4]">
                      <td className="p-3 whitespace-nowrap">{i.invoice_date}</td>
                      <td className="p-3">{i.counterparty_name}</td>
                      <td className="p-3 font-mono text-xs">{i.counterparty_gstin || "—"}</td>
                      <td className="p-3 font-mono text-xs">{i.invoice_number || "—"}</td>
                      <td className="p-3 font-mono text-xs">{i.hsn_code || "—"}</td>
                      <td className="p-3 text-right font-mono">{fmtINR(i.taxable_amount)}</td>
                      <td className="p-3 text-right font-mono">{fmtINR(i.cgst)}</td>
                      <td className="p-3 text-right font-mono">{fmtINR(i.sgst)}</td>
                      <td className="p-3 text-right font-mono">{fmtINR(i.igst)}</td>
                      <td className="p-3 text-right font-mono font-semibold">{fmtINR(i.total_amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}

      {/* OTP modal for GSP submission */}
      {otpModal && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={() => setOtpModal(null)}>
          <Card className="max-w-md w-full p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-2 mb-2">
              <Check className="w-5 h-5 text-green-700"/>
              <h2 className="font-heading text-2xl font-black">Aadhaar OTP dijiye</h2>
            </div>
            <p className="text-stone-600 text-sm">Aapke registered mobile pe GSTN se OTP aayega. 6 digit OTP daalein.</p>
            <div className="mt-4">
              <Label>OTP</Label>
              <Input value={otp} onChange={(e) => setOtp(e.target.value)} maxLength={6} placeholder="123456" data-testid="otp-input"/>
              <div className="text-xs text-stone-500 mt-1">Simulation mode: koi bhi 6-digit OTP daalein (e.g. 123456).</div>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <Button variant="outline" onClick={() => { setOtpModal(null); setOtp(""); }}>Cancel</Button>
              <Button onClick={submitOtp} disabled={busy} data-testid="otp-submit">Submit & get ARN</Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

function KV({ label, value, sub }) {
  return (
    <div className="rounded-lg border border-[#E7E5E4] p-4 bg-white">
      <div className="text-xs font-bold uppercase tracking-widest text-stone-500">{label}</div>
      <div className="font-heading text-2xl font-black text-ink mt-1">{value}</div>
      {sub && <div className="text-[11px] text-stone-500 mt-1">{sub}</div>}
    </div>
  );
}

function generateMonths() {
  const arr = [];
  const now = new Date();
  for (let i = 0; i < 12; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    arr.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`);
  }
  return arr;
}
