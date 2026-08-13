from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models import ExpenseCategory, Membership, MonthlyExpense, Operator, Teacher, Visit
from app.services.lesson_finance import ensure_visit_financials, quantize_money

TEACHER_EXPENSE_CATEGORY_NAME = "Оплата преподавателям"

DEFAULT_EXPENSE_CATEGORIES = [
    {"name": "Егорова", "default_amount": Decimal("60000"), "is_variable": False, "sort_order": 10},
    {"name": "Вова", "default_amount": Decimal("50000"), "is_variable": False, "sort_order": 20},
    {"name": "Кулер", "default_amount": Decimal("14000"), "is_variable": False, "sort_order": 30},
    {"name": "Коммуналка", "default_amount": Decimal("41400"), "is_variable": False, "sort_order": 40},
    {"name": "Интернет", "default_amount": Decimal("39800"), "is_variable": False, "sort_order": 50},
    {"name": "Ковры", "default_amount": None, "is_variable": True, "sort_order": 60},
    {"name": "Уборщица", "default_amount": Decimal("48000"), "is_variable": True, "sort_order": 70},
    {"name": "Администратор", "default_amount": None, "is_variable": True, "sort_order": 80},
    {"name": "Дворник", "default_amount": None, "is_variable": True, "sort_order": 90},
    {"name": TEACHER_EXPENSE_CATEGORY_NAME, "default_amount": None, "is_variable": True, "sort_order": 100},
]


def month_bounds(year: int, month: int) -> tuple[date, date]:
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Месяц должен быть от 1 до 12")
    return date(year, month, 1), date(year, month, monthrange(year, month)[1])


def ensure_expense_categories(db: Session) -> list[ExpenseCategory]:
    for item in DEFAULT_EXPENSE_CATEGORIES:
        category = db.query(ExpenseCategory).filter(ExpenseCategory.name == item["name"]).first()
        if not category:
            db.add(
                ExpenseCategory(
                    name=item["name"],
                    default_amount=item["default_amount"],
                    is_variable=item["is_variable"],
                    is_active=True,
                    reminder_day=26,
                    sort_order=item["sort_order"],
                )
            )
    db.commit()
    return db.query(ExpenseCategory).order_by(ExpenseCategory.sort_order, ExpenseCategory.name).all()


def ensure_monthly_expenses(db: Session, year: int, month: int) -> list[MonthlyExpense]:
    month_bounds(year, month)
    categories = ensure_expense_categories(db)
    existing = {
        expense.category_id: expense
        for expense in db.query(MonthlyExpense).filter(MonthlyExpense.year == year, MonthlyExpense.month == month).all()
    }
    for category in categories:
        if not category.is_active or category.id in existing:
            continue
        planned = Decimal(category.default_amount or 0)
        db.add(MonthlyExpense(category_id=category.id, year=year, month=month, planned_amount=quantize_money(planned)))
    db.commit()
    return (
        db.query(MonthlyExpense)
        .options(joinedload(MonthlyExpense.category), joinedload(MonthlyExpense.paid_by))
        .join(ExpenseCategory)
        .filter(MonthlyExpense.year == year, MonthlyExpense.month == month)
        .order_by(ExpenseCategory.sort_order, ExpenseCategory.name)
        .all()
    )


def _expense_status(expense: MonthlyExpense, today: date | None = None) -> str:
    if expense.paid:
        return "paid"
    current = today or date.today()
    if current.year == expense.year and current.month == expense.month:
        if current.day > expense.category.reminder_day:
            return "overdue"
        if current.day == expense.category.reminder_day:
            return "due_today"
    return "pending"


def _effective_amount(expense: MonthlyExpense, teacher_expense_total: Decimal) -> Decimal:
    if expense.category.name == TEACHER_EXPENSE_CATEGORY_NAME:
        return quantize_money(teacher_expense_total)
    return quantize_money(Decimal(expense.actual_amount if expense.actual_amount is not None else expense.planned_amount or 0))


