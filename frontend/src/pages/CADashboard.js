import React, { useEffect, useMemo, useState } from "react";
import {
  Users, FileCheck, IndianRupee, AlertTriangle, RefreshCcw, UserPlus, Search,
  ChevronRight, X, MessageCircle, CheckCircle2, Clock, XCircle, Download
} from "lucide-react";
import { toast } from "sonner";
import api from "../lib/api";
import { Card, Button, Input, Label, Badge, Select } from "../components/ui/primitives";
import { fmtINR, currentMonthISO } from "../lib/utils";

const STATUS_TONE = {
  filed: "success",
  draft: "info",
  pending: "warning",
  failed: "danger",
};

export default function CADashboard() {
  const [month, setMonth] = useState(currentMonthISO());
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all"); // all / pending / filed
  const [drawer, setDrawer] = useState(null); // vendor_id selected
  const [drawerData, setDrawerData] = useState(null);
  const [showInvite, setShowInvite] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.get("/ca/clients", { params: { month } });
      setData(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Clients load nahi ho paye");
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [month]); // eslint-disable-line

  const filtered = useMemo(() => {
    if (!data) return [];
    const q = search.toLowerCase();
    return data.clients.filter((c) => {
      if (statusFilter === "pending" && c.gstr1_status === "filed" && c.gstr3b_status === "filed") return false;
      if (statusFilter === "filed" && (c.gstr1_status !== "filed" || c.gstr3b_status !== "filed")) return false;
      if (!q) return true;
      return (
        (c.business_name || "").toLowerCase().includes(q) ||
        (c.name || "").toLowerCase().includes(q) ||
        (c.gstin || "").toLowerCase().includes(q) ||
        (c.city || "").toLowerCase().includes(q)
      );
    });
  }, [data, search, statusFilter]);

  const openDrawer = async (vendorId) => {
    setDrawer(vendorId);
    setDrawerData(null);
    try {
      const res = await api.get(`/ca/clients/${vendorId}/summary`, { params: { month } });
      setDrawerData(res.data);
    } catch (err) { toast.error("Client summary load fail"); }
  };

  const mark = async (vendor_id, return_type, status) => {
    try {
      await api.post("/ca/filings/mark", { vendor_id, period: month, return_type, status });
      toast.success(`${return_type.toUpperCase()} ${status}`);
      load();
      if (drawer === vendor_id) openDrawer(vendor_id);
    } catch (err) { toast.error(err.response?.data?.detail || "Mark fail"); }
  };

  const remove = async (vendor_id) => {
    if (!window.confirm("Client remove karna hai? (Data delete nahi hoga.)")) return;
    try {
      await api.delete(`/ca/clients/${vendor_id}`);
      toast.success("Client hata diya");
      load();
      setDrawer(null);
    } catch (err) { toast.error("Remove fail"); }
  };

  const exportCsv = async () => {
    try {
      const res = await api.get(`/ca/export`, { params: { month, format: "csv" }, responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `hisaabbot-ca-export-${month}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("CSV download shuru ho gaya");
    } catch (err) { toast.error("Export fail"); }
  };

  const exportJson = async () => {
    try {
      const res = await api.get(`/ca/export`, { params: { month, format: "json" } });
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `hisaabbot-ca-export-${month}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("JSON download shuru ho gaya");
    } catch (err) { toast.error("Export fail"); }
  };

  const stats = data?.stats;

  return (
    <div className="space-y-6" data-testid="ca-dashboard">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-ochre">CA PLAN</div>
          <h1 className="font-heading text-4xl font-black text-ink mt-1">Bulk client dashboard</h1>
          <p className="text-stone-600 mt-1">Apne saare clients ek jagah — filing status, tax liability, alerts.</p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={month} onChange={(e) => setMonth(e.target.value)} className="w-auto" data-testid="ca-month">
            {generateMonths().map((m) => <option key={m} value={m}>{m}</option>)}
          </Select>
          <Button variant="outline" onClick={load} data-testid="ca-refresh"><RefreshCcw className="w-4 h-4 mr-1.5"/>Refresh</Button>
          <Button variant="outline" onClick={exportCsv} data-testid="ca-export-csv"><Download className="w-4 h-4 mr-1.5"/>Export CSV</Button>
          <Button variant="outline" onClick={exportJson} data-testid="ca-export-json"><Download className="w-4 h-4 mr-1.5"/>JSON</Button>
          <Button onClick={() => setShowInvite(true)} data-testid="ca-invite-btn"><UserPlus className="w-4 h-4 mr-1.5"/>Invite client</Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5 stagger">
        <StatCard icon={<Users/>} label="Total clients" value={stats?.total_clients ?? "—"} sub={`${stats?.pending ?? 0} pending action`} testid="stat-clients"/>
        <StatCard icon={<FileCheck/>} label="GSTR-1 filed" value={`${stats?.gstr1_filed ?? 0} / ${stats?.total_clients ?? 0}`} sub="Outward supplies" tone="info" testid="stat-gstr1"/>
        <StatCard icon={<FileCheck/>} label="GSTR-3B filed" value={`${stats?.gstr3b_filed ?? 0} / ${stats?.total_clients ?? 0}`} sub="Tax liability" tone="warning" testid="stat-gstr3b"/>
        <StatCard icon={<IndianRupee/>} label="Combined tax payable" value={fmtINR(stats?.combined_net_payable || 0)} sub={`Sales: ${fmtINR(stats?.combined_sales || 0)}`} tone="success" testid="stat-tax"/>
      </div>

      {/* Search + filter */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[240px] max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-stone-400"/>
          <Input placeholder="Search by business, name, GSTIN, city…" value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" data-testid="ca-search"/>
        </div>
        <div className="inline-flex rounded-lg border border-[#E7E5E4] bg-white p-1">
          {[["all", "Sab"], ["pending", "Pending"], ["filed", "Filed"]].map(([k, l]) => (
            <button key={k}
              onClick={() => setStatusFilter(k)}
              className={`px-3 py-1.5 rounded-md text-sm font-semibold ${statusFilter === k ? "bg-ink text-paper" : "text-stone-700 hover:bg-parchment"}`}
              data-testid={`ca-filter-${k}`}
            >{l}</button>
          ))}
        </div>
      </div>

      {/* Client table */}
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-parchment/70 text-left text-stone-700">
              <tr>
                <th className="p-4 font-semibold">Business</th>
                <th className="p-4 font-semibold">GSTIN</th>
                <th className="p-4 font-semibold text-right">Sales</th>
                <th className="p-4 font-semibold text-right">Tax payable</th>
                <th className="p-4 font-semibold">GSTR-1</th>
                <th className="p-4 font-semibold">GSTR-3B</th>
                <th className="p-4 font-semibold w-8"></th>
              </tr>
            </thead>
            <tbody>
              {loading && <tr><td colSpan={7} className="p-6 text-center text-stone-500">Loading…</td></tr>}
              {!loading && filtered.length === 0 && (
                <tr><td colSpan={7} className="p-10 text-center text-stone-500">
                  {statusFilter !== "all" || search
                    ? "Koi client match nahi hua. Filter clear karein."
                    : "Abhi koi client nahi. \"Invite client\" se add karein."}
                </td></tr>
              )}
              {filtered.map((c) => (
                <tr key={c.vendor_id} onClick={() => openDrawer(c.vendor_id)}
                    className="border-t border-[#E7E5E4] hover:bg-parchment/30 cursor-pointer"
                    data-testid={`ca-row-${c.vendor_id}`}>
                  <td className="p-4">
                    <div className="font-semibold">{c.business_name || c.name}</div>
                    <div className="text-xs text-stone-500">{c.name} · {c.city || "—"}</div>
                  </td>
                  <td className="p-4 font-mono text-xs">{c.gstin || "—"}</td>
                  <td className="p-4 text-right font-mono">{fmtINR(c.sales_total)}</td>
                  <td className="p-4 text-right font-mono font-semibold text-terracotta">{fmtINR(c.net_payable)}</td>
                  <td className="p-4"><StatusPill status={c.gstr1_status}/></td>
                  <td className="p-4"><StatusPill status={c.gstr3b_status}/></td>
                  <td className="p-4 text-right"><ChevronRight className="w-4 h-4 text-stone-400"/></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Drawer */}
      {drawer && (
        <div className="fixed inset-0 z-40 bg-black/40" onClick={() => setDrawer(null)}>
          <div className="absolute right-0 top-0 bottom-0 w-full max-w-2xl bg-paper shadow-2xl overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="sticky top-0 bg-paper border-b border-[#E7E5E4] px-6 py-4 flex items-center justify-between">
              <h2 className="font-heading text-2xl font-black text-ink">Client details</h2>
              <button onClick={() => setDrawer(null)} data-testid="ca-drawer-close"><X className="w-5 h-5"/></button>
            </div>
            {drawerData ? (
              <div className="p-6 space-y-5">
                <div>
                  <div className="text-xs font-bold uppercase tracking-widest text-ochre">{drawerData.vendor.period}</div>
                  <h3 className="font-heading text-3xl font-black">{drawerData.vendor.business_name}</h3>
                  <div className="text-stone-600 text-sm">{drawerData.vendor.name} · {drawerData.vendor.city || "—"}</div>
                  <div className="text-xs font-mono text-stone-500 mt-1">GSTIN {drawerData.vendor.gstin || "—"} · {drawerData.vendor.phone || "—"}</div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <KV label="Sales (MTD)" value={fmtINR(drawerData.gstr1.total_amount)}/>
                  <KV label="Purchase (MTD)" value={fmtINR(drawerData.gstr3b.inward_taxable + drawerData.gstr3b.itc_total)}/>
                  <KV label="Output tax" value={fmtINR(drawerData.gstr3b.output_tax_total)}/>
                  <KV label="ITC" value={fmtINR(drawerData.gstr3b.itc_total)}/>
                  <KV label="Net GST payable" value={fmtINR(drawerData.gstr3b.net_payable)} accent/>
                  <KV label="Invoices" value={`${drawerData.gstr3b.sales_count} sales · ${drawerData.gstr3b.purchase_count} purchase`}/>
                </div>

                {/* Filing actions */}
                <Card className="p-4">
                  <div className="text-xs font-bold uppercase tracking-widest text-stone-500 mb-2">FILING ACTIONS</div>
                  <div className="space-y-3">
                    <FilingRow label="GSTR-1" status={drawerData.vendor.gstr1_status}
                      onMark={(s) => mark(drawerData.vendor.vendor_id, "gstr1", s)}
                      testid="drawer-gstr1"/>
                    <FilingRow label="GSTR-3B" status={drawerData.vendor.gstr3b_status}
                      onMark={(s) => mark(drawerData.vendor.vendor_id, "gstr3b", s)}
                      testid="drawer-gstr3b"/>
                  </div>
                </Card>

                {/* Invoices */}
                <div>
                  <div className="text-xs font-bold uppercase tracking-widest text-stone-500 mb-2">INVOICES ({drawerData.invoices.length})</div>
                  <div className="space-y-2">
                    {drawerData.invoices.length === 0 && (
                      <div className="text-stone-500 text-sm">Is mahine koi invoice nahi.</div>
                    )}
                    {drawerData.invoices.map((inv) => (
                      <div key={inv._id} className="flex items-center justify-between p-3 rounded-lg bg-white border border-[#E7E5E4]">
                        <div>
                          <div className="text-sm font-semibold">{inv.counterparty_name}</div>
                          <div className="text-xs text-stone-500 font-mono">{inv.invoice_number || "—"} · {inv.invoice_date}</div>
                        </div>
                        <div className="text-right">
                          <div className="font-mono font-semibold">{fmtINR(inv.total_amount)}</div>
                          <Badge tone={inv.type === "sales" ? "success" : "warning"}>{inv.type === "sales" ? "Bikri" : "Khareed"}</Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex justify-between pt-4 border-t border-[#E7E5E4]">
                  <Button variant="danger" onClick={() => remove(drawerData.vendor.vendor_id)} data-testid="ca-remove-btn">Remove client</Button>
                  <a href={`https://wa.me/${(drawerData.vendor.phone || '').replace(/\D/g, '')}`} target="_blank" rel="noreferrer">
                    <Button variant="whatsapp" data-testid="ca-wa-btn"><MessageCircle className="w-4 h-4 mr-2"/>WhatsApp reminder</Button>
                  </a>
                </div>
              </div>
            ) : <div className="p-10 text-center text-stone-500">Loading…</div>}
          </div>
        </div>
      )}

      {showInvite && <InviteModal onClose={() => setShowInvite(false)} onDone={() => { setShowInvite(false); load(); }}/>}
    </div>
  );
}

function StatCard({ icon, label, value, sub, tone = "default", testid }) {
  const toneMap = {
    default: "bg-parchment text-ink border-[#E7E5E4]",
    success: "bg-green-50 text-green-800 border-green-200",
    info: "bg-sky-50 text-sky-800 border-sky-200",
    warning: "bg-amber-50 text-amber-900 border-amber-200",
  };
  return (
    <Card className="p-5" data-testid={testid}>
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center border ${toneMap[tone]}`}>{icon}</div>
      <div className="mt-4 text-xs font-bold uppercase tracking-widest text-stone-500">{label}</div>
      <div className="font-heading text-3xl font-black text-ink mt-1">{value}</div>
      <div className="text-xs text-stone-500 mt-1">{sub}</div>
    </Card>
  );
}

function StatusPill({ status }) {
  const label = { filed: "Filed", pending: "Pending", draft: "Draft ready" }[status] || status;
  const icon = { filed: <CheckCircle2 className="w-3 h-3"/>, pending: <AlertTriangle className="w-3 h-3"/>, draft: <Clock className="w-3 h-3"/> }[status] || null;
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
      status === "filed" ? "bg-green-50 text-green-800 border border-green-200" :
      status === "draft" ? "bg-sky-50 text-sky-800 border border-sky-200" :
      "bg-amber-50 text-amber-900 border border-amber-200"}`}>
      {icon}{label}
    </span>
  );
}

function FilingRow({ label, status, onMark, testid }) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="font-semibold">{label}</div>
        <StatusPill status={status}/>
      </div>
      <div className="flex gap-1.5">
        {status !== "filed" && (
          <Button size="sm" onClick={() => onMark("filed")} data-testid={`${testid}-file`}>Mark filed</Button>
        )}
        {status === "filed" && (
          <Button size="sm" variant="outline" onClick={() => onMark("pending")} data-testid={`${testid}-reopen`}>Reopen</Button>
        )}
      </div>
    </div>
  );
}

function KV({ label, value, accent }) {
  return (
    <div className={`rounded-lg p-3 border ${accent ? "bg-ink text-paper border-ink" : "bg-white border-[#E7E5E4]"}`}>
      <div className={`text-[10px] font-bold uppercase tracking-widest ${accent ? "text-ochre" : "text-stone-500"}`}>{label}</div>
      <div className="font-heading text-lg font-black mt-1">{value}</div>
    </div>
  );
}

function InviteModal({ onClose, onDone }) {
  const [f, setF] = useState({ name: "", business_name: "", email: "", phone: "", gstin: "", city: "" });
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const submit = async (e) => {
    e.preventDefault();
    if (!f.name || (!f.email && !f.phone)) { toast.error("Naam + email ya phone zaroori"); return; }
    setBusy(true);
    try {
      await api.post("/ca/clients/invite", f);
      toast.success("Client add ho gaya! Aap unhe manually WhatsApp par invite kar sakte hain.");
      onDone();
    } catch (err) { toast.error(err.response?.data?.detail || "Invite fail"); }
    finally { setBusy(false); }
  };
  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
      <Card className="max-w-lg w-full p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h2 className="font-heading text-2xl font-black">Invite a client</h2>
          <button onClick={onClose}><X className="w-5 h-5"/></button>
        </div>
        <p className="text-stone-600 text-sm mt-1">Client ki basic details bharo. Woh HisaabBot pe login karke apna data upload kar sakenge.</p>
        <form onSubmit={submit} className="mt-4 space-y-3">
          <div className="grid sm:grid-cols-2 gap-3">
            <div><Label>Client naam*</Label><Input value={f.name} onChange={set("name")} required data-testid="invite-name"/></div>
            <div><Label>Business name</Label><Input value={f.business_name} onChange={set("business_name")} data-testid="invite-business"/></div>
            <div><Label>Email</Label><Input type="email" value={f.email} onChange={set("email")} data-testid="invite-email"/></div>
            <div><Label>Phone</Label><Input value={f.phone} onChange={set("phone")} placeholder="+91…" data-testid="invite-phone"/></div>
            <div><Label>GSTIN</Label><Input value={f.gstin} onChange={set("gstin")} style={{textTransform:"uppercase"}} data-testid="invite-gstin"/></div>
            <div><Label>City</Label><Input value={f.city} onChange={set("city")} data-testid="invite-city"/></div>
          </div>
          <div className="flex justify-end gap-2 pt-3">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={busy} data-testid="invite-submit">{busy ? "Adding…" : "Add client"}</Button>
          </div>
        </form>
      </Card>
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
