import React, { useRef, useState } from "react";
import { Mic, Send, Save, StopCircle, Upload } from "lucide-react";
import { toast } from "sonner";
import api from "../lib/api";
import { Card, Button, Textarea, Badge } from "../components/ui/primitives";
import { fmtINR, todayISO } from "../lib/utils";

export default function VoicePage() {
  const [transcript, setTranscript] = useState("");
  const [text, setText] = useState("");
  const [extracted, setExtracted] = useState(null);
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const mediaRef = useRef(null);
  const chunksRef = useRef([]);

  const uploadFile = async (file) => {
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("language", "hi");
      const res = await api.post("/voice/extract", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setTranscript(res.data.transcript || "");
      setExtracted(res.data);
      toast.success("Voice note process ho gaya");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Voice fail");
    } finally { setBusy(false); }
  };

  const onPickFile = (e) => {
    const f = e.target.files?.[0];
    if (f) uploadFile(f);
    e.target.value = "";
  };

  const startRec = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, { mimeType: pickMime() });
      chunksRef.current = [];
      mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      mr.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: mr.mimeType });
        const file = new File([blob], `note.${extFor(mr.mimeType)}`, { type: mr.mimeType });
        stream.getTracks().forEach((t) => t.stop());
        await uploadFile(file);
      };
      mr.start();
      mediaRef.current = mr;
      setRecording(true);
    } catch (e) {
      toast.error("Mic access nahi mila. Text field use karein.");
    }
  };

  const stopRec = () => {
    mediaRef.current?.stop();
    setRecording(false);
  };

  const extractText = async () => {
    if (!text.trim()) { toast.error("Text likhein pehle"); return; }
    setBusy(true);
    try {
      const res = await api.post("/voice/extract-text", { text });
      setTranscript(res.data.transcript || text);
      setExtracted(res.data);
    } catch (err) { toast.error(err.response?.data?.detail || "Extract fail"); }
    finally { setBusy(false); }
  };

  const saveAsInvoice = async () => {
    if (!extracted) return;
    const payload = {
      type: extracted.type === "sales" ? "sales" : "purchase",
      counterparty_name: extracted.counterparty_name || "Unknown",
      counterparty_gstin: extracted.counterparty_gstin || null,
      invoice_number: extracted.invoice_number || null,
      invoice_date: extracted.invoice_date || todayISO(),
      hsn_code: extracted.hsn_code || null,
      taxable_amount: Number(extracted.taxable_amount || 0),
      cgst: Number(extracted.cgst || 0),
      sgst: Number(extracted.sgst || 0),
      igst: Number(extracted.igst || 0),
      total_tax: Number(extracted.total_tax || 0),
      total_amount: Number(extracted.total_amount || 0),
      notes: extracted.notes || transcript,
    };
    try {
      await api.post("/invoices", payload);
      toast.success("Invoice register mein add ho gaya");
      setExtracted(null); setTranscript(""); setText("");
    } catch (err) { toast.error(err.response?.data?.detail || "Save fail"); }
  };

  return (
    <div className="space-y-6 max-w-4xl" data-testid="voice-page">
      <div>
        <div className="text-xs font-bold uppercase tracking-widest text-ochre">VOICE NOTES</div>
        <h1 className="font-heading text-4xl font-black text-ink mt-1">Bol ke invoice banaayein</h1>
        <p className="text-stone-600 mt-1">Hindi, English ya Hinglish — bas bolo. Whisper AI transcribe karega, GPT-4o structured invoice bana dega.</p>
      </div>

      <Card className="p-6">
        <div className="text-xs font-bold uppercase tracking-widest text-stone-500">STEP 1</div>
        <h2 className="font-heading text-2xl font-bold text-ink">Voice input</h2>
        <p className="text-stone-600 mt-1 text-sm">Example: "Aaj Sharma Textiles se 50,000 ka maal aaya, 12% GST"</p>
        <div className="mt-4 flex flex-wrap gap-3 items-center">
          {!recording ? (
            <Button onClick={startRec} disabled={busy} data-testid="voice-record-btn"><Mic className="w-4 h-4 mr-2"/> Recording shuru</Button>
          ) : (
            <Button variant="danger" onClick={stopRec} data-testid="voice-stop-btn"><StopCircle className="w-4 h-4 mr-2"/> Recording rokein</Button>
          )}
          <label className="inline-flex">
            <Button variant="outline" onClick={(e) => e.preventDefault()} data-testid="voice-upload-btn">
              <Upload className="w-4 h-4 mr-2"/> Audio file upload
            </Button>
            <input type="file" accept="audio/mp3,audio/mpeg,audio/wav,audio/webm,audio/m4a,audio/x-m4a" className="sr-only" onChange={onPickFile}/>
          </label>
          {recording && <span className="text-sm text-terracotta animate-pulse">● Recording…</span>}
          {busy && <span className="text-sm text-stone-500">Processing…</span>}
        </div>

        <div className="mt-5">
          <div className="text-xs font-bold uppercase tracking-widest text-stone-500 mb-1.5">OR text mein likho:</div>
          <Textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Aaj ki bikri 25,000 rupees, 18% GST" data-testid="voice-text-input"/>
          <Button className="mt-2" onClick={extractText} disabled={busy} data-testid="voice-extract-text-btn">
            <Send className="w-4 h-4 mr-2"/> Extract karo
          </Button>
        </div>
      </Card>

      {transcript && (
        <Card className="p-6" data-testid="voice-transcript">
          <div className="text-xs font-bold uppercase tracking-widest text-stone-500">STEP 2</div>
          <h2 className="font-heading text-2xl font-bold text-ink">Transcript</h2>
          <div className="mt-3 p-4 rounded-lg bg-parchment/60 border border-[#E7E5E4] italic text-stone-800">"{transcript}"</div>
        </Card>
      )}

      {extracted && (
        <Card className="p-6" data-testid="voice-extracted">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs font-bold uppercase tracking-widest text-stone-500">STEP 3</div>
              <h2 className="font-heading text-2xl font-bold text-ink">Structured data</h2>
            </div>
            <Badge tone={extracted.confidence > 0.7 ? "success" : "warning"}>Confidence: {Math.round((extracted.confidence || 0) * 100)}%</Badge>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-4">
            <KV label="Type" value={extracted.type || "—"}/>
            <KV label="Party" value={extracted.counterparty_name || "—"}/>
            <KV label="Date" value={extracted.invoice_date || "—"}/>
            <KV label="Taxable" value={fmtINR(extracted.taxable_amount || 0)}/>
            <KV label="Tax rate" value={extracted.tax_rate ? `${extracted.tax_rate}%` : "—"}/>
            <KV label="Total tax" value={fmtINR(extracted.total_tax || 0)}/>
            <KV label="Total amount" value={fmtINR(extracted.total_amount || 0)}/>
          </div>
          <div className="mt-5 flex justify-end">
            <Button onClick={saveAsInvoice} data-testid="voice-save-invoice-btn"><Save className="w-4 h-4 mr-2"/>Invoice register mein save</Button>
          </div>
        </Card>
      )}
    </div>
  );
}

function KV({ label, value }) {
  return (
    <div className="rounded-lg border border-[#E7E5E4] p-3 bg-white">
      <div className="text-[10px] font-bold uppercase tracking-widest text-stone-500">{label}</div>
      <div className="font-semibold text-ink mt-1 text-sm">{value}</div>
    </div>
  );
}

function pickMime() {
  const options = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg"];
  for (const o of options) if (typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(o)) return o;
  return "audio/webm";
}

function extFor(mime) {
  if (mime.includes("webm")) return "webm";
  if (mime.includes("mp4")) return "m4a";
  if (mime.includes("ogg")) return "ogg";
  if (mime.includes("wav")) return "wav";
  return "webm";
}
