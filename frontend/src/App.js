import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "./context/AuthContext";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DashboardLayout from "./pages/DashboardLayout";
import DashboardHome from "./pages/DashboardHome";
import ChatPlayground from "./pages/ChatPlayground";
import InvoicesPage from "./pages/InvoicesPage";
import GstReturnsPage from "./pages/GstReturnsPage";
import UpiReconPage from "./pages/UpiReconPage";
import VoicePage from "./pages/VoicePage";
import SettingsPage from "./pages/SettingsPage";
import CADashboard from "./pages/CADashboard";

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading || user === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-paper">
        <div className="text-ink font-semibold">Loading HisaabBot…</div>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster
          position="top-right"
          toastOptions={{
            style: { background: "#1E3F33", color: "#FDFBF7", border: "1px solid #2A5244" },
          }}
        />
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<RegisterPage />} />
          <Route
            path="/app"
            element={
              <Protected>
                <DashboardLayout />
              </Protected>
            }
          >
            <Route index element={<DashboardHome />} />
            <Route path="chat" element={<ChatPlayground />} />
            <Route path="invoices" element={<InvoicesPage />} />
            <Route path="gst" element={<GstReturnsPage />} />
            <Route path="upi" element={<UpiReconPage />} />
            <Route path="voice" element={<VoicePage />} />
            <Route path="clients" element={<CADashboard />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
