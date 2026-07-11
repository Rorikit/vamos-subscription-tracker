import { api } from "./client";
import { FinanceSummary, Membership, Payment, TeacherEarning, Visit } from "../types/domain";

export const financeService = {
  summary: () => api<FinanceSummary>("/finance/summary"),
  teacherEarnings: (params: { date_from?: string; date_to?: string; teacher_id?: string } = {}) => {
    const search = new URLSearchParams();
    if (params.date_from) search.set("date_from", params.date_from);
    if (params.date_to) search.set("date_to", params.date_to);
    if (params.teacher_id) search.set("teacher_id", params.teacher_id);
    return api<TeacherEarning[]>(`/finance/teacher-earnings${search.toString() ? `?${search}` : ""}`);
  },
  payments: () => api<Payment[]>("/finance/payments"),
  dashboard: () =>
    api<{ summary: FinanceSummary; memberships: Membership[]; payments: Payment[]; visits: Visit[] }>("/finance/dashboard"),
};
