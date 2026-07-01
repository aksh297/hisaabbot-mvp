import React, { useEffect, useRef, useState } from "react";
import { Upload, Camera, Trash2, Save, X, ArrowRight } from "lucide-react";
import { toast } from "sonner";
import api from "../lib/api";
import { Button, Card, Input, Label, Select, Badge } from "../components/ui/primitives";
import { fmtINR, fmtDate, todayISO } from "../lib/utils";

const EMPTY_FORM = {
  type: "purchase",
  counterparty_name: "",
  counterparty_gstin: "",
  invoice_number: "",
  invoice_date: todayISO(),
  hsn_code: "",
  place_of_supply: "",
  taxable_amount: 0,
  cgst: 0,
  sgst: 0,
  igst: 0,
  total_tax: 0,
  total_amount: 0,
  notes: "",
  image_url: null,
};

export default function InvoicesPage() {
  const [invoices, setInvoices] = useState([]);
  const [filter, setFilter] = useState("all");
  const [form, setForm] = useState(EMPTY_FORM);
  const [loading, setLoading] = useState(false);
  const [ocring, setOcring] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const fileRef = useRef(null);

  const load = async () => {
    setLoading(true);
    try {
      const params = filter === "all" ? {} : { type: filter };
      const res = await api.get("/invoices", { params });
      setInvoices(res.data);
    } catch (e) {
      toast.error("Invoices load nahi ho paye");
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [filter]); // eslint-disable-line

  const set = (k) => (e) => {
    const val = ["taxable_amount", "cgst", "sgst", "igst", "total_tax", "total_amount"].includes(k)
      ? Number(e.target.value || 0) : e.target.value;
    setForm({ ...form, [k]: val });
  };

  const recompute = () => {
    const tax = Number(form.cgst) + Number(form.sgst) + Number(form.igst);
    const total = Number(form.taxable_amount) + tax;
    setForm((f) => ({ ...f, total_tax: tax, total_amount: total }));
  };

  const onFile = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setOcring(true);
    try {
      const fd = new FormData();
      fd.append("file", f);
      const res = await api.post("/invoices/ocr", fd, { headers: { "Content-Type": "multipart/form-data" } });
      const d = res.data || {};
      setForm({
        ...EMPTY_FORM,
        type: d.detected_type === "sales" ? "sales" : "purchase",
        counterparty_name: d.counterparty_name || "",
        counterparty_gstin: d.counterparty_gstin || "",
        invoice_number: d.invoice_number || "",
        invoice_date: d.invoice_date || todayISO(),
        hsn_code: d.hsn_code || "",
        place_of_supply: d.place_of_supply || "",
        taxable_amount: Number(d.taxable_amount || 0),
        cgst: Number(d.cgst || 0),
        sgst: Number(d.sgst || 0),
        igst: Number(d.igst || 0),
        total_tax: Number(d.total_tax || 0),
        total_amount: Number(d.total_amount || 0),
        image_url: d.image_url || null,
        notes: d.notes || "",
      });
      setShowForm(true);
      toast.success("OCR ho gayi! Confirm karke save karein.");
    } catch (err) {
      toast.error(err.response?.data?.detail || "OCR fail ho gaya");
    } finally {
      setOcring(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const save = async () => {
    if (!form.counterparty_name) {
      toast.error("Party name zaroori hai"); return;
    }
    try {
      await api.post("/invoices", form);
      toast.success("Invoice save ho gaya");
      setShowForm(false);
      setForm(EMPTY_FORM);
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Save fail");
    }
  };

  const del = async (id) => {
    if (!window.confirm("Delete karna hai?")) return;
    try {
      await api.delete(`/invoices/${id}`);
      toast.success("Delete ho gaya");
      load();
    } catch { toast.error("Delete fail"); }
  };

  return (
    <div className="space-y-6" data-testid="invoices-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-ochre">INVOICES</div>
          <h1 className="font-heading text-4xl font-black text-ink mt-1">Purchase & Sales register</h1>
          <p className="text-stone-600 mt-1">Photo upload karo → AI OCR karega → aap confirm karke save karein.</p>
        </div>
        <div className="flex gap-2">
          <Select value={filter} onChange={(e) => setFilter(e.target.value)} data-testid="invoices-filter" className="w-auto">
            <option value="all">Sab invoices</option>
            <option value="purchase">Khareed (Purchase)</option>
            <option value="sales">Bikri (Sales)</option>
          </Select>
          <Button onClick={() => fileRef.current?.click()} disabled={ocring} data-testid="invoices-upload-btn">
            {ocring ? "OCR chal raha…" : (<><Camera className="w-4 h-4 mr-2"/> Invoice photo upload</>)}
          </Button>
          <input type="file" ref={fileRef} accept="image/png,image/jpeg,image/webp,application/pdf" className="hidden" onChange={onFile}/>
          <Button variant="outline" onClick={() => { setForm(EMPTY_FORM); setShowForm(true); }} data-testid="invoices-manual-btn">
            <Upload className="w-4 h-4 mr-2"/> Manual entry
          </Button>
        </div>
      </div>

      {showForm && (
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-xs font-bold uppercase tracking-widest text-stone-500">NEW INVOICE</div>
              <h2 className="font-heading text-2xl font-bold text-ink">Details confirm karein</h2>
            </div>
            <button onClick={() => setShowForm(false)} data-testid="invoices-form-close"><X className="w-5 h-5"/></button>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <Label>Type</Label>
              <Select value={form.type} onChange={set("type")} data-testid="inv-type">
                <option value="purchase">Purchase (khareed)</option>
                <option value="sales">Sales (bikri)</option>
              </Select>
            </div>
            <div>
              <Label>Party name</Label>
              <Input value={form.counterparty_name} onChange={set("counterparty_name")} data-testid="inv-party"/>
            </div>
            <div>
              <Label>Party GSTIN</Label>
              <Input value={form.counterparty_gstin} onChange={set("counterparty_gstin")} style={{textTransform:"uppercase"}} data-testid="inv-gstin"/>
            </div>
            <div>
              <Label>Invoice #</Label>
              <Input value={form.invoice_number} onChange={set("invoice_number")} data-testid="inv-number"/>
            </div>
            <div>
              <Label>Invoice date</Label>
              <Input type="date" value={form.invoice_date} onChange={set("invoice_date")} data-testid="inv-date"/>
            </div>
            <div>
              <Label>HSN code</Label>
              <Input value={form.hsn_code} onChange={set("hsn_code")} data-testid="inv-hsn"/>
            </div>
            <div>
              <Label>Taxable amount</Label>
              <Input type="number" value={form.taxable_amount} onChange={set("taxable_amount")} onBlur={recompute} data-testid="inv-taxable"/>
            </div>
            <div>
              <Label>CGST</Label>
              <Input type="number" value={form.cgst} onChange={set("cgst")} onBlur={recompute} data-testid="inv-cgst"/>
            </div>
            <div>
              <Label>SGST</Label>
              <Input type="number" value={form.sgst} onChange={set("sgst")} onBlur={recompute} data-testid="inv-sgst"/>
            </div>
            <div>
              <Label>IGST</Label>
              <Input type="number" value={form.igst} onChange={set("igst")} onBlur={recompute} data-testid="inv-igst"/>
            </div>
            <div>
              <Label>Total tax</Label>
              <Input type="number" value={form.total_tax} onChange={set("total_tax")} data-testid="inv-tax"/>
            </div>
            <div>
              <Label>Total amount</Label>
              <Input type="number" value={form.total_amount} onChange={set("total_amount")} data-testid="inv-total"/>
            </div>
          </div>
          <div className="mt-5 flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
            <Button onClick={save} data-testid="inv-save"><Save className="w-4 h-4 mr-2"/> Register mein save</Button>
          </div>
        </Card>
      )}

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-parchment/70 text-left text-stone-700">
              <tr>
                <th className="p-4 font-semibold">Type</th>
                <th className="p-4 font-semibold">Date</th>
                <th className="p-4 font-semibold">Party</th>
                <th className="p-4 font-semibold">GSTIN</th>
                <th className="p-4 font-semibold">Inv #</th>
                <th className="p-4 font-semibold text-right">Taxable</th>
                <th className="p-4 font-semibold text-right">Tax</th>
                <th className="p-4 font-semibold text-right">Total</th>
                <th className="p-4 font-semibold"></th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={9} className="p-6 text-center text-stone-500">Loading…</td></tr>
              )}
              {!loading && invoices.length === 0 && (
                <tr><td colSpan={9} className="p-8 text-center text-stone-500">
                  Koi invoice nahi. Upar "Invoice photo upload" ya "Manual entry" se add karein.
                </td></tr>
              )}
              {invoices.map((inv) => (
                <tr key={inv._id} className="border-t border-[#E7E5E4] hover:bg-parchment/30" data-testid={`invoice-row-${inv._id}`}>
                  <td className="p-4">
                    <Badge tone={inv.type === "sales" ? "success" : "warning"}>{inv.type === "sales" ? "Bikri" : "Khareed"}</Badge>
                  </td>
                  <td className="p-4 whitespace-nowrap">{fmtDate(inv.invoice_date)}</td>
                  <td className="p-4">{inv.counterparty_name}</td>
                  <td className="p-4 font-mono text-xs">{inv.counterparty_gstin || "—"}</td>
                  <td className="p-4 font-mono text-xs">{inv.invoice_number || "—"}</td>
                  <td className="p-4 text-right font-mono">{fmtINR(inv.taxable_amount)}</td>
                  <td className="p-4 text-right font-mono">{fmtINR(inv.total_tax)}</td>
                  <td className="p-4 text-right font-mono font-semibold">{fmtINR(inv.total_amount)}</td>
                  <td className="p-4">
                    <button onClick={() => del(inv._id)} className="text-terracotta hover:text-red-700" data-testid={`invoice-del-${inv._id}`}><Trash2 className="w-4 h-4"/></button>
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
