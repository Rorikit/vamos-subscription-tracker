import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus } from "lucide-react";

import type { Operator } from "../../shared/api/authService";
import { membershipTypeService } from "../../shared/api/membershipTypeService";
import { operatorService } from "../../shared/api/operatorService";
import { teacherService } from "../../shared/api/teacherService";
import { toCurrency } from "../../shared/api/client";
import { MembershipTypeForm, TeacherForm } from "../../shared/ui/Forms";
import { Modal } from "../../shared/ui/Modal";
import { Teacher } from "../../shared/types/domain";

export function SettingsPage() {
  const [typeOpen, setTypeOpen] = useState(false);
  const [teacherModal, setTeacherModal] = useState<Teacher | "new" | null>(null);
  const [operatorModal, setOperatorModal] = useState<Operator | "new" | null>(null);
  const types = useQuery({ queryKey: ["membership-types"], queryFn: membershipTypeService.list });
  const teachers = useQuery({ queryKey: ["teachers"], queryFn: teacherService.list });
  const operators = useQuery({ queryKey: ["operators"], queryFn: operatorService.list });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">Настройки</h1>
        <p className="mt-1 text-sm text-slate-500">Управление типами абонементов, преподавателями и пользователями приложения.</p>
      </div>

      <section className="panel overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2 className="font-bold text-ink">Пользователи</h2>
          <button className="btn-primary" onClick={() => setOperatorModal("new")}>
            <Plus size={18} /> Создать пользователя
          </button>
        </div>
        <table className="w-full">
          <thead className="bg-slate-50">
            <tr>
              <th className="th">Имя</th>
              <th className="th">Логин</th>
              <th className="th">Роль</th>
              <th className="th">Статус</th>
              <th className="th">Создан</th>
              <th className="th">Действия</th>
            </tr>
          </thead>
          <tbody>
            {operators.data?.map((operator) => (
              <tr key={operator.id}>
                <td className="td font-semibold text-ink">{operator.full_name}</td>
                <td className="td">{operator.username}</td>
                <td className="td">{roleLabel(operator.role)}</td>
                <td className="td">{operator.is_active ? "Активен" : "Отключен"}</td>
                <td className="td">{new Intl.DateTimeFormat("ru-RU").format(new Date(operator.created_at))}</td>
                <td className="td">
                  <button className="font-semibold text-mint hover:text-teal-700" onClick={() => setOperatorModal(operator)}>
                    <Pencil className="mr-1 inline" size={16} /> Редактировать
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="panel overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2 className="font-bold text-ink">Типы абонементов</h2>
          <button className="btn-primary" onClick={() => setTypeOpen(true)}>
            <Plus size={18} /> Создать тип
          </button>
        </div>
        <table className="w-full">
          <thead className="bg-slate-50">
            <tr>
              <th className="th">Название</th>
              <th className="th">Занятий</th>
              <th className="th">Цена</th>
              <th className="th">Срок</th>
              <th className="th">Описание</th>
              <th className="th">Статус</th>
            </tr>
          </thead>
          <tbody>
            {types.data?.map((type) => (
              <tr key={type.id}>
                <td className="td font-semibold text-ink">{type.name}</td>
                <td className="td">{type.lesson_count}</td>
                <td className="td">{toCurrency(type.price)}</td>
                <td className="td">{type.validity_days} дней</td>
                <td className="td">{type.description ?? "—"}</td>
                <td className="td">{type.is_active ? "Активен" : "Отключен"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="panel overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2 className="font-bold text-ink">Преподаватели</h2>
          <button className="btn-primary" onClick={() => setTeacherModal("new")}>
            <Plus size={18} /> Создать преподавателя
          </button>
        </div>
        <table className="w-full">
          <thead className="bg-slate-50">
            <tr>
              <th className="th">ФИО</th>
              <th className="th">Телефон</th>
              <th className="th">Комментарий</th>
              <th className="th">Процент преподавателя</th>
              <th className="th">Статус</th>
              <th className="th">Действия</th>
            </tr>
          </thead>
          <tbody>
            {teachers.data?.map((teacher) => (
              <tr key={teacher.id}>
                <td className="td font-semibold text-ink">{teacher.full_name}</td>
                <td className="td">{teacher.phone ?? "—"}</td>
                <td className="td">{teacher.comment ?? "—"}</td>
                <td className="td">{Number(teacher.teacher_share_percent).toLocaleString("ru-RU")}%</td>
                <td className="td">{teacher.is_active ? "Активен" : "Отключен"}</td>
                <td className="td">
                  <button className="font-semibold text-mint hover:text-teal-700" onClick={() => setTeacherModal(teacher)}>
                    <Pencil className="mr-1 inline" size={16} /> Редактировать
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <Modal title="Создать тип абонемента" open={typeOpen} onClose={() => setTypeOpen(false)}>
        <MembershipTypeForm onDone={() => setTypeOpen(false)} />
      </Modal>
      <Modal
        title={teacherModal === "new" ? "Создать преподавателя" : "Редактировать преподавателя"}
        open={teacherModal !== null}
        onClose={() => setTeacherModal(null)}
      >
        <TeacherForm teacher={teacherModal && teacherModal !== "new" ? teacherModal : undefined} onDone={() => setTeacherModal(null)} />
      </Modal>
      <Modal
        title={operatorModal === "new" ? "Создать пользователя" : "Редактировать пользователя"}
        open={operatorModal !== null}
        onClose={() => setOperatorModal(null)}
      >
        <OperatorForm operator={operatorModal && operatorModal !== "new" ? operatorModal : undefined} onDone={() => setOperatorModal(null)} />
      </Modal>
    </div>
  );
}

function OperatorForm({ operator, onDone }: { operator?: Operator; onDone: () => void }) {
  const queryClient = useQueryClient();
  const [fullName, setFullName] = useState(operator?.full_name ?? "");
  const [username, setUsername] = useState(operator?.username ?? "");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Operator["role"]>(operator?.role ?? "operator");
  const [isActive, setIsActive] = useState(operator?.is_active ?? true);
  const mutation = useMutation({
    mutationFn: () => {
      const payload = {
        full_name: fullName,
        username,
        password: password || undefined,
        role,
        is_active: isActive,
      };
      return operator ? operatorService.update(operator.id, payload) : operatorService.create({ ...payload, password });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["operators"] });
      queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
      onDone();
    },
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    mutation.mutate();
  }

  return (
    <form className="space-y-4" onSubmit={submit}>
      <Field label="Имя" value={fullName} onChange={setFullName} required />
      <Field label="Логин" value={username} onChange={setUsername} required />
      <label className="block text-sm font-medium text-slate-700">
        Роль
        <select className="input mt-1" value={role} onChange={(event) => setRole(event.target.value as Operator["role"])}>
          <option value="admin">Администратор</option>
          <option value="operator">Оператор</option>
          <option value="finance">Финансист</option>
        </select>
      </label>
      <Field label={operator ? "Новый пароль" : "Пароль"} value={password} onChange={setPassword} type="password" required={!operator} />
      <label className="flex items-center gap-2 text-sm font-semibold text-slate-700">
        <input checked={isActive} type="checkbox" onChange={(event) => setIsActive(event.target.checked)} />
        Активен
      </label>
      {mutation.error ? <p className="text-sm text-coral">{mutation.error.message}</p> : null}
      <button className="btn-primary w-full" disabled={mutation.isPending || !fullName || !username || (!operator && !password)}>
        {mutation.isPending ? "Сохранение..." : operator ? "Сохранить пользователя" : "Создать пользователя"}
      </button>
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

function roleLabel(role: Operator["role"]) {
  const labels: Record<Operator["role"], string> = {
    admin: "Администратор",
    operator: "Оператор",
    finance: "Финансист",
  };
  return labels[role];
}
