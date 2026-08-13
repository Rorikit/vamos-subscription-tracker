import { api } from "./client";
import type { ExtraExpense, ExtraExpenseStatus, ExtraExpenseSummary } from "../types/domain";

export type ExtraExpenseFilters = {
  date_from?: string;
  date_to?: string;
  search?: string;
  status?: ExtraExpenseStatus | "";
  page?: number;
  page_size?: number;
};

function toSearch(params: ExtraExpenseFilters = {}) {
  const search = new URLSearchParams();
  if (params.date_from) search.set("date_from", params.date_from);
  if (params.date_to) search.set("date_to", params.date_to);
  if (params.search) search.set("search", params.search);
  if (params.status) search.set("status", params.status);
  if (params.page) search.set("page", String(params.page));
  if (params.page_size) search.set("page_size", String(params.page_size));
  return search.toString();
}

export const extraExpenseService = {
  list: (params: ExtraExpenseFilters = {}) => {
    const search = toSearch(params);
    return api<ExtraExpense[]>(`/extra-expenses${search ? `?${search}` : ""}`);
  },
  summary: (params: Pick<ExtraExpenseFilters, "date_from" | "date_to"> = {}) => {
    const search = toSearch(params);
    return api<ExtraExpenseSummary>(`/extra-expenses/summary${search ? `?${search}` : ""}`);
  },
  create: (payload: { title: string; amount: string; expense_date: string; comment?: string | null }) =>
    api<ExtraExpense>("/extra-expenses", { method: "POST", body: JSON.stringify(payload) }),
  update: (id: number, payload: Partial<{ title: string; amount: string; expense_date: string; comment: string | null }>) =>
    api<ExtraExpense>(`/extra-expenses/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  cancel: (id: number) =>
    api<ExtraExpense>(`/extra-expenses/${id}/cancel`, { method: "POST" }),
};
