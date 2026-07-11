import { api } from "./client";
import { Participant, ParticipantListItem } from "../types/domain";

export const participantService = {
  list: (search = "") => api<ParticipantListItem[]>(`/participants${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  get: (id: number) => api<Participant>(`/participants/${id}`),
  create: (payload: Partial<Participant>) => api<Participant>("/participants", { method: "POST", body: JSON.stringify(payload) }),
  update: (id: number, payload: Partial<Participant>) =>
    api<Participant>(`/participants/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
};
