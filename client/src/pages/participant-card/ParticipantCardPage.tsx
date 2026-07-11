import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { CreditCard, Pause, Play, Plus, Ticket, XCircle } from "lucide-react";

import { membershipService } from "../../shared/api/membershipService";
import { participantService } from "../../shared/api/participantService";
import { paymentService } from "../../shared/api/paymentService";
import { toCurrency, toDate } from "../../shared/api/client";
import { visitService } from "../../shared/api/visitService";
import { MembershipForm, PaymentForm, WriteOffForm } from "../../shared/ui/Forms";
import { Modal } from "../../shared/ui/Modal";
import { StatCard } from "../../shared/ui/StatCard";
import { StatusBadge } from "../../shared/ui/StatusBadge";

export function ParticipantCardPage() {
  const id = Number(useParams().id);
  const queryClient = useQueryClient();
  const [modal, setModal] = useState<"visit" | "payment" | "membership" | null>(null);
  const participant = useQuery({ queryKey: ["participant", id], queryFn: () => participantService.get(id) });
  const memberships = useQuery({ queryKey: ["memberships"], queryFn: () => membershipService.list("all") });
  const visits = useQuery({ queryKey: ["visits", id], queryFn: () => visitService.byParticipant(id) });
  const payments = useQuery({ queryKey: ["payments", id], queryFn: () => paymentService.byParticipant(id) });
  const participantMemberships = memberships.data?.filter((membership) => membership.participant_id === id) ?? [];
  const current = participantMemberships.find((membership) => membership.is_currently_active) ?? participantMemberships[0];
  const statusMutation = useMutation({
    mutationFn: ({ action, membershipId }: { action: "freeze" | "unfreeze" | "cancel"; membershipId: number }) =>
      action === "freeze" ? membershipService.freeze(membershipId) : action === "unfreeze" ? membershipService.unfreeze(membershipId) : membershipService.cancel(membershipId),
    onSuccess: () => queryClient.invalidateQueries(),
  });
  const cancelVisit = useMutation({ mutationFn: visitService.cancel, onSuccess: () => queryClient.invalidateQueries() });
  const cancelPayment = useMutation({ mutationFn: paymentService.cancel, onSuccess: () => queryClient.invalidateQueries() });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">{participant.data?.full_name ?? "Карточка участника"}</h1>
          <p className="mt-1 text-sm text-slate-500">{participant.data?.phone} {participant.data?.comment ? ` / ${participant.data.comment}` : ""}</p>
        </div>
        <div className="flex gap-2">
          <button className="btn-secondary" onClick={() => setModal("membership")}><Ticket size={18} /> Создать абонемент</button>
          <button className="btn-secondary" onClick={() => setModal("payment")} disabled={!participantMemberships.length}><CreditCard size={18} /> Добавить оплату</button>
          <button className="btn-primary" onClick={() => setModal("visit")}><Plus size={18} /> Списать занятие</button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Текущий статус" value={<StatusBadge status={current?.status} />} />
        <StatCard label="Остаток занятий" value={current ? `${current.remaining_lessons} / ${current.total_lessons}` : "—"} />
        <StatCard label="Дата окончания" value={current ? toDate(current.end_date) : "—"} />
        <StatCard label="Стоимость" value={current ? toCurrency(current.price) : "—"} />
      </div>

      {current ? (
        <section className="panel p-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-bold text-ink">Текущий активный абонемент</h2>
              <p className="mt-1 text-sm text-slate-500">{current.membership_type?.name}, {toDate(current.start_date)} - {toDate(current.end_date)}</p>
            </div>
            <div className="flex gap-2">
              {current.status === "frozen" ? (
                <button className="btn-secondary" onClick={() => statusMutation.mutate({ action: "unfreeze", membershipId: current.id })}><Play size={18} /> Разморозить</button>
              ) : (
                <button className="btn-secondary" onClick={() => statusMutation.mutate({ action: "freeze", membershipId: current.id })}><Pause size={18} /> Заморозить</button>
              )}
              <button className="btn-danger" onClick={() => statusMutation.mutate({ action: "cancel", membershipId: current.id })}><XCircle size={18} /> Отменить абонемент</button>
            </div>
          </div>
        </section>
      ) : null}

      <div className="grid grid-cols-2 gap-6">
        <section className="panel overflow-hidden">
          <SectionTitle title="История абонементов" />
          <table className="w-full">
            <thead><tr><th className="th">Тип</th><th className="th">Период</th><th className="th">Остаток</th><th className="th">Статус</th></tr></thead>
            <tbody>
              {participantMemberships.map((membership) => (
                <tr key={membership.id}>
                  <td className="td">{membership.membership_type?.name}</td>
                  <td className="td">{toDate(membership.start_date)} - {toDate(membership.end_date)}</td>
                  <td className="td">{membership.remaining_lessons}</td>
                  <td className="td"><StatusBadge status={membership.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
        <section className="panel overflow-hidden">
          <SectionTitle title="История посещений" />
          <table className="w-full">
            <thead><tr><th className="th">Дата</th><th className="th">Участник</th><th className="th">Абонемент</th><th className="th">Преподаватель</th><th className="th">Статус</th><th className="th"></th></tr></thead>
            <tbody>
              {visits.data?.map((visit) => (
                <tr key={visit.id}>
                  <td className="td">{toDate(visit.visit_date)}</td>
                  <td className="td">{participant.data?.full_name}</td>
                  <td className="td">{visit.membership_type?.name ?? "—"}</td>
                  <td className="td">{visit.teacher?.full_name ?? "—"}</td>
                  <td className="td">{visit.is_cancelled ? "Возвращено" : "Активно"}</td>
                  <td className="td">
                    {!visit.is_cancelled ? (
                      <button
                        className="font-semibold text-coral"
                        onClick={() => {
                          if (window.confirm("Вы уверены, что хотите вернуть занятие?")) {
                            cancelVisit.mutate(visit.id);
                          }
                        }}
                      >
                        Вернуть занятие
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
      <section className="panel overflow-hidden">
        <SectionTitle title="История оплат" />
        <table className="w-full">
          <thead><tr><th className="th">Дата</th><th className="th">Сумма</th><th className="th">Способ</th><th className="th">Комментарий</th><th className="th"></th></tr></thead>
          <tbody>
            {payments.data?.map((payment) => (
              <tr key={payment.id}>
                <td className="td">{toDate(payment.payment_date)}</td>
                <td className="td">{toCurrency(payment.amount)}</td>
                <td className="td">{payment.payment_method}</td>
                <td className="td">{payment.comment ?? "—"}</td>
                <td className="td">{!payment.is_cancelled ? <button className="font-semibold text-coral" onClick={() => cancelPayment.mutate(payment.id)}>Отменить</button> : "Отменена"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <Modal title="Списать занятие" open={modal === "visit"} onClose={() => setModal(null)}>
        <WriteOffForm participantId={id} onDone={() => setModal(null)} />
      </Modal>
      <Modal title="Добавить оплату" open={modal === "payment"} onClose={() => setModal(null)}>
        <PaymentForm participantId={id} memberships={participantMemberships} onDone={() => setModal(null)} />
      </Modal>
      <Modal title="Создать абонемент" open={modal === "membership"} onClose={() => setModal(null)}>
        <MembershipForm participantId={id} onDone={() => setModal(null)} />
      </Modal>
    </div>
  );
}

function SectionTitle({ title }: { title: string }) {
  return <div className="border-b border-slate-100 px-5 py-4 font-bold text-ink">{title}</div>;
}
