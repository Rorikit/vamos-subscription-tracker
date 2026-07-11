import { createContext, useContext, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import type { Operator } from "../../shared/api/authService";
import { clearAuthToken, getAuthToken, setAuthToken } from "../../shared/api/authToken";

type AuthContextValue = {
  operator: Operator | null;
  token: string | null;
  isAuthenticated: boolean;
  setOperator: (operator: Operator) => void;
  login: (token: string, operator: Operator) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const [token, setToken] = useState<string | null>(() => getAuthToken());
  const [operator, setOperatorState] = useState<Operator | null>(null);

  const value = useMemo<AuthContextValue>(
    () => ({
      operator,
      token,
      isAuthenticated: Boolean(token),
      setOperator: setOperatorState,
      login: (nextToken, nextOperator) => {
        setAuthToken(nextToken);
        setToken(nextToken);
        setOperatorState(nextOperator);
      },
      logout: () => {
        clearAuthToken();
        setToken(null);
        setOperatorState(null);
        queryClient.clear();
      },
    }),
    [operator, queryClient, token],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
