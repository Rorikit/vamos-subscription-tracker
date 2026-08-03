import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { membershipService } from "../../shared/api/membershipService";
import { toCurrency, toDate } from "../../shared/api/client";
import { MembershipStatus } from "../../shared/types/domain";
import { StatusBadge } from "../../shared/ui/StatusBadge";

const filters: Array<{ value: MembershipStatus | "all"; label: string }> = [
  { value: "all", label: "Все" },
  { value: "active", label: "Активные" },
  { value: "finished", label: "Законченные" },
  { value: "expired", label: "Просроченные" },
  { value: "frozen", label: "Замороженные" },
  { value: "cancelled", label: "Отмененные" },
];

export function MembershipsPage() {
  const [status, setStatus] = useState<MembershipStatus | "all">("all");
  const { data } = useQuery({ queryKey: ["memberships", status], queryFn: () => membershipService.list(status) });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">Абонементы</h1>
        <p className="mt-1 text-sm text-slate-500">Все выданные абонементы и их текущие состояния.</p>
      </div>
      <div className="flex gap-2">
        {filters.map((filter) => (
          <button key={filter.value} className={status === filter.value ? "btn-primary" : "btn-secondary"} onClick={() => setStatus(filter.value)}>
            {filter.label}
          </button>
        ))}
      </div>
      <section className="panel overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-50">
            <tr><th className="th">Участник</th><th className="th">Тип</th><th className="th">Период</th><th className="th">Остаток</th><th className="th">Цена</th><th className="th">Ставка преподавателя</th><th className="th">Статус</th></tr>
          </thead>
          <tbody>
            {data?.map((membership) => (
              <tr key={membership.id}>
                <td className="td font-semibold text-ink">{membership.participant?.full_name}</td>
                <td className="td">{membership.membership_type?.name}</td>
                <td className="td">{toDate(membership.start_date)} - {toDate(membership.end_date)}</td>
                <td className="td">{membership.remaining_lessons} / {membership.total_lessons}</td>
                <td className="td">{toCurrency(membership.price)}</td>
                <td className="td">{toCurrency(membership.teacher_lesson_rate)}</td>
                <td className="td"><StatusBadge status={membership.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
