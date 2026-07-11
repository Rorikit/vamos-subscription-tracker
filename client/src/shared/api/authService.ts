import { api } from "./client";

export type Operator = {
  id: number;
  username: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type LoginResponse = {
  access_token: string;
  token_type: "bearer";
  operator: Operator;
};

export const authService = {
  login: (payload: { username: string; password: string }) =>
    api<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  me: () => api<Operator>("/auth/me"),
};
