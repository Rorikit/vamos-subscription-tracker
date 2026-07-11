import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Plus, Ticket, UserPlus } from "lucide-react";

import { participantService } from "../../shared/api/participantService";
import { toDate } from "../../shared/api/client";
import { MembershipForm, ParticipantForm, WriteOffForm } from "../../shared/ui/Forms";
import { Modal } from "../../shared/ui/Modal";
import { StatusBadge } from "../../shared/ui/StatusBadge";
import { useDebouncedValue } from "../../shared/ui/useDebouncedValue";

export function ParticipantsPage() {
  const [modal, setModal] = useState<"participant" | "membership" | "visit" | null>(null);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);
  const { data, isLoading } = useQuery({
    queryKey: ["participants", debouncedSearch],
    queryFn: () => participantService.list(debouncedSearch),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Участники</h1>
          <p className="mt-1 text-sm text-slate-500">Карточки участников, активные абонементы и быстрые действия.</p>
        </div>
        <div className="flex gap-2">
          <button className="btn-secondary" onClick={() => setModal("membership")}><Ticket size={18} /> Создать абонемент</button>
          <button className="btn-secondary" onClick={() => setModal("visit")}><Plus size={18} /> Списать занятие</button>
          <button className="btn-primary" onClick={() => setModal("participant")}><UserPlus size={18} /> Создать участника</button>
        </div>
      </div>
      <section className="panel overflow-hidden">
        <div className="border-b border-slate-100 p-4">
          <input
            className="input max-w-md"
            placeholder="Поиск по ФИО или телефону"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <table className="w-full">
          <thead className="bg-slate-50">
            <tr><th className="th">ФИО</th><th className="th">Телефон</th><th className="th">Статус</th><th className="th">Остаток</th><th className="th">Дата окончания</th><th className="th">Действия</th></tr>
          </thead>
          <tbody>
            {isLoading ? <tr><td className="td" colSpan={6}>Загрузка...</td></tr> : null}
            {!isLoading && data?.length === 0 ? <tr><td className="td text-center text-slate-500" colSpan={6}>Участники не найдены</td></tr> : null}
            {data?.map((participant) => (
              <tr key={participant.id}>
                <td className="td font-semibold text-ink">{participant.full_name}</td>
                <td className="td">{participant.phone}</td>
                <td className="td"><StatusBadge status={participant.active_membership_status} /></td>
                <td className="td">{participant.remaining_lessons ?? "—"}</td>
                <td className="td">{toDate(participant.end_date)}</td>
                <td className="td">
                  <Link className="font-semibold text-mint hover:text-teal-700" to={`/participants/${participant.id}`}>Открыть карточку</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <Modal title="Создать участника" open={modal === "participant"} onClose={() => setModal(null)}>
        <ParticipantForm onDone={() => setModal(null)} />
      </Modal>
      <Modal title="Создать абонемент" open={modal === "membership"} onClose={() => setModal(null)}>
        <MembershipForm onDone={() => setModal(null)} />
      </Modal>
      <Modal title="Списать занятие" open={modal === "visit"} onClose={() => setModal(null)}>
        <WriteOffForm onDone={() => setModal(null)} />
      </Modal>
    </div>
  );
}

