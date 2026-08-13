import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarPlus, CheckCircle2, ChevronLeft, ChevronRight, RotateCcw, XCircle } from "lucide-react";

import { participantService } from "../../shared/api/participantService";
import { scheduleService } from "../../shared/api/scheduleService";
import { teacherService } from "../../shared/api/teacherService";
import { toCurrency } from "../../shared/api/client";
import { Modal } from "../../shared/ui/Modal";
import { useDebouncedValue } from "../../shared/ui/useDebouncedValue";
import type { AttendanceStatus, ParticipantListItem, ScheduleEvent, ScheduleEventStatus, ScheduleEventType } from "../../shared/types/domain";

type ViewMode = "day" | "week" | "month";
type EventDraft = { date: string; startTime: string; endTime: string };

const statusLabels: Record<ScheduleEventStatus, string> = {
  scheduled: "Запланировано",
  completed: "Проведено",
  cancelled: "Отменено",
};

const eventTypeLabels: Record<ScheduleEventType, string> = {
  group: "Групповое",
  individual: "Индивидуальное",
  course: "Курс",
  other: "Другое",
};

const attendanceLabels: Record<AttendanceStatus, string> = {
  planned: "Запланирован",
  attended: "Посетил",
  absent: "Отсутствовал",
  cancelled: "Участие отменено",
  refunded: "Возвращено",
};

const teacherPalette = ["#159895", "#4361ee", "#ef476f", "#f59e0b", "#8b5cf6", "#0f766e"];

