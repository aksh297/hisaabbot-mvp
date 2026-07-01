import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  MessageCircle, Camera, Mic, FileText, ShieldCheck, IndianRupee,
  Zap, ArrowRight, Check, Sparkles, BadgeCheck, Store, TrendingUp
} from "lucide-react";
import { Button, Card, Badge } from "../components/ui/primitives";

const heroImg = "https://images.pexels.com/photos/35317008/pexels-photo-35317008.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-paper text-ink">
      {/* Nav */}
      <header className="sticky top-0 z-40 backdrop-blur-xl bg-paper/80 border-b border-[#E7E5E4]/60">
        <div className="max-w-7xl mx-auto px-5 sm:px-8 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2" data-testid="brand-link">
            <div className="w-9 h-9 rounded-lg bg-ink text-white flex items-center justify-center font-heading font-black">ह</div>
            <div>
              <div className="font-heading font-black text-lg leading-none">HisaabBot</div>
              <div className="text-[10px] text-stone-500 font-mono uppercase tracking-widest">Apna CA · WhatsApp pe</div>
            </div>
          </Link>
          <nav className="hidden md:flex items-center gap-8 text-sm font-semibold text-stone-700">
            <a href="#how" className="hover:text-ink" data-testid="nav-how">Kaise kaam karta hai</a>
            <a href="#features" className="hover:text-ink" data-testid="nav-features">Features</a>
            <a href="#pricing" className="hover:text-ink" data-testid="nav-pricing">Pricing</a>
            <a href="#ca" className="hover:text-ink" data-testid="nav-ca">For CAs</a>
          </nav>
          <div className="flex items-center gap-2">
            <Link to="/login"><Button variant="ghost" size="sm" data-testid="nav-login-btn">Login</Button></Link>
            <Link to="/signup"><Button size="sm" data-testid="nav-signup-btn">Shuru karein</Button></Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="max-w-7xl mx-auto px-5 sm:px-8 pt-14 sm:pt-20 pb-16 grid lg:grid-cols-12 gap-10 items-center">
          <motion.div initial={{opacity:0, y:20}} animate={{opacity:1, y:0}} transition={{duration:0.6}} className="lg:col-span-7">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-ochrelight border border-ochre/30 text-ink text-xs font-bold">
              <Sparkles className="w-3.5 h-3.5" /> Bharat's first WhatsApp-native CA
            </div>
            <h1 className="font-heading text-5xl sm:text-6xl lg:text-7xl font-black leading-[0.95] tracking-tight mt-5">
              Apna CA,<br />
              <span className="text-ochre">WhatsApp</span> pe.
            </h1>
            <p className="mt-6 text-lg sm:text-xl text-stone-700 max-w-xl leading-relaxed">
              Invoice ki <b>photo</b> bhejo, Hindi mein <b>voice note</b> bolo — HisaabBot GST filing, bookkeeping aur UPI reconciliation sab kar deta hai. Sirf <b>₹999/month</b>. Pehla mahina free.
            </p>
            <div className="mt-8 flex flex-col sm:flex-row gap-3">
              <Link to="/signup"><Button size="lg" className="w-full sm:w-auto" data-testid="hero-signup-btn">
                <MessageCircle className="w-5 h-5 mr-2" /> Free mein try karein
              </Button></Link>
              <a href="#how"><Button size="lg" variant="outline" className="w-full sm:w-auto" data-testid="hero-how-btn">
                Kaise kaam karta hai <ArrowRight className="w-4 h-4 ml-2" />
              </Button></a>
            </div>
            <div className="mt-8 flex flex-wrap gap-5 text-sm text-stone-600">
              <div className="flex items-center gap-2"><Check className="w-4 h-4 text-green-700"/>Hindi + English + Hinglish</div>
              <div className="flex items-center gap-2"><Check className="w-4 h-4 text-green-700"/>Zero app download</div>
              <div className="flex items-center gap-2"><Check className="w-4 h-4 text-green-700"/>UPI-integrated</div>
            </div>
          </motion.div>

          {/* Right: WhatsApp chat mock */}
          <motion.div initial={{opacity:0, y:20}} animate={{opacity:1, y:0}} transition={{duration:0.7, delay:0.15}} className="lg:col-span-5">
            <PhoneMock />
          </motion.div>
        </div>
        {/* decorative */}
        <div aria-hidden className="pointer-events-none absolute -top-24 -right-32 w-[500px] h-[500px] rounded-full bg-ochrelight/40 blur-3xl" />
      </section>

      {/* Trust bar */}
      <section className="border-y border-[#E7E5E4] bg-parchment/40">
        <div className="max-w-7xl mx-auto px-5 sm:px-8 py-5 grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
          <Stat value="1.6 Cr+" label="GST taxpayers in India" />
          <Stat value="₹50/day" label="Late filing penalty" />
          <Stat value="3x sasta" label="Local CA se kam" />
          <Stat value="2 sec" label="Photo → invoice entry" />
        </div>
      </section>

      {/* How */}
      <section id="how" className="max-w-7xl mx-auto px-5 sm:px-8 py-20">
        <SectionHeader kicker="3 SIMPLE STEPS" title="Kaise kaam karta hai" />
        <div className="grid md:grid-cols-3 gap-6 mt-10">
          {[
            { i: <Camera className="w-6 h-6"/>, t: "Photo bhejo", d: "Invoice ki photo WhatsApp pe bhejo. GPT-4o vision se AI vendor, GSTIN, amount, HSN aur tax nikaalta hai." },
            { i: <Mic className="w-6 h-6"/>, t: "Ya voice bolo", d: "\"Sharma Textiles se 50,000 ka maal aaya, 12% GST\" — Whisper AI Hindi/Hinglish samajhta hai." },
            { i: <FileText className="w-6 h-6"/>, t: "GST ready", d: "GSTR-1 aur 3B automatically calculate. UPI receipts match. Filing date se pehle reminder." },
          ].map((s, idx) => (
            <Card key={idx} className="p-6 grain">
              <div className="w-11 h-11 rounded-lg bg-ink text-white flex items-center justify-center">{s.i}</div>
              <h3 className="mt-4 font-heading text-2xl font-bold">{s.t}</h3>
              <p className="mt-2 text-stone-600 leading-relaxed">{s.d}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* Features bento */}
      <section id="features" className="bg-parchment/60 py-20 border-y border-[#E7E5E4]">
        <div className="max-w-7xl mx-auto px-5 sm:px-8">
          <SectionHeader kicker="EVERYTHING YOUR CA DOES" title="Full-service compliance, ek chat mein" />
          <div className="grid md:grid-cols-6 gap-5 mt-10">
            <FeatureCard className="md:col-span-3" icon={<Camera/>} title="Invoice OCR" desc="GPT-4o vision Hindi + English mixed bills se vendor, GSTIN, HSN, tax auto-extract karta hai." image={heroImg} />
            <FeatureCard className="md:col-span-3" icon={<ShieldCheck/>} title="GSTR-1 + 3B engine" desc="CGST / SGST / IGST logic built-in. ITC reconciliation. Deadline countdown. Simulated JSON export." />
            <FeatureCard className="md:col-span-2" icon={<Mic/>} title="Voice notes" desc={"Hindi/Hinglish transcription (Whisper). 'Aaj ki bikri 25,000' bolo — entry ho jaayegi."} />
            <FeatureCard className="md:col-span-2" icon={<IndianRupee/>} title="UPI reconciliation" desc="Payment screenshot → auto-match invoice ke saath. Cash-flow visible." />
            <FeatureCard className="md:col-span-2" icon={<Zap/>} title="Deadline reminders" desc="GSTR-1 (11 tarikh) aur 3B (20 tarikh) se 5 din pehle alert. Penalty se bacho." />
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="max-w-7xl mx-auto px-5 sm:px-8 py-20">
        <SectionHeader kicker="PRICING" title="Sasta, seedha, no hidden charges" />
        <div className="grid md:grid-cols-4 gap-5 mt-10">
          <Price plan="Free" price="₹0" period="hamesha" bullets={["10 invoices/month", "GST reminders", "Basic dashboard"]} />
          <Price plan="Starter" price="₹999" period="/month" popular bullets={["Unlimited invoices", "GSTR-1 + 3B prep", "UPI reconciliation", "Hindi + English", "Priority chat"]} />
          <Price plan="Pro" price="₹1,999" period="/month" bullets={["Everything in Starter", "Auto-filing (via GSP)", "ITC reconciliation", "All Indian languages"]} />
          <Price plan="CA Plan" price="₹499" period="/client/mo" bullets={["Bulk client dashboard", "White-label option", "Priority support", "Custom exports"]} />
        </div>
        <p className="mt-6 text-xs text-stone-500 text-center">*Payments via UPI autopay (Razorpay). Cancel anytime. GST included where applicable.</p>
      </section>

      {/* CA section */}
      <section id="ca" className="bg-ink text-paper py-20">
        <div className="max-w-7xl mx-auto px-5 sm:px-8 grid md:grid-cols-2 gap-10 items-center">
          <div>
            <Badge tone="ochre">FOR CA'S & ACCOUNTANTS</Badge>
            <h2 className="font-heading text-4xl sm:text-5xl font-black mt-4 leading-tight">
              40+ clients ek dashboard se manage karo.
            </h2>
            <p className="mt-4 text-stone-300 leading-relaxed">
              Clients khud invoices bhej dete hain WhatsApp par. Aap sirf review karo, file karo. Zero chase-up. Extra revenue.
            </p>
            <ul className="mt-6 space-y-2 text-stone-200">
              <li className="flex items-start gap-2"><Check className="w-5 h-5 text-ochre mt-0.5"/> Bulk filing dashboard</li>
              <li className="flex items-start gap-2"><Check className="w-5 h-5 text-ochre mt-0.5"/> Reseller commission ₹200/client/month</li>
              <li className="flex items-start gap-2"><Check className="w-5 h-5 text-ochre mt-0.5"/> White-label with your firm's name</li>
            </ul>
            <Link to="/signup" className="inline-block mt-8"><Button variant="secondary" size="lg" data-testid="ca-signup-btn">CA plan sign-up</Button></Link>
          </div>
          <Card className="bg-inkhover border-inkhover text-paper p-6">
            <div className="text-xs font-bold uppercase text-ochre tracking-widest">Sample dashboard</div>
            <div className="mt-4 space-y-3">
              {[
                { name: "Sharma Textiles", status: "GSTR-1 pending", tone: "warning" },
                { name: "Verma Traders", status: "Filed", tone: "success" },
                { name: "Kailash Kirana", status: "Draft ready", tone: "info" },
                { name: "Bharat Kapda", status: "GSTR-3B due 3d", tone: "warning" },
              ].map((c, i) => (
                <div key={i} className="flex justify-between items-center bg-ink rounded-lg px-4 py-3 border border-inkhover">
                  <div className="flex items-center gap-3">
                    <Store className="w-4 h-4 text-ochre"/>
                    <span className="font-semibold">{c.name}</span>
                  </div>
                  <Badge tone={c.tone}>{c.status}</Badge>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-paper border-t border-[#E7E5E4]">
        <div className="max-w-7xl mx-auto px-5 sm:px-8 py-10 grid md:grid-cols-3 gap-6 text-sm text-stone-600">
          <div>
            <div className="font-heading font-black text-lg text-ink">HisaabBot</div>
            <p className="mt-2">Built with ❤ for Bharat's small business owners.</p>
          </div>
          <div>
            <div className="font-semibold text-ink">Product</div>
            <ul className="mt-2 space-y-1">
              <li><a href="#features" className="hover:text-ink">Features</a></li>
              <li><a href="#pricing" className="hover:text-ink">Pricing</a></li>
              <li><a href="#ca" className="hover:text-ink">For CAs</a></li>
            </ul>
          </div>
          <div>
            <div className="font-semibold text-ink">Company</div>
            <ul className="mt-2 space-y-1">
              <li>© 2026 HisaabBot</li>
              <li>Made in India · Data in Mumbai</li>
            </ul>
          </div>
        </div>
      </footer>
    </div>
  );
}

function Stat({ value, label }) {
  return (
    <div>
      <div className="font-heading text-3xl sm:text-4xl font-black text-ink">{value}</div>
      <div className="text-xs sm:text-sm text-stone-600 mt-1">{label}</div>
    </div>
  );
}

function SectionHeader({ kicker, title }) {
  return (
    <div className="text-left">
      <div className="text-xs font-bold uppercase tracking-[0.25em] text-ochre">{kicker}</div>
      <h2 className="font-heading text-3xl sm:text-5xl font-black text-ink mt-2 max-w-3xl leading-tight">{title}</h2>
    </div>
  );
}

function FeatureCard({ icon, title, desc, className = "", image }) {
  return (
    <Card className={`p-6 relative overflow-hidden ${className}`}>
      <div className="w-10 h-10 rounded-lg bg-ochrelight text-ink flex items-center justify-center">{icon}</div>
      <h3 className="mt-4 font-heading text-xl font-bold">{title}</h3>
      <p className="mt-2 text-stone-600 leading-relaxed">{desc}</p>
      {image && (
        <div className="mt-5 rounded-lg overflow-hidden border border-[#E7E5E4] aspect-video">
          <img src={image} alt="" className="w-full h-full object-cover"/>
        </div>
      )}
    </Card>
  );
}

function Price({ plan, price, period, bullets, popular }) {
  return (
    <Card className={`p-6 relative ${popular ? "ring-2 ring-ink" : ""}`}>
      {popular && (
        <div className="absolute -top-3 left-6"><Badge tone="ochre">MOST POPULAR</Badge></div>
      )}
      <div className="text-sm font-bold uppercase tracking-widest text-stone-500">{plan}</div>
      <div className="mt-3 flex items-baseline gap-1">
        <span className="font-heading text-4xl font-black text-ink">{price}</span>
        <span className="text-stone-500 text-sm">{period}</span>
      </div>
      <ul className="mt-5 space-y-2 text-sm text-stone-700">
        {bullets.map((b, i) => (
          <li key={i} className="flex items-start gap-2"><BadgeCheck className="w-4 h-4 text-green-700 mt-0.5"/>{b}</li>
        ))}
      </ul>
      <Link to="/signup" className="block mt-6"><Button className="w-full" variant={popular ? "primary" : "outline"} data-testid={`pricing-${plan.toLowerCase()}-btn`}>
        Choose {plan}
      </Button></Link>
    </Card>
  );
}

function PhoneMock() {
  const bubbles = [
    { from: "user", text: "Namaste bhai", ts: "10:00" },
    { from: "bot", text: "Namaste! Main HisaabBot hoon 👋 Aapka digital CA. Shuru karne ke liye apna GSTIN bhejiye.", ts: "10:00" },
    { from: "user", text: "08AABCU9603R1ZM", ts: "10:01" },
    { from: "bot", text: "Verified ✅ Aap **Sharma Textiles** hain, Jaipur. Aaj se aap invoices ki photo bhej sakte hain.", ts: "10:01" },
    { from: "user", text: "📷 [invoice photo bheji]", ts: "10:02" },
    { from: "bot", text: "Padha! Vendor: Kailash Textiles, Amount: ₹50,400 (12% GST). Purchase register mein add karoon?", ts: "10:02" },
  ];
  return (
    <div className="relative">
      <div className="mx-auto max-w-sm rounded-[2.5rem] border-[10px] border-ink bg-ink shadow-2xl overflow-hidden">
        <div className="bg-wadark text-white px-4 py-3 flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-wagreen flex items-center justify-center font-heading font-black">H</div>
          <div>
            <div className="font-semibold text-sm">HisaabBot</div>
            <div className="text-[10px] opacity-75">online · replies in seconds</div>
          </div>
        </div>
        <div className="bg-chatbg bg-chat-pattern bg-blend-multiply p-4 h-[440px] overflow-y-auto space-y-2">
          {bubbles.map((b, i) => (
            <div key={i} className={`flex ${b.from === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[80%] px-3 py-2 rounded-lg text-sm shadow-sm ${b.from === "user" ? "bg-wamsg text-ink" : "bg-white text-ink"}`}>
                <div dangerouslySetInnerHTML={{ __html: b.text.replace(/\*\*(.*?)\*\*/g, "<b>$1</b>") }} />
                <div className="text-[10px] text-stone-500 mt-1 text-right">{b.ts}</div>
              </div>
            </div>
          ))}
        </div>
        <div className="bg-[#F0F0F0] px-3 py-3 flex items-center gap-2">
          <div className="flex-1 bg-white rounded-full px-4 py-2 text-sm text-stone-400">Message HisaabBot…</div>
          <div className="w-9 h-9 rounded-full bg-wagreen flex items-center justify-center text-white">
            <TrendingUp className="w-4 h-4"/>
          </div>
        </div>
      </div>
    </div>
  );
}
