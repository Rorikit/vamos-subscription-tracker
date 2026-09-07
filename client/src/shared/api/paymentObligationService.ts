import { api } from "./client";
import type { PaymentObligation, PaymentObligationSummary } from "../types/domain";

export const paymentObligationService = {
  getCurrent: () => api<PaymentObligationSummary>("/payment-obligations/current"),
  getByPeriod: (params: { year?: number; month?: number; status?: string } = {}) => {
    const search = new URLSearchParams();
    if (params.year) search.set("year", String(params.year));
    if (params.month) search.set("month", String(params.month));
    if (params.status) search.set("status", params.status);
    return api<PaymentObligationSummary>(`/payment-obligations${search.toString() ? `?${search}` : ""}`);
  },
  pay: (id: number, payload: { actual_amount?: string } = {}) =>
    api<PaymentObligation>(`/payment-obligations/${id}/pay`, { method: "POST", body: JSON.stringify(payload) }),
  unpay: (id: number) =>
    api<PaymentObligation>(`/payment-obligations/${id}/unpay`, { method: "POST" }),
};
