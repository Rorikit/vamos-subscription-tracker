export type MembershipStatus = "active" | "finished" | "expired" | "frozen" | "cancelled";

export type Participant = {
  id: number;
  full_name: string;
  phone: string | null;
  comment: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type ParticipantListItem = Participant & {
  active_membership_id: number | null;
  active_membership_status: string | null;
  remaining_lessons: number | null;
  end_date: string | null;
};

export type MembershipType = {
  id: number;
  name: string;
  lesson_count: number;
  price: string;
  validity_days: number;
  description: string | null;
  is_active: boolean;
};

export type Membership = {
  id: number;
  participant_id: number;
  membership_type_id: number;
  total_lessons: number;
  remaining_lessons: number;
  price: string;
  teacher_lesson_rate: string;
  start_date: string;
  end_date: string;
  status: MembershipStatus;
  is_currently_active: boolean;
  participant?: { id: number; full_name: string; phone?: string | null } | null;
  membership_type?: { id: number; name: string } | null;
};

export type Teacher = {
  id: number;
  full_name: string;
  phone: string | null;
  comment: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type Visit = {
  id: number;
  participant_id: number;
  membership_id: number;
  teacher_id: number;
  visit_date: string;
  lesson_price: string | null;
  teacher_lesson_rate: string | null;
  teacher_earning: string | null;
  school_earning: string | null;
  is_cancelled: boolean;
  participant?: { id: number; full_name: string } | null;
  teacher?: { id: number; full_name: string } | null;
  membership_type?: { id: number; name: string } | null;
};

export type FinanceSummary = {
  memberships_sold_total: string;
  practice_income: string;
  income_total: string;
  completed_lessons_value: string;
  teacher_earnings_total: string;
  school_earnings_total: string;
  completed_visits_count: number;
  average_lesson_price: string;
  average_teacher_earning: string;
  active_teachers_count: number;
};

export type MonthlyExpense = {
  id: number;
  category_id: number;
  category_name: string;
  year: number;
  month: number;
  planned_amount: string;
  actual_amount: string | null;
  effective_amount: string;
  paid: boolean;
  paid_at: string | null;
  paid_by_user_id: number | null;
  paid_by_name: string | null;
  comment: string | null;
  is_variable: boolean;
  reminder_day: number;
  status: "paid" | "pending" | "due_today" | "overdue";
  is_teacher_expense: boolean;
};

export type ExpenseChartItem = {
  category_id: number;
  category_name: string;
  amount: string;
  percentage: string;
  is_teacher_expense: boolean;
};

export type FinanceMonthlyReport = {
  year: number;
  month: number;
  date_from: string;
  date_to: string;
  income_total: string;
  memberships_sold_total: string;
  practice_income: string;
  expenses_total: string;
  teacher_expense_total: string;
  net_result: string;
  unpaid_expenses_count: number;
  unpaid_expenses_total: string;
  completed_visits_count: number;
  chart: ExpenseChartItem[];
  expenses: MonthlyExpense[];
  teacher_earnings: TeacherEarning[];
};

export type ReminderStatus = {
  year: number;
  month: number;
  active: boolean;
  unpaid_count: number;
  unpaid_total: string;
};

export type TeacherEarningVisit = {
  visit_id: number;
  visit_date: string;
  participant_id: number;
  participant_name: string;
  membership_id: number;
  membership_name: string;
  lesson_price: string;
  teacher_lesson_rate: string;
  teacher_earning: string;
  school_earning: string;
  is_cancelled: boolean;
};

export type TeacherEarning = {
  teacher_id: number;
  teacher_name: string;
  average_teacher_lesson_rate: string;
  visits_count: number;
  completed_lessons_value: string;
  teacher_earned: string;
  school_earned: string;
  average_lesson_price: string;
  average_teacher_earning: string;
  last_visit_date: string | null;
  visits: TeacherEarningVisit[];
};

export type AuditLog = {
  id: number;
  operator_id: number | null;
  operator_name: string | null;
  action: string;
  entity_type: string;
  entity_id: number | null;
  entity_label: string | null;
  before_json: string | null;
  after_json: string | null;
  created_at: string;
};

export type ScheduleEventStatus = "scheduled" | "completed" | "cancelled";
export type ScheduleEventType = "group" | "individual" | "course" | "other";
export type AttendanceStatus = "planned" | "attended" | "absent" | "cancelled" | "refunded";

export type ScheduleEventParticipant = {
  id: number;
  schedule_event_id: number;
  participant_id: number;
  attendance_status: AttendanceStatus;
  visit_id: number | null;
  participant?: { id: number; full_name: string; phone?: string | null } | null;
  visit?: Visit | null;
  created_at: string;
  updated_at: string;
};

export type ScheduleEvent = {
  id: number;
  title: string;
  description: string | null;
  teacher_id: number;
  starts_at: string;
  ends_at: string;
  status: ScheduleEventStatus;
  event_type: ScheduleEventType;
  location: string | null;
  color: string | null;
  recurrence_group_id: string | null;
  recurrence_rule: string | null;
  cancelled_at: string | null;
  completed_at: string | null;
  teacher?: { id: number; full_name: string } | null;
  participants: ScheduleEventParticipant[];
  created_at: string;
  updated_at: string;
};

export type ScheduleConflict = {
  event_id: number;
  title: string;
  teacher_name: string | null;
  starts_at: string;
  ends_at: string;
};

export type PracticeRentalStatus = "active" | "cancelled";

export type PracticeTariff = {
  id: number;
  name: string;
  price: string;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
};

export type PracticeRental = {
  id: number;
  registered_teacher_id: number | null;
  customer_name: string;
  tariff_id: number | null;
  tariff_name_snapshot: string;
  amount: string;
  practiced_at: string;
  status: PracticeRentalStatus;
  comment: string | null;
  created_by_user_id: number;
  created_by_name: string | null;
  cancelled_at: string | null;
  cancelled_by_user_id: number | null;
  created_at: string;
  updated_at: string;
};

export type PracticeRentalSummary = {
  income_total: string;
  rentals_count: number;
  average_check: string;
};
