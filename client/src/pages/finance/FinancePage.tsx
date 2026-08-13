import { Fragment, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, ChevronDown, ChevronLeft, ChevronRight, ChevronUp, Pencil, RotateCcw, Save } from "lucide-react";

import { financeService } from "../../shared/api/financeService";
import { toCurrency, toDate } from "../../shared/api/client";
import { StatCard } from "../../shared/ui/StatCard";
import type { FinanceMonthlyReport, MonthlyExpense, TeacherEarning } from "../../shared/types/domain";

const monthFormatter = new Intl.DateTimeFormat("ru-RU", { month: "long", year: "numeric" });

export function FinancePage() {
  const queryClient = useQueryClient();
  const [monthDate, setMonthDate] = useState(() => startOfMonth(new Date()));
  const [editingExpense, setEditingExpense] = useState<MonthlyExpense | null>(null);
  const [expandedTeachers, setExpandedTeachers] = useState(false);
  const year = monthDate.getFullYear();
  const month = monthDate.getMonth() + 1;
  const queryKey = ["finance-monthly-report", year, month];
  const report = useQuery({ queryKey, queryFn: () => financeService.monthlyReport({ year, month }) });

  const updateExpense = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: { planned_amount?: string; actual_amount?: string | null; comment?: string | null } }) =>
      financeService.updateExpense(id, payload),
    onSuccess: () => {
      setEditingExpense(null);
      queryClient.invalidateQueries({ queryKey });
      queryClient.invalidateQueries({ queryKey: ["finance-reminders"] });
    },
  });
  const payExpense = useMutation({
    mutationFn: financeService.payExpense,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
      queryClient.invalidateQueries({ queryKey: ["finance-reminders"] });
    },
  });
  const unpayExpense = useMutation({
    mutationFn: financeService.unpayExpense,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
      queryClient.invalidateQueries({ queryKey: ["finance-reminders"] });
    },
  });

  function shiftMonth(step: number) {
    const next = new Date(monthDate);
    next.setMonth(next.getMonth() + step);
    setMonthDate(startOfMonth(next));
  }

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-ink">Финансы</h1>
          <p className="mt-1 text-sm text-slate-500">Доходы, обязательные расходы, выплаты преподавателям и итоговый финансовый результат школы.</p>
        </div>
        <div className="flex items-center gap-2">
          <button className="btn-secondary h-10 px-3" onClick={() => shiftMonth(-1)} title="Предыдущий месяц"><ChevronLeft size={18} /></button>
          <div className="input flex h-10 min-w-56 items-center justify-center font-semibold capitalize">{monthFormatter.format(monthDate)}</div>
          <button className="btn-secondary h-10 px-3" onClick={() => shiftMonth(1)} title="Следующий месяц"><ChevronRight size={18} /></button>
        </div>
      </div>

      {report.isError ? <ErrorState onRetry={() => report.refetch()} /> : null}
      {report.data ? <FinanceContent report={report.data} onEdit={setEditingExpense} onPay={(id) => payExpense.mutate(id)} onUnpay={(id) => unpayExpense.mutate(id)} expandedTeachers={expandedTeachers} onToggleTeachers={() => setExpandedTeachers((value) => !value)} /> : null}
      {report.isLoading ? <LoadingState /> : null}

      {editingExpense ? (
        <ExpenseEditor
          expense={editingExpense}
          pending={updateExpense.isPending}
          error={updateExpense.error instanceof Error ? updateExpense.error.message : null}
          onClose={() => setEditingExpense(null)}
          onSubmit={(payload) => updateExpense.mutate({ id: editingExpense.id, payload })}
        />
      ) : null}
    </div>
  );
}

