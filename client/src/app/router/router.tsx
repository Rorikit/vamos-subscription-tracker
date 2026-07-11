import { Navigate, createBrowserRouter } from "react-router-dom";

import { ProtectedRoute } from "../auth/ProtectedRoute";
import { AppLayout } from "../layout/AppLayout";
import { DashboardPage } from "../../pages/dashboard/DashboardPage";
import { FinancePage } from "../../pages/finance/FinancePage";
import { LoginPage } from "../../pages/login/LoginPage";
import { MembershipsPage } from "../../pages/memberships/MembershipsPage";
import { ParticipantCardPage } from "../../pages/participant-card/ParticipantCardPage";
import { ParticipantsPage } from "../../pages/participants/ParticipantsPage";
import { SettingsPage } from "../../pages/settings/SettingsPage";

export const router = createBrowserRouter([
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
      { path: "dashboard", element: <DashboardPage /> },
      { path: "participants", element: <ParticipantsPage /> },
      { path: "participants/:id", element: <ParticipantCardPage /> },
      { path: "memberships", element: <MembershipsPage /> },
      { path: "finance", element: <FinancePage /> },
      { path: "settings", element: <SettingsPage /> },
    ],
  },
]);
