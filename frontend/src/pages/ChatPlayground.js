import React, { useEffect, useRef, useState } from "react";
import { Paperclip, Send, Camera, User, Sparkles } from "lucide-react";
import api from "../lib/api";
import { Button, Card } from "../components/ui/primitives";
import { fmtINR } from "../lib/utils";
import { toast } from "sonner";

export default function ChatPlayground() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [imgB64, setImgB64] = useState(null);
  const [imgPreview, setImgPreview] = useState(null);
  const sessionIdRef = useRef(`chat-${Date.now()}`);
  const scrollRef = useRef(null);

  useEffect(() => {
    // Seed greeting
    setMessages([
      { role: "assistant", text: "Namaste! 🙏 Main HisaabBot hoon — aapka digital CA. Aap invoice ki **photo**, **voice note** ya seedha Hindi/English mein baat kar sakte hain. Shuru karein?", ts: new Date().toISOString() },
    ]);
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const onPickImage = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > 5 * 1024 * 1024) {
      toast.error("Image bahut badi hai (max 5MB)");
      return;
    }
    const b64 = await fileToB64(f);
    setImgB64(b64.split(",")[1]);
    setImgPreview(b64);
  };

  const send = async (e) => {
    e?.preventDefault();
    const text = input.trim();
    if (!text && !imgB64) return;
    setSending(true);
    const userMsg = { role: "user", text: text || "(invoice photo)", ts: new Date().toISOString(), image: imgPreview };
    setMessages((m) => [...m, userMsg, { role: "assistant", text: "…", pending: true }]);
    setInput("");
    const localImg = imgB64;
    setImgB64(null); setImgPreview(null);
    try {
      const res = await api.post("/chat/message", {
        session_id: sessionIdRef.current,
        message: text || "Please review this invoice.",
        image_base64: localImg,
      });
      sessionIdRef.current = res.data.session_id;
      setMessages((m) => [...m.filter((x) => !x.pending), { role: "assistant", text: res.data.reply, ts: new Date().toISOString() }]);
    } catch (err) {
      setMessages((m) => [...m.filter((x) => !x.pending), { role: "assistant", text: "Uf! Kuch gadbad ho gayi. Dubara try karein.", error: true }]);
      toast.error(err.response?.data?.detail || err.message);
    } finally {
      setSending(false);
    }
  };

  const quickChips = [
    "Aaj ki bikri batao",
    "GST filing status kya hai",
    "Aaj ki khareedari 25,000 rupees, 18% GST",
    "HSN code 5208 kya hai?",
  ];

  return (
    <div className="max-w-4xl mx-auto" data-testid="chat-playground">
      <div className="mb-6">
        <div className="text-xs font-bold uppercase tracking-widest text-ochre">WHATSAPP PLAYGROUND</div>
        <h1 className="font-heading text-4xl font-black text-ink mt-1">HisaabBot se baat karein</h1>
        <p className="text-stone-600 mt-1">Yeh ek simulated WhatsApp interface hai. Real WhatsApp integration (Gupshup) production launch pe activate hoga.</p>
      </div>

      <Card className="overflow-hidden">
        {/* Chat header */}
        <div className="bg-wadark text-white px-4 py-3 flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-wagreen flex items-center justify-center font-heading font-black">H</div>
          <div className="flex-1">
            <div className="font-semibold">HisaabBot</div>
            <div className="text-[11px] opacity-75 flex items-center gap-1"><Sparkles className="w-3 h-3"/> Online · GPT-4o powered</div>
          </div>
        </div>

        {/* Messages */}
        <div ref={scrollRef} className="bg-chatbg bg-chat-pattern bg-blend-multiply px-4 py-5 h-[520px] overflow-y-auto space-y-2">
          {messages.map((m, i) => (
            <Bubble key={i} msg={m} />
          ))}
        </div>

        {/* Composer */}
        <form onSubmit={send} className="bg-[#F0F0F0] p-3 space-y-2">
          {imgPreview && (
            <div className="relative inline-block">
              <img src={imgPreview} alt="preview" className="h-24 rounded-lg border border-stone-300"/>
              <button type="button" onClick={() => { setImgB64(null); setImgPreview(null); }} className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-terracotta text-white text-xs" data-testid="chat-remove-image">×</button>
            </div>
          )}
          <div className="flex items-center gap-2">
            <label className="w-10 h-10 rounded-full bg-white flex items-center justify-center border border-stone-300 cursor-pointer hover:bg-stone-50" data-testid="chat-attach-btn">
              <Paperclip className="w-4 h-4 text-stone-600"/>
              <input type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={onPickImage}/>
            </label>
            <input
              className="flex-1 bg-white rounded-full px-4 py-2.5 text-sm border border-stone-300 focus:outline-none focus:border-wagreen"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Message HisaabBot… (Hindi/English)"
              disabled={sending}
              data-testid="chat-input"
            />
            <button type="submit" className="w-10 h-10 rounded-full bg-wagreen text-white flex items-center justify-center hover:bg-wadark disabled:opacity-50" disabled={sending} data-testid="chat-send-btn">
              <Send className="w-4 h-4"/>
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {quickChips.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setInput(c)}
                className="text-xs px-3 py-1.5 rounded-full bg-white border border-stone-300 hover:bg-parchment"
                data-testid={`chip-${c.slice(0,10).replace(/\s/g,'-').toLowerCase()}`}
              >
                {c}
              </button>
            ))}
          </div>
        </form>
      </Card>
    </div>
  );
}

function Bubble({ msg }) {
  const isUser = msg.role === "user";
  const html = (msg.text || "").replace(/\*\*(.*?)\*\*/g, "<b>$1</b>").replace(/\n/g, "<br/>");
  if (msg.pending) {
    return (
      <div className="flex justify-start">
        <div className="bg-white rounded-lg px-3 py-2 flex items-center gap-1 shadow-sm">
          <span className="typing-dot"/><span className="typing-dot"/><span className="typing-dot"/>
        </div>
      </div>
    );
  }
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} animate-fade-up`}>
      <div className={`max-w-[80%] px-3 py-2 rounded-lg text-sm shadow-sm ${isUser ? "bg-wamsg text-ink" : msg.error ? "bg-red-50 text-red-800" : "bg-white text-ink"}`}>
        {msg.image && <img src={msg.image} alt="" className="rounded mb-1 max-h-40 object-cover"/>}
        <div dangerouslySetInnerHTML={{ __html: html }} />
        {msg.ts && <div className="text-[10px] text-stone-500 mt-1 text-right">{new Date(msg.ts).toLocaleTimeString("en-IN",{hour:"2-digit", minute:"2-digit"})}</div>}
      </div>
    </div>
  );
}

function fileToB64(file) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(r.result);
    r.onerror = reject;
    r.readAsDataURL(file);
  });
}
