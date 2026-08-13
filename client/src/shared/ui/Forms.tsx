import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { membershipService } from "../api/membershipService";
import { membershipTypeService } from "../api/membershipTypeService";
import { participantService } from "../api/participantService";
import { teacherService } from "../api/teacherService";
import { Membership, Teacher } from "../types/domain";
import { useDebouncedValue } from "./useDebouncedValue";

export function ParticipantForm({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient();
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [comment, setComment] = useState("");
  const mutation = useMutation({
    mutationFn: () => participantService.create({ full_name: fullName, phone, comment, is_active: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["participants"] });
      onDone();
    },
  });

  return (
    <form className="space-y-4" onSubmit={(event) => submit(event, mutation.mutate)}>
      <Field label="ФИО" value={fullName} onChange={setFullName} required />
      <Field label="Телефон" value={phone} onChange={setPhone} />
      <label className="block text-sm font-medium text-slate-700">
        Комментарий
        <textarea className="textarea mt-1" value={comment} onChange={(event) => setComment(event.target.value)} />
      </label>
      <SubmitButton label="Создать участника" pending={mutation.isPending} />
    </form>
  );
}

export function MembershipForm({ participantId, membership, onDone }: { participantId?: number; membership?: Membership; onDone: () => void }) {
  const queryClient = useQueryClient();
  const [selectedParticipant, setSelectedParticipant] = useState((participantId ?? membership?.participant_id)?.toString() ?? "");
  const [membershipTypeId, setMembershipTypeId] = useState(membership?.membership_type_id.toString() ?? "");
  const [totalLessons, setTotalLessons] = useState(membership?.total_lessons.toString() ?? "");
  const [remainingLessons, setRemainingLessons] = useState(membership?.remaining_lessons.toString() ?? "");
  const [price, setPrice] = useState(membership?.price ?? "");
  const [teacherLessonRate, setTeacherLessonRate] = useState(membership?.teacher_lesson_rate ?? "");
  const [startDate, setStartDate] = useState(membership?.start_date ?? "");
  const [endDate, setEndDate] = useState(membership?.end_date ?? "");
  const [participantSearch, setParticipantSearch] = useState("");
  const debouncedSearch = useDebouncedValue(participantSearch, 300);
  const participants = useQuery({
    queryKey: ["participants", "membership-form", debouncedSearch],
    queryFn: () => participantService.list(debouncedSearch),
  });
  const types = useQuery({ queryKey: ["membership-types"], queryFn: membershipTypeService.list });
  const selectedType = types.data?.find((type) => String(type.id) === membershipTypeId);
  const lessonCount = Number(totalLessons || selectedType?.lesson_count || 0);
  const coursePrice = Number(price || selectedType?.price || 0);
  const lessonPrice = lessonCount > 0 ? coursePrice / lessonCount : 0;
  const teacherTotal = Number(teacherLessonRate || 0) * lessonCount;
  const schoolTotal = Math.max(coursePrice - teacherTotal, 0);
  function selectMembershipType(value: string) {
    setMembershipTypeId(value);
    const nextType = types.data?.find((type) => String(type.id) === value);
    if (!nextType) {
      setTeacherLessonRate("");
      return;
    }
    const defaultRate = Number(nextType.price) / nextType.lesson_count / 2;
    setTotalLessons(String(nextType.lesson_count));
    setRemainingLessons(String(nextType.lesson_count));
    setPrice(String(nextType.price));
    setTeacherLessonRate(defaultRate.toFixed(2));
  }
  const mutation = useMutation({
    mutationFn: () => {
      if (membership) {
        return membershipService.update(membership.id, {
          total_lessons: Number(totalLessons),
          remaining_lessons: Number(remainingLessons),
          price,
          teacher_lesson_rate: teacherLessonRate,
          start_date: startDate,
          end_date: endDate,
        });
      }
      return membershipService.create({
          participant_id: Number(selectedParticipant),
          membership_type_id: Number(membershipTypeId),
          teacher_lesson_rate: Number(teacherLessonRate),
        });
    },
    onSuccess: () => {
      queryClient.invalidateQueries();
      onDone();
    },
  });

  return (
    <form className="space-y-4" onSubmit={(event) => submit(event, mutation.mutate)}>
      {!participantId && !membership ? (
        <>
          <Field label="Поиск участника" value={participantSearch} onChange={setParticipantSearch} />
          <label className="block text-sm font-medium text-slate-700">
            Участник
            <select className="input mt-1" value={selectedParticipant} onChange={(event) => setSelectedParticipant(event.target.value)} required>
              <option value="">Выберите участника</option>
              {participants.data?.map((participant) => (
                <option key={participant.id} value={participant.id}>
                  {participant.full_name} {participant.phone ? ` / ${participant.phone}` : ""}
                </option>
              ))}
            </select>
          </label>
          {!participants.isLoading && participants.data?.length === 0 ? <p className="text-sm text-slate-500">Участники не найдены</p> : null}
        </>
      ) : null}
      <label className="block text-sm font-medium text-slate-700">
        Тип абонемента
        <select className="input mt-1" value={membershipTypeId} onChange={(event) => selectMembershipType(event.target.value)} required disabled={Boolean(membership)}>
          <option value="">Выберите тип</option>
          {types.data?.map((type) => (
            <option key={type.id} value={type.id}>
              {type.name}, {type.lesson_count} занятий
            </option>
          ))}
        </select>
      </label>
      <div className="rounded-md border border-slate-200 p-4">
        <div className="font-bold text-ink">Основная информация</div>
        <div className="mt-3 grid grid-cols-2 gap-3">
          <Field label="Всего занятий" value={totalLessons} onChange={setTotalLessons} type="number" required />
          <Field label="Осталось занятий" value={remainingLessons} onChange={setRemainingLessons} type="number" required />
          {membership ? <Field label="Дата начала" value={startDate} onChange={setStartDate} type="date" required /> : null}
          {membership ? <Field label="Дата окончания" value={endDate} onChange={setEndDate} type="date" required /> : null}
        </div>
      </div>
      <div className="rounded-md border border-slate-200 p-4">
        <div className="font-bold text-ink">Финансовые условия</div>
        <div className="mt-3 grid grid-cols-2 gap-3">
          <Field label="Стоимость абонемента" value={price} onChange={setPrice} type="number" required />
          <Field label="Выплата преподавателю за занятие" value={teacherLessonRate} onChange={setTeacherLessonRate} type="number" required />
        </div>
        <p className="mt-3 text-xs text-slate-500">
          Цена занятия: {formatMoney(lessonPrice)}. Заработок преподавателя за весь абонемент: {formatMoney(teacherTotal)}.
          Заработок школы: {formatMoney(schoolTotal)}. Backend проверит итоговые значения при сохранении.
        </p>
      </div>
      <SubmitButton label={membership ? "Сохранить абонемент" : "Создать абонемент"} pending={mutation.isPending} />
      {mutation.error ? <p className="text-sm text-coral">{mutation.error.message}</p> : null}
    </form>
  );
}

