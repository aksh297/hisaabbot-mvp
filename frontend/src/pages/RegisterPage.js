import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";
import { Button, Input, Label, Card, Select } from "../components/ui/primitives";
import { formatApiErrorDetail } from "../lib/api";

export default function RegisterPage() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    phone: "",
    business_name: "",
    gstin: "",
    city: "",
    language: "hi",
  });
  const [loading, setLoading] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const onSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const payload = { ...form };
      if (!payload.gstin) delete payload.gstin;
      await register(payload);
      toast.success("Account ban gaya! Chaliye dashboard.");
      nav("/app");
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail) || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-paper flex items-center justify-center px-4 py-10">
      <div className="max-w-lg w-full">
        <Link to="/" className="flex items-center gap-2 mb-8" data-testid="signup-brand">
          <div className="w-10 h-10 rounded-lg bg-ink text-white flex items-center justify-center font-heading font-black text-lg">ह</div>
          <div>
            <div className="font-heading font-black text-xl leading-none">HisaabBot</div>
            <div className="text-[10px] text-stone-500 font-mono uppercase tracking-widest">Apna CA · WhatsApp pe</div>
          </div>
        </Link>
        <Card className="p-8">
          <h1 className="font-heading text-3xl font-black text-ink">Free account banaayein</h1>
          <p className="text-stone-600 mt-1">Pehla mahina bilkul free. Card ki zaroorat nahi.</p>
          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <Label>Aapka naam</Label>
                <Input value={form.name} onChange={set("name")} required data-testid="signup-name-input"/>
              </div>
              <div>
                <Label>Business name</Label>
                <Input value={form.business_name} onChange={set("business_name")} placeholder="e.g. Sharma Textiles" data-testid="signup-business-input"/>
              </div>
            </div>
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <Label>Email</Label>
                <Input type="email" value={form.email} onChange={set("email")} required data-testid="signup-email-input"/>
              </div>
              <div>
                <Label>Phone (WhatsApp)</Label>
                <Input value={form.phone} onChange={set("phone")} placeholder="+91 98765 43210" data-testid="signup-phone-input"/>
              </div>
            </div>
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <Label>GSTIN (optional)</Label>
                <Input value={form.gstin} onChange={set("gstin")} placeholder="08AABCU9603R1ZM" style={{textTransform:"uppercase"}} data-testid="signup-gstin-input"/>
              </div>
              <div>
                <Label>City</Label>
                <Input value={form.city} onChange={set("city")} placeholder="Jaipur" data-testid="signup-city-input"/>
              </div>
            </div>
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <Label>Language preference</Label>
                <Select value={form.language} onChange={set("language")} data-testid="signup-language-select">
                  <option value="hi">Hindi</option>
                  <option value="en">English</option>
                  <option value="mr">Marathi</option>
                  <option value="ta">Tamil</option>
                  <option value="gu">Gujarati</option>
                </Select>
              </div>
              <div>
                <Label>Password</Label>
                <Input type="password" value={form.password} onChange={set("password")} required minLength={6} data-testid="signup-password-input"/>
              </div>
            </div>
            <Button type="submit" className="w-full" disabled={loading} data-testid="signup-submit-btn">
              {loading ? "Loading…" : "Free account banaayein"}
            </Button>
          </form>
          <div className="mt-4 text-center text-sm text-stone-600">
            Pehle se account hai?{" "}
            <Link to="/login" className="font-semibold text-ink hover:underline" data-testid="signup-login-link">Login karein</Link>
          </div>
        </Card>
      </div>
    </div>
  );
}
