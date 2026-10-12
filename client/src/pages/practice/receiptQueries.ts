import type { QueryClient } from "@tanstack/react-query";

export function invalidatePracticeData(queryClient: QueryClient) {
  queryClient.invalidateQueries({ queryKey: ["water-receipts"] });
  queryClient.invalidateQueries({ queryKey: ["water-summary"] });
  queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  queryClient.invalidateQueries({ queryKey: ["practice-rentals"] });
  queryClient.invalidateQueries({ queryKey: ["practice-summary"] });
  queryClient.invalidateQueries({ queryKey: ["finance-monthly-report"] });
  queryClient.invalidateQueries({ queryKey: ["finance-summary"] });
}
