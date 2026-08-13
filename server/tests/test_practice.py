from datetime import date, datetime, timedelta
from decimal import Decimal
import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Membership, MembershipStatus, MembershipType, Operator, OperatorRole, Participant, PracticeTariff, ScheduleEvent, Teacher, Visit
from app.schemas.practice import PracticeRentalCreate
from app.services.auth import hash_password
from app.services.finance import get_summary, get_teacher_earnings
from app.services.practice import cancel_practice_rental, create_practice_rental, ensure_practice_tariffs, get_practice_summary, list_practice_rentals, update_practice_tariff


class PracticeRentalTest(unittest.TestCase):
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
        self.teacher = Teacher(full_name="Анна Практика", phone="+7 900 100-10-10")
        self.participant = Participant(full_name="Ученик")
        membership_type = MembershipType(name="8 занятий", lesson_count=8, price=Decimal("8000"), validity_days=30)
        self.db.add_all([self.operator, self.teacher, self.participant, membership_type])
        self.db.commit()

        self.membership = Membership(
            participant_id=self.participant.id,
            membership_type_id=membership_type.id,
            total_lessons=8,
            remaining_lessons=8,
            price=Decimal("8000"),
            teacher_lesson_rate=Decimal("400"),
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status=MembershipStatus.ACTIVE,
        )
        self.db.add(self.membership)
        self.db.commit()
        self.tariffs = ensure_practice_tariffs(self.db)

    def tearDown(self) -> None:
        self.db.close()

    def test_create_with_registered_teacher_saves_snapshot_and_amount(self) -> None:
        rental = self._create(self.tariffs[0].id, registered_teacher_id=self.teacher.id, customer_name="Будет заменено")

        self.assertEqual(rental.customer_name, "Анна Практика")
        self.assertEqual(rental.amount, Decimal("300.00"))
        self.assertEqual(rental.tariff_name_snapshot, "Практика — 300 ₽")

    def test_create_without_teacher_uses_manual_name_and_500_tariff(self) -> None:
        rental = self._create(self.tariffs[1].id, customer_name="Александр")

        self.assertIsNone(rental.registered_teacher_id)
        self.assertEqual(rental.customer_name, "Александр")
        self.assertEqual(rental.amount, Decimal("500.00"))

    def test_tariff_update_does_not_change_old_rental_snapshot(self) -> None:
        rental = self._create(self.tariffs[0].id, customer_name="Александр")
        update_practice_tariff(self.db, self.tariffs[0].id, {"price": Decimal("350"), "name": "Практика — 350 ₽"})
        self.db.refresh(rental)

        self.assertEqual(rental.amount, Decimal("300.00"))
        self.assertEqual(rental.tariff_name_snapshot, "Практика — 300 ₽")

    def test_inactive_tariff_cannot_be_used(self) -> None:
        update_practice_tariff(self.db, self.tariffs[0].id, {"is_active": False})

        with self.assertRaises(HTTPException):
            self._create(self.tariffs[0].id, customer_name="Александр")

    def test_cancel_excludes_from_practice_and_finance_summary(self) -> None:
        rental = self._create(self.tariffs[1].id, customer_name="Александр")
        self.assertEqual(get_practice_summary(self.db)["income_total"], Decimal("500.00"))
        self.assertEqual(get_summary(self.db)["practice_income"], Decimal("500.00"))
        self.assertEqual(get_summary(self.db)["income_total"], Decimal("8500.00"))

        cancel_practice_rental(self.db, rental.id, self.operator)

        self.assertEqual(get_practice_summary(self.db)["income_total"], Decimal("0.00"))
        self.assertEqual(get_summary(self.db)["practice_income"], Decimal("0.00"))
        self.assertEqual(get_summary(self.db)["income_total"], Decimal("8000.00"))
        with self.assertRaises(HTTPException):
            cancel_practice_rental(self.db, rental.id, self.operator)

    def test_practice_does_not_create_schedule_visit_membership_or_teacher_earnings(self) -> None:
        membership_lessons = self.membership.remaining_lessons
        schedule_count = self.db.query(ScheduleEvent).count()
        visit_count = self.db.query(Visit).count()

        self._create(self.tariffs[0].id, registered_teacher_id=self.teacher.id, customer_name="Анна Практика")

        self.db.refresh(self.membership)
        self.assertEqual(self.db.query(ScheduleEvent).count(), schedule_count)
        self.assertEqual(self.db.query(Visit).count(), visit_count)
        self.assertEqual(self.membership.remaining_lessons, membership_lessons)
        self.assertEqual(get_teacher_earnings(self.db, teacher_id=self.teacher.id)[0]["teacher_earned"], Decimal("0.00"))

    def test_search_is_case_insensitive(self) -> None:
        self._create(self.tariffs[0].id, customer_name="Александр")

        results = list_practice_rentals(self.db, search="алекс")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["customer_name"], "Александр")

    def _create(self, tariff_id: int, customer_name: str, registered_teacher_id: int | None = None):
        return create_practice_rental(
            self.db,
            PracticeRentalCreate(
                registered_teacher_id=registered_teacher_id,
                customer_name=customer_name,
                tariff_id=tariff_id,
                practiced_at=datetime(2026, 8, 14, 17, 30),
            ),
            self.operator,
        )


if __name__ == "__main__":
    unittest.main()
