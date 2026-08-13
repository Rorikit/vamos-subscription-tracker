import { api } from "./client";
import { Visit } from "../types/domain";

export const visitService = {
  byParticipant: (participantId: number) => api<Visit[]>(`/participants/${participantId}/visits`),
  cancel: (id: number) => api<Visit>(`/visits/${id}/cancel`, { method: "POST" }),
};
