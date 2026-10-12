import { api } from "./client";
import type { PracticeFilters } from "./practiceService";
import type { PaymentMethod } from "../types/domain";
export type WaterReceipt = { id: number; amount: string; received_on: string; payment_method: PaymentMethod; status: "active" | "cancelled"; comment: string | null; created_by_name: string | null };
export const waterService = {
  list: (filters: PracticeFilters) => {
    const params = new URLSearchParams();
    for (const name of ["date_from", "date_to", "search", "status", "page", "page_size"] as const) if (filters[name]) params.set(name, String(filters[name]));
    return api<WaterReceipt[]>(`/water-receipts?${params}`);
  },
  summary: (from: string, to: string) => api<{ income_total: string; receipts_count: number }>(`/water-receipts/summary?date_from=${from}&date_to=${to}`),
  create: (payload: { amount: string; received_on: string; payment_method: PaymentMethod; comment: string | null; request_id: string }) => api<WaterReceipt>("/water-receipts", { method: "POST", body: JSON.stringify(payload) }),
  cancel: (id: number) => api<WaterReceipt>(`/water-receipts/${id}/cancel`, { method: "POST" }),
  delete: (id: number) => api<void>(`/water-receipts/${id}`, { method: "DELETE" }),
};
