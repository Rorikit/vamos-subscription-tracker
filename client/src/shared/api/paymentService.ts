import { api } from "./client";
import { Payment } from "../types/domain";

export const paymentService = {
  byParticipant: (participantId: number) => api<Payment[]>(`/participants/${participantId}/payments`),
  create: (payload: { participant_id: number; membership_id: number; amount: number; payment_method: string; comment?: string }) =>
    api<Payment>("/payments", { method: "POST", body: JSON.stringify(payload) }),
  cancel: (id: number) => api<Payment>(`/payments/${id}/cancel`, { method: "POST" }),
};

