import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { membershipService } from "../api/membershipService";
import { membershipTypeService } from "../api/membershipTypeService";
import { participantService } from "../api/participantService";
import { paymentService } from "../api/paymentService";
import { teacherService } from "../api/teacherService";
import { visitService } from "../api/visitService";
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

export function MembershipForm({ participantId, onDone }: { participantId?: number; onDone: () => void }) {
  const queryClient = useQueryClient();
  const [selectedParticipant, setSelectedParticipant] = useState(participantId?.toString() ?? "");
  const [membershipTypeId, setMembershipTypeId] = useState("");
  const [participantSearch, setParticipantSearch] = useState("");
  const debouncedSearch = useDebouncedValue(participantSearch, 300);
  const participants = useQuery({
    queryKey: ["participants", "membership-form", debouncedSearch],
    queryFn: () => participantService.list(debouncedSearch),
  });
  const types = useQuery({ queryKey: ["membership-types"], queryFn: membershipTypeService.list });
  const mutation = useMutation({
    mutationFn: () => membershipService.create({ participant_id: Number(selectedParticipant), membership_type_id: Number(membershipTypeId) }),
    onSuccess: () => {
      queryClient.invalidateQueries();
      onDone();
    },
  });

  return (
    <form className="space-y-4" onSubmit={(event) => submit(event, mutation.mutate)}>
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
      <label className="block text-sm font-medium text-slate-700">
        Тип абонемента
        <select className="input mt-1" value={membershipTypeId} onChange={(event) => setMembershipTypeId(event.target.value)} required>
          <option value="">Выберите тип</option>
          {types.data?.map((type) => (
            <option key={type.id} value={type.id}>
              {type.name}, {type.lesson_count} занятий
            </option>
          ))}
        </select>
      </label>
      <SubmitButton label="Создать абонемент" pending={mutation.isPending} />
    </form>
  );
}

export function WriteOffForm({ participantId, onDone }: { participantId?: number; onDone: () => void }) {
  const queryClient = useQueryClient();
  const [selectedParticipant, setSelectedParticipant] = useState(participantId?.toString() ?? "");
  const [participantSearch, setParticipantSearch] = useState("");
  const [teacherId, setTeacherId] = useState("");
  const debouncedSearch = useDebouncedValue(participantSearch, 300);
  const participants = useQuery({
    queryKey: ["participants", "write-off-form", debouncedSearch],
    queryFn: () => participantService.list(debouncedSearch),
  });
  const teachers = useQuery({ queryKey: ["teachers"], queryFn: teacherService.list });
  const activeTeachers = teachers.data?.filter((teacher) => teacher.is_active) ?? [];
  const mutation = useMutation({
    mutationFn: () => visitService.writeOff({ participant_id: Number(selectedParticipant), teacher_id: Number(teacherId) }),
    onSuccess: () => {
      queryClient.invalidateQueries();
      onDone();
    },
  });

  return (
    <form className="space-y-4" onSubmit={(event) => submit(event, mutation.mutate)}>
      {!participantId ? <Field label="Поиск участника" value={participantSearch} onChange={setParticipantSearch} /> : null}
      <label className="block text-sm font-medium text-slate-700">
        Участник
        <select className="input mt-1" value={selectedParticipant} onChange={(event) => setSelectedParticipant(event.target.value)} required disabled={Boolean(participantId)}>
          <option value="">Выберите участника</option>
          {participants.data?.map((participant) => (
            <option key={participant.id} value={participant.id}>
              {participant.full_name} {participant.phone ? ` / ${participant.phone}` : ""}
            </option>
          ))}
        </select>
      </label>
      {!participants.isLoading && participants.data?.length === 0 ? <p className="text-sm text-slate-500">Участники не найдены</p> : null}
      <label className="block text-sm font-medium text-slate-700">
        Преподаватель
        <select className="input mt-1" value={teacherId} onChange={(event) => setTeacherId(event.target.value)} required>
          <option value="">Выберите преподавателя</option>
          {activeTeachers.map((teacher) => (
            <option key={teacher.id} value={teacher.id}>
              {teacher.full_name}
            </option>
          ))}
        </select>
      </label>
      <button className="btn-primary w-full" type="submit" disabled={mutation.isPending || !teacherId || !selectedParticipant}>
        {mutation.isPending ? "Сохранение..." : "Списать занятие"}
      </button>
      {mutation.error ? <p className="text-sm text-coral">{mutation.error.message}</p> : null}
    </form>
  );
}

export function PaymentForm({ participantId, memberships, onDone }: { participantId?: number; memberships: Membership[]; onDone: () => void }) {
  const queryClient = useQueryClient();
  const [membershipId, setMembershipId] = useState(memberships[0]?.id.toString() ?? "");
  const [amount, setAmount] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("cash");
  const [comment, setComment] = useState("");
  const mutation = useMutation({
    mutationFn: () =>
      paymentService.create({
        participant_id: participantId ?? memberships.find((membership) => membership.id === Number(membershipId))!.participant_id,
        membership_id: Number(membershipId),
        amount: Number(amount),
        payment_method: paymentMethod,
        comment,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries();
      onDone();
    },
  });

  return (
    <form className="space-y-4" onSubmit={(event) => submit(event, mutation.mutate)}>
      <label className="block text-sm font-medium text-slate-700">
        Абонемент
        <select className="input mt-1" value={membershipId} onChange={(event) => setMembershipId(event.target.value)} required>
          <option value="">Выберите абонемент</option>
          {memberships.map((membership) => (
            <option key={membership.id} value={membership.id}>
              #{membership.id} {membership.membership_type?.name}
            </option>
          ))}
        </select>
      </label>
      <Field label="Сумма" value={amount} onChange={setAmount} type="number" required />
      <label className="block text-sm font-medium text-slate-700">
        Способ оплаты
        <select className="input mt-1" value={paymentMethod} onChange={(event) => setPaymentMethod(event.target.value)}>
          <option value="cash">Наличные</option>
          <option value="card">Карта</option>
          <option value="transfer">Перевод</option>
        </select>
      </label>
      <Field label="Комментарий" value={comment} onChange={setComment} />
      <SubmitButton label="Добавить оплату" pending={mutation.isPending} />
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
  const [teacherSharePercent, setTeacherSharePercent] = useState(teacher?.teacher_share_percent ?? "50");
  const [isActive, setIsActive] = useState(teacher?.is_active ?? true);
  const mutation = useMutation({
    mutationFn: () => {
      const payload = { full_name: fullName, phone, comment, teacher_share_percent: teacherSharePercent, is_active: isActive };
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
      <Field label="Процент преподавателя" value={teacherSharePercent} onChange={setTeacherSharePercent} type="number" required />
      <label className="flex items-center gap-2 text-sm font-semibold text-slate-700">
        <input checked={isActive} type="checkbox" onChange={(event) => setIsActive(event.target.checked)} />
        Активен
      </label>
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
