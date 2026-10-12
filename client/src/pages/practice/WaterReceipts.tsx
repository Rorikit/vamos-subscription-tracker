import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { waterService, type WaterReceipt } from "../../shared/api/waterService";
import type { PracticeFilters } from "../../shared/api/practiceService";
import type { PaymentMethod } from "../../shared/types/domain";
import { toCurrency, toDate } from "../../shared/api/client";
import { invalidatePracticeData } from "./receiptQueries";

function localDate() { const now = new Date(); return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10); }

export function WaterForm({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient();
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState(localDate);
  const [method, setMethod] = useState<PaymentMethod | "">("");
  const [comment, setComment] = useState("");
  const [requestId] = useState(() => crypto.randomUUID());
  const valid = /^\d+(?:[.,]\d{1,2})?$/.test(amount) && Number(amount.replace(",", ".")) > 0 && Number(amount.replace(",", ".")) < 100000000 && Boolean(date && method);
  const create = useMutation({ mutationFn: () => waterService.create({ amount: amount.replace(",", "."), received_on: date, payment_method: method as PaymentMethod, comment: comment.trim() || null, request_id: requestId }), onSuccess: () => { invalidatePracticeData(queryClient); onDone(); } });
  function submit(event: FormEvent) { event.preventDefault(); if (valid && !create.isPending) create.mutate(); }
  return <form className="space-y-4" onSubmit={submit}>
    <div className="text-lg font-semibold text-ink">Вода</div>
    <div className="grid gap-4 sm:grid-cols-2">
      <label className="text-sm font-medium text-slate-700">Сумма, ₽<input className="input mt-1" inputMode="decimal" autoFocus value={amount} onChange={e => setAmount(e.target.value)} placeholder="Например: 150" required /></label>
      <label className="text-sm font-medium text-slate-700">Дата<input className="input mt-1" type="date" value={date} onChange={e => setDate(e.target.value)} required /></label>
    </div>
    <fieldset><legend className="mb-2 text-sm font-medium text-slate-700">Способ оплаты</legend><div className="grid grid-cols-2 gap-2">
      {(["cash", "card"] as const).map(m => <button key={m} type="button" aria-pressed={method === m} className={`rounded-md border px-4 py-3 text-left font-semibold ${method === m ? "border-mint bg-teal-50 text-ink" : "border-slate-200 text-slate-600"}`} onClick={() => setMethod(m)}>{m === "cash" ? "Наличными" : "Картой"}</button>)}
    </div></fieldset>
    <label className="block text-sm font-medium text-slate-700">Комментарий<textarea className="textarea mt-1" maxLength={2000} value={comment} onChange={e => setComment(e.target.value)} placeholder="Необязательно" /></label>
    {create.error ? <p role="alert" className="text-sm text-coral">{create.error.message}</p> : null}
    <button className="btn-primary w-full" disabled={!valid || create.isPending}>{create.isPending ? "Сохраняем..." : "Сохранить поступление"}</button>
  </form>;
}

export function WaterHistory({ filters, canMutate, canDelete }: { filters: PracticeFilters; canMutate: boolean; canDelete: boolean }) {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  useEffect(() => setPage(1), [filters.date_from, filters.date_to, filters.search, filters.status]);
  const query = useQuery({ queryKey: ["water-receipts", filters, page], queryFn: () => waterService.list({ ...filters, page }) });
  const cancel = useMutation({ mutationFn: waterService.cancel, onSuccess: () => invalidatePracticeData(qc) });
  const remove = useMutation({ mutationFn: waterService.delete, onSuccess: () => invalidatePracticeData(qc) });
  function action(row: WaterReceipt, deletion: boolean) { if (window.confirm(`${deletion ? "Удалить" : "Отменить"} поступление за воду на ${toCurrency(row.amount)}?`)) (deletion ? remove : cancel).mutate(row.id); }
  return <section className="panel overflow-hidden">
    <div className="border-b border-slate-100 px-5 py-4 font-bold text-ink">Поступления за воду</div>
    {query.isLoading ? <p className="p-5 text-sm text-slate-500">Загружаем поступления...</p> : null}
    {query.isError ? <div role="alert" className="p-5 text-coral">Не удалось загрузить воду. <button className="btn-secondary" onClick={() => query.refetch()}>Повторить</button></div> : null}
    {cancel.error || remove.error ? <p role="alert" className="p-5 text-coral">{(cancel.error || remove.error)?.message}</p> : null}
    {query.data?.length === 0 ? <p className="p-8 text-sm text-slate-500">За выбранный период поступлений за воду нет.</p> : null}
    {query.data && query.data.length > 0 ? <div className="overflow-auto"><table className="w-full min-w-[800px]"><thead className="bg-slate-50"><tr>{["Дата", "Позиция", "Сумма", "Способ оплаты", "Статус", "Кто добавил", "Действия"].map(h => <th className="th" key={h}>{h}</th>)}</tr></thead><tbody>
      {query.data.map(row => <tr key={row.id} className={row.status === "cancelled" ? "bg-slate-50 opacity-60" : undefined}>
        <td className="td">{toDate(row.received_on)}</td><td className="td"><div className="font-semibold text-ink">Вода</div>{row.comment ? <div className="text-xs text-slate-500">{row.comment}</div> : null}</td>
        <td className="td font-semibold">{toCurrency(row.amount)}</td><td className="td">{row.payment_method === "cash" ? "Наличными" : "Картой"}</td><td className="td">{row.status === "active" ? "Активно" : "Отменено"}</td><td className="td">{row.created_by_name ?? "—"}</td>
        <td className="td"><div className="flex gap-2">{canMutate && row.status === "active" ? <button className="btn-secondary" disabled={cancel.isPending} onClick={() => action(row, false)}>Отменить</button> : null}{canDelete ? <button className="btn-danger" disabled={remove.isPending} onClick={() => action(row, true)}>Удалить</button> : null}</div></td>
      </tr>)}
    </tbody></table></div> : null}
    <div className="flex items-center justify-between border-t border-slate-100 p-4 text-sm">
      <button className="btn-secondary" disabled={page === 1 || query.isFetching} onClick={() => setPage(page - 1)}>Назад</button>
      <span>Страница {page}</span>
      <button className="btn-secondary" disabled={query.isFetching || query.isError || (query.data?.length ?? 0) < 100} onClick={() => setPage(page + 1)}>Далее</button>
    </div>
  </section>;
}
