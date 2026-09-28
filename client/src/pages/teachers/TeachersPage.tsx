import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Pencil, Plus } from "lucide-react";

import { teacherService } from "../../shared/api/teacherService";
import type { Teacher } from "../../shared/types/domain";
import { TeacherForm } from "../../shared/ui/Forms";
import { Modal } from "../../shared/ui/Modal";

export function TeachersPage() {
  const [teacherModal, setTeacherModal] = useState<Teacher | "new" | null>(null);
  const teachers = useQuery({ queryKey: ["teachers"], queryFn: teacherService.list });

  return (
    <div className="space-y-5">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Преподаватели</h1>
          <p className="mt-1 text-sm text-slate-500">Контактные данные и доступность преподавателей для расписания и списания занятий.</p>
        </div>
        <button className="btn-primary" onClick={() => setTeacherModal("new")}>
          <Plus size={18} /> Создать преподавателя
        </button>
      </div>

      {teachers.isError ? (
        <div className="panel border-red-100 bg-red-50 p-4 text-sm text-red-700">Не удалось загрузить преподавателей.</div>
      ) : null}

      <section className="panel overflow-hidden">
        <table className="w-full border-collapse">
          <thead>
            <tr><th className="th">ФИО</th><th className="th">Телефон</th><th className="th">Комментарий</th><th className="th">Статус</th><th className="th">Действия</th></tr>
          </thead>
          <tbody>
            {teachers.data?.map((teacher) => (
              <tr key={teacher.id}>
                <td className="td font-semibold text-ink">{teacher.full_name}</td>
                <td className="td">{teacher.phone ?? "—"}</td>
                <td className="td">{teacher.comment ?? "—"}</td>
                <td className="td">
                  <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${teacher.is_active ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>
                    {teacher.is_active ? "Активен" : "Отключен"}
                  </span>
                </td>
                <td className="td">
                  <button className="inline-flex items-center gap-1.5 font-semibold text-mint hover:text-teal-700" onClick={() => setTeacherModal(teacher)}>
                    <Pencil size={16} /> Редактировать
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {teachers.isLoading ? <div className="border-t border-slate-100 p-6 text-sm text-slate-500">Загружаем преподавателей...</div> : null}
        {!teachers.isLoading && teachers.data?.length === 0 ? <div className="border-t border-slate-100 p-6 text-sm text-slate-500">Преподаватели пока не добавлены.</div> : null}
      </section>

      <Modal title={teacherModal === "new" ? "Создать преподавателя" : "Редактировать преподавателя"} open={teacherModal !== null} onClose={() => setTeacherModal(null)}>
        <TeacherForm teacher={teacherModal && teacherModal !== "new" ? teacherModal : undefined} onDone={() => setTeacherModal(null)} />
      </Modal>
    </div>
  );
}
