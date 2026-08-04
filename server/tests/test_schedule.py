from datetime import date, datetime, timedelta
from decimal import Decimal
import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Membership, MembershipStatus, MembershipType, Participant, ScheduleEventStatus, Teacher
from app.schemas.schedule import ScheduleEventCreate, ScheduleEventUpdate
from app.services.schedule_events import complete_event, create_events, move_event, return_participant_visit, update_event


class ScheduleEventTest(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)
        self.db = self.Session()

        teacher = Teacher(full_name="Анна Преподаватель")
        participant = Participant(full_name="Алексей Ученик", phone="+7 900 000-00-00")
        second = Participant(full_name="Мария Ученик", phone="+7 900 000-00-01")
        membership_type = MembershipType(name="8 занятий", lesson_count=8, price=Decimal("12000"), validity_days=30)
        self.db.add_all([teacher, participant, second, membership_type])
        self.db.commit()

        for participant_id in [participant.id, second.id]:
            self.db.add(
                Membership(
                    participant_id=participant_id,
                    membership_type_id=membership_type.id,
                    total_lessons=8,
                    remaining_lessons=8,
                    price=Decimal("12000"),
                    teacher_lesson_rate=Decimal("700"),
                    start_date=date.today(),
                    end_date=date.today() + timedelta(days=30),
                    status=MembershipStatus.ACTIVE,
                )
            )
        self.db.commit()
        self.teacher_id = teacher.id
        self.participant_id = participant.id
        self.second_id = second.id
        self.starts_at = datetime(2026, 8, 3, 10, 0)
        self.ends_at = datetime(2026, 8, 3, 11, 0)

    def tearDown(self) -> None:
        self.db.close()

    def payload(self, **overrides) -> ScheduleEventCreate:
        data = {
            "title": "Бачата",
            "teacher_id": self.teacher_id,
            "starts_at": self.starts_at,
            "ends_at": self.ends_at,
            "event_type": "group",
            "participant_ids": [self.participant_id],
        }
        data.update(overrides)
        return ScheduleEventCreate(**data)

    def test_create_single_and_group_event(self) -> None:
        events = create_events(self.db, self.payload(participant_ids=[self.participant_id, self.second_id]))
        self.assertEqual(len(events), 1)
        self.assertEqual(len(events[0].participants), 2)

    def test_create_recurring_series(self) -> None:
        events = create_events(self.db, self.payload(recurrence={"frequency": "weekly", "count": 4}))
        self.assertEqual(len(events), 4)
        self.assertTrue(events[0].recurrence_group_id)

    def test_teacher_conflict_and_adjacent_event(self) -> None:
        create_events(self.db, self.payload())
        with self.assertRaises(HTTPException):
            create_events(self.db, self.payload(starts_at=datetime(2026, 8, 3, 10, 30), ends_at=datetime(2026, 8, 3, 11, 30)))
        adjacent = create_events(self.db, self.payload(starts_at=datetime(2026, 8, 3, 11, 0), ends_at=datetime(2026, 8, 3, 12, 0)))
        self.assertEqual(adjacent[0].starts_at.hour, 11)

    def test_cancelled_event_does_not_conflict(self) -> None:
        event = create_events(self.db, self.payload())[0]
        event.status = ScheduleEventStatus.CANCELLED
        self.db.add(event)
        self.db.commit()
        events = create_events(self.db, self.payload())
        self.assertEqual(len(events), 1)

    def test_move_and_update_event(self) -> None:
        event = create_events(self.db, self.payload())[0]
        moved = move_event(self.db, event.id, datetime(2026, 8, 4, 12, 0), datetime(2026, 8, 4, 13, 0))
        self.assertEqual(moved.starts_at.day, 4)
        updated = update_event(self.db, event.id, ScheduleEventUpdate(title="Сальса"))
        self.assertEqual(updated.title, "Сальса")

    def test_update_event_keeps_existing_participant_without_duplicate(self) -> None:
        event = create_events(self.db, self.payload())[0]
        updated = update_event(
            self.db,
            event.id,
            ScheduleEventUpdate(title="Сальса", participant_ids=[self.participant_id]),
        )

        self.assertEqual(updated.title, "Сальса")
        self.assertEqual([item.participant_id for item in updated.participants], [self.participant_id])

    def test_complete_group_event_and_return_visit(self) -> None:
        event = create_events(self.db, self.payload(participant_ids=[self.participant_id, self.second_id]))[0]
        completed = complete_event(
            self.db,
            event.id,
            [
                {"participant_id": self.participant_id, "attendance_status": "attended"},
                {"participant_id": self.second_id, "attendance_status": "absent"},
            ],
        )
        self.assertEqual(completed.status, ScheduleEventStatus.COMPLETED)
        attended = next(item for item in completed.participants if item.participant_id == self.participant_id)
        absent = next(item for item in completed.participants if item.participant_id == self.second_id)
        self.assertTrue(attended.visit_id)
        self.assertIsNone(absent.visit_id)

        returned = return_participant_visit(self.db, event.id, self.participant_id)
        returned_item = next(item for item in returned.participants if item.participant_id == self.participant_id)
        self.assertEqual(returned_item.attendance_status, "refunded")
        with self.assertRaises(HTTPException):
            return_participant_visit(self.db, event.id, self.participant_id)

    def test_duplicate_participant_rejected(self) -> None:
        with self.assertRaises(HTTPException):
            create_events(self.db, self.payload(participant_ids=[self.participant_id, self.participant_id]))


if __name__ == "__main__":
    unittest.main()