def _serialize_expense(expense: MonthlyExpense, teacher_expense_total: Decimal) -> dict:
    is_teacher_expense = expense.category.name == TEACHER_EXPENSE_CATEGORY_NAME
    effective = _effective_amount(expense, teacher_expense_total)
    planned = teacher_expense_total if is_teacher_expense else Decimal(expense.planned_amount or 0)
    actual = teacher_expense_total if is_teacher_expense else expense.actual_amount
    return {
        "id": expense.id,
        "category_id": expense.category_id,
        "category_name": expense.category.name,
        "year": expense.year,
        "month": expense.month,
        "planned_amount": quantize_money(planned),
        "actual_amount": quantize_money(actual) if actual is not None else None,
        "effective_amount": effective,
        "paid": expense.paid,
        "paid_at": expense.paid_at.date() if expense.paid_at else None,
        "paid_by_user_id": expense.paid_by_user_id,
        "paid_by_name": expense.paid_by.full_name if expense.paid_by else None,
        "comment": expense.comment,
        "is_variable": expense.category.is_variable,
        "reminder_day": expense.category.reminder_day,
        "status": _expense_status(expense),
        "is_teacher_expense": is_teacher_expense,
    }


def get_monthly_report(db: Session, year: int, month: int) -> dict:
    date_from, date_to = month_bounds(year, month)
    expenses = ensure_monthly_expenses(db, year, month)
    summary = get_summary(db, date_from=date_from, date_to=date_to)
    teacher_earnings = get_teacher_earnings(db, date_from=date_from, date_to=date_to, include_cancelled=True)
    teacher_expense_total = quantize_money(Decimal(summary["teacher_earnings_total"]))
    serialized_expenses = [_serialize_expense(expense, teacher_expense_total) for expense in expenses]
    expenses_total = quantize_money(sum((Decimal(item["effective_amount"]) for item in serialized_expenses), Decimal("0")))
    income_total = quantize_money(Decimal(summary["memberships_sold_total"]))
    net_result = quantize_money(income_total - expenses_total)
    unpaid = [item for item in serialized_expenses if not item["paid"]]
    unpaid_total = quantize_money(sum((Decimal(item["effective_amount"]) for item in unpaid), Decimal("0")))
    chart = []
    for item in serialized_expenses:
        amount = Decimal(item["effective_amount"])
        percentage = quantize_money((amount / expenses_total * Decimal("100")) if expenses_total else Decimal("0"))
        chart.append(
            {
                "category_id": item["category_id"],
                "category_name": item["category_name"],
                "amount": amount,
                "percentage": percentage,
                "is_teacher_expense": item["is_teacher_expense"],
            }
        )
    chart.sort(key=lambda item: (item["amount"], item["category_name"]), reverse=True)
    return {
        "year": year,
        "month": month,
        "date_from": date_from,
        "date_to": date_to,
        "income_total": income_total,
        "memberships_sold_total": income_total,
        "expenses_total": expenses_total,
        "teacher_expense_total": teacher_expense_total,
        "net_result": net_result,
        "unpaid_expenses_count": len(unpaid),
        "unpaid_expenses_total": unpaid_total,
        "completed_visits_count": summary["completed_visits_count"],
        "chart": chart,
        "expenses": serialized_expenses,
        "teacher_earnings": teacher_earnings,
    }


def list_monthly_expenses(db: Session, year: int, month: int) -> list[dict]:
    report = get_monthly_report(db, year, month)
    return report["expenses"]


