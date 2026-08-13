import { api } from "./client";
import { Membership, MembershipStatus } from "../types/domain";

export const membershipService = {
  list: (status?: MembershipStatus | "all") => api<Membership[]>(`/memberships${status && status !== "all" ? `?status=${status}` : ""}`),
  get: (id: number) => api<Membership>(`/memberships/${id}`),
  create: (payload: { participant_id: number; membership_type_id: number; teacher_lesson_rate: number }) =>
    api<Membership>("/memberships", { method: "POST", body: JSON.stringify(payload) }),
  update: (id: number, payload: Partial<Pick<Membership, "total_lessons" | "remaining_lessons" | "price" | "teacher_lesson_rate" | "start_date" | "end_date">>) =>
    api<Membership>(`/memberships/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  freeze: (id: number) => api<Membership>(`/memberships/${id}/freeze`, { method: "POST" }),
  unfreeze: (id: number) => api<Membership>(`/memberships/${id}/unfreeze`, { method: "POST" }),
  cancel: (id: number) => api<Membership>(`/memberships/${id}/cancel`, { method: "POST" }),
};
