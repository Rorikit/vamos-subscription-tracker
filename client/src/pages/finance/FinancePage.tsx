import { Fragment, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, ChevronRight } from "lucide-react";

import { financeService } from "../../shared/api/financeService";
import { teacherService } from "../../shared/api/teacherService";
import { toCurrency, toDate } from "../../shared/api/client";
import { StatCard } from "../../shared/ui/StatCard";

export function FinancePage() {
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [teacherId, setTeacherId] = useState("");
  const [expandedTeacherId, setExpandedTeacherId] = useState<number | null>(null);
  const summary = useQuery({ queryKey: ["finance-summary"], queryFn: financeService.summary });
  const teachers = useQuery({ queryKey: ["teachers"], queryFn: teacherService.list });
  const earnings = useQuery({
    queryKey: ["teacher-earnings", dateFrom, dateTo, teacherId],
    queryFn: () => financeService.teacherEarnings({ date_from: dateFrom, date_to: dateTo, teacher_id: teacherId }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">Финансы</h1>
        <p className="mt-1 text-sm text-slate-500">Выручка и подробный заработок преподавателей по занятиям.</p>
      </div>
      <div className="grid grid-cols-3 gap-4">
        <StatCard label="Общая выручка" value={toCurrency(summary.data?.total_revenue ?? 0)} />
        <StatCard label="Всего проведено занятий" value={summary.data?.total_visits ?? 0} />
        <StatCard label="Заработок преподавателей" value={toCurrency(summary.data?.teacher_earnings_total ?? 0)} />
      </div>
      <section className="panel p-5">
        <div className="grid grid-cols-3 gap-4">
          <label className="block text-sm font-medium text-slate-700">
            Период с
            <input className="input mt-1" type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
          </label>
          <label className="block text-sm font-medium text-slate-700">
            Период по
            <input className="input mt-1" type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
          </label>
          <label className="block text-sm font-medium text-slate-700">
            Преподаватель
            <select className="input mt-1" value={teacherId} onChange={(event) => setTeacherId(event.target.value)}>
              <option value="">Все преподаватели</option>
              {teachers.data?.map((teacher) => (
                <option key={teacher.id} value={teacher.id}>
                  {teacher.full_name}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>
      <section className="panel overflow-hidden">
        <SectionTitle title="Заработок преподавателей" />
        <table className="w-full">
          <thead>
            <tr>
              <th className="th w-12"></th>
              <th className="th">Преподаватель</th>
              <th className="th">Количество занятий</th>
              <th className="th">Заработано</th>
              <th className="th">Средняя стоимость занятия</th>
            </tr>
          </thead>
          <tbody>
            {earnings.data?.map((item) => {
              const expanded = expandedTeacherId === item.teacher_id;
              return (
                <Fragment key={item.teacher_id}>
                  <tr key={item.teacher_id}>
                    <td className="td">
                      <button
                        className="btn-secondary h-8 w-8 px-0"
                        onClick={() => setExpandedTeacherId(expanded ? null : item.teacher_id)}
                        aria-label="Показать занятия"
                      >
                        {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                      </button>
                    </td>
                    <td className="td font-semibold text-ink">{item.teacher_name}</td>
                    <td className="td">{item.visits_count}</td>
                    <td className="td">{toCurrency(item.total_earned)}</td>
                    <td className="td">{toCurrency(item.average_lesson_price)}</td>
                  </tr>
                  {expanded ? (
                    <tr key={`${item.teacher_id}-details`}>
                      <td className="td bg-slate-50" colSpan={5}>
                        <table className="w-full">
                          <thead>
                            <tr>
                              <th className="th">Дата</th>
                              <th className="th">Ученик</th>
                              <th className="th">Абонемент</th>
                              <th className="th">Стоимость занятия</th>
                              <th className="th">Статус</th>
                            </tr>
                          </thead>
                          <tbody>
                            {item.visits.map((visit) => (
                              <tr key={visit.visit_id}>
                                <td className="td">{toDate(visit.visit_date)}</td>
                                <td className="td">{visit.participant_name}</td>
                                <td className="td">{visit.membership_name}</td>
                                <td className="td">{toCurrency(visit.lesson_price)}</td>
                                <td className="td">{visit.is_cancelled ? "Возвращено" : "Активно"}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              );
            })}
            {!earnings.isLoading && earnings.data?.length === 0 ? (
              <tr><td className="td text-center text-slate-500" colSpan={5}>Занятия не найдены</td></tr>
            ) : null}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function SectionTitle({ title }: { title: string }) {
  return <div className="border-b border-slate-100 px-5 py-4 font-bold text-ink">{title}</div>;
}