def update_monthly_expense(db: Session, expense_id: int, data: dict) -> MonthlyExpense:
    expense = db.get(MonthlyExpense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Расход не найден")
    if expense.category and expense.category.name == TEACHER_EXPENSE_CATEGORY_NAME and any(key in data for key in {"planned_amount", "actual_amount"}):
        raise HTTPException(status_code=400, detail="Выплаты преподавателям рассчитываются автоматически")
    for key, value in data.items():
        setattr(expense, key, value)
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


def mark_expense_paid(db: Session, expense_id: int, operator: Operator) -> MonthlyExpense:
    expense = db.get(MonthlyExpense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Расход не найден")
    expense.paid = True
    expense.paid_at = datetime.utcnow()
    expense.paid_by_user_id = operator.id
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


def mark_expense_unpaid(db: Session, expense_id: int) -> MonthlyExpense:
    expense = db.get(MonthlyExpense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Расход не найден")
    expense.paid = False
    expense.paid_at = None
    expense.paid_by_user_id = None
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


def get_reminder_status(db: Session, year: int | None = None, month: int | None = None) -> dict:
    today = date.today()
    target_year = year or today.year
    target_month = month or today.month
    report = get_monthly_report(db, target_year, target_month)
    active_unpaid = [
        item
        for item in report["expenses"]
        if not item["paid"] and item["status"] in {"due_today", "overdue"}
    ]
    total = quantize_money(sum((Decimal(item["effective_amount"]) for item in active_unpaid), Decimal("0")))
    return {
        "year": target_year,
        "month": target_month,
        "active": bool(active_unpaid),
        "unpaid_count": len(active_unpaid),
        "unpaid_total": total,
    }


def get_teacher_earnings(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    teacher_id: int | None = None,
    membership_type_id: int | None = None,
    include_cancelled: bool = False,
) -> list[dict]:
    teachers_query = db.query(Teacher).order_by(Teacher.full_name)
    if teacher_id:
        teachers_query = teachers_query.filter(Teacher.id == teacher_id)
    teachers = teachers_query.all()

    query = (
        db.query(Visit)
        .options(
            joinedload(Visit.teacher),
            joinedload(Visit.participant),
            joinedload(Visit.membership).joinedload(Membership.membership_type),
        )
    )
    if date_from:
        query = query.filter(Visit.visit_date >= date_from)
    if date_to:
        query = query.filter(Visit.visit_date <= date_to)
    if teacher_id:
        query = query.filter(Visit.teacher_id == teacher_id)
    if membership_type_id:
        query = query.join(Membership, Visit.membership_id == Membership.id).filter(Membership.membership_type_id == membership_type_id)
    if not include_cancelled:
        query = query.filter(Visit.is_cancelled.is_(False))

    visits = query.order_by(Visit.visit_date.desc(), Visit.id.desc()).all()
    valid_visits = []
    for visit in visits:
        try:
            ensure_visit_financials(visit)
        except HTTPException:
            continue
        db.add(visit)
        valid_visits.append(visit)
    db.commit()
    visits = valid_visits

    earnings: dict[int, dict] = {
        teacher.id: {
            "teacher_id": teacher.id,
            "teacher_name": teacher.full_name,
            "average_teacher_lesson_rate": Decimal("0"),
            "visits_count": 0,
            "completed_lessons_value": Decimal("0"),
            "teacher_earned": Decimal("0"),
            "school_earned": Decimal("0"),
            "average_lesson_price": Decimal("0"),
            "average_teacher_earning": Decimal("0"),
            "last_visit_date": None,
            "visits": [],
        }
        for teacher in teachers
    }

    for visit in visits:
        if visit.teacher_id not in earnings:
            continue
        item = earnings[visit.teacher_id]
        lesson_price = quantize_money(Decimal(visit.lesson_price or 0))
        teacher_lesson_rate = quantize_money(Decimal(visit.teacher_lesson_rate or visit.teacher_earning or 0))
        teacher_earning = quantize_money(Decimal(visit.teacher_earning or 0))
        school_earning = quantize_money(Decimal(visit.school_earning or 0))
        item["visits"].append(
            {
                "visit_id": visit.id,
                "visit_date": visit.visit_date,
                "participant_id": visit.participant_id,
                "participant_name": visit.participant.full_name if visit.participant else "—",
                "membership_id": visit.membership_id,
                "membership_name": visit.membership.membership_type.name if visit.membership and visit.membership.membership_type else f"Абонемент #{visit.membership_id}",
                "lesson_price": lesson_price,
                "teacher_lesson_rate": teacher_lesson_rate,
                "teacher_earning": teacher_earning,
                "school_earning": school_earning,
                "is_cancelled": visit.is_cancelled,
            }
        )
        if visit.is_cancelled:
            continue
        item["visits_count"] += 1
        item["completed_lessons_value"] += lesson_price
        item["teacher_earned"] += teacher_earning
        item["school_earned"] += school_earning
        if item["last_visit_date"] is None or visit.visit_date > item["last_visit_date"]:
            item["last_visit_date"] = visit.visit_date

    for item in earnings.values():
        visits_count = item["visits_count"]
        item["completed_lessons_value"] = quantize_money(item["completed_lessons_value"])
        item["teacher_earned"] = quantize_money(item["teacher_earned"])
        item["school_earned"] = quantize_money(item["school_earned"])
        item["average_lesson_price"] = quantize_money(item["completed_lessons_value"] / Decimal(visits_count)) if visits_count else Decimal("0.00")
        item["average_teacher_earning"] = quantize_money(item["teacher_earned"] / Decimal(visits_count)) if visits_count else Decimal("0.00")
        item["average_teacher_lesson_rate"] = item["average_teacher_earning"]

    return sorted(
        earnings.values(),
        key=lambda item: (item["last_visit_date"] or date.min, item["teacher_earned"], item["teacher_name"]),
        reverse=True,
    )


def get_summary(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    teacher_id: int | None = None,
    membership_type_id: int | None = None,
) -> dict:
    teacher_membership_ids: list[int] | None = None
    if teacher_id:
        teacher_membership_query = db.query(Visit.membership_id).filter(
            Visit.teacher_id == teacher_id,
            Visit.is_cancelled.is_(False),
        )
        if date_from:
            teacher_membership_query = teacher_membership_query.filter(Visit.visit_date >= date_from)
        if date_to:
            teacher_membership_query = teacher_membership_query.filter(Visit.visit_date <= date_to)
        teacher_membership_ids = [row[0] for row in teacher_membership_query.distinct().all()]

    memberships_query = db.query(func.coalesce(func.sum(Membership.price), 0))
    if date_from:
        memberships_query = memberships_query.filter(Membership.start_date >= date_from)
    if date_to:
        memberships_query = memberships_query.filter(Membership.start_date <= date_to)
    if teacher_membership_ids is not None:
        memberships_query = memberships_query.filter(Membership.id.in_(teacher_membership_ids))
    if membership_type_id:
        memberships_query = memberships_query.filter(Membership.membership_type_id == membership_type_id)
    memberships_sold_total = Decimal(memberships_query.scalar() or 0)

    visit_query = db.query(Visit).filter(Visit.is_cancelled.is_(False))
    if date_from:
        visit_query = visit_query.filter(Visit.visit_date >= date_from)
    if date_to:
        visit_query = visit_query.filter(Visit.visit_date <= date_to)
    if teacher_id:
        visit_query = visit_query.filter(Visit.teacher_id == teacher_id)
    if membership_type_id:
        visit_query = visit_query.join(Membership, Visit.membership_id == Membership.id).filter(Membership.membership_type_id == membership_type_id)
    visits = visit_query.options(joinedload(Visit.teacher), joinedload(Visit.membership)).all()
    valid_visits = []
    for visit in visits:
        try:
            ensure_visit_financials(visit)
        except HTTPException:
            continue
        db.add(visit)
        valid_visits.append(visit)
    db.commit()
    visits = valid_visits

    completed_lessons_value = sum((Decimal(visit.lesson_price or 0) for visit in visits), Decimal("0"))
    teacher_earnings_total = sum((Decimal(visit.teacher_earning or 0) for visit in visits), Decimal("0"))
    school_earnings_total = sum((Decimal(visit.school_earning or 0) for visit in visits), Decimal("0"))
    completed_visits_count = len(visits)
    active_teachers_query = db.query(Teacher).filter(Teacher.is_active.is_(True))
    if teacher_id:
        active_teachers_query = active_teachers_query.filter(Teacher.id == teacher_id)
    active_teachers_count = active_teachers_query.count()

    return {
        "memberships_sold_total": quantize_money(memberships_sold_total),
        "completed_lessons_value": quantize_money(completed_lessons_value),
        "teacher_earnings_total": quantize_money(teacher_earnings_total),
        "school_earnings_total": quantize_money(school_earnings_total),
        "completed_visits_count": completed_visits_count,
        "average_lesson_price": quantize_money(completed_lessons_value / Decimal(completed_visits_count)) if completed_visits_count else Decimal("0.00"),
        "average_teacher_earning": quantize_money(teacher_earnings_total / Decimal(completed_visits_count)) if completed_visits_count else Decimal("0.00"),
        "active_teachers_count": active_teachers_count,
    }


def ensure_teacher_seed(db: Session) -> list[Teacher]:
    if db.query(Teacher).count() == 0:
        db.add_all(
            [
                Teacher(full_name="София Белова", phone="+7 901 100-10-10", comment="Сальса и бачата"),
                Teacher(full_name="Марк Волков", phone="+7 901 200-20-20", comment="Групповые занятия"),
                Teacher(full_name="Виктория Лебедева", phone="+7 901 300-30-30", comment="Индивидуальные занятия"),
            ]
        )
        db.commit()
    return db.query(Teacher).order_by(Teacher.id).all()
