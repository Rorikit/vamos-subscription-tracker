import { api } from "./client";
import { FinanceSummary, Membership, Payment, TeacherEarning, Visit } from "../types/domain";

export const financeService = {
  summary: (params: { date_from?: string; date_to?: string; teacher_id?: string; membership_type_id?: string; payment_method?: string } = {}) => {
    const search = new URLSearchParams();
    if (params.date_from) search.set("date_from", params.date_from);
    if (params.date_to) search.set("date_to", params.date_to);
    if (params.teacher_id) search.set("teacher_id", params.teacher_id);
    if (params.membership_type_id) search.set("membership_type_id", params.membership_type_id);
    if (params.payment_method) search.set("payment_method", params.payment_method);
    return api<FinanceSummary>(`/finance/summary${search.toString() ? `?${search}` : ""}`);
  },
  teacherEarnings: (params: { date_from?: string; date_to?: string; teacher_id?: string; membership_type_id?: string; include_cancelled?: boolean } = {}) => {
    const search = new URLSearchParams();
    if (params.date_from) search.set("date_from", params.date_from);
    if (params.date_to) search.set("date_to", params.date_to);
    if (params.teacher_id) search.set("teacher_id", params.teacher_id);
    if (params.membership_type_id) search.set("membership_type_id", params.membership_type_id);
    if (params.include_cancelled) search.set("include_cancelled", "true");
    return api<TeacherEarning[]>(`/finance/teacher-earnings${search.toString() ? `?${search}` : ""}`);
  },
  payments: (params: { date_from?: string; date_to?: string; membership_type_id?: string; payment_method?: string } = {}) => {
    const search = new URLSearchParams();
    if (params.date_from) search.set("date_from", params.date_from);
    if (params.date_to) search.set("date_to", params.date_to);
    if (params.membership_type_id) search.set("membership_type_id", params.membership_type_id);
    if (params.payment_method) search.set("payment_method", params.payment_method);
    return api<Payment[]>(`/finance/payments${search.toString() ? `?${search}` : ""}`);
  },
  dashboard: () =>
    api<{ summary: FinanceSummary; memberships: Membership[]; payments: Payment[]; visits: Visit[] }>("/finance/dashboard"),
};