export function SchedulePage() {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<ViewMode>("week");
  const [anchorDate, setAnchorDate] = useState(() => formatDateInput(new Date()));
  const [teacherId, setTeacherId] = useState("");
  const [status, setStatus] = useState<ScheduleEventStatus | "">("");
  const [eventType, setEventType] = useState<ScheduleEventType | "">("");
  const [editorEvent, setEditorEvent] = useState<ScheduleEvent | "new" | null>(null);
  const [eventDraft, setEventDraft] = useState<EventDraft | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<ScheduleEvent | null>(null);
  const [completeEvent, setCompleteEvent] = useState<ScheduleEvent | null>(null);
  const [drawerError, setDrawerError] = useState<string | null>(null);

  const range = useMemo(() => getRange(anchorDate, mode), [anchorDate, mode]);
  const filters = {
    date_from: range.start.toISOString(),
    date_to: range.end.toISOString(),
    teacher_id: teacherId,
    status,
    event_type: eventType,
  };
  const teachers = useQuery({ queryKey: ["teachers"], queryFn: teacherService.list });
  const events = useQuery({ queryKey: ["schedule-events", filters], queryFn: () => scheduleService.list(filters) });

  const deleteMutation = useMutation({
    mutationFn: (eventId: number) => scheduleService.delete(eventId),
    onMutate: () => {
      setDrawerError(null);
    },
    onSuccess: () => {
      setDrawerError(null);
      setSelectedEvent(null);
      queryClient.invalidateQueries();
    },
    onError: (error) => {
      setDrawerError(error instanceof Error ? error.message : "Не удалось удалить занятие");
    },
  });
  const cancelMutation = useMutation({
    mutationFn: (eventId: number) => scheduleService.cancel(eventId),
    onMutate: () => {
      setDrawerError(null);
    },
    onSuccess: (event) => {
      setDrawerError(null);
      queryClient.invalidateQueries();
      setSelectedEvent(event);
    },
    onError: (error) => {
      setDrawerError(error instanceof Error ? error.message : "Не удалось отменить занятие");
    },
  });
  const returnMutation = useMutation({
    mutationFn: ({ eventId, participantId }: { eventId: number; participantId: number }) => scheduleService.returnParticipant(eventId, participantId),
    onSuccess: (event) => {
      queryClient.invalidateQueries({ queryKey: ["schedule-events"] });
      queryClient.invalidateQueries({ queryKey: ["finance"] });
      queryClient.invalidateQueries({ queryKey: ["participants"] });
      setSelectedEvent(event);
    },
  });

  const teacherColor = (id: number) => teacherPalette[Math.abs(id) % teacherPalette.length];
  const visibleEvents = events.data ?? [];

  function shift(step: number) {
    const date = new Date(anchorDate);
    if (mode === "day") date.setDate(date.getDate() + step);
    if (mode === "week") date.setDate(date.getDate() + step * 7);
    if (mode === "month") date.setMonth(date.getMonth() + step);
    setAnchorDate(formatDateInput(date));
  }

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-ink">Расписание</h1>
          <p className="mt-1 text-sm text-slate-500">Планирование занятий, проведение и возвраты из календаря.</p>
        </div>
        <button className="btn-primary" onClick={() => setEditorEvent("new")}>
          <CalendarPlus size={18} />
          Создать занятие
        </button>
      </div>

      <section className="panel sticky top-20 z-10 p-4">
        <div className="grid grid-cols-[auto_auto_auto_160px_1fr_1fr_1fr] items-end gap-3">
          <button className="btn-secondary" onClick={() => setAnchorDate(formatDateInput(new Date()))}>Сегодня</button>
          <button className="btn-secondary h-10 px-3" onClick={() => shift(-1)} title="Назад"><ChevronLeft size={18} /></button>
          <button className="btn-secondary h-10 px-3" onClick={() => shift(1)} title="Вперед"><ChevronRight size={18} /></button>
          <label className="text-sm font-medium text-slate-700">
            Дата
            <input className="input mt-1" type="date" value={anchorDate} onChange={(event) => setAnchorDate(event.target.value)} />
          </label>
          <label className="text-sm font-medium text-slate-700">
            Преподаватель
            <select className="input mt-1" value={teacherId} onChange={(event) => setTeacherId(event.target.value)}>
              <option value="">Все преподаватели</option>
              {teachers.data?.map((teacher) => <option key={teacher.id} value={teacher.id}>{teacher.full_name}</option>)}
            </select>
          </label>
          <label className="text-sm font-medium text-slate-700">
            Тип
            <select className="input mt-1" value={eventType} onChange={(event) => setEventType(event.target.value as ScheduleEventType | "")}>
              <option value="">Все типы</option>
              <option value="group">Групповое</option>
              <option value="individual">Индивидуальное</option>
              <option value="course">Курс</option>
              <option value="other">Другое</option>
            </select>
          </label>
          <label className="text-sm font-medium text-slate-700">
            Статус
            <select className="input mt-1" value={status} onChange={(event) => setStatus(event.target.value as ScheduleEventStatus | "")}>
              <option value="">Все статусы</option>
              <option value="scheduled">Запланировано</option>
              <option value="completed">Проведено</option>
              <option value="cancelled">Отменено</option>
            </select>
          </label>
        </div>
        <div className="mt-4 flex items-center justify-between">
          <div className="text-lg font-bold text-ink">{rangeTitle(range.start, mode)}</div>
          <div className="flex rounded-md border border-slate-200 bg-white p-1">
            {(["day", "week", "month"] as ViewMode[]).map((item) => (
              <button key={item} className={`h-9 rounded px-4 text-sm font-semibold ${mode === item ? "bg-mint text-white" : "text-slate-600"}`} onClick={() => setMode(item)}>
                {item === "day" ? "День" : item === "week" ? "Неделя" : "Месяц"}
              </button>
            ))}
          </div>
        </div>
      </section>

      {events.isError ? <ErrorBlock onRetry={() => events.refetch()} /> : null}
      {events.isLoading ? <LoadingGrid /> : <CalendarCanvas mode={mode} start={range.start} events={visibleEvents} teacherColor={teacherColor} onOpen={(event) => { setDrawerError(null); setSelectedEvent(event); }} onCreate={(date) => { setAnchorDate(formatDateInput(date)); setEventDraft(makeDraft(date)); setEditorEvent("new"); }} />}

      {!events.isLoading && visibleEvents.length === 0 ? (
        <div className="panel p-10 text-center">
          <div className="font-semibold text-ink">На выбранный период занятий нет.</div>
          <button className="btn-primary mx-auto mt-4" onClick={() => setEditorEvent("new")}>Создать занятие</button>
        </div>
      ) : null}

      <Modal title={editorEvent === "new" ? "Создать занятие" : "Редактировать занятие"} open={editorEvent !== null} onClose={() => setEditorEvent(null)}>
        <ScheduleEventForm event={editorEvent && editorEvent !== "new" ? editorEvent : undefined} anchorDate={anchorDate} draft={eventDraft} onDone={() => { setEditorEvent(null); setEventDraft(null); queryClient.invalidateQueries({ queryKey: ["schedule-events"] }); }} />
      </Modal>
      <EventDrawer open={selectedEvent !== null} onClose={() => setSelectedEvent(null)}>
        {selectedEvent ? (
          <EventCard
            event={selectedEvent}
            error={drawerError}
            deleting={deleteMutation.isPending}
            cancelling={cancelMutation.isPending}
            onEdit={() => { setEditorEvent(selectedEvent); setSelectedEvent(null); }}
            onMove={() => { setEditorEvent(selectedEvent); setSelectedEvent(null); }}
            onDelete={() => deleteMutation.mutate(selectedEvent.id)}
            onCancel={() => cancelMutation.mutate(selectedEvent.id)}
            onComplete={() => { setCompleteEvent(selectedEvent); setSelectedEvent(null); }}
            onReturn={(participantId) => returnMutation.mutate({ eventId: selectedEvent.id, participantId })}
          />
        ) : null}
      </EventDrawer>
      <Modal title="Отметить проведение занятия" open={completeEvent !== null} onClose={() => setCompleteEvent(null)}>
        {completeEvent ? <CompleteEventForm event={completeEvent} onDone={(event) => { setCompleteEvent(null); setSelectedEvent(event); queryClient.invalidateQueries({ queryKey: ["schedule-events"] }); }} /> : null}
      </Modal>
    </div>
  );
}

