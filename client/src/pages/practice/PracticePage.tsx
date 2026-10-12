import { FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, RotateCcw, Trash2 } from "lucide-react";

import { useAuth } from "../../app/auth/AuthProvider";
import { toCurrency, toDate } from "../../shared/api/client";
import { practiceService, type PracticeFilters } from "../../shared/api/practiceService";
import { invalidatePracticeData } from "./receiptQueries";
import { WaterForm, WaterHistory } from "./WaterReceipts";
import { waterService } from "../../shared/api/waterService";
import { teacherService } from "../../shared/api/teacherService";
import { Modal } from "../../shared/ui/Modal";
import { StatCard } from "../../shared/ui/StatCard";
import type { PaymentMethod, PracticeRental } from "../../shared/types/domain";

const today = toDateTimeLocal(new Date()).slice(0, 10);

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
  const [page, setPage] = useState(1);
  const [receiptType, setReceiptType] = useState<"practice" | "water">("practice");
  const [formType, setFormType] = useState<"practice" | "water">("practice");

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search), 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  useEffect(() => setPage(1), [dateFrom, dateTo, debouncedSearch, tariffId, status, receiptType]);

  const filters = useMemo<PracticeFilters>(
    () => ({ date_from: dateFrom, date_to: dateTo, search: debouncedSearch, tariff_id: tariffId, status, page, page_size: 100 }),
    [dateFrom, dateTo, debouncedSearch, tariffId, status, page],
  );
  const rentals = useQuery({ queryKey: ["practice-rentals", filters], queryFn: () => practiceService.rentals(filters) });
  const summary = useQuery({ queryKey: ["practice-summary", dateFrom, dateTo], queryFn: () => practiceService.summary({ date_from: dateFrom, date_to: dateTo }) });
  const tariffs = useQuery({ queryKey: ["practice-tariffs"], queryFn: () => practiceService.tariffs() });

  const waterSummary = useQuery({ queryKey: ["water-summary", dateFrom, dateTo], queryFn: () => waterService.summary(dateFrom, dateTo) });
  function openForm() { setFormType(receiptType); setModalOpen(true); }

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
          <h1 className="text-2xl font-bold text-ink">Поступления</h1>
          <p className="mt-1 text-sm text-slate-500">Практики и вода: история поступлений и способы оплаты.</p>
        </div>
        {canMutate ? (
          <button className="btn-primary" onClick={openForm}>
            <Plus size={18} /> Добавить поступление
          </button>
        ) : null}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Всего поступлений" value={summary.isError || waterSummary.isError ? "—" : toCurrency(Number(summary.data?.income_total ?? 0) + Number(waterSummary.data?.income_total ?? 0))} hint="Практики и вода за период" />
        <StatCard label="Практики" value={summary.isError ? "—" : toCurrency(summary.data?.income_total ?? 0)} hint={`${summary.data?.rentals_count ?? 0} аренд`} />
        <StatCard label="Вода" value={waterSummary.isError ? "—" : toCurrency(waterSummary.data?.income_total ?? 0)} hint={`Записей: ${waterSummary.data?.receipts_count ?? 0}`} />
        <StatCard label="Средний чек практики" value={summary.isError ? "—" : toCurrency(summary.data?.average_check ?? 0)} hint="Только аренды зала" />
      </div>
      {summary.isError || waterSummary.isError ? <ErrorState onRetry={() => { summary.refetch(); waterSummary.refetch(); }} /> : null}
      <div className="flex gap-2" aria-label="Тип поступления">
        <button className={receiptType === "practice" ? "btn-primary" : "btn-secondary"} aria-pressed={receiptType === "practice"} onClick={() => setReceiptType("practice")}>Практики</button>
        <button className={receiptType === "water" ? "btn-primary" : "btn-secondary"} aria-pressed={receiptType === "water"} onClick={() => setReceiptType("water")}>Вода</button>
      </div>

      <section className="panel p-4">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-[160px_160px_minmax(220px,1fr)_220px_180px]">
          <Field label="Период с" type="date" value={dateFrom} onChange={setDateFrom} />
          <Field label="Период по" type="date" value={dateTo} onChange={setDateTo} />
          <Field label={receiptType === "practice" ? "Поиск арендатора" : "Поиск"} value={search} onChange={setSearch} placeholder={receiptType === "practice" ? "ФИО или имя" : "Вода или комментарий"} />
          <label className="block text-sm font-medium text-slate-700">
            Тариф
            <select disabled={receiptType === "water"} className="input mt-1 disabled:opacity-40" value={tariffId} onChange={(event) => setTariffId(event.target.value)}>
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

      {receiptType === "water" ? <WaterHistory filters={filters} canMutate={canMutate} canDelete={canDelete} /> : <section className="panel overflow-hidden">
        <div className="border-b border-slate-100 px-5 py-4 font-bold text-ink">История практик</div>
        {rentals.isError ? <ErrorState onRetry={() => rentals.refetch()} /> : null}
        {rentals.isLoading ? <div className="p-5 text-sm text-slate-500">Загружаем практики...</div> : null}
        {rentals.data && rentals.data.length === 0 ? (
          <div className="p-8 text-sm text-slate-500">
            За выбранный период практик нет.
            {canMutate ? <button className="ml-3 font-semibold text-mint" onClick={openForm}>Добавить практику</button> : null}
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
                  <th className="th">Способ оплаты</th>
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
                    <td className="td">{rental.payment_method === "card" ? "Картой" : "Наличными"}</td>
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
        <div className="flex items-center justify-between border-t border-slate-100 p-4 text-sm">
          <button className="btn-secondary" disabled={page === 1 || rentals.isFetching} onClick={() => setPage(page - 1)}>Назад</button>
          <span>Страница {page}</span>
          <button className="btn-secondary" disabled={rentals.isFetching || rentals.isError || (rentals.data?.length ?? 0) < 100} onClick={() => setPage(page + 1)}>Далее</button>
        </div>
      </section>}

      <Modal title="Добавить поступление" open={modalOpen} onClose={() => setModalOpen(false)}>
        <div className="mb-5 grid grid-cols-2 gap-2 rounded-md bg-slate-100 p-1" aria-label="Тип нового поступления">
          <button className={formType === "practice" ? "btn-primary" : "btn-secondary"} aria-pressed={formType === "practice"} onClick={() => setFormType("practice")}>Практика</button>
          <button className={formType === "water" ? "btn-primary" : "btn-secondary"} aria-pressed={formType === "water"} onClick={() => setFormType("water")}>Вода</button>
        </div>
        {formType === "practice" ? <PracticeForm onDone={() => { setReceiptType("practice"); setModalOpen(false); }} /> : <WaterForm onDone={() => { setReceiptType("water"); setModalOpen(false); }} /> }
      </Modal>
    </div>
  );
}


