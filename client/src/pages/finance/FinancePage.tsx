import { Fragment, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, RefreshCw } from "lucide-react";

import { financeService } from "../../shared/api/financeService";
import { teacherService } from "../../shared/api/teacherService";
import { toCurrency, toDate } from "../../shared/api/client";
import { StatCard } from "../../shared/ui/StatCard";
import type { TeacherEarning } from "../../shared/types/domain";

export function FinancePage() {
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [teacherId, setTeacherId] = useState("");
  const [expandedTeacherId, setExpandedTeacherId] = useState<number | null>(null);

  const filters = { date_from: dateFrom, date_to: dateTo, teacher_id: teacherId };
  const summary = useQuery({ queryKey: ["finance-summary", filters], queryFn: () => financeService.summary(filters) });
  const teachers = useQuery({ queryKey: ["teachers"], queryFn: teacherService.list });
  const earnings = useQuery({
    queryKey: ["teacher-earnings", filters],
    queryFn: () => financeService.teacherEarnings({ ...filters, include_cancelled: true }),
  });

  const completedValue = Number(summary.data?.completed_lessons_value ?? 0);
  const teacherTotal = Number(summary.data?.teacher_earnings_total ?? 0);
  const schoolTotal = Number(summary.data?.school_earnings_total ?? 0);
  const teacherPercent = completedValue ? Math.round((teacherTotal / completedValue) * 100) : 0;
  const schoolPercent = completedValue ? Math.max(0, 100 - teacherPercent) : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">Финансы</h1>
        <p className="mt-1 text-sm text-slate-500">Продажи, проведенные занятия, выплаты преподавателям и доход школы.</p>
      </div>

      <section className="panel p-5">
        <div className="grid grid-cols-[1fr_1fr_1fr_auto] items-end gap-4">
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
          <button className="btn-secondary" onClick={() => { setDateFrom(""); setDateTo(""); setTeacherId(""); }}>
            <RefreshCw size={17} />
            Сбросить
          </button>
        </div>
      </section>

      {summary.isError || earnings.isError ? (
        <ErrorState onRetry={() => { summary.refetch(); earnings.refetch(); }} />
      ) : null}

      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Продажи абонементов" value={toCurrency(summary.data?.memberships_sold_total ?? 0)} hint="По дате начала абонемента" />
        <StatCard label="Получено оплат" value={toCurrency(summary.data?.payments_received_total ?? 0)} hint="Неотмененные платежи" />
        <StatCard label="Стоимость проведенных занятий" value={toCurrency(summary.data?.completed_lessons_value ?? 0)} hint="Только проведенные занятия" />
        <StatCard label="Доход школы" value={toCurrency(summary.data?.school_earnings_total ?? 0)} hint="После выплат преподавателям" />
      </div>

      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Проведено занятий" value={summary.data?.completed_visits_count ?? 0} />
        <StatCard label="Средняя цена занятия" value={toCurrency(summary.data?.average_lesson_price ?? 0)} />
        <StatCard label="Средняя выплата преподавателю" value={toCurrency(summary.data?.average_teacher_earning ?? 0)} />
        <StatCard label="Активных преподавателей" value={summary.data?.active_teachers_count ?? 0} />
      </div>

      <section className="panel p-5">
        <h2 className="font-bold text-ink">Распределение стоимости проведенных занятий</h2>
        {completedValue ? (
          <div className="mt-4 space-y-3">
            <div className="flex h-4 overflow-hidden rounded-full bg-slate-100">
              <div className="bg-mint" style={{ width: `${teacherPercent}%` }} />
              <div className="bg-coral" style={{ width: `${schoolPercent}%` }} />
            </div>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <DistributionItem title="Преподавателям" value={teacherTotal} percent={teacherPercent} color="bg-mint" />
              <DistributionItem title="Школе" value={schoolTotal} percent={schoolPercent} color="bg-coral" />
            </div>
          </div>
        ) : (
          <EmptyText text="За выбранный период проведенных занятий нет." />
        )}
      </section>

      <section className="panel overflow-hidden">
        <SectionTitle title="Заработок преподавателей" />
        {earnings.isLoading ? <LoadingRows /> : null}
        {!earnings.isLoading && earnings.data?.length === 0 ? <EmptyBlock text="За выбранный период проведенных занятий нет." /> : null}
        {!earnings.isLoading && earnings.data?.length ? (
          <TeacherTable
            data={earnings.data}
            expandedTeacherId={expandedTeacherId}
            onToggle={(id) => setExpandedTeacherId(expandedTeacherId === id ? null : id)}
          />
        ) : null}
      </section>
    </div>
  );
}

