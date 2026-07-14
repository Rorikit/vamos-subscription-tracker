import { api } from "./client";
import type { AuditLog } from "../types/domain";

export const auditLogService = {
  list: (params: { date_from?: string; date_to?: string; operator_id?: string; action?: string; entity_type?: string; entity_id?: string } = {}) => {
    const search = new URLSearchParams();
    if (params.date_from) search.set("date_from", params.date_from);
    if (params.date_to) search.set("date_to", params.date_to);
    if (params.operator_id) search.set("operator_id", params.operator_id);
    if (params.action) search.set("action", params.action);
    if (params.entity_type) search.set("entity_type", params.entity_type);
    if (params.entity_id) search.set("entity_id", params.entity_id);
    return api<AuditLog[]>(`/audit-logs${search.toString() ? `?${search}` : ""}`);
  },
};
