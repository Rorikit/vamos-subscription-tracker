import { api } from "./client";
import { FinanceMonthlyReport, FinanceSummary, Membership, MonthlyExpense, ReminderStatus, TeacherEarning, Visit } from "../types/domain";

export const financeService = {
  summary: (params: { date_from?: string; date_to?: string; teacher_id?: string; membership_type_id?: string } = {}) => {
    const search = new URLSearchParams();
    if (params.date_from) search.set("date_from", params.date_from);
    if (params.date_to) search.set("date_to", params.date_to);
    if (params.teacher_id) search.set("teacher_id", params.teacher_id);
    if (params.membership_type_id) search.set("membership_type_id", params.membership_type_id);
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
  dashboard: () =>
    api<{ summary: FinanceSummary; memberships: Membership[]; visits: Visit[] }>("/finance/dashboard"),
  monthlyReport: (params: { year: number; month: number }) =>
    api<FinanceMonthlyReport>(`/finance/monthly-report?year=${params.year}&month=${params.month}`),
  expenses: (params: { year: number; month: number }) =>
    api<MonthlyExpense[]>(`/finance/expenses?year=${params.year}&month=${params.month}`),
  updateExpense: (id: number, payload: { planned_amount?: string; actual_amount?: string | null; comment?: string | null }) =>
    api<MonthlyExpense>(`/finance/expenses/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  payExpense: (id: number) =>
    api<MonthlyExpense>(`/finance/expenses/${id}/pay`, { method: "POST" }),
  unpayExpense: (id: number) =>
    api<MonthlyExpense>(`/finance/expenses/${id}/unpay`, { method: "POST" }),
  reminderStatus: (params?: { year?: number; month?: number }) => {
    const search = new URLSearchParams();
    if (params?.year) search.set("year", String(params.year));
    if (params?.month) search.set("month", String(params.month));
    return api<ReminderStatus>(`/finance/reminders/status${search.toString() ? `?${search}` : ""}`);
  },
};