function TeacherTable({ data, expandedTeacherId, onToggle }: { data: TeacherEarning[]; expandedTeacherId: number | null; onToggle: (id: number) => void }) {
  return (
    <table className="w-full">
      <thead className="bg-slate-50">
        <tr>
          <th className="th">Преподаватель</th>
          <th className="th">Проведено занятий</th>
          <th className="th">Стоимость занятий</th>
          <th className="th">Процент</th>
          <th className="th">Выплата</th>
          <th className="th">Доход школы</th>
          <th className="th">Средняя выплата</th>
          <th className="th">Подробнее</th>
        </tr>
      </thead>
      <tbody>
        {data.map((item) => {
          const expanded = expandedTeacherId === item.teacher_id;
          return (
            <Fragment key={item.teacher_id}>
              <tr className={expanded ? "bg-teal-50/40" : ""}>
                <td className="td">
                  <button className="flex w-full items-center gap-3 text-left" onClick={() => onToggle(item.teacher_id)}>
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-100 text-sm font-bold text-slate-600">
                      {initials(item.teacher_name)}
                    </span>
                    <span>
                      <span className="block font-semibold text-ink">{item.teacher_name}</span>
                      <span className="text-xs text-slate-500">
                        {item.last_visit_date ? `Последнее занятие: ${toDate(item.last_visit_date)}` : "Занятий нет"}
                      </span>
                    </span>
                  </button>
                </td>
                <td className="td">{item.visits_count}</td>
                <td className="td">{toCurrency(item.completed_lessons_value)}</td>
                <td className="td">{Number(item.teacher_share_percent).toLocaleString("ru-RU")}%</td>
                <td className="td font-semibold text-ink">{toCurrency(item.teacher_earned)}</td>
                <td className="td">{toCurrency(item.school_earned)}</td>
                <td className="td">{toCurrency(item.average_teacher_earning)}</td>
                <td className="td">
                  <button className="btn-secondary h-9" onClick={() => onToggle(item.teacher_id)}>
                    {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                    Подробнее
                  </button>
                </td>
              </tr>
              {expanded ? (
                <tr>
                  <td className="td bg-slate-50" colSpan={8}>
                    <VisitDetails item={item} />
                  </td>
                </tr>
              ) : null}
            </Fragment>
          );
        })}
      </tbody>
    </table>
  );
}

function VisitDetails({ item }: { item: TeacherEarning }) {
  if (!item.visits.length) {
    return <EmptyText text="У преподавателя нет занятий за выбранный период." />;
  }
  return (
    <table className="w-full">
      <thead>
        <tr>
          <th className="th">Дата</th>
          <th className="th">Ученик</th>
          <th className="th">Абонемент</th>
          <th className="th">Цена занятия</th>
          <th className="th">Процент</th>
          <th className="th">Выплата</th>
          <th className="th">Доход школы</th>
          <th className="th">Статус</th>
        </tr>
      </thead>
      <tbody>
        {item.visits.map((visit) => (
          <tr key={visit.visit_id} className={visit.is_cancelled ? "opacity-55" : ""}>
            <td className="td">{toDate(visit.visit_date)}</td>
            <td className="td">{visit.participant_name}</td>
            <td className="td">{visit.membership_name}</td>
            <td className="td">{toCurrency(visit.lesson_price)}</td>
            <td className="td">{Number(visit.teacher_share_percent).toLocaleString("ru-RU")}%</td>
            <td className="td">{toCurrency(visit.teacher_earning)}</td>
            <td className="td">{toCurrency(visit.school_earning)}</td>
            <td className="td">
              {visit.is_cancelled ? (
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-500">Возвращено · Не учтено в итогах</span>
              ) : (
                <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">Проведено</span>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function DistributionItem({ title, value, percent, color }: { title: string; value: number; percent: number; color: string }) {
  return (
    <div className="flex items-center justify-between rounded-md border border-slate-100 px-3 py-2">
      <div className="flex items-center gap-2">
        <span className={`h-3 w-3 rounded-full ${color}`} />
        <span className="font-medium text-slate-700">{title}</span>
      </div>
      <div className="text-right">
        <div className="font-bold text-ink">{toCurrency(value)}</div>
        <div className="text-xs text-slate-500">{percent}%</div>
      </div>
    </div>
  );
}

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="panel flex items-center justify-between border-red-100 bg-red-50 p-4 text-sm text-red-700">
      <span>Не удалось загрузить финансовые данные.</span>
      <button className="btn-secondary h-9 bg-white" onClick={onRetry}>Повторить</button>
    </div>
  );
}

function LoadingRows() {
  return (
    <div className="space-y-2 p-5">
      {[1, 2, 3].map((item) => <div key={item} className="h-12 animate-pulse rounded-md bg-slate-100" />)}
    </div>
  );
}

function EmptyBlock({ text }: { text: string }) {
  return <div className="p-8 text-center text-sm text-slate-500">{text}</div>;
}

function EmptyText({ text }: { text: string }) {
  return <p className="text-sm text-slate-500">{text}</p>;
}

function SectionTitle({ title }: { title: string }) {
  return <div className="border-b border-slate-100 px-5 py-4 font-bold text-ink">{title}</div>;
}

function initials(name: string) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}
