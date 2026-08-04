import { api } from "./client";
import { ScheduleConflict, ScheduleEvent, ScheduleEventStatus, ScheduleEventType, AttendanceStatus } from "../types/domain";

export type ScheduleFilters = {
  date_from: string;
  date_to: string;
  teacher_id?: string;
  participant_id?: string;
  status?: ScheduleEventStatus | "";
  event_type?: ScheduleEventType | "";
};

function query(params: Record<string, string | undefined>) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) search.set(key, value);
  });
  return search.toString();
}

export const scheduleService = {
  list: (filters: ScheduleFilters) => api<ScheduleEvent[]>(`/schedule-events?${query(filters)}`),
  get: (id: number) => api<ScheduleEvent>(`/schedule-events/${id}`),
  create: (payload: {
    title: string;
    description?: string | null;
    teacher_id: number;
    starts_at: string;
    ends_at: string;
    event_type: ScheduleEventType;
    location?: string | null;
    color?: string | null;
    participant_ids: number[];
    recurrence?: Record<string, unknown> | null;
  }) => api<ScheduleEvent[]>("/schedule-events", { method: "POST", body: JSON.stringify(payload) }),
  update: (id: number, payload: Partial<ScheduleEvent> & { participant_ids?: number[] }) =>
    api<ScheduleEvent>(`/schedule-events/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  move: (id: number, payload: { starts_at: string; ends_at: string; scope?: string }) =>
    api<ScheduleEvent>(`/schedule-events/${id}/move`, { method: "POST", body: JSON.stringify(payload) }),
  cancel: (id: number) => api<ScheduleEvent>(`/schedule-events/${id}/cancel`, { method: "POST" }),
  delete: (id: number) => api<void>(`/schedule-events/${id}`, { method: "DELETE" }),
  complete: (id: number, participants: Array<{ participant_id: number; attendance_status: AttendanceStatus }>) =>
    api<ScheduleEvent>(`/schedule-events/${id}/complete`, { method: "POST", body: JSON.stringify({ participants }) }),
  returnParticipant: (eventId: number, participantId: number) =>
    api<ScheduleEvent>(`/schedule-events/${eventId}/participants/${participantId}/return`, { method: "POST" }),
  conflicts: (payload: { teacher_id: number; starts_at: string; ends_at: string; exclude_event_id?: number }) =>
    api<ScheduleConflict[]>(`/schedule-events/conflicts?${query({
      teacher_id: String(payload.teacher_id),
      starts_at: payload.starts_at,
      ends_at: payload.ends_at,
      exclude_event_id: payload.exclude_event_id ? String(payload.exclude_event_id) : undefined,
    })}`),
};
