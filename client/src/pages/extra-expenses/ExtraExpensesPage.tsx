import { FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Pencil, Plus, RotateCcw } from "lucide-react";

import { useAuth } from "../../app/auth/AuthProvider";
import { toCurrency, toDate } from "../../shared/api/client";
import { extraExpenseService, type ExtraExpenseFilters } from "../../shared/api/extraExpenseService";
import { Modal } from "../../shared/ui/Modal";
import { StatCard } from "../../shared/ui/StatCard";
import type { ExtraExpense } from "../../shared/types/domain";

const monthFormatter = new Intl.DateTimeFormat("ru-RU", { month: "long", year: "numeric" });

export function ExtraExpensesPage() {
  const auth = useAuth();
  const queryClient = useQueryClient();
  const canMutate = auth.operator?.role === "admin" || auth.operator?.role === "operator";
  const [monthDate, setMonthDate] = useState(() => startOfMonth(new Date()));
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [status, setStatus] = useState<ExtraExpenseFilters["status"]>("");
  const [editingExpense, setEditingExpense] = useState<ExtraExpense | "new" | null>(null);
  const dateFrom = toInputDate(startOfMonth(monthDate));
  const dateTo = toInputDate(endOfMonth(monthDate));
  const filters = useMemo<ExtraExpenseFilters>(
    () => ({ date_from: dateFrom, date_to: dateTo, search: debouncedSearch, status, page_size: 100 }),
    [dateFrom, dateTo, debouncedSearch, status],
  );

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search), 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  const expenses = useQuery({ queryKey: ["extra-expenses", filters], queryFn: () => extraExpenseService.list(filters) });
  const summary = useQuery({ queryKey: ["extra-expenses-summary", dateFrom, dateTo], queryFn: () => extraExpenseService.summary({ date_from: dateFrom, date_to: dateTo }) });
  const cancelExpense = useMutation({
    mutationFn: extraExpenseService.cancel,
    onSuccess: invalidateExtraExpenseData(queryClient),
  });

  function shiftMonth(step: number) {
    const next = new Date(monthDate);
    next.setMonth(next.getMonth() + step);
    setMonthDate(startOfMonth(next));
  }

  function handleCancel(expense: ExtraExpense) {
    if (window.confirm(`Отменить расход «${expense.title}» на ${toCurrency(expense.amount)}?`)) {
      cancelExpense.mutate(expense.id);
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-ink">Внештатные расходы</h1>
          <p className="mt-1 text-sm text-slate-500">Нерегулярные траты школы без фиксированных категорий и повторяемости.</p>
        </div>
        <div className="flex items-center gap-2">
          <button className="btn-secondary h-10 px-3" onClick={() => shiftMonth(-1)} title="Предыдущий месяц"><ChevronLeft size={18} /></button>
          <div className="input flex h-10 min-w-56 items-center justify-center font-semibold capitalize">{monthFormatter.format(monthDate)}</div>
          <button className="btn-secondary h-10 px-3" onClick={() => shiftMonth(1)} title="Следующий месяц"><ChevronRight size={18} /></button>
          {canMutate ? (
            <button className="btn-primary" onClick={() => setEditingExpense("new")}><Plus size={18} /> Добавить расход</button>
          ) : null}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <StatCard label="Внештатные расходы за месяц" value={toCurrency(summary.data?.expenses_total ?? 0)} hint="Только активные записи" />
        <StatCard label="Количество расходов" value={String(summary.data?.expenses_count ?? 0)} hint="За выбранный месяц" />
        <StatCard label="Средний расход" value={toCurrency(summary.data?.average_expense ?? 0)} hint="Сумма / количество" />
      </div>

      <section className="panel p-4">
        <div className="grid grid-cols-[minmax(260px,1fr)_180px] gap-3">
          <Field label="Поиск по названию" value={search} onChange={setSearch} placeholder="Например: ремонт" />
          <label className="block text-sm font-medium text-slate-700">
            Статус
            <select className="input mt-1" value={status} onChange={(event) => setStatus(event.target.value as ExtraExpenseFilters["status"])}>
              <option value="">Все</option>
              <option value="active">Активно</option>
              <option value="cancelled">Отменено</option>
            </select>
          </label>
        </div>
      </section>

      <section className="panel overflow-hidden">
        <div className="border-b border-slate-100 px-5 py-4 font-bold text-ink">История расходов</div>
        {expenses.isError ? <ErrorState onRetry={() => expenses.refetch()} /> : null}
        {expenses.isLoading ? <div className="p-5 text-sm text-slate-500">Загружаем расходы...</div> : null}
        {expenses.data && expenses.data.length === 0 ? (
          <div className="p-8 text-sm text-slate-500">
            За выбранный период внештатных расходов нет.
            {canMutate ? <button className="ml-3 font-semibold text-mint" onClick={() => setEditingExpense("new")}>Добавить расход</button> : null}
          </div>
        ) : null}
        {expenses.data && expenses.data.length > 0 ? (
          <div className="overflow-auto">
            <table className="w-full min-w-[980px]">
              <thead className="bg-slate-50">
                <tr>
                  <th className="th">Дата</th>
                  <th className="th">Название</th>
                  <th className="th">Сумма</th>
                  <th className="th">Комментарий</th>
                  <th className="th">Кто добавил</th>
                  <th className="th">Статус</th>
                  <th className="th">Действия</th>
                </tr>
              </thead>
              <tbody>
                {expenses.data.map((expense) => (
                  <tr key={expense.id} className={expense.status === "cancelled" ? "bg-slate-50 opacity-60" : undefined}>
                    <td className="td">{toDate(expense.expense_date)}</td>
                    <td className="td font-semibold text-ink">{expense.title}</td>
                    <td className="td font-semibold text-ink">{toCurrency(expense.amount)}</td>
                    <td className="td">{expense.comment ?? "—"}</td>
                    <td className="td">{expense.created_by_name ?? "—"}</td>
                    <td className="td"><StatusBadge status={expense.status} /></td>
                    <td className="td">
                      {canMutate && expense.status === "active" ? (
                        <div className="flex flex-wrap gap-2">
                          <button className="btn-secondary h-9 px-3" onClick={() => setEditingExpense(expense)}><Pencil size={16} /> Редактировать</button>
                          <button className="btn-secondary h-9 px-3 text-coral" onClick={() => handleCancel(expense)} disabled={cancelExpense.isPending}><RotateCcw size={16} /> Отменить</button>
                        </div>
                      ) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <Modal
        title={editingExpense === "new" ? "Добавить расход" : "Редактировать расход"}
        open={editingExpense !== null}
        onClose={() => setEditingExpense(null)}
      >
        <ExtraExpenseForm expense={editingExpense && editingExpense !== "new" ? editingExpense : undefined} onDone={() => setEditingExpense(null)} />
      </Modal>
    </div>
  );
}

function ExtraExpenseForm({ expense, onDone }: { expense?: ExtraExpense; onDone: () => void }) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(expense?.title ?? "");
  const [amount, setAmount] = useState(expense?.amount ?? "");
  const [expenseDate, setExpenseDate] = useState(expense?.expense_date ?? toInputDate(new Date()));
  const [comment, setComment] = useState(expense?.comment ?? "");
  const mutation = useMutation({
    mutationFn: () => {
      const payload = { title, amount, expense_date: expenseDate, comment: comment.trim() || null };
      return expense ? extraExpenseService.update(expense.id, payload) : extraExpenseService.create(payload);
    },
    onSuccess: () => {
      invalidateExtraExpenseData(queryClient)();
      onDone();
    },
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    mutation.mutate();
  }

  return (
    <form className="space-y-4" onSubmit={submit}>
      <Field label="Название" value={title} onChange={setTitle} placeholder="Ремонт кондиционера" required />
      <Field label="Стоимость" value={amount} onChange={setAmount} type="number" placeholder="12000" required />
      <Field label="Дата расхода" value={expenseDate} onChange={setExpenseDate} type="date" required />
      <label className="block text-sm font-medium text-slate-700">
        Комментарий
        <textarea className="textarea mt-1" value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Необязательно" />
      </label>
      {mutation.error ? <div className="rounded-md border border-red-100 bg-red-50 px-3 py-2 text-sm text-coral">{mutation.error.message}</div> : null}
      <button className="btn-primary w-full" disabled={mutation.isPending || !title.trim() || !amount || !expenseDate}>
        {mutation.isPending ? "Сохраняем..." : expense ? "Сохранить расход" : "Добавить расход"}
      </button>
    </form>
  );
}

function invalidateExtraExpenseData(queryClient: ReturnType<typeof useQueryClient>) {
  return () => {
    queryClient.invalidateQueries({ queryKey: ["extra-expenses"] });
    queryClient.invalidateQueries({ queryKey: ["extra-expenses-summary"] });
    queryClient.invalidateQueries({ queryKey: ["finance-monthly-report"] });
    queryClient.invalidateQueries({ queryKey: ["finance-summary"] });
  };
}

function StatusBadge({ status }: { status: ExtraExpense["status"] }) {
  const isActive = status === "active";
  return <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${isActive ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>{isActive ? "Активно" : "Отменено"}</span>;
}

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="m-5 flex items-center justify-between rounded-md border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
      <span>Не удалось загрузить внештатные расходы.</span>
      <button className="btn-secondary h-9 bg-white" onClick={onRetry}>Повторить</button>
    </div>
  );
}

function Field({ label, value, onChange, type = "text", placeholder, required = false }: { label: string; value: string; onChange: (value: string) => void; type?: string; placeholder?: string; required?: boolean }) {
  return (
    <label className="block text-sm font-medium text-slate-700">
      {label}
      <input className="input mt-1" value={value} type={type} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} required={required} />
    </label>
  );
}

function startOfMonth(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function endOfMonth(date: Date) {
  return new Date(date.getFullYear(), date.getMonth() + 1, 0);
}

function toInputDate(date: Date) {
  const offset = date.getTimezoneOffset();
  return new Date(date.getTime() - offset * 60_000).toISOString().slice(0, 10);
}
