import React, { createContext, useContext, useEffect, useState } from "react";
import api from "../lib/api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null = checking, false = anon, obj = user
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    try {
      const res = await api.get("/auth/me");
      setUser(res.data);
    } catch {
      // Only clear if we haven't already logged in via another path
      setUser((u) => (u && typeof u === "object" ? u : false));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const login = async (email, password) => {
    const res = await api.post("/auth/login", { email, password });
    if (res.data.access_token) localStorage.setItem("hb_token", res.data.access_token);
    setUser(res.data.user);
    return res.data.user;
  };

  const register = async (payload) => {
    const res = await api.post("/auth/register", payload);
    if (res.data.access_token) localStorage.setItem("hb_token", res.data.access_token);
    setUser(res.data.user);
    return res.data.user;
  };

  const logout = async () => {
    try { await api.post("/auth/logout"); } catch {}
    localStorage.removeItem("hb_token");
    setUser(false);
  };

  return (
    <AuthCtx.Provider value={{ user, loading, login, register, logout, refresh, setUser }}>
      {children}
    </AuthCtx.Provider>
  );
}

export function useAuth() {
  return useContext(AuthCtx);
}
