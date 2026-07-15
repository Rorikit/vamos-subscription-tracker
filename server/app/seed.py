from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import Membership, MembershipStatus, MembershipType, Participant, Payment, Teacher, Visit


def seed_data(db: Session) -> None:
    if db.query(Participant).first():
        return

    types = [
        MembershipType(name="Старт 4", lesson_count=4, price=4000, validity_days=30, description="4 занятия на месяц"),
        MembershipType(name="База 8", lesson_count=8, price=7200, validity_days=45, description="Популярный абонемент"),
        MembershipType(name="Интенсив 12", lesson_count=12, price=9600, validity_days=60, description="Для регулярных занятий"),
    ]
    participants = [
        Participant(full_name="Анна Смирнова", phone="+7 900 111-22-33", comment="Предпочитает вечер"),
        Participant(full_name="Илья Морозов", phone="+7 900 222-33-44"),
        Participant(full_name="Мария Кузнецова", phone="+7 900 333-44-55"),
        Participant(full_name="Дмитрий Орлов", phone="+7 900 444-55-66"),
        Participant(full_name="Елена Васильева", phone="+7 900 555-66-77"),
    ]
    teachers = [
        Teacher(full_name="София Белова", phone="+7 901 100-10-10", comment="Сальса и бачата"),
        Teacher(full_name="Марк Волков", phone="+7 901 200-20-20", comment="Групповые занятия"),
        Teacher(full_name="Виктория Лебедева", phone="+7 901 300-30-30", comment="Индивидуальные занятия"),
    ]
    db.add_all(types + participants + teachers)
    db.commit()

    today = date.today()
    memberships = [
        Membership(participant_id=1, membership_type_id=2, total_lessons=8, remaining_lessons=5, price=7200, teacher_lesson_rate=450, start_date=today - timedelta(days=10), end_date=today + timedelta(days=35), status=MembershipStatus.ACTIVE),
        Membership(participant_id=2, membership_type_id=1, total_lessons=4, remaining_lessons=1, price=4000, teacher_lesson_rate=500, start_date=today - timedelta(days=25), end_date=today + timedelta(days=5), status=MembershipStatus.ACTIVE),
        Membership(participant_id=3, membership_type_id=3, total_lessons=12, remaining_lessons=0, price=9600, teacher_lesson_rate=400, start_date=today - timedelta(days=50), end_date=today + timedelta(days=10), status=MembershipStatus.FINISHED),
        Membership(participant_id=4, membership_type_id=2, total_lessons=8, remaining_lessons=8, price=7200, teacher_lesson_rate=450, start_date=today - timedelta(days=60), end_date=today - timedelta(days=15), status=MembershipStatus.EXPIRED),
        Membership(participant_id=5, membership_type_id=3, total_lessons=12, remaining_lessons=9, price=9600, teacher_lesson_rate=400, start_date=today - timedelta(days=3), end_date=today + timedelta(days=57), status=MembershipStatus.ACTIVE),
    ]
    db.add_all(memberships)
    db.commit()

    db.add_all(
        [
            Payment(participant_id=1, membership_id=1, amount=7200, payment_date=today - timedelta(days=9), payment_method="card", comment="Полная оплата"),
            Payment(participant_id=2, membership_id=2, amount=2000, payment_date=today - timedelta(days=23), payment_method="cash", comment="Частичная оплата"),
            Payment(participant_id=3, membership_id=3, amount=9600, payment_date=today - timedelta(days=48), payment_method="transfer"),
            Payment(participant_id=4, membership_id=4, amount=3000, payment_date=today - timedelta(days=58), payment_method="cash"),
            Payment(participant_id=5, membership_id=5, amount=5000, payment_date=today - timedelta(days=2), payment_method="card"),
        ]
    )
    db.add_all(
        [
            Visit(participant_id=1, membership_id=1, teacher_id=1, visit_date=today - timedelta(days=8)),
            Visit(participant_id=1, membership_id=1, teacher_id=2, visit_date=today - timedelta(days=5)),
            Visit(participant_id=1, membership_id=1, teacher_id=1, visit_date=today - timedelta(days=1)),
            Visit(participant_id=2, membership_id=2, teacher_id=2, visit_date=today - timedelta(days=20)),
            Visit(participant_id=2, membership_id=2, teacher_id=3, visit_date=today - timedelta(days=14)),
            Visit(participant_id=3, membership_id=3, teacher_id=3, visit_date=today - timedelta(days=4)),
            Visit(participant_id=5, membership_id=5, teacher_id=1, visit_date=today - timedelta(days=1)),
        ]
    )
    db.commit()
