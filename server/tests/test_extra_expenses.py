from datetime import date, datetime
from decimal import Decimal
import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import ExpenseCategory, ExtraExpense, MonthlyExpense, Operator, OperatorRole
from app.schemas.extra_expense import ExtraExpenseCreate
from app.services.auth import hash_password
from app.services.extra_expenses import (
    cancel_extra_expense,
    create_extra_expense,
    delete_extra_expense,
    get_extra_expense_summary,
    list_extra_expenses,
    update_extra_expense,
)
from app.services.finance import get_monthly_report


class ExtraExpenseTest(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)
        self.db = self.Session()
        self.operator = Operator(
            username="admin",
            full_name="Администратор",
            role=OperatorRole.ADMIN,
            password_hash=hash_password("Admin_123"),
        )
        self.category = ExpenseCategory(name="Регулярный расход", default_amount=Decimal("200000"), is_active=True, sort_order=10)
        self.db.add_all([self.operator, self.category])
        self.db.commit()
        self.monthly_expense = MonthlyExpense(
            category_id=self.category.id,
            year=2026,
            month=8,
            planned_amount=Decimal("200000"),
        )
        self.db.add(self.monthly_expense)
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()

    def test_create_amount_validation_and_empty_title(self) -> None:
        expense = self._create("Ремонт кондиционера", Decimal("12000"), date(2026, 8, 14))

        self.assertEqual(expense.title, "Ремонт кондиционера")
        self.assertEqual(expense.amount, Decimal("12000.00"))
        self.assertEqual(expense.created_by_user_id, self.operator.id)

        with self.assertRaises(ValueError):
            ExtraExpenseCreate(title=" ", amount=Decimal("100"), expense_date=date(2026, 8, 14))
        with self.assertRaises(ValueError):
            ExtraExpenseCreate(title="Лампы", amount=Decimal("0"), expense_date=date(2026, 8, 14))

    def test_update_changes_finance_and_moves_between_months(self) -> None:
        expense = self._create("Лампы", Decimal("3500"), date(2026, 8, 12))
        august = get_monthly_report(self.db, 2026, 8)
        september = get_monthly_report(self.db, 2026, 9)
        self.assertEqual(august["extra_expenses_total"], Decimal("3500.00"))
        self.assertEqual(september["extra_expenses_total"], Decimal("0.00"))

        update_extra_expense(self.db, expense.id, {"amount": Decimal("8000"), "expense_date": date(2026, 9, 1)})

        august = get_monthly_report(self.db, 2026, 8)
        september = get_monthly_report(self.db, 2026, 9)
        self.assertEqual(august["extra_expenses_total"], Decimal("0.00"))
        self.assertEqual(september["extra_expenses_total"], Decimal("8000.00"))

    def test_cancelled_does_not_enter_summary_or_finance(self) -> None:
        expense = self._create("Замена замка", Decimal("8000"), date(2026, 8, 14))
        self.assertEqual(get_extra_expense_summary(self.db, date(2026, 8, 1), date(2026, 8, 31))["expenses_total"], Decimal("8000.00"))

        cancel_extra_expense(self.db, expense.id, self.operator)

        self.assertEqual(get_extra_expense_summary(self.db, date(2026, 8, 1), date(2026, 8, 31))["expenses_total"], Decimal("0.00"))
        self.assertEqual(get_monthly_report(self.db, 2026, 8)["extra_expenses_total"], Decimal("0.00"))
        with self.assertRaises(HTTPException):
            cancel_extra_expense(self.db, expense.id, self.operator)
        with self.assertRaises(HTTPException):
            update_extra_expense(self.db, expense.id, {"amount": Decimal("1000")})

    def test_delete_removes_expense_from_history_and_finance(self) -> None:
        expense = self._create("Замена замка", Decimal("8000"), date(2026, 8, 14))
        self.assertEqual(get_monthly_report(self.db, 2026, 8)["extra_expenses_total"], Decimal("8000.00"))

        delete_extra_expense(self.db, expense.id)

        self.assertEqual(list_extra_expenses(self.db), [])
        self.assertEqual(get_monthly_report(self.db, 2026, 8)["extra_expenses_total"], Decimal("0.00"))
        with self.assertRaises(HTTPException):
            delete_extra_expense(self.db, expense.id)

    def test_search_and_created_at_does_not_affect_period(self) -> None:
        expense = self._create("Мелкий ремонт", Decimal("5700"), date(2026, 8, 14))
        expense.created_at = datetime(2026, 9, 1, 12, 0)
        self.db.add(expense)
        self.db.commit()

        self.assertEqual(len(list_extra_expenses(self.db, search="ремонт")), 1)
        self.assertEqual(get_monthly_report(self.db, 2026, 8)["extra_expenses_total"], Decimal("5700.00"))
        self.assertEqual(get_monthly_report(self.db, 2026, 9)["extra_expenses_total"], Decimal("0.00"))

    def test_finance_formula_includes_extra_expense(self) -> None:
        self._create("Печать рекламы", Decimal("20000"), date(2026, 8, 14))
        report = get_monthly_report(self.db, 2026, 8)
        expected_regular = sum((Decimal(item["effective_amount"]) for item in report["expenses"] if not item["is_teacher_expense"]), Decimal("0"))

        self.assertEqual(report["regular_expenses_total"], expected_regular)
        self.assertEqual(report["teacher_expense_total"], Decimal("0.00"))
        self.assertEqual(report["extra_expenses_total"], Decimal("20000.00"))
        self.assertEqual(report["expenses_total"], expected_regular + Decimal("20000.00"))
        self.assertEqual(report["net_result"], -report["expenses_total"])

    def _create(self, title: str, amount: Decimal, expense_date: date) -> ExtraExpense:
        return create_extra_expense(
            self.db,
            ExtraExpenseCreate(title=title, amount=amount, expense_date=expense_date),
            self.operator,
        )


if __name__ == "__main__":
    unittest.main()
