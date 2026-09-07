import { api } from "./client";
import type { NotificationSummary } from "../types/domain";

export const notificationService = {
  summary: () => api<NotificationSummary>("/notifications/summary"),
};
