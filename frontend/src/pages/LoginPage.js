import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";
import { Button, Input, Label, Card } from "../components/ui/primitives";
import { formatApiErrorDetail } from "../lib/api";

export default function LoginPage() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("ramesh@hisaabbot.in");
  const [password, setPassword] = useState("demo123");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email, password);
      toast.success("Swagat hai! Dashboard le chalte hain.");
      nav("/app");
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail) || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-paper flex items-center justify-center px-4">
      <div className="max-w-md w-full">
        <Link to="/" className="flex items-center gap-2 mb-8" data-testid="login-brand">
          <div className="w-10 h-10 rounded-lg bg-ink text-white flex items-center justify-center font-heading font-black text-lg">ह</div>
          <div>
            <div className="font-heading font-black text-xl leading-none">HisaabBot</div>
            <div className="text-[10px] text-stone-500 font-mono uppercase tracking-widest">Apna CA · WhatsApp pe</div>
          </div>
        </Link>
        <Card className="p-8">
          <h1 className="font-heading text-3xl font-black text-ink">Wapas swagat hai</h1>
          <p className="text-stone-600 mt-1">Apna account access karein.</p>
          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            <div>
              <Label>Email</Label>
              <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required data-testid="login-email-input" />
            </div>
            <div>
              <Label>Password</Label>
              <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required data-testid="login-password-input" />
            </div>
            <Button type="submit" className="w-full" disabled={loading} data-testid="login-submit-btn">
              {loading ? "Loading…" : "Login karein"}
            </Button>
          </form>
          <div className="mt-4 rounded-lg bg-parchment/60 border border-[#E7E5E4] px-3 py-2 text-xs text-stone-600">
            <b>Demo login:</b> ramesh@hisaabbot.in / demo123
          </div>
          <div className="mt-4 text-center text-sm text-stone-600">
            Account nahi hai?{" "}
            <Link to="/signup" className="font-semibold text-ink hover:underline" data-testid="login-signup-link">Sign up karein</Link>
          </div>
        </Card>
      </div>
    </div>
  );
}
