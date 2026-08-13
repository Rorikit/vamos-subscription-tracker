import { api } from "./client";
import { FinanceSummary, Membership, TeacherEarning, Visit } from "../types/domain";

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
};
