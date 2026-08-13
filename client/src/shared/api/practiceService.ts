import { api } from "./client";
import type { PracticeRental, PracticeRentalStatus, PracticeRentalSummary, PracticeTariff } from "../types/domain";

export type PracticeFilters = {
  date_from?: string;
  date_to?: string;
  search?: string;
  tariff_id?: string;
  status?: PracticeRentalStatus | "";
  page?: number;
  page_size?: number;
};

function toSearch(params: PracticeFilters = {}) {
  const search = new URLSearchParams();
  if (params.date_from) search.set("date_from", params.date_from);
  if (params.date_to) search.set("date_to", params.date_to);
  if (params.search) search.set("search", params.search);
  if (params.tariff_id) search.set("tariff_id", params.tariff_id);
  if (params.status) search.set("status", params.status);
  if (params.page) search.set("page", String(params.page));
  if (params.page_size) search.set("page_size", String(params.page_size));
  return search.toString();
}

export const practiceService = {
  rentals: (params: PracticeFilters = {}) => {
    const search = toSearch(params);
    return api<PracticeRental[]>(`/practice-rentals${search ? `?${search}` : ""}`);
  },
  summary: (params: Pick<PracticeFilters, "date_from" | "date_to"> = {}) => {
    const search = toSearch(params);
    return api<PracticeRentalSummary>(`/practice-rentals/summary${search ? `?${search}` : ""}`);
  },
  create: (payload: { registered_teacher_id: number | null; customer_name: string; tariff_id: number; practiced_at: string; comment?: string | null }) =>
    api<PracticeRental>("/practice-rentals", { method: "POST", body: JSON.stringify(payload) }),
  cancel: (id: number) =>
    api<PracticeRental>(`/practice-rentals/${id}/cancel`, { method: "POST" }),
  tariffs: (activeOnly = false) =>
    api<PracticeTariff[]>(`/practice-tariffs${activeOnly ? "?active_only=true" : ""}`),
  createTariff: (payload: { name: string; price: string; is_active: boolean; sort_order: number }) =>
    api<PracticeTariff>("/practice-tariffs", { method: "POST", body: JSON.stringify(payload) }),
  updateTariff: (id: number, payload: Partial<{ name: string; price: string; is_active: boolean; sort_order: number }>) =>
    api<PracticeTariff>(`/practice-tariffs/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
};
