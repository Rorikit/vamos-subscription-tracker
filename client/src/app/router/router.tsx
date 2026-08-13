import { Navigate, createBrowserRouter } from "react-router-dom";

import { ProtectedRoute } from "../auth/ProtectedRoute";
import { RoleRoute } from "../auth/RoleRoute";
import { AppLayout } from "../layout/AppLayout";
import { DashboardPage } from "../../pages/dashboard/DashboardPage";
import { AuditLogsPage } from "../../pages/audit-logs/AuditLogsPage";
import { FinancePage } from "../../pages/finance/FinancePage";
import { LoginPage } from "../../pages/login/LoginPage";
import { MembershipsPage } from "../../pages/memberships/MembershipsPage";
import { ParticipantCardPage } from "../../pages/participant-card/ParticipantCardPage";
import { ParticipantsPage } from "../../pages/participants/ParticipantsPage";
import { SchedulePage } from "../../pages/schedule/SchedulePage";
import { SettingsPage } from "../../pages/settings/SettingsPage";

const basename = (import.meta.env.VITE_BASE_PATH ?? "/").replace(/\/$/, "") || "/";

export const router = createBrowserRouter(
  [
    { path: "/login", element: <LoginPage /> },
    {
      path: "/",
      element: (
        <ProtectedRoute>
          <AppLayout />
        </ProtectedRoute>
      ),
      children: [
        { index: true, element: <Navigate to="/dashboard" replace /> },
        { path: "dashboard", element: <RoleRoute roles={["admin", "operator", "finance"]}><DashboardPage /></RoleRoute> },
        { path: "schedule", element: <RoleRoute roles={["admin", "operator"]}><SchedulePage /></RoleRoute> },
        { path: "participants", element: <RoleRoute roles={["admin", "operator"]}><ParticipantsPage /></RoleRoute> },
        { path: "participants/:id", element: <RoleRoute roles={["admin", "operator"]}><ParticipantCardPage /></RoleRoute> },
        { path: "memberships", element: <RoleRoute roles={["admin", "operator"]}><MembershipsPage /></RoleRoute> },
        { path: "finance", element: <RoleRoute roles={["admin", "finance"]}><FinancePage /></RoleRoute> },
        { path: "audit-logs", element: <RoleRoute roles={["admin"]}><AuditLogsPage /></RoleRoute> },
        { path: "settings", element: <RoleRoute roles={["admin"]}><SettingsPage /></RoleRoute> },
      ],
    },
  ],
  { basename },
);