function CalendarCanvas({ mode, start, events, teacherColor, onOpen, onCreate }: { mode: ViewMode; start: Date; events: ScheduleEvent[]; teacherColor: (id: number) => string; onOpen: (event: ScheduleEvent) => void; onCreate: (date: Date) => void }) {
  if (mode === "month") return <MonthView start={start} events={events} teacherColor={teacherColor} onOpen={onOpen} onCreate={onCreate} />;
  const days = mode === "day" ? [start] : Array.from({ length: 7 }, (_, index) => addDays(start, index));
  const slots = Array.from({ length: 31 }, (_, index) => {
    const totalMinutes = 8 * 60 + index * 30;
    return { hour: Math.floor(totalMinutes / 60), minute: totalMinutes % 60 };
  });
  return (
    <section className="panel flex max-h-[calc(100vh-270px)] min-h-[460px] flex-col overflow-hidden">
      <div className={`grid ${mode === "day" ? "grid-cols-1" : "grid-cols-7"} border-b border-slate-100 bg-slate-50`}>
        {days.map((day) => <button key={day.toISOString()} className="px-3 py-3 text-left text-sm font-bold text-ink" onClick={() => onCreate(day)}>{weekday(day)} · {day.getDate()}</button>)}
      </div>
      <div className={`grid flex-1 ${mode === "day" ? "grid-cols-1" : "grid-cols-7"} divide-x divide-slate-100 overflow-auto`}>
        {days.map((day) => {
          const dayEvents = events.filter((event) => sameDay(new Date(event.starts_at), day)).sort((a, b) => a.starts_at.localeCompare(b.starts_at));
          return (
            <div key={day.toISOString()} className="space-y-2 p-3">
              {dayEvents.map((event) => <EventPill key={event.id} event={event} color={event.color || teacherColor(event.teacher_id)} onOpen={onOpen} />)}
              <div className="grid grid-cols-2 gap-2">
                {slots.map(({ hour, minute }) => {
                  const slot = new Date(day);
                  slot.setHours(hour, minute, 0, 0);
                  return <button key={`${hour}-${minute}`} className="h-10 rounded-md border border-dashed border-slate-200 text-xs font-semibold text-slate-400 hover:border-mint hover:text-mint" onClick={() => onCreate(slot)}>{String(hour).padStart(2, "0")}:{String(minute).padStart(2, "0")}</button>;
                })}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function MonthView({ start, events, teacherColor, onOpen, onCreate }: { start: Date; events: ScheduleEvent[]; teacherColor: (id: number) => string; onOpen: (event: ScheduleEvent) => void; onCreate: (date: Date) => void }) {
  const first = new Date(start.getFullYear(), start.getMonth(), 1);
  const gridStart = addDays(first, -(first.getDay() || 7) + 1);
  const days = Array.from({ length: 42 }, (_, index) => addDays(gridStart, index));
  return (
    <section className="panel overflow-hidden">
      <div className="grid grid-cols-7 bg-slate-50 text-sm font-bold text-slate-500">
        {["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"].map((day) => <div key={day} className="px-3 py-2">{day}</div>)}
      </div>
      <div className="grid grid-cols-7">
        {days.map((day) => {
          const dayEvents = events.filter((event) => sameDay(new Date(event.starts_at), day));
          const shown = dayEvents.slice(0, 3);
          return (
            <div key={day.toISOString()} className={`min-h-32 border-t border-r border-slate-100 p-2 text-left ${day.getMonth() === start.getMonth() ? "bg-white" : "bg-slate-50/60"}`}>
              <button className={`mb-2 text-sm font-bold ${sameDay(day, new Date()) ? "text-mint" : "text-ink"}`} onClick={() => onCreate(day)}>{day.getDate()}</button>
              <div className="space-y-1">
                {shown.map((event) => <EventPill key={event.id} compact event={event} color={event.color || teacherColor(event.teacher_id)} onOpen={onOpen} />)}
                {dayEvents.length > shown.length ? <div className="text-xs font-semibold text-slate-500">Еще {dayEvents.length - shown.length}</div> : null}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function EventPill({ event, color, compact = false, onOpen }: { event: ScheduleEvent; color: string; compact?: boolean; onOpen: (event: ScheduleEvent) => void }) {
  return (
    <button
      className={`w-full rounded-md border-l-4 bg-white p-2 text-left shadow-sm ring-1 ring-slate-100 transition hover:shadow ${event.status === "cancelled" ? "opacity-50 line-through" : ""} ${event.status === "completed" ? "bg-emerald-50/60" : ""}`}
      style={{ borderLeftColor: color }}
      onClick={(click) => { click.stopPropagation(); onOpen(event); }}
    >
      <div className="text-xs font-semibold text-slate-500">{timeRange(event.starts_at, event.ends_at)} · {statusLabels[event.status]}</div>
      <div className="truncate font-bold text-ink">{event.title}</div>
      {!compact ? <div className="mt-1 text-xs text-slate-500">{event.teacher?.full_name ?? "Преподаватель"} · {eventTypeLabels[event.event_type]} · {event.participants.length} уч.</div> : null}
    </button>
  );
}

function ScheduleEventForm({ event, anchorDate, draft, onDone }: { event?: ScheduleEvent; anchorDate: string; draft?: EventDraft | null; onDone: () => void }) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(event?.title ?? "");
  const [date, setDate] = useState(event ? formatDateInput(new Date(event.starts_at)) : draft?.date ?? anchorDate);
  const [startTime, setStartTime] = useState(event ? formatTimeInput(new Date(event.starts_at)) : draft?.startTime ?? "10:00");
  const [endTime, setEndTime] = useState(event ? formatTimeInput(new Date(event.ends_at)) : draft?.endTime ?? "11:00");
  const [teacherId, setTeacherId] = useState(event?.teacher_id.toString() ?? "");
  const [eventType, setEventType] = useState<ScheduleEventType>(event?.event_type ?? "group");
  const [location, setLocation] = useState(event?.location ?? "");
  const [description, setDescription] = useState(event?.description ?? "");
  const [color, setColor] = useState(event?.color ?? "#159895");
  const [participantIds, setParticipantIds] = useState<number[]>(event?.participants.map((item) => item.participant_id) ?? []);
  const [participantSearch, setParticipantSearch] = useState("");
  const debouncedSearch = useDebouncedValue(participantSearch, 300);
  const teachers = useQuery({ queryKey: ["teachers"], queryFn: teacherService.list });
  const participants = useQuery({ queryKey: ["participants", "schedule-form", debouncedSearch], queryFn: () => participantService.list(debouncedSearch) });
  const startsAt = useMemo(() => toIsoDateTime(date, startTime), [date, startTime]);
  const endsAt = useMemo(() => toIsoDateTime(date, endTime), [date, endTime]);
  const timeIsValid = Boolean(startsAt && endsAt && new Date(endsAt).getTime() > new Date(startsAt).getTime());
  const conflictCheck = useQuery({
    queryKey: ["schedule-conflicts", teacherId, startsAt, endsAt, event?.id],
    queryFn: () => scheduleService.conflicts({ teacher_id: Number(teacherId), starts_at: startsAt!, ends_at: endsAt!, exclude_event_id: event?.id }),
    enabled: Boolean(teacherId && startsAt && endsAt && timeIsValid),
    retry: false,
  });
  const mutation = useMutation<unknown, Error>({
    mutationFn: () => {
      const starts_at = startsAt!;
      const ends_at = endsAt!;
      if (event) {
        return scheduleService.update(event.id, { title, description, teacher_id: Number(teacherId), starts_at, ends_at, event_type: eventType, location, color, participant_ids: participantIds });
      }
      return scheduleService.create({
        title,
        description,
        teacher_id: Number(teacherId),
        starts_at,
        ends_at,
        event_type: eventType,
        location,
        color,
        participant_ids: participantIds,
        recurrence: null,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["schedule-events"] });
      onDone();
    },
  });
  const selectedParticipants = participants.data?.filter((participant) => participantIds.includes(participant.id)) ?? [];
  const activeTeacher = teachers.data?.find((teacher) => String(teacher.id) === teacherId);
  const validationIssues = [
    !title.trim() ? "Введите название занятия." : null,
    !teacherId ? "Выберите преподавателя." : null,
    teacherId && !activeTeacher ? "Выбранный преподаватель не найден в списке." : null,
    activeTeacher && !activeTeacher.is_active ? "Выбранный преподаватель отключен. Выберите активного преподавателя." : null,
    !date ? "Выберите дату занятия." : null,
    !startTime ? "Выберите время начала." : null,
    !endTime ? "Выберите время окончания." : null,
    startsAt && endsAt && !timeIsValid ? "Время окончания должно быть позже времени начала." : null,
    conflictCheck.data?.length ? `Преподаватель уже занят: ${conflictCheck.data[0].title}, ${timeRange(conflictCheck.data[0].starts_at, conflictCheck.data[0].ends_at)}.` : null,
  ].filter(Boolean) as string[];
  const warnings = [
    participantIds.length === 0
      ? "Можно создать слот преподавателя без участников и добавить учеников позже."
      : null,
    selectedParticipants.some((participant) => !participant.active_membership_id)
      ? "У части участников нет активного абонемента. Backend не даст добавить их в занятие."
      : null,
  ].filter(Boolean) as string[];
  const canSubmit = validationIssues.length === 0 && !conflictCheck.isFetching;

  function submit(formEvent: FormEvent) {
    formEvent.preventDefault();
    mutation.mutate();
  }

  return (
    <form className="space-y-4" onSubmit={submit}>
      <Field label="Название занятия" value={title} onChange={setTitle} required />
      <div className="grid grid-cols-3 gap-3">
        <Field label="Дата" value={date} onChange={setDate} type="date" required />
        <Field label="Начало" value={startTime} onChange={setStartTime} type="time" step="1800" required />
        <Field label="Окончание" value={endTime} onChange={setEndTime} type="time" step="1800" required />
      </div>
      <label className="block text-sm font-medium text-slate-700">
        Преподаватель
        <select className="input mt-1" value={teacherId} onChange={(item) => setTeacherId(item.target.value)} required>
          <option value="">Выберите преподавателя</option>
          {teachers.data?.filter((teacher) => teacher.is_active).map((teacher) => <option key={teacher.id} value={teacher.id}>{teacher.full_name}</option>)}
        </select>
      </label>
      <label className="block text-sm font-medium text-slate-700">
        Тип занятия
        <select className="input mt-1" value={eventType} onChange={(item) => setEventType(item.target.value as ScheduleEventType)}>
          <option value="group">Групповое</option>
          <option value="individual">Индивидуальное</option>
          <option value="course">Курс</option>
          <option value="other">Другое</option>
        </select>
      </label>
      <Field label="Место" value={location} onChange={setLocation} />
      <Field label="Описание" value={description} onChange={setDescription} />
      <Field label="Цвет" value={color} onChange={setColor} type="color" />
      <div>
        <label className="block text-sm font-medium text-slate-700">
          Участники
          <input className="input mt-1" value={participantSearch} onChange={(item) => setParticipantSearch(item.target.value)} placeholder="Поиск по ФИО или телефону" />
        </label>
        <div className="mt-2 max-h-48 space-y-2 overflow-auto rounded-md border border-slate-200 p-2">
          {participants.data?.map((participant) => <ParticipantChoice key={participant.id} participant={participant} checked={participantIds.includes(participant.id)} onToggle={() => setParticipantIds((ids) => ids.includes(participant.id) ? ids.filter((id) => id !== participant.id) : [...ids, participant.id])} />)}
          {!participants.isLoading && participants.data?.length === 0 ? <div className="text-sm text-slate-500">Участники не найдены</div> : null}
        </div>
      </div>
      <ValidationPanel issues={validationIssues} warnings={warnings} checking={conflictCheck.isFetching} />
      {mutation.error ? <p className="rounded-md border border-red-100 bg-red-50 px-3 py-2 text-sm text-coral">{mutation.error.message}</p> : null}
      <button className="btn-primary w-full" disabled={mutation.isPending || !canSubmit}>
        {mutation.isPending ? "Сохранение..." : event ? "Сохранить занятие" : "Создать занятие"}
      </button>
    </form>
  );
}

function ValidationPanel({ issues, warnings, checking }: { issues: string[]; warnings: string[]; checking: boolean }) {
  if (!issues.length && !warnings.length && !checking) return null;
  return (
    <div className="space-y-2">
      {checking ? <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">Проверяем занятость преподавателя...</div> : null}
      {issues.length ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
          <div className="font-semibold">Чтобы создать занятие, исправьте:</div>
          <ul className="mt-1 list-disc space-y-1 pl-4">
            {issues.map((issue) => <li key={issue}>{issue}</li>)}
          </ul>
        </div>
      ) : null}
      {warnings.length ? (
        <div className="rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-800">
          {warnings.map((warning) => <div key={warning}>{warning}</div>)}
        </div>
      ) : null}
    </div>
  );
}

function ParticipantChoice({ participant, checked, onToggle }: { participant: ParticipantListItem; checked: boolean; onToggle: () => void }) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-3 rounded-md px-2 py-2 hover:bg-slate-50">
      <span>
        <span className="block text-sm font-semibold text-ink">{participant.full_name}</span>
        <span className="text-xs text-slate-500">{participant.phone ?? "Без телефона"} · {participant.remaining_lessons ?? 0} занятий</span>
      </span>
      <input type="checkbox" checked={checked} onChange={onToggle} />
    </label>
  );
}

function EventCard({
  event,
  error,
  deleting,
  cancelling,
  onEdit,
  onMove,
  onDelete,
  onCancel,
  onComplete,
  onReturn,
}: {
  event: ScheduleEvent;
  error: string | null;
  deleting: boolean;
  cancelling: boolean;
  onEdit: () => void;
  onMove: () => void;
  onDelete: () => void;
  onCancel: () => void;
  onComplete: () => void;
  onReturn: (participantId: number) => void;
}) {
  const [confirmAction, setConfirmAction] = useState<"cancel" | "delete" | null>(null);
  const totalTeacher = event.participants.reduce((sum, item) => sum + Number(item.visit?.teacher_earning ?? 0), 0);
  const totalSchool = event.participants.reduce((sum, item) => sum + Number(item.visit?.school_earning ?? 0), 0);
  const canDelete = event.status === "scheduled" || event.status === "cancelled";
  const canCancel = event.status === "scheduled" || event.status === "completed";

  useEffect(() => {
    setConfirmAction(null);
  }, [event.id]);

  return (
    <div className="space-y-4">
      <div>
        <div className="text-xl font-bold text-ink">{event.title}</div>
        <div className="text-sm text-slate-500">{timeRange(event.starts_at, event.ends_at)} · {event.teacher?.full_name} · {eventTypeLabels[event.event_type]}</div>
      </div>
      <div className="grid grid-cols-3 gap-3">
        <Info label="Статус" value={statusLabels[event.status]} />
        <Info label="Место" value={event.location || "—"} />
        <Info label="Участников" value={String(event.participants.length)} />
      </div>
      {event.status === "completed" ? <div className="grid grid-cols-2 gap-3"><Info label="Выплата преподавателю" value={toCurrency(totalTeacher)} /><Info label="Доход школы" value={toCurrency(totalSchool)} /></div> : null}
      <div className="rounded-md border border-slate-200">
        {event.participants.map((item) => (
          <div key={item.id} className="flex items-center justify-between border-b border-slate-100 px-3 py-2 last:border-b-0">
            <div>
              <div className="font-semibold text-ink">{item.participant?.full_name}</div>
              <div className="text-xs text-slate-500">{attendanceLabels[item.attendance_status]} {item.visit?.is_cancelled ? "· занятие возвращено" : ""}</div>
            </div>
            {event.status === "completed" && item.visit_id && !item.visit?.is_cancelled && item.attendance_status === "attended" ? (
              <button className="btn-secondary h-9" onClick={() => window.confirm("Вернуть занятие участнику?") && onReturn(item.participant_id)}>
                <RotateCcw size={16} /> Вернуть
              </button>
            ) : null}
          </div>
        ))}
      </div>
      <div className="flex flex-wrap gap-2">
        {event.status === "scheduled" ? (
          <>
            <button className="btn-primary" onClick={onComplete}><CheckCircle2 size={17} /> Отметить проведение</button>
            <button className="btn-secondary" onClick={onEdit}>Добавить участника</button>
            <button className="btn-secondary" onClick={onEdit}>Редактировать</button>
            <button className="btn-secondary" onClick={onMove}>Перенести</button>
          </>
        ) : null}
        {canCancel ? (
          <button className="btn-secondary text-coral" disabled={cancelling || deleting} onClick={() => setConfirmAction("cancel")}>
            <XCircle size={17} /> {cancelling ? "Отмена..." : event.status === "completed" ? "Отменить проведение" : "Отменить занятие"}
          </button>
        ) : null}
        {canDelete ? (
          <button className="btn-secondary text-coral" disabled={deleting || cancelling} onClick={() => setConfirmAction("delete")}>
            <XCircle size={17} /> {deleting ? "Удаление..." : "Удалить"}
          </button>
        ) : null}
      </div>
      {confirmAction ? (
        <div className="rounded-md border border-coral/30 bg-coral/10 p-3">
          <div className="text-sm font-semibold text-ink">
            {confirmAction === "delete"
              ? "Удалить занятие из расписания полностью?"
              : event.status === "completed"
                ? "Отменить проведение и вернуть посещения?"
                : "Отменить занятие?"}
          </div>
          <div className="mt-1 text-xs text-slate-500">
            {timeRange(event.starts_at, event.ends_at)} · {event.teacher?.full_name ?? "Преподаватель не указан"} · {event.participants.length} участник(ов)
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              className="btn-secondary text-coral"
              disabled={deleting || cancelling}
              onClick={() => {
                if (confirmAction === "delete") onDelete();
                if (confirmAction === "cancel") onCancel();
              }}
            >
              <XCircle size={17} /> {confirmAction === "delete" ? "Да, удалить" : "Да, отменить"}
            </button>
            <button className="btn-secondary" disabled={deleting || cancelling} onClick={() => setConfirmAction(null)}>
              Не выполнять
            </button>
          </div>
        </div>
      ) : null}
      {error ? <div className="rounded-md border border-red-100 bg-red-50 px-3 py-2 text-sm text-coral">{error}</div> : null}
    </div>
  );
}

function CompleteEventForm({ event, onDone }: { event: ScheduleEvent; onDone: (event: ScheduleEvent) => void }) {
  const [attendance, setAttendance] = useState<Record<number, AttendanceStatus>>(Object.fromEntries(event.participants.map((item) => [item.participant_id, "attended"])));
  const mutation = useMutation({
    mutationFn: () => scheduleService.complete(event.id, Object.entries(attendance).map(([participantId, attendance_status]) => ({ participant_id: Number(participantId), attendance_status }))),
    onSuccess: onDone,
  });
  return (
    <div className="space-y-4">
      <div className="rounded-md bg-slate-50 p-3 text-sm text-slate-600">
        Будет проведено занятий: {Object.values(attendance).filter((status) => status === "attended").length}. Финальный расчет выполнит backend.
      </div>
      {event.participants.map((item) => (
        <label key={item.id} className="block text-sm font-medium text-slate-700">
          {item.participant?.full_name}
          <select className="input mt-1" value={attendance[item.participant_id]} onChange={(select) => setAttendance({ ...attendance, [item.participant_id]: select.target.value as AttendanceStatus })}>
            <option value="attended">Посетил</option>
            <option value="absent">Отсутствовал</option>
            <option value="cancelled">Участие отменено</option>
          </select>
        </label>
      ))}
      {mutation.error ? <p className="text-sm text-coral">{mutation.error.message}</p> : null}
      <button className="btn-primary w-full" disabled={mutation.isPending} onClick={() => mutation.mutate()}>
        {mutation.isPending ? "Проведение..." : "Подтвердить проведение"}
      </button>
    </div>
  );
}

function Field({ label, value, onChange, type = "text", required = false, step }: { label: string; value: string; onChange: (value: string) => void; type?: string; required?: boolean; step?: string }) {
  return (
    <label className="block text-sm font-medium text-slate-700">
      {label}
      <input className="input mt-1" value={value} type={type} step={step} onChange={(event) => onChange(event.target.value)} required={required} />
    </label>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return <div className="rounded-md bg-slate-50 p-3"><div className="text-xs font-semibold uppercase text-slate-400">{label}</div><div className="mt-1 font-bold text-ink">{value}</div></div>;
}

function ErrorBlock({ onRetry }: { onRetry: () => void }) {
  return <div className="panel flex items-center justify-between border-red-100 bg-red-50 p-4 text-sm text-red-700"><span>Не удалось загрузить расписание.</span><button className="btn-secondary bg-white" onClick={onRetry}>Повторить</button></div>;
}

function LoadingGrid() {
  return <div className="panel grid grid-cols-7 gap-3 p-5">{Array.from({ length: 14 }, (_, index) => <div key={index} className="h-24 animate-pulse rounded-md bg-slate-100" />)}</div>;
}

function getRange(anchor: string, mode: ViewMode) {
  const date = new Date(`${anchor}T00:00:00`);
  if (mode === "day") return { start: date, end: addDays(date, 1) };
  if (mode === "month") return { start: new Date(date.getFullYear(), date.getMonth(), 1), end: new Date(date.getFullYear(), date.getMonth() + 1, 1) };
  const start = addDays(date, -(date.getDay() || 7) + 1);
  return { start, end: addDays(start, 7) };
}

function addDays(date: Date, days: number) {
  const copy = new Date(date);
  copy.setDate(copy.getDate() + days);
  return copy;
}

function sameDay(a: Date, b: Date) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

function formatDateInput(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function formatTimeInput(date: Date) {
  return `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}

function weekday(date: Date) {
  return new Intl.DateTimeFormat("ru-RU", { weekday: "short" }).format(date);
}

function rangeTitle(date: Date, mode: ViewMode) {
  const options: Intl.DateTimeFormatOptions = mode === "month" ? { month: "long", year: "numeric" } : { day: "numeric", month: "long", year: "numeric" };
  return new Intl.DateTimeFormat("ru-RU", options).format(date);
}

function timeRange(start: string, end: string) {
  const formatter = new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", minute: "2-digit" });
  return `${formatter.format(new Date(start))}-${formatter.format(new Date(end))}`;
}

function toIsoDateTime(date: string, time: string) {
  if (!date || !time) return null;
  const value = new Date(`${date}T${time}`);
  return Number.isNaN(value.getTime()) ? null : value.toISOString();
}

function makeDraft(date: Date): EventDraft {
  const start = new Date(date);
  if (start.getHours() === 0 && start.getMinutes() === 0) {
    start.setHours(10, 0, 0, 0);
  }
  const end = new Date(start);
  end.setMinutes(end.getMinutes() + 60);
  return { date: formatDateInput(start), startTime: formatTimeInput(start), endTime: formatTimeInput(end) };
}

function EventDrawer({ open, onClose, children }: { open: boolean; onClose: () => void; children: ReactNode }) {
  useEffect(() => {
    if (!open) return;
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/30" onClick={onClose}>
      <aside className="h-full w-[460px] max-w-[calc(100vw-32px)] overflow-y-auto bg-white p-6 shadow-2xl" onClick={(event) => event.stopPropagation()}>
        <div className="mb-4 flex justify-end">
          <button className="btn-secondary h-9 px-3" onClick={onClose}>Закрыть</button>
        </div>
        {children}
      </aside>
    </div>
  );
}
