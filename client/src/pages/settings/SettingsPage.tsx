import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus, Pencil } from "lucide-react";

import { membershipTypeService } from "../../shared/api/membershipTypeService";
import { teacherService } from "../../shared/api/teacherService";
import { toCurrency } from "../../shared/api/client";
import { MembershipTypeForm, TeacherForm } from "../../shared/ui/Forms";
import { Modal } from "../../shared/ui/Modal";
import { Teacher } from "../../shared/types/domain";

export function SettingsPage() {
  const [typeOpen, setTypeOpen] = useState(false);
  const [teacherModal, setTeacherModal] = useState<Teacher | "new" | null>(null);
  const types = useQuery({ queryKey: ["membership-types"], queryFn: membershipTypeService.list });
  const teachers = useQuery({ queryKey: ["teachers"], queryFn: teacherService.list });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">Настройки</h1>
        <p className="mt-1 text-sm text-slate-500">Управление типами абонементов и преподавателями.</p>
      </div>

      <section className="panel overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2 className="font-bold text-ink">Типы абонементов</h2>
          <button className="btn-primary" onClick={() => setTypeOpen(true)}><Plus size={18} /> Создать тип</button>
        </div>
        <table className="w-full">
          <thead className="bg-slate-50">
            <tr><th className="th">Название</th><th className="th">Занятий</th><th className="th">Цена</th><th className="th">Срок</th><th className="th">Описание</th><th className="th">Статус</th></tr>
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
          <button className="btn-primary" onClick={() => setTeacherModal("new")}><Plus size={18} /> Создать преподавателя</button>
        </div>
        <table className="w-full">
          <thead className="bg-slate-50">
            <tr><th className="th">ФИО</th><th className="th">Телефон</th><th className="th">Комментарий</th><th className="th">Статус</th><th className="th">Действия</th></tr>
          </thead>
          <tbody>
            {teachers.data?.map((teacher) => (
              <tr key={teacher.id}>
                <td className="td font-semibold text-ink">{teacher.full_name}</td>
                <td className="td">{teacher.phone ?? "—"}</td>
                <td className="td">{teacher.comment ?? "—"}</td>
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
    </div>
  );
}

