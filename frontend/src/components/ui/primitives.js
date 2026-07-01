import React from "react";
import { cn } from "../../lib/utils";

export function Button({ className, variant = "primary", size = "md", children, ...props }) {
  const base = "inline-flex items-center justify-center font-semibold rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-ink";
  const sizes = { sm: "px-3 py-1.5 text-sm", md: "px-5 py-2.5 text-sm", lg: "px-7 py-3.5 text-base" };
  const variants = {
    primary: "bg-ink text-white hover:bg-inkhover shadow-sm hover:shadow",
    secondary: "bg-ochrelight text-ink hover:bg-[#E3BA79]",
    outline: "border border-ink text-ink hover:bg-parchment",
    ghost: "text-ink hover:bg-parchment",
    danger: "bg-terracotta text-white hover:bg-[#a94933]",
    whatsapp: "bg-wagreen text-white hover:bg-wadark shadow",
  };
  return (
    <button className={cn(base, sizes[size], variants[variant], className)} {...props}>
      {children}
    </button>
  );
}

export function Input({ className, ...props }) {
  return (
    <input
      className={cn(
        "w-full px-4 py-2.5 rounded-lg border border-[#E7E5E4] bg-white text-[#1C1B1F] placeholder-stone-400",
        "focus:outline-none focus:ring-2 focus:ring-ink/40 focus:border-ink transition",
        className
      )}
      {...props}
    />
  );
}

export function Textarea({ className, ...props }) {
  return (
    <textarea
      className={cn(
        "w-full px-4 py-2.5 rounded-lg border border-[#E7E5E4] bg-white text-[#1C1B1F] placeholder-stone-400",
        "focus:outline-none focus:ring-2 focus:ring-ink/40 focus:border-ink transition min-h-[80px] resize-y",
        className
      )}
      {...props}
    />
  );
}

export function Label({ className, children, ...props }) {
  return (
    <label className={cn("block text-sm font-semibold text-[#57534E] mb-1.5", className)} {...props}>
      {children}
    </label>
  );
}

export function Card({ className, children, ...props }) {
  return (
    <div
      className={cn(
        "bg-paper rounded-xl border border-[#E7E5E4] shadow-sm hover:shadow-md transition-shadow duration-200",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function Badge({ children, tone = "default", className }) {
  const tones = {
    default: "bg-parchment text-ink border border-[#E7E5E4]",
    success: "bg-green-50 text-green-800 border border-green-200",
    warning: "bg-amber-50 text-amber-900 border border-amber-200",
    danger: "bg-red-50 text-red-800 border border-red-200",
    info: "bg-sky-50 text-sky-800 border border-sky-200",
    ochre: "bg-ochrelight text-ink border border-ochre/30",
  };
  return (
    <span className={cn("inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold", tones[tone], className)}>
      {children}
    </span>
  );
}

export function Select({ className, children, ...props }) {
  return (
    <select
      className={cn(
        "w-full px-4 py-2.5 rounded-lg border border-[#E7E5E4] bg-white text-[#1C1B1F]",
        "focus:outline-none focus:ring-2 focus:ring-ink/40 focus:border-ink transition",
        className
      )}
      {...props}
    >
      {children}
    </select>
  );
}
