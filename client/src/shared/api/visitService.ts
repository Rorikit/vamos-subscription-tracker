import { api } from "./client";
import { Visit } from "../types/domain";

export const visitService = {
  byParticipant: (participantId: number) => api<Visit[]>(`/participants/${participantId}/visits`),
  writeOff: (payload: { participant_id: number; membership_id?: number; teacher_id: number; visit_date?: string }) =>
    api<Visit>("/visits/write-off", { method: "POST", body: JSON.stringify(payload) }),
  cancel: (id: number) => api<Visit>(`/visits/${id}/cancel`, { method: "POST" }),
};