function PracticeForm({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient();
  const teachers = useQuery({ queryKey: ["teachers"], queryFn: teacherService.list });
  const tariffs = useQuery({ queryKey: ["practice-tariffs", "active"], queryFn: () => practiceService.tariffs(true) });
  const [mode, setMode] = useState<"teacher" | "manual">("teacher");
  const [teacherId, setTeacherId] = useState("");
  const [customerName, setCustomerName] = useState("");
  const [tariffId, setTariffId] = useState("");
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod | "">("");
  const [practicedAt, setPracticedAt] = useState(() => toDateTimeLocal(new Date()));
  const [comment, setComment] = useState("");
  const selectedTariff = tariffs.data?.find((tariff) => String(tariff.id) === tariffId);
  const selectedTeacher = teachers.data?.find((teacher) => String(teacher.id) === teacherId);
  const selectedAmount = paymentMethod === "card" ? selectedTariff?.card_price : paymentMethod === "cash" ? selectedTariff?.cash_price : null;
  const canSubmit = Boolean(tariffId && paymentMethod && practicedAt && (mode === "teacher" ? teacherId : customerName.trim()));
  const createRental = useMutation({
    mutationFn: () =>
      practiceService.create({
        registered_teacher_id: mode === "teacher" ? Number(teacherId) : null,
        customer_name: mode === "teacher" ? selectedTeacher?.full_name ?? "" : customerName.trim(),
        tariff_id: Number(tariffId),
        payment_method: paymentMethod as PaymentMethod,
        practiced_at: new Date(practicedAt).toISOString(),
        comment: comment.trim() || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["water-receipts"] });
  queryClient.invalidateQueries({ queryKey: ["water-summary"] });
  queryClient.invalidateQueries({ queryKey: ["dashboard"] });
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
              <div className="mt-1 text-xs">Наличными {toCurrency(tariff.cash_price)} · Картой {toCurrency(tariff.card_price)}</div>
            </button>
          ))}
        </div>
      </div>
      <div>
        <div className="mb-2 text-sm font-medium text-slate-700">Способ оплаты</div>
        <div className="grid grid-cols-2 gap-2">
          <button type="button" className={`rounded-md border px-4 py-3 text-left ${paymentMethod === "cash" ? "border-mint bg-teal-50 text-ink" : "border-slate-200 bg-white text-slate-600"}`} onClick={() => setPaymentMethod("cash")} disabled={!selectedTariff}>
            <div className="font-semibold">Наличными</div><div className="text-sm">{selectedTariff ? toCurrency(selectedTariff.cash_price) : "—"}</div>
          </button>
          <button type="button" className={`rounded-md border px-4 py-3 text-left ${paymentMethod === "card" ? "border-mint bg-teal-50 text-ink" : "border-slate-200 bg-white text-slate-600"}`} onClick={() => setPaymentMethod("card")} disabled={!selectedTariff}>
            <div className="font-semibold">Картой</div><div className="text-sm">{selectedTariff ? toCurrency(selectedTariff.card_price) : "—"}</div>
          </button>
        </div>
      </div>
      <Field label="Дата и время" type="datetime-local" value={practicedAt} onChange={setPracticedAt} required />
      <label className="block text-sm font-medium text-slate-700">
        Комментарий
        <textarea className="textarea mt-1" value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Необязательно" />
      </label>
      <div className="rounded-md bg-slate-50 px-4 py-3 text-sm">
        <span className="text-slate-500">К оплате: </span>
        <span className="font-bold text-ink">{selectedAmount ? toCurrency(selectedAmount) : selectedTariff ? "выберите способ оплаты" : "выберите тариф"}</span>
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
      <span>Не удалось загрузить поступления.</span>
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
