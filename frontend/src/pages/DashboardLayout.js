import React, { useState } from "react";
import { NavLink, Outlet, useNavigate, Link } from "react-router-dom";
import {
  LayoutDashboard, MessageCircle, FileText, ShieldCheck, IndianRupee, Mic,
  Settings, LogOut, Menu, X, Users
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { Button, Badge } from "../components/ui/primitives";
import { cn } from "../lib/utils";

const NAV_VENDOR = [
  { to: "/app", end: true, icon: LayoutDashboard, label: "Dashboard", testid: "nav-dashboard" },
  { to: "/app/chat", icon: MessageCircle, label: "Chat playground", testid: "nav-chat" },
  { to: "/app/invoices", icon: FileText, label: "Invoices", testid: "nav-invoices" },
  { to: "/app/gst", icon: ShieldCheck, label: "GST returns", testid: "nav-gst" },
  { to: "/app/upi", icon: IndianRupee, label: "UPI reconciliation", testid: "nav-upi" },
  { to: "/app/voice", icon: Mic, label: "Voice notes", testid: "nav-voice" },
  { to: "/app/settings", icon: Settings, label: "Settings", testid: "nav-settings" },
];

const NAV_CA = [
  { to: "/app/clients", end: true, icon: Users, label: "Clients", testid: "nav-clients" },
  { to: "/app/chat", icon: MessageCircle, label: "Chat playground", testid: "nav-chat" },
  { to: "/app/settings", icon: Settings, label: "Settings", testid: "nav-settings" },
];

export default function DashboardLayout() {
  const { user, logout } = useAuth();
  const nvg = useNavigate();
  const [open, setOpen] = useState(false);
  const nav = user?.role === "ca" ? NAV_CA : NAV_VENDOR;

  const doLogout = async () => {
    await logout();
    nvg("/");
  };

  return (
    <div className="min-h-screen bg-paper text-ink flex">
      {/* Sidebar */}
      <aside className={cn(
        "fixed lg:static inset-y-0 left-0 z-30 w-72 bg-ink text-paper flex flex-col transition-transform duration-300",
        open ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
      )}>
        <div className="px-5 py-5 border-b border-inkhover flex items-center justify-between">
          <Link to="/app" className="flex items-center gap-2" data-testid="sidebar-brand">
            <div className="w-9 h-9 rounded-lg bg-ochre text-ink flex items-center justify-center font-heading font-black">ह</div>
            <div>
              <div className="font-heading font-black text-lg leading-none">HisaabBot</div>
              <div className="text-[10px] text-stone-300 font-mono uppercase tracking-widest">Dashboard</div>
            </div>
          </Link>
          <button className="lg:hidden text-paper" onClick={() => setOpen(false)}><X className="w-5 h-5"/></button>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {nav.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-semibold transition-colors",
                  isActive ? "bg-ochre text-ink" : "text-stone-200 hover:bg-inkhover"
                )
              }
              data-testid={n.testid}
            >
              <n.icon className="w-4 h-4" /> {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-inkhover">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-full bg-ochre text-ink flex items-center justify-center font-heading font-black">
              {(user?.name || "U").charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0">
              <div className="font-semibold truncate">{user?.name || "User"}</div>
              <div className="text-xs text-stone-300 truncate">{user?.business_name || user?.email}</div>
            </div>
          </div>
          <Button variant="outline" className="w-full !border-inkhover !text-paper hover:!bg-inkhover" onClick={doLogout} data-testid="logout-btn">
            <LogOut className="w-4 h-4 mr-2"/> Logout
          </Button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 min-w-0 flex flex-col">
        {/* topbar */}
        <div className="sticky top-0 z-20 backdrop-blur-xl bg-paper/80 border-b border-[#E7E5E4] px-5 lg:px-8 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button className="lg:hidden" onClick={() => setOpen(true)} data-testid="sidebar-open"><Menu className="w-5 h-5"/></button>
            <div>
              <div className="text-xs font-mono uppercase tracking-widest text-stone-500">
                {user?.business_name || "HisaabBot"}
              </div>
              <div className="text-sm font-semibold">{user?.gstin ? `GSTIN: ${user.gstin}` : "GSTIN not set"}</div>
            </div>
          </div>
          <div className="hidden sm:flex items-center gap-2">
            <Badge tone="ochre">Beta · Simulated GST</Badge>
          </div>
        </div>

        <main className="flex-1 p-5 lg:p-8 overflow-x-hidden">
          <Outlet />
        </main>
      </div>

      {open && <div className="fixed inset-0 bg-black/40 z-20 lg:hidden" onClick={() => setOpen(false)} />}
    </div>
  );
}
