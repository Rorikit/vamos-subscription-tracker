from datetime import date
from decimal import Decimal
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import ExpenseCategory, Membership, MembershipStatus, MembershipType, MonthlyExpense, Operator, OperatorRole, Participant, Teacher, Visit
from app.services.finance import TEACHER_EXPENSE_CATEGORY_NAME, get_monthly_report, get_reminder_status, mark_expense_paid
from app.services.lesson_finance import calculate_visit_financials
from app.services.auth import hash_password
from app.services.notifications import get_notification_summary
from app.services.payment_obligations import list_current_payment_obligations, mark_payment_obligation_paid


class FinanceExpensesTest(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)
        self.db = self.Session()
        self.operator = Operator(username="admin", full_name="Admin", role=OperatorRole.ADMIN, password_hash=hash_password("Strong_123"))
        self.work_operator = Operator(username="operator", full_name="Operator", role=OperatorRole.OPERATOR, password_hash=hash_password("Strong_123"))
        teacher = Teacher(full_name="Teacher")
        participant = Participant(full_name="Student")
        membership_type = MembershipType(name="10 lessons", lesson_count=10, price=Decimal("10000"), validity_days=30)
        self.db.add_all([self.operator, self.work_operator, teacher, participant, membership_type])
        self.db.commit()
        membership = Membership(
            participant_id=participant.id,
            membership_type_id=membership_type.id,
            total_lessons=10,
            remaining_lessons=9,
            price=Decimal("10000"),
            teacher_lesson_rate=Decimal("400"),
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
            status=MembershipStatus.ACTIVE,
        )
        self.db.add(membership)
        self.db.commit()
        financials = calculate_visit_financials(membership)
        self.db.add(
            Visit(
                participant_id=participant.id,
                membership_id=membership.id,
                teacher_id=teacher.id,
                visit_date=date(2026, 8, 12),
                lesson_price=financials["lesson_price"],
                teacher_lesson_rate=financials["teacher_lesson_rate"],
                teacher_earning=financials["teacher_earning"],
                school_earning=financials["school_earning"],
            )
        )
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()

    def test_monthly_report_includes_expenses_teacher_expense_and_net_result(self) -> None:
        report = get_monthly_report(self.db, 2026, 8)
        teacher_expense = next(item for item in report["expenses"] if item["category_name"] == TEACHER_EXPENSE_CATEGORY_NAME)

        self.assertEqual(report["income_total"], Decimal("10000.00"))
        self.assertEqual(teacher_expense["effective_amount"], Decimal("400.00"))
        self.assertIn(teacher_expense["category_id"], [item["category_id"] for item in report["chart"]])
        self.assertEqual(report["net_result"], report["income_total"] - report["expenses_total"])

    def test_new_month_has_new_unpaid_rows_without_changing_previous_month(self) -> None:
        august = get_monthly_report(self.db, 2026, 8)
        expense = next(item for item in august["expenses"] if item["category_name"] == "Егорова")
        mark_expense_paid(self.db, expense["id"], self.operator)

        september = get_monthly_report(self.db, 2026, 9)
        august_again = get_monthly_report(self.db, 2026, 8)
        august_expense = next(item for item in august_again["expenses"] if item["category_name"] == "Егорова")
        september_expense = next(item for item in september["expenses"] if item["category_name"] == "Егорова")

        self.assertTrue(august_expense["paid"])
        self.assertFalse(september_expense["paid"])

    def test_reminder_status_is_inactive_before_due_day_for_selected_month(self) -> None:
        status = get_reminder_status(self.db, 2026, 9)

        self.assertFalse(status["active"])
        self.assertEqual(status["unpaid_count"], 0)

    def test_operator_payment_obligations_use_monthly_expense_source_of_truth(self) -> None:
        today = date.today()
        category = ExpenseCategory(name="Тестовый платеж", default_amount=Decimal("1200"), is_variable=False, reminder_day=today.day)
        self.db.add(category)
        self.db.commit()
        self.db.add(MonthlyExpense(category_id=category.id, year=today.year, month=today.month, planned_amount=Decimal("1200")))
        self.db.commit()

        obligations = list_current_payment_obligations(self.db)
        obligation = next(item for item in obligations["items"] if item["name"] == "Тестовый платеж")
        paid = mark_payment_obligation_paid(self.db, obligation["id"], self.work_operator)

        self.assertTrue(paid.paid)
        self.assertEqual(paid.paid_by_user_id, self.work_operator.id)
        self.assertIsNotNone(paid.paid_at)
        with self.assertRaises(Exception):
            mark_payment_obligation_paid(self.db, obligation["id"], self.work_operator)

    def test_variable_payment_obligation_requires_actual_amount(self) -> None:
        today = date.today()
        category = ExpenseCategory(name="Переменный платеж", default_amount=Decimal("2000"), is_variable=True, reminder_day=today.day)
        self.db.add(category)
        self.db.commit()
        expense = MonthlyExpense(category_id=category.id, year=today.year, month=today.month, planned_amount=Decimal("2000"))
        self.db.add(expense)
        self.db.commit()

        with self.assertRaises(Exception):
            mark_payment_obligation_paid(self.db, expense.id, self.work_operator)

        paid = mark_payment_obligation_paid(self.db, expense.id, self.work_operator, Decimal("2500"))
        self.assertTrue(paid.paid)
        self.assertEqual(paid.actual_amount, Decimal("2500.00"))

    def test_global_notification_disappears_after_current_due_payments_are_paid(self) -> None:
        today = date.today()
        category = ExpenseCategory(name="Напоминание", default_amount=Decimal("1000"), is_variable=False, reminder_day=today.day)
        self.db.add(category)
        self.db.commit()
        expense = MonthlyExpense(category_id=category.id, year=today.year, month=today.month, planned_amount=Decimal("1000"))
        self.db.add(expense)
        self.db.commit()

        before = get_notification_summary(self.db, self.work_operator)
        mark_payment_obligation_paid(self.db, expense.id, self.work_operator)
        after = get_notification_summary(self.db, self.work_operator)

        self.assertEqual(before["items"][0]["action"], "/payment-obligations")
        self.assertEqual(after["items"], [])


if __name__ == "__main__":
    unittest.main()