export function MembershipTypeForm({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [lessonCount, setLessonCount] = useState("8");
  const [price, setPrice] = useState("7200");
  const [validityDays, setValidityDays] = useState("45");
  const [description, setDescription] = useState("");
  const mutation = useMutation({
    mutationFn: () =>
      membershipTypeService.create({
        name,
        lesson_count: Number(lessonCount),
        price,
        validity_days: Number(validityDays),
        description,
        is_active: true,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["membership-types"] });
      onDone();
    },
  });

  return (
    <form className="grid grid-cols-2 gap-4" onSubmit={(event) => submit(event, mutation.mutate)}>
      <Field label="Название" value={name} onChange={setName} required />
      <Field label="Занятий" value={lessonCount} onChange={setLessonCount} type="number" required />
      <Field label="Цена" value={price} onChange={setPrice} type="number" required />
      <Field label="Дней действия" value={validityDays} onChange={setValidityDays} type="number" required />
      <div className="col-span-2">
        <Field label="Описание" value={description} onChange={setDescription} />
      </div>
      <div className="col-span-2">
        <SubmitButton label="Создать тип" pending={mutation.isPending} />
      </div>
    </form>
  );
}

export function TeacherForm({ teacher, onDone }: { teacher?: Teacher; onDone: () => void }) {
  const queryClient = useQueryClient();
  const [fullName, setFullName] = useState(teacher?.full_name ?? "");
  const [phone, setPhone] = useState(teacher?.phone ?? "");
  const [comment, setComment] = useState(teacher?.comment ?? "");
  const [isActive, setIsActive] = useState(teacher?.is_active ?? true);
  const mutation = useMutation({
    mutationFn: () => {
      const payload = { full_name: fullName, phone, comment, is_active: isActive };
      return teacher ? teacherService.update(teacher.id, payload) : teacherService.create(payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teachers"] });
      onDone();
    },
  });

  return (
    <form className="space-y-4" onSubmit={(event) => submit(event, mutation.mutate)}>
      <Field label="ФИО" value={fullName} onChange={setFullName} required />
      <Field label="Телефон" value={phone} onChange={setPhone} />
      <Field label="Комментарий" value={comment} onChange={setComment} />
      <label className="flex items-center gap-2 text-sm font-semibold text-slate-700">
        <input checked={isActive} type="checkbox" onChange={(event) => setIsActive(event.target.checked)} />
        Активен
      </label>
      {mutation.error ? <p className="text-sm text-coral">{mutation.error.message}</p> : null}
      <SubmitButton label={teacher ? "Сохранить преподавателя" : "Создать преподавателя"} pending={mutation.isPending} />
    </form>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  required = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  required?: boolean;
}) {
  return (
    <label className="block text-sm font-medium text-slate-700">
      {label}
      <input className="input mt-1" value={value} type={type} onChange={(event) => onChange(event.target.value)} required={required} />
    </label>
  );
}

function SubmitButton({ label, pending }: { label: string; pending: boolean }) {
  return (
    <button className="btn-primary w-full" type="submit" disabled={pending}>
      {pending ? "Сохранение..." : label}
    </button>
  );
}

function submit(event: FormEvent, action: () => void) {
  event.preventDefault();
  action();
}

function formatMoney(value: number) {
  return value.toLocaleString("ru-RU", { style: "currency", currency: "RUB", maximumFractionDigits: 0 });
}
