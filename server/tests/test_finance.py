from datetime import date, timedelta
from decimal import Decimal
import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Membership, MembershipStatus, MembershipType, Participant, Teacher
from app.services.finance import get_summary, get_teacher_earnings
from app.services.memberships import cancel_visit, write_off_visit


class FinanceSnapshotTest(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)
        self.db = self.Session()

        participant = Participant(full_name="Алексей Иванов", phone="+7 900 000-00-00")
        teacher = Teacher(full_name="Ирина Петрова", teacher_share_percent=Decimal("50"))
        membership_type = MembershipType(name="8 занятий", lesson_count=8, price=Decimal("14400"), validity_days=30)
        self.db.add_all([participant, teacher, membership_type])
        self.db.commit()

        membership = Membership(
            participant_id=participant.id,
            membership_type_id=membership_type.id,
            total_lessons=8,
            remaining_lessons=8,
            price=Decimal("14400"),
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status=MembershipStatus.ACTIVE,
        )
        self.db.add(membership)
        self.db.commit()
        self.participant_id = participant.id
        self.teacher_id = teacher.id
        self.membership_id = membership.id

    def tearDown(self) -> None:
        self.db.close()

    def test_visit_financial_snapshot_and_return(self) -> None:
        first = write_off_visit(self.db, self.participant_id, self.membership_id, self.teacher_id, date.today())
        self.assertEqual(first.lesson_price, Decimal("1800.00"))
        self.assertEqual(first.teacher_earning, Decimal("900.00"))
        self.assertEqual(first.school_earning, Decimal("900.00"))

        teacher = self.db.get(Teacher, self.teacher_id)
        teacher.teacher_share_percent = Decimal("60")
        self.db.add(teacher)
        self.db.commit()
        self.db.refresh(first)
        self.assertEqual(first.teacher_earning, Decimal("900.00"))

        second = write_off_visit(self.db, self.participant_id, self.membership_id, self.teacher_id, date.today())
        self.assertEqual(second.teacher_share_percent, Decimal("60.00"))
        self.assertEqual(second.teacher_earning, Decimal("1080.00"))
        self.assertEqual(second.school_earning, Decimal("720.00"))

        summary = get_summary(self.db)
        self.assertEqual(summary["completed_lessons_value"], Decimal("3600.00"))
        self.assertEqual(summary["teacher_earnings_total"], Decimal("1980.00"))
        self.assertEqual(summary["school_earnings_total"], Decimal("1620.00"))
        self.assertEqual(summary["completed_lessons_value"], summary["teacher_earnings_total"] + summary["school_earnings_total"])

        cancel_visit(self.db, first.id)
        summary = get_summary(self.db)
        self.assertEqual(summary["completed_lessons_value"], Decimal("1800.00"))
        self.assertEqual(summary["teacher_earnings_total"], Decimal("1080.00"))

        with self.assertRaises(HTTPException):
            cancel_visit(self.db, first.id)

    def test_teacher_and_period_filters(self) -> None:
        write_off_visit(self.db, self.participant_id, self.membership_id, self.teacher_id, date.today())
        tomorrow = date.today() + timedelta(days=1)

        self.assertEqual(get_summary(self.db, date_from=tomorrow)["completed_visits_count"], 0)
        self.assertEqual(get_summary(self.db, teacher_id=self.teacher_id)["completed_visits_count"], 1)
        self.assertEqual(get_teacher_earnings(self.db, teacher_id=self.teacher_id)[0]["visits_count"], 1)

    def test_zero_total_lessons_is_rejected(self) -> None:
        membership = self.db.get(Membership, self.membership_id)
        membership.total_lessons = 0
        self.db.add(membership)
        self.db.commit()

        with self.assertRaises(HTTPException):
            write_off_visit(self.db, self.participant_id, self.membership_id, self.teacher_id, date.today())


if __name__ == "__main__":
    unittest.main()
