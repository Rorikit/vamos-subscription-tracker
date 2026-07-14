import { Fragment, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, RefreshCw } from "lucide-react";

import { auditLogService } from "../../shared/api/auditLogService";
import { operatorService } from "../../shared/api/operatorService";
import type { AuditLog } from "../../shared/types/domain";

export function AuditLogsPage() {
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [operatorId, setOperatorId] = useState("");
  const [action, setAction] = useState("");
  const [entityType, setEntityType] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const filters = { date_from: dateFrom, date_to: dateTo, operator_id: operatorId, action, entity_type: entityType };
  const logs = useQuery({ queryKey: ["audit-logs", filters], queryFn: () => auditLogService.list(filters) });
  const operators = useQuery({ queryKey: ["operators"], queryFn: operatorService.list });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">Журнал действий</h1>
        <p className="mt-1 text-sm text-slate-500">Кто, когда и что изменил в системе.</p>
      </div>

      <section className="panel p-5">
        <div className="grid grid-cols-[1fr_1fr_1fr_1fr_1fr_auto] items-end gap-4">
          <Field label="Период с" value={dateFrom} onChange={setDateFrom} type="date" />
          <Field label="Период по" value={dateTo} onChange={setDateTo} type="date" />
          <label className="block text-sm font-medium text-slate-700">
            Оператор
            <select className="input mt-1" value={operatorId} onChange={(event) => setOperatorId(event.target.value)}>
              <option value="">Все</option>
              {operators.data?.map((operator) => (
                <option key={operator.id} value={operator.id}>{operator.full_name}</option>
              ))}
            </select>
          </label>
          <Field label="Действие" value={action} onChange={setAction} />
          <Field label="Объект" value={entityType} onChange={setEntityType} />
          <button className="btn-secondary" onClick={() => { setDateFrom(""); setDateTo(""); setOperatorId(""); setAction(""); setEntityType(""); }}>
            <RefreshCw size={17} />
            Сбросить
          </button>
        </div>
      </section>

      <section className="panel overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-50">
            <tr>
              <th className="th">Дата</th>
              <th className="th">Оператор</th>
              <th className="th">Действие</th>
              <th className="th">Объект</th>
              <th className="th">Описание</th>
              <th className="th">Детали</th>
            </tr>
          </thead>
          <tbody>
            {logs.data?.map((log) => {
              const expanded = expandedId === log.id;
              return (
                <Fragment key={log.id}>
                  <tr>
                    <td className="td">{new Intl.DateTimeFormat("ru-RU", { dateStyle: "short", timeStyle: "short" }).format(new Date(log.created_at))}</td>
                    <td className="td">{log.operator_name ?? "Система"}</td>
                    <td className="td">{actionLabel(log.action)}</td>
                    <td className="td">{entityLabel(log.entity_type)}</td>
                    <td className="td">{log.entity_label ?? "—"}</td>
                    <td className="td">
                      <button className="btn-secondary h-9" onClick={() => setExpandedId(expanded ? null : log.id)}>
                        {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                        Открыть
                      </button>
                    </td>
                  </tr>
                  {expanded ? (
                    <tr>
                      <td className="td bg-slate-50" colSpan={6}>
                        <AuditDetails log={log} />
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              );
            })}
          </tbody>
        </table>
        {!logs.isLoading && logs.data?.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-500">События не найдены</div>
        ) : null}
      </section>
    </div>
  );
}

function AuditDetails({ log }: { log: AuditLog }) {
  return (
    <div className="grid grid-cols-2 gap-4 text-sm">
      <JsonBlock title="До" value={log.before_json} />
      <JsonBlock title="После" value={log.after_json} />
    </div>
  );
}

function JsonBlock({ title, value }: { title: string; value: string | null }) {
  return (
    <div>
      <div className="mb-2 font-semibold text-ink">{title}</div>
      <pre className="max-h-72 overflow-auto rounded-md bg-white p-3 text-xs text-slate-700">{formatJson(value)}</pre>
    </div>
  );
}

function Field({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (value: string) => void; type?: string }) {
  return (
    <label className="block text-sm font-medium text-slate-700">
      {label}
      <input className="input mt-1" type={type} value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function formatJson(value: string | null) {
  if (!value) return "—";
  try {
    return JSON.stringify(JSON.parse(value), null, 2);
  } catch {
    return value;
  }
}

function actionLabel(action: string) {
  const labels: Record<string, string> = {
    operator_login: "Вход",
    participant_created: "Создание участника",
    participant_updated: "Редактирование участника",
    membership_created: "Создание абонемента",
    membership_frozen: "Заморозка абонемента",
    membership_unfrozen: "Разморозка абонемента",
    membership_cancelled: "Отмена абонемента",
    visit_written_off: "Списание занятия",
    visit_returned: "Возврат занятия",
    payment_created: "Добавление оплаты",
    payment_cancelled: "Отмена оплаты",
    teacher_created: "Создание преподавателя",
    teacher_updated: "Редактирование преподавателя",
    membership_type_created: "Создание типа абонемента",
    membership_type_updated: "Редактирование типа абонемента",
    operator_created: "Создание пользователя",
    operator_updated: "Редактирование пользователя",
  };
  return labels[action] ?? action;
}

function entityLabel(entity: string) {
  const labels: Record<string, string> = {
    operator: "Пользователь",
    participant: "Участник",
    membership: "Абонемент",
    visit: "Занятие",
    payment: "Оплата",
    teacher: "Преподаватель",
    membership_type: "Тип абонемента",
  };
  return labels[entity] ?? entity;
}
