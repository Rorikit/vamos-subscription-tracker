import { FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, RotateCcw, Trash2 } from "lucide-react";

import { useAuth } from "../../app/auth/AuthProvider";
import { toCurrency, toDate } from "../../shared/api/client";
import { practiceService, type PracticeFilters } from "../../shared/api/practiceService";
import { teacherService } from "../../shared/api/teacherService";
import { Modal } from "../../shared/ui/Modal";
import { StatCard } from "../../shared/ui/StatCard";
import type { PracticeRental } from "../../shared/types/domain";

const today = new Date().toISOString().slice(0, 10);

export function PracticePage() {
  const auth = useAuth();
  const queryClient = useQueryClient();
  const canMutate = auth.operator?.role === "admin" || auth.operator?.role === "operator";
  const canDelete = auth.operator?.role === "admin";
  const [dateFrom, setDateFrom] = useState(today.slice(0, 8) + "01");
  const [dateTo, setDateTo] = useState(today);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [tariffId, setTariffId] = useState("");
  const [status, setStatus] = useState<PracticeFilters["status"]>("");
  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search), 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  const filters = useMemo<PracticeFilters>(
    () => ({ date_from: dateFrom, date_to: dateTo, search: debouncedSearch, tariff_id: tariffId, status, page_size: 100 }),
    [dateFrom, dateTo, debouncedSearch, tariffId, status],
  );
  const rentals = useQuery({ queryKey: ["practice-rentals", filters], queryFn: () => practiceService.rentals(filters) });
  const summary = useQuery({ queryKey: ["practice-summary", dateFrom, dateTo], queryFn: () => practiceService.summary({ date_from: dateFrom, date_to: dateTo }) });
  const tariffs = useQuery({ queryKey: ["practice-tariffs"], queryFn: () => practiceService.tariffs() });

  const cancelRental = useMutation({
    mutationFn: practiceService.cancel,
    onSuccess: () => invalidatePracticeData(queryClient),
  });
  const deleteRental = useMutation({
    mutationFn: practiceService.delete,
    onSuccess: () => invalidatePracticeData(queryClient),
  });

  function handleCancel(rental: PracticeRental) {
    if (window.confirm(`Отменить практику ${rental.customer_name} на ${toCurrency(rental.amount)}?`)) {
      cancelRental.mutate(rental.id);
    }
  }

  function handleDelete(rental: PracticeRental) {
    if (window.confirm(`Удалить практику ${rental.customer_name} полностью? Запись исчезнет из истории.`)) {
      deleteRental.mutate(rental.id);
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-ink">Практика</h1>
          <p className="mt-1 text-sm text-slate-500">Учет аренды зала для самостоятельной практики и занятий внешних преподавателей.</p>
        </div>
        {canMutate ? (
          <button className="btn-primary" onClick={() => setModalOpen(true)}>
            <Plus size={18} /> Добавить практику
          </button>
        ) : null}
      </div>

      <div className="grid grid-cols-3 gap-4">
        <StatCard label="Доход от практики" value={toCurrency(summary.data?.income_total ?? 0)} hint="Только активные записи" />
        <StatCard label="Количество аренд" value={String(summary.data?.rentals_count ?? 0)} hint="За выбранный период" />
        <StatCard label="Средний чек" value={toCurrency(summary.data?.average_check ?? 0)} hint="Доход / количество аренд" />
      </div>

      <section className="panel p-4">
        <div className="grid grid-cols-[160px_160px_minmax(220px,1fr)_220px_180px] gap-3">
          <Field label="Период с" type="date" value={dateFrom} onChange={setDateFrom} />
          <Field label="Период по" type="date" value={dateTo} onChange={setDateTo} />
          <Field label="Поиск арендатора" value={search} onChange={setSearch} placeholder="ФИО или имя" />
          <label className="block text-sm font-medium text-slate-700">
            Тариф
            <select className="input mt-1" value={tariffId} onChange={(event) => setTariffId(event.target.value)}>
              <option value="">Все тарифы</option>
              {tariffs.data?.map((tariff) => (
                <option key={tariff.id} value={tariff.id}>{tariff.name}</option>
              ))}
            </select>
          </label>
          <label className="block text-sm font-medium text-slate-700">
            Статус
            <select className="input mt-1" value={status} onChange={(event) => setStatus(event.target.value as PracticeFilters["status"])}>
              <option value="">Все</option>
              <option value="active">Активно</option>
              <option value="cancelled">Отменено</option>
            </select>
          </label>
        </div>
      </section>

      <section className="panel overflow-hidden">
        <div className="border-b border-slate-100 px-5 py-4 font-bold text-ink">История практик</div>
        {rentals.isError ? <ErrorState onRetry={() => rentals.refetch()} /> : null}
        {rentals.isLoading ? <div className="p-5 text-sm text-slate-500">Загружаем практики...</div> : null}
        {rentals.data && rentals.data.length === 0 ? (
          <div className="p-8 text-sm text-slate-500">
            За выбранный период практик нет.
            {canMutate ? <button className="ml-3 font-semibold text-mint" onClick={() => setModalOpen(true)}>Добавить практику</button> : null}
          </div>
        ) : null}
        {rentals.data && rentals.data.length > 0 ? (
          <div className="overflow-auto">
            <table className="w-full min-w-[1080px]">
              <thead className="bg-slate-50">
                <tr>
                  <th className="th">Дата</th>
                  <th className="th">Время</th>
                  <th className="th">Арендатор</th>
                  <th className="th">Тариф</th>
                  <th className="th">Сумма</th>
                  <th className="th">Статус</th>
                  <th className="th">Кто добавил</th>
                  <th className="th">Действия</th>
                </tr>
              </thead>
              <tbody>
                {rentals.data.map((rental) => (
                  <tr key={rental.id} className={rental.status === "cancelled" ? "bg-slate-50 opacity-60" : undefined}>
                    <td className="td">{toDate(rental.practiced_at)}</td>
                    <td className="td">{new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", minute: "2-digit" }).format(new Date(rental.practiced_at))}</td>
                    <td className="td">
                      <div className="font-semibold text-ink">{rental.customer_name}</div>
                      {rental.comment ? <div className="text-xs text-slate-500">{rental.comment}</div> : null}
                    </td>
                    <td className="td">{rental.tariff_name_snapshot}</td>
                    <td className="td font-semibold text-ink">{toCurrency(rental.amount)}</td>
                    <td className="td"><PracticeStatus status={rental.status} /></td>
                    <td className="td">{rental.created_by_name ?? "—"}</td>
                    <td className="td">
                      {canMutate || canDelete ? (
                        <div className="flex flex-wrap gap-2">
                          {canMutate && rental.status === "active" ? (
                            <button className="btn-secondary h-9 px-3 text-coral" onClick={() => handleCancel(rental)} disabled={cancelRental.isPending}>
                              <RotateCcw size={16} /> Отменить
                            </button>
                          ) : null}
                          {canDelete ? (
                            <button className="btn-danger h-9 px-3" onClick={() => handleDelete(rental)} disabled={deleteRental.isPending}>
                              <Trash2 size={16} /> Удалить
                            </button>
                          ) : null}
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

      <Modal title="Добавить практику" open={modalOpen} onClose={() => setModalOpen(false)}>
        <PracticeForm onDone={() => setModalOpen(false)} />
      </Modal>
    </div>
  );
}

function invalidatePracticeData(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ["practice-rentals"] });
  queryClient.invalidateQueries({ queryKey: ["practice-summary"] });
  queryClient.invalidateQueries({ queryKey: ["finance-monthly-report"] });
  queryClient.invalidateQueries({ queryKey: ["finance-summary"] });
}

function PracticeForm({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient();
  const teachers = useQuery({ queryKey: ["teachers"], queryFn: teacherService.list });
  const tariffs = useQuery({ queryKey: ["practice-tariffs", "active"], queryFn: () => practiceService.tariffs(true) });
  const [mode, setMode] = useState<"teacher" | "manual">("teacher");
  const [teacherId, setTeacherId] = useState("");
  const [customerName, setCustomerName] = useState("");
  const [tariffId, setTariffId] = useState("");
  const [practicedAt, setPracticedAt] = useState(() => toDateTimeLocal(new Date()));
  const [comment, setComment] = useState("");
  const selectedTariff = tariffs.data?.find((tariff) => String(tariff.id) === tariffId);
  const selectedTeacher = teachers.data?.find((teacher) => String(teacher.id) === teacherId);
  const canSubmit = Boolean(tariffId && practicedAt && (mode === "teacher" ? teacherId : customerName.trim()));
  const createRental = useMutation({
    mutationFn: () =>
      practiceService.create({
        registered_teacher_id: mode === "teacher" ? Number(teacherId) : null,
        customer_name: mode === "teacher" ? selectedTeacher?.full_name ?? "" : customerName.trim(),
        tariff_id: Number(tariffId),
        practiced_at: new Date(practicedAt).toISOString(),
        comment: comment.trim() || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["practice-rentals"] });
      queryClient.invalidateQueries({ queryKey: ["practice-summary"] });
      queryClient.invalidateQueries({ queryKey: ["finance-monthly-report"] });
      queryClient.invalidateQueries({ queryKey: ["finance-summary"] });
      onDone();
    },
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (canSubmit) createRental.mutate();
  }

  return (
    <form className="space-y-4" onSubmit={submit}>
      <div className="grid grid-cols-2 gap-2 rounded-md bg-slate-100 p-1">
        <button type="button" className={`h-9 rounded text-sm font-semibold ${mode === "teacher" ? "bg-white text-ink shadow-sm" : "text-slate-500"}`} onClick={() => setMode("teacher")}>Выбрать преподавателя</button>
        <button type="button" className={`h-9 rounded text-sm font-semibold ${mode === "manual" ? "bg-white text-ink shadow-sm" : "text-slate-500"}`} onClick={() => setMode("manual")}>Указать вручную</button>
      </div>
      {mode === "teacher" ? (
        <label className="block text-sm font-medium text-slate-700">
          Арендатор
          <select className="input mt-1" value={teacherId} onChange={(event) => setTeacherId(event.target.value)} required>
            <option value="">Выберите преподавателя</option>
            {teachers.data?.filter((teacher) => teacher.is_active).map((teacher) => (
              <option key={teacher.id} value={teacher.id}>{teacher.full_name}</option>
            ))}
          </select>
        </label>
      ) : (
        <Field label="Арендатор" value={customerName} onChange={setCustomerName} placeholder="Например: Александр" required />
      )}
      <div>
        <div className="mb-2 text-sm font-medium text-slate-700">Тариф</div>
        <div className="grid grid-cols-2 gap-2">
          {tariffs.data?.map((tariff) => (
            <button key={tariff.id} type="button" className={`rounded-md border px-4 py-3 text-left transition ${tariffId === String(tariff.id) ? "border-mint bg-teal-50 text-ink" : "border-slate-200 bg-white text-slate-600"}`} onClick={() => setTariffId(String(tariff.id))}>
              <div className="font-semibold">{tariff.name}</div>
              <div className="text-sm">{toCurrency(tariff.price)}</div>
            </button>
          ))}
        </div>
      </div>
      <Field label="Дата и время" type="datetime-local" value={practicedAt} onChange={setPracticedAt} required />
      <label className="block text-sm font-medium text-slate-700">
        Комментарий
        <textarea className="textarea mt-1" value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Необязательно" />
      </label>
      <div className="rounded-md bg-slate-50 px-4 py-3 text-sm">
        <span className="text-slate-500">К оплате: </span>
        <span className="font-bold text-ink">{selectedTariff ? toCurrency(selectedTariff.price) : "выберите тариф"}</span>
      </div>
      {createRental.error ? <div className="rounded-md border border-red-100 bg-red-50 px-3 py-2 text-sm text-coral">{createRental.error.message}</div> : null}
      <button className="btn-primary w-full" disabled={!canSubmit || createRental.isPending}>
        {createRental.isPending ? "Сохраняем..." : "Сохранить практику"}
      </button>
    </form>
  );
}

function PracticeStatus({ status }: { status: PracticeRental["status"] }) {
  const isActive = status === "active";
  return <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${isActive ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>{isActive ? "Активно" : "Отменено"}</span>;
}

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="m-5 flex items-center justify-between rounded-md border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
      <span>Не удалось загрузить данные по практике.</span>
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

function toDateTimeLocal(date: Date) {
  const offset = date.getTimezoneOffset();
  return new Date(date.getTime() - offset * 60_000).toISOString().slice(0, 16);
}