function FinanceContent({
  report,
  onEdit,
  onPay,
  onUnpay,
  expandedTeachers,
  onToggleTeachers,
}: {
  report: FinanceMonthlyReport;
  onEdit: (expense: MonthlyExpense) => void;
  onPay: (id: number) => void;
  onUnpay: (id: number) => void;
  expandedTeachers: boolean;
  onToggleTeachers: () => void;
}) {
  const unpaidText = `${report.unpaid_expenses_count} платеж${plural(report.unpaid_expenses_count, "", "а", "ей")}`;
  return (
    <>
      {report.unpaid_expenses_count ? (
        <a href="#reminders" className="block rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-900">
          Есть неоплаченные расходы за месяц: {unpaidText} на сумму {toCurrency(report.unpaid_expenses_total)}. Перейти к оплатам
        </a>
      ) : null}

      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Доходы" value={toCurrency(report.income_total)} hint="Продажи абонементов за месяц" />
        <StatCard label="Расходы" value={toCurrency(report.expenses_total)} hint="Обязательные платежи и выплаты" />
        <StatCard label={Number(report.net_result) >= 0 ? "Прибыль" : "Убыток"} value={toCurrency(report.net_result)} hint="Доходы минус расходы" />
        <StatCard label="Не оплачено" value={unpaidText} hint={toCurrency(report.unpaid_expenses_total)} />
      </div>

      <div className="grid grid-cols-[minmax(0,1fr)_minmax(420px,0.9fr)] gap-5">
        <section className="panel p-5">
          <SectionTitle title="Структура расходов" compact />
          <ExpenseBars report={report} />
        </section>
        <section className="panel p-5">
          <SectionTitle title="Расходы по категориям" compact />
          <ExpenseSummaryTable expenses={report.expenses} />
        </section>
      </div>

      <section id="reminders" className="panel overflow-hidden">
        <SectionTitle title="Напоминатель обязательных платежей" />
        <ExpenseTable expenses={report.expenses} onEdit={onEdit} onPay={onPay} onUnpay={onUnpay} />
      </section>

      <section className="panel overflow-hidden">
        <button className="flex w-full items-center justify-between border-b border-slate-100 px-5 py-4 text-left font-bold text-ink" onClick={onToggleTeachers}>
          <span>Детализация выплат преподавателям</span>
          {expandedTeachers ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </button>
        {expandedTeachers ? <TeacherDetails data={report.teacher_earnings} /> : <div className="px-5 py-4 text-sm text-slate-500">Выплаты преподавателям учтены в расходах как категория «Оплата преподавателям».</div>}
      </section>
    </>
  );
}

function ExpenseBars({ report }: { report: FinanceMonthlyReport }) {
  if (!report.chart.length || Number(report.expenses_total) === 0) {
    return <EmptyText text="Расходов за выбранный месяц пока нет." />;
  }
  return (
    <div className="mt-4 space-y-3">
      {report.chart.map((item) => (
        <div key={item.category_id}>
          <div className="mb-1 flex items-center justify-between gap-3 text-sm">
            <span className="truncate font-semibold text-ink" title={item.category_name}>{item.category_name}</span>
            <span className="shrink-0 text-slate-500">{toCurrency(item.amount)} · {Number(item.percentage).toFixed(1)}%</span>
          </div>
          <div className="h-2.5 overflow-hidden rounded bg-slate-100">
            <div className="h-full rounded bg-mint" style={{ width: `${Math.min(100, Number(item.percentage))}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function ExpenseSummaryTable({ expenses }: { expenses: MonthlyExpense[] }) {
  return (
    <div className="mt-4 max-h-72 overflow-auto">
      <table className="w-full">
        <thead>
          <tr>
            <th className="th">Категория</th>
            <th className="th">План</th>
            <th className="th">Факт</th>
          </tr>
        </thead>
        <tbody>
          {expenses.map((expense) => (
            <tr key={expense.id}>
              <td className="td">{expense.category_name}</td>
              <td className="td">{toCurrency(expense.planned_amount)}</td>
              <td className="td font-semibold text-ink">{expense.actual_amount ? toCurrency(expense.actual_amount) : toCurrency(expense.effective_amount)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ExpenseTable({ expenses, onEdit, onPay, onUnpay }: { expenses: MonthlyExpense[]; onEdit: (expense: MonthlyExpense) => void; onPay: (id: number) => void; onUnpay: (id: number) => void }) {
  return (
    <div className="max-h-[420px] overflow-auto">
      <table className="w-full">
        <thead className="sticky top-0 bg-slate-50">
          <tr>
            <th className="th">Расход</th>
            <th className="th">План</th>
            <th className="th">Факт</th>
            <th className="th">Срок</th>
            <th className="th">Статус</th>
            <th className="th">Оплачено</th>
            <th className="th">Действия</th>
          </tr>
        </thead>
        <tbody>
          {expenses.map((expense) => (
            <tr key={expense.id}>
              <td className="td">
                <div className="font-semibold text-ink">{expense.category_name}</div>
                {expense.comment ? <div className="text-xs text-slate-500">{expense.comment}</div> : null}
              </td>
              <td className="td">{toCurrency(expense.planned_amount)}</td>
              <td className="td">{expense.actual_amount ? toCurrency(expense.actual_amount) : <span className="text-slate-400">по плану: {toCurrency(expense.effective_amount)}</span>}</td>
              <td className="td">{expense.reminder_day} число</td>
              <td className="td"><StatusBadge status={expense.status} /></td>
              <td className="td">{expense.paid_at ? `${toDate(expense.paid_at)}${expense.paid_by_name ? ` · ${expense.paid_by_name}` : ""}` : "—"}</td>
              <td className="td">
                <div className="flex flex-wrap gap-2">
                  {!expense.is_teacher_expense ? (
                    <button className="btn-secondary h-9 px-3" onClick={() => onEdit(expense)} title="Редактировать"><Pencil size={16} /></button>
                  ) : null}
                  {expense.paid ? (
                    <button className="btn-secondary h-9 px-3" onClick={() => onUnpay(expense.id)}><RotateCcw size={16} /> Снять оплату</button>
                  ) : (
                    <button className="btn-primary h-9 px-3" onClick={() => onPay(expense.id)}><CheckCircle2 size={16} /> Оплачено</button>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TeacherDetails({ data }: { data: TeacherEarning[] }) {
  if (!data.length) {
    return <div className="p-5"><EmptyText text="Начислений преподавателям за выбранный месяц нет." /></div>;
  }
  return (
    <table className="w-full">
      <thead className="bg-slate-50">
        <tr>
          <th className="th">Преподаватель</th>
          <th className="th">Занятий</th>
          <th className="th">Начислено</th>
          <th className="th">Средняя выплата</th>
        </tr>
      </thead>
      <tbody>
        {data.map((item) => (
          <Fragment key={item.teacher_id}>
            <tr>
              <td className="td font-semibold text-ink">{item.teacher_name}</td>
              <td className="td">{item.visits_count}</td>
              <td className="td">{toCurrency(item.teacher_earned)}</td>
              <td className="td">{toCurrency(item.average_teacher_earning)}</td>
            </tr>
            {item.visits.slice(0, 5).map((visit) => (
              <tr key={visit.visit_id} className="bg-slate-50/60 text-sm">
                <td className="td pl-10">{toDate(visit.visit_date)} · {visit.participant_name}</td>
                <td className="td">{visit.is_cancelled ? "Возвращено" : "Проведено"}</td>
                <td className="td">{visit.is_cancelled ? "0 ₽" : toCurrency(visit.teacher_earning)}</td>
                <td className="td">{visit.membership_name}</td>
              </tr>
            ))}
          </Fragment>
        ))}
      </tbody>
    </table>
  );
}

function ExpenseEditor({ expense, pending, error, onClose, onSubmit }: { expense: MonthlyExpense; pending: boolean; error: string | null; onClose: () => void; onSubmit: (payload: { planned_amount?: string; actual_amount?: string | null; comment?: string | null }) => void }) {
  const [planned, setPlanned] = useState(expense.planned_amount);
  const [actual, setActual] = useState(expense.actual_amount ?? "");
  const [comment, setComment] = useState(expense.comment ?? "");
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/30 p-6" onClick={onClose}>
      <form className="w-full max-w-lg rounded-md bg-white p-5 shadow-2xl" onClick={(event) => event.stopPropagation()} onSubmit={(event) => { event.preventDefault(); onSubmit({ planned_amount: planned, actual_amount: actual || null, comment: comment || null }); }}>
        <div className="mb-4 text-lg font-bold text-ink">Редактировать расход</div>
        <div className="space-y-3">
          <label className="block text-sm font-medium text-slate-700">Расход<input className="input mt-1" value={expense.category_name} disabled /></label>
          <label className="block text-sm font-medium text-slate-700">План<input className="input mt-1" type="number" min="0" step="0.01" value={planned} onChange={(event) => setPlanned(event.target.value)} /></label>
          <label className="block text-sm font-medium text-slate-700">Факт<input className="input mt-1" type="number" min="0" step="0.01" value={actual} onChange={(event) => setActual(event.target.value)} placeholder="Если пусто, используется план" /></label>
          <label className="block text-sm font-medium text-slate-700">Комментарий<input className="input mt-1" value={comment} onChange={(event) => setComment(event.target.value)} /></label>
        </div>
        {error ? <div className="mt-3 rounded-md border border-red-100 bg-red-50 px-3 py-2 text-sm text-coral">{error}</div> : null}
        <div className="mt-5 flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose}>Отмена</button>
          <button className="btn-primary" disabled={pending}><Save size={16} /> Сохранить</button>
        </div>
      </form>
    </div>
  );
}

function StatusBadge({ status }: { status: MonthlyExpense["status"] }) {
  const labels = {
    paid: "Оплачено",
    pending: "Ожидает оплаты",
    due_today: "К оплате сегодня",
    overdue: "Просрочено",
  };
  const classes = {
    paid: "bg-emerald-50 text-emerald-700",
    pending: "bg-slate-100 text-slate-600",
    due_today: "bg-amber-50 text-amber-700",
    overdue: "bg-red-50 text-red-700",
  };
  return <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${classes[status]}`}>{labels[status]}</span>;
}

function SectionTitle({ title, compact = false }: { title: string; compact?: boolean }) {
  return <div className={compact ? "font-bold text-ink" : "border-b border-slate-100 px-5 py-4 font-bold text-ink"}>{title}</div>;
}

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="panel flex items-center justify-between border-red-100 bg-red-50 p-4 text-sm text-red-700">
      <span>Не удалось загрузить финансовый отчет.</span>
      <button className="btn-secondary h-9 bg-white" onClick={onRetry}>Повторить</button>
    </div>
  );
}

function LoadingState() {
  return <div className="panel p-8 text-sm text-slate-500">Загружаем финансовый отчет...</div>;
}

function EmptyText({ text }: { text: string }) {
  return <p className="text-sm text-slate-500">{text}</p>;
}

function startOfMonth(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function plural(value: number, one: string, few: string, many: string) {
  const mod10 = value % 10;
  const mod100 = value % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;
  return many;
}
