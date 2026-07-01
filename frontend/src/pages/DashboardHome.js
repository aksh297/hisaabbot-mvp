import React, { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import {
  TrendingUp, TrendingDown, IndianRupee, Calendar, ArrowRight, Camera, Mic, MessageCircle
} from "lucide-react";
import api from "../lib/api";
import { Card, Button, Badge } from "../components/ui/primitives";
import { fmtINR } from "../lib/utils";
import { useAuth } from "../context/AuthContext";

export default function DashboardHome() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  // CA users go straight to bulk client view
  useEffect(() => {
    if (user?.role === "ca") return;
    api.get("/dashboard/summary").then((r) => setData(r.data)).finally(() => setLoading(false));
  }, [user?.role]);

  if (user?.role === "ca") return <Navigate to="/app/clients" replace/>;
  if (loading) return <div className="text-stone-500">Loading dashboard…</div>;
  if (!data) return <div className="text-terracotta">Dashboard load nahi ho paya.</div>;

  const monthProfit = data.month.profit;

  return (
    <div className="space-y-8" data-testid="dashboard-home">
      <div>
        <div className="text-xs font-bold uppercase tracking-widest text-ochre">HOME</div>
        <h1 className="font-heading text-4xl sm:text-5xl font-black text-ink mt-1">Aapka aaj ka hisaab</h1>
        <p className="text-stone-600 mt-2">Ek nazar mein sab kuch — sales, purchase, UPI aur GST deadlines.</p>
      </div>

      {/* Today */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5 stagger">
        <StatCard
          icon={<TrendingUp className="w-5 h-5"/>}
          label="Aaj ki bikri"
          value={fmtINR(data.today.sales.total)}
          hint={`${data.today.sales.count} invoice`}
          tone="success"
          testid="stat-today-sales"
        />
        <StatCard
          icon={<TrendingDown className="w-5 h-5"/>}
          label="Aaj ki khareedari"
          value={fmtINR(data.today.purchase.total)}
          hint={`${data.today.purchase.count} invoice`}
          tone="warning"
          testid="stat-today-purchase"
        />
        <StatCard
          icon={<IndianRupee className="w-5 h-5"/>}
          label="Is mahine UPI aaya"
          value={fmtINR(data.upi_month.total)}
          hint={`${data.upi_month.count} transactions`}
          tone="info"
          testid="stat-upi-month"
        />
        <StatCard
          icon={<Calendar className="w-5 h-5"/>}
          label="Is mahine profit"
          value={fmtINR(monthProfit)}
          hint={`Sales - Purchase`}
          tone={monthProfit >= 0 ? "success" : "danger"}
          testid="stat-month-profit"
        />
      </div>

      {/* Monthly + deadlines */}
      <div className="grid lg:grid-cols-3 gap-5">
        <Card className="p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-xs font-bold uppercase tracking-widest text-stone-500">MONTH-TO-DATE</div>
              <h2 className="font-heading text-2xl font-bold text-ink mt-1">Is mahine ka summary</h2>
            </div>
            <Link to="/app/gst"><Button size="sm" variant="outline">GST returns dekho <ArrowRight className="w-4 h-4 ml-1.5"/></Button></Link>
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            <MiniStat label="Total sales" value={fmtINR(data.month.sales.total)} sub={`${data.month.sales.count} bikri invoices`} accent="ochre"/>
            <MiniStat label="Total purchase" value={fmtINR(data.month.purchase.total)} sub={`${data.month.purchase.count} khareed invoices`} accent="ink"/>
          </div>
        </Card>

        <Card className="p-6">
          <div className="text-xs font-bold uppercase tracking-widest text-stone-500">FILING DEADLINES</div>
          <h2 className="font-heading text-2xl font-bold text-ink mt-1">Agli tareekh</h2>
          <div className="mt-4 space-y-3">
            {(data.deadlines || []).map((d, i) => (
              <div key={i} className="flex items-center justify-between p-3 rounded-lg border border-[#E7E5E4] bg-white">
                <div>
                  <div className="font-semibold">{d.return_type}</div>
                  <div className="text-xs text-stone-500">Period {d.period}</div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-mono">{d.due_date}</div>
                  <Badge tone={d.days_left <= 5 ? "danger" : d.days_left <= 10 ? "warning" : "success"}>
                    {d.days_left} din baaki
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Quick actions */}
      <div>
        <div className="text-xs font-bold uppercase tracking-widest text-ochre">QUICK ACTIONS</div>
        <h2 className="font-heading text-2xl font-bold text-ink mt-1 mb-4">Aage kya karna hai?</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <QuickAction to="/app/chat" icon={<MessageCircle/>} title="WhatsApp chat try karein" desc="Bot ke saath baat karo — Hindi mein bhi." testid="qa-chat"/>
          <QuickAction to="/app/invoices" icon={<Camera/>} title="Invoice ki photo upload" desc="OCR se auto-entry — 2 sec mein." testid="qa-invoice"/>
          <QuickAction to="/app/voice" icon={<Mic/>} title="Voice note bhejo" desc="Whisper AI Hindi/Hinglish samajhta hai." testid="qa-voice"/>
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, hint, tone = "default", testid }) {
  const toneMap = {
    success: "bg-green-50 text-green-800 border-green-200",
    warning: "bg-amber-50 text-amber-900 border-amber-200",
    info: "bg-sky-50 text-sky-800 border-sky-200",
    danger: "bg-red-50 text-red-800 border-red-200",
    default: "bg-parchment text-ink border-[#E7E5E4]",
  };
  return (
    <Card className="p-5" data-testid={testid}>
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center border ${toneMap[tone]}`}>{icon}</div>
      <div className="mt-4 text-xs font-bold uppercase tracking-widest text-stone-500">{label}</div>
      <div className="font-heading text-3xl font-black text-ink mt-1">{value}</div>
      <div className="text-xs text-stone-500 mt-1">{hint}</div>
    </Card>
  );
}

function MiniStat({ label, value, sub, accent }) {
  const accentBg = accent === "ochre" ? "bg-ochrelight" : "bg-ink text-paper";
  return (
    <div className="rounded-lg border border-[#E7E5E4] p-4 bg-white">
      <div className={`inline-block px-2 py-0.5 text-xs font-bold rounded ${accentBg}`}>{label}</div>
      <div className="font-heading text-2xl font-black text-ink mt-2">{value}</div>
      <div className="text-xs text-stone-500 mt-1">{sub}</div>
    </div>
  );
}

function QuickAction({ to, icon, title, desc, testid }) {
  return (
    <Link to={to} className="block" data-testid={testid}>
      <Card className="p-5 hover:-translate-y-0.5 transition-transform h-full">
        <div className="w-10 h-10 rounded-lg bg-ochrelight text-ink flex items-center justify-center">{icon}</div>
        <h3 className="font-heading text-lg font-bold mt-3">{title}</h3>
        <p className="text-stone-600 text-sm mt-1">{desc}</p>
        <div className="mt-3 text-sm font-semibold text-ink flex items-center gap-1">Chalein <ArrowRight className="w-4 h-4"/></div>
      </Card>
    </Link>
  );
}
