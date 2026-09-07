import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";
import { CheckCircle2, RotateCcw, WalletCards } from "lucide-react";

import { paymentObligationService } from "../../shared/api/paymentObligationService";
import { toCurrency, toDate } from "../../shared/api/client";
import { Modal } from "../../shared/ui/Modal";
import { StatCard } from "../../shared/ui/StatCard";
import type { PaymentObligation } from "../../shared/types/domain";

const monthFormatter = new Intl.DateTimeFormat("ru-RU", { month: "long", year: "numeric" });

export function PaymentObligationsPage() {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<PaymentObligation | null>(null);
  const [actualAmount, setActualAmount] = useState("");
  const queryKey = ["paymentObligations", "current"];
  const obligations = useQuery({ queryKey, queryFn: paymentObligationService.getCurrent });

  const currentMonth = useMemo(() => {
    if (!obligations.data) return "";
    return monthFormatter.format(new Date(obligations.data.year, obligations.data.month - 1, 1));
  }, [obligations.data]);

  const pay = useMutation({
    mutationFn: ({ obligation, actual_amount }: { obligation: PaymentObligation; actual_amount?: string }) =>
      paymentObligationService.pay(obligation.id, actual_amount ? { actual_amount } : {}),
    onSuccess: () => {
      setSelected(null);
      setActualAmount("");
      invalidatePaymentQueries(queryClient);
    },
  });

  const unpay = useMutation({
    mutationFn: paymentObligationService.unpay,
    onSuccess: () => invalidatePaymentQueries(queryClient),
  });

  function startPay(obligation: PaymentObligation) {
    if (!obligation.is_variable) {
      if (window.confirm(`Отметить платеж как оплаченный?\n\n${obligation.name}\n${toCurrency(obligation.display_amount)}`)) {
        pay.mutate({ obligation });
      }
      return;
    }
    setSelected(obligation);
    setActualAmount(obligation.actual_amount ?? obligation.display_amount);
  }

  function confirmVariablePay() {
    if (!selected) return;
    pay.mutate({ obligation: selected, actual_amount: actualAmount });
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-ink">Обязательные платежи</h1>
        <p className="mt-1 text-sm text-slate-500">Операционный список платежей текущего месяца без доступа к финансовой аналитике.</p>
      </div>

      {obligations.isError ? <ErrorState onRetry={() => obligations.refetch()} /> : null}
      {obligations.data ? (
        <>
          <div className="flex items-center justify-between rounded-md border border-slate-200 bg-white px-5 py-4">
            <div>
              <div className="text-xs font-semibold uppercase text-slate-500">Период</div>
              <div className="mt-1 text-lg font-bold capitalize text-ink">{currentMonth}</div>
            </div>
            <WalletCards className="text-mint" size={26} />
          </div>

          <div className="grid grid-cols-4 gap-4">
            <StatCard label="К оплате" value={obligations.data.unpaid_count} hint="Ожидают отметки" />
            <StatCard label="Просрочено" value={obligations.data.overdue_count} hint="Срок уже прошел" />
            <StatCard label="Сегодня" value={obligations.data.due_today_count} hint="Срок оплаты сегодня" />
            <StatCard label="Оплачено" value={obligations.data.paid_count} hint="Закрыто за месяц" />
          </div>

          <section className="panel overflow-hidden">
            <div className="border-b border-slate-100 px-5 py-4 font-bold text-ink">Список обязательных платежей</div>
            {obligations.data.items.length ? (
              <div className="divide-y divide-slate-100">
                {obligations.data.items.map((item) => (
                  <div key={item.id} className="grid grid-cols-[minmax(260px,1fr)_160px_170px_180px_220px] items-center gap-4 px-5 py-4">
                    <div>
                      <div className="font-semibold text-ink">{item.name}</div>
                      <div className="mt-1 text-xs text-slate-500">
                        {item.is_variable ? `План: ${toCurrency(item.planned_amount)}` : "Фиксированный платеж"}
                        {item.comment ? ` · ${item.comment}` : ""}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs font-semibold uppercase text-slate-500">Сумма</div>
                      <div className="mt-1 font-bold text-ink">{toCurrency(item.display_amount)}</div>
                    </div>
                    <div>
                      <div className="text-xs font-semibold uppercase text-slate-500">Срок</div>
                      <div className="mt-1 text-sm text-slate-700">до {toDate(item.due_date)}</div>
                    </div>
                    <StatusBadge status={item.status} />
                    <div className="flex justify-end gap-2">
                      {item.paid ? (
                        <button className="btn-secondary h-9 px-3" onClick={() => unpay.mutate(item.id)} disabled={unpay.isPending}>
                          <RotateCcw size={16} /> Снять оплату
                        </button>
                      ) : (
                        <button className="btn-primary h-9 px-3" onClick={() => startPay(item)} disabled={pay.isPending}>
                          <CheckCircle2 size={16} /> Отметить оплачено
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 text-sm text-slate-500">Обязательных платежей за текущий месяц нет.</div>
            )}
          </section>
        </>
      ) : null}
      {obligations.isLoading ? <div className="panel p-8 text-sm text-slate-500">Загружаем обязательные платежи...</div> : null}

      <Modal title={selected ? selected.name : "Оплата"} open={Boolean(selected)} onClose={() => setSelected(null)}>
        {selected ? (
          <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); confirmVariablePay(); }}>
            <div className="rounded-md border border-slate-100 bg-slate-50 px-4 py-3">
              <div className="text-xs font-semibold uppercase text-slate-500">План</div>
              <div className="mt-1 text-lg font-bold text-ink">{toCurrency(selected.planned_amount)}</div>
            </div>
            <label className="block text-sm font-medium text-slate-700">
              Фактическая сумма
              <input className="input mt-1" type="number" min="0.01" step="0.01" value={actualAmount} onChange={(event) => setActualAmount(event.target.value)} required />
            </label>
            {pay.error instanceof Error ? <div className="rounded-md border border-red-100 bg-red-50 px-3 py-2 text-sm text-coral">{pay.error.message}</div> : null}
            <div className="flex justify-end gap-2">
              <button type="button" className="btn-secondary" onClick={() => setSelected(null)}>Отмена</button>
              <button className="btn-primary" disabled={pay.isPending}>Подтвердить оплату</button>
            </div>
          </form>
        ) : null}
      </Modal>
    </div>
  );
}

function invalidatePaymentQueries(queryClient: QueryClient) {
  queryClient.invalidateQueries({ queryKey: ["paymentObligations"] });
  queryClient.invalidateQueries({ queryKey: ["notifications", "summary"] });
  queryClient.invalidateQueries({ queryKey: ["finance-monthly-report"] });
  queryClient.invalidateQueries({ queryKey: ["finance-summary"] });
  queryClient.invalidateQueries({ queryKey: ["finance-reminders"] });
}

function StatusBadge({ status }: { status: PaymentObligation["status"] }) {
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
  return <span className={`w-fit rounded-full px-2.5 py-1 text-xs font-semibold ${classes[status]}`}>{labels[status]}</span>;
}

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="panel flex items-center justify-between border-red-100 bg-red-50 p-4 text-sm text-red-700">
      <span>Не удалось загрузить обязательные платежи.</span>
      <button className="btn-secondary h-9 bg-white" onClick={onRetry}>Повторить</button>
    </div>
  );
}
