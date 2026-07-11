import { api } from "./client";
import { Teacher } from "../types/domain";

export const teacherService = {
  list: () => api<Teacher[]>("/teachers"),
  get: (id: number) => api<Teacher>(`/teachers/${id}`),
  create: (payload: Partial<Teacher>) => api<Teacher>("/teachers", { method: "POST", body: JSON.stringify(payload) }),
  update: (id: number, payload: Partial<Teacher>) =>
    api<Teacher>(`/teachers/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
};
