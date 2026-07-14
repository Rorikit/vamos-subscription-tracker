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
  start_date: string;
  end_date: string;
  status: MembershipStatus;
  is_currently_active: boolean;
  paid_amount: string;
  participant?: { id: number; full_name: string; phone?: string | null } | null;
  membership_type?: { id: number; name: string } | null;
};

export type Teacher = {
  id: number;
  full_name: string;
  phone: string | null;
  comment: string | null;
  teacher_share_percent: string;
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
  teacher_share_percent: string | null;
  teacher_earning: string | null;
  school_earning: string | null;
  is_cancelled: boolean;
  participant?: { id: number; full_name: string } | null;
  teacher?: { id: number; full_name: string } | null;
  membership_type?: { id: number; name: string } | null;
};

export type Payment = {
  id: number;
  participant_id: number;
  membership_id: number;
  amount: string;
  payment_date: string;
  payment_method: string;
  comment: string | null;
  is_cancelled: boolean;
  participant?: { id: number; full_name: string } | null;
};

export type FinanceSummary = {
  memberships_sold_total: string;
  payments_received_total: string;
  completed_lessons_value: string;
  teacher_earnings_total: string;
  school_earnings_total: string;
  completed_visits_count: number;
  average_lesson_price: string;
  average_teacher_earning: string;
  active_teachers_count: number;
};

export type TeacherEarningVisit = {
  visit_id: number;
  visit_date: string;
  participant_id: number;
  participant_name: string;
  membership_id: number;
  membership_name: string;
  lesson_price: string;
  teacher_share_percent: string;
  teacher_earning: string;
  school_earning: string;
  is_cancelled: boolean;
};

export type TeacherEarning = {
  teacher_id: number;
  teacher_name: string;
  teacher_share_percent: string;
  visits_count: number;
  completed_lessons_value: string;
  teacher_earned: string;
  school_earned: string;
  average_lesson_price: string;
  average_teacher_earning: string;
  share_of_total_teacher_payouts: string;
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
