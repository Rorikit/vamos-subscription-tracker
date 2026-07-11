import { api } from "./client";
import type { Operator } from "./authService";

export type OperatorPayload = {
  username: string;
  full_name: string;
  password?: string;
  is_active: boolean;
};

export const operatorService = {
  list: () => api<Operator[]>("/operators"),
  create: (payload: OperatorPayload & { password: string }) =>
    api<Operator>("/operators", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  update: (id: number, payload: Partial<OperatorPayload>) =>
    api<Operator>(`/operators/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
};
