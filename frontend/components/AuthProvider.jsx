"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

import { api, clearToken, getToken, setToken } from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [me, setMe] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setMe(null);
      setLoading(false);
      return null;
    }
    try {
      const user = await api("/users/me");
      setMe(user);
      return user;
    } catch {
      clearToken();
      setMe(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(
    async (identifier, password) => {
      const data = await api("/auth/login", {
        method: "POST",
        body: { identifier, password },
        auth: false,
      });
      setToken(data.access_token);
      return refresh();
    },
    [refresh],
  );

  const register = useCallback(async (payload) => {
    return api("/auth/register", {
      method: "POST",
      body: payload,
      auth: false,
    });
  }, []);

  const logout = useCallback(async () => {
    try {
      await api("/auth/logout", { method: "POST" });
    } catch {
      // Stateless JWT: even if the call fails, dropping the token logs out.
    }
    clearToken();
    setMe(null);
  }, []);

  const value = { me, loading, login, register, logout, refresh, setMe };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return context;
}
