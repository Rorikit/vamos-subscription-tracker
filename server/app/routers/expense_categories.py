from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ExpenseCategory, Operator
from app.schemas.finance import ExpenseCategoryCreate, ExpenseCategoryRead, ExpenseCategoryUpdate
from app.services.audit import log_action, snapshot
from app.services.auth import require_admin, require_finance_access
from app.services.finance import ensure_expense_categories

router = APIRouter(prefix="/expense-categories", tags=["expense-categories"])


@router.get("", response_model=list[ExpenseCategoryRead])
def list_expense_categories(db: Session = Depends(get_db), _operator: Operator = Depends(require_finance_access)):
    ensure_expense_categories(db)
    return db.query(ExpenseCategory).order_by(ExpenseCategory.sort_order, ExpenseCategory.name).all()


@router.post("", response_model=ExpenseCategoryRead)
def create_expense_category(
    payload: ExpenseCategoryCreate,
    db: Session = Depends(get_db),
    operator: Operator = Depends(require_admin),
):
    name = payload.name.strip()
    if db.query(ExpenseCategory).filter(ExpenseCategory.name == name).first():
        raise HTTPException(status_code=400, detail="Категория с таким названием уже существует")
    category = ExpenseCategory(**payload.model_dump(exclude={"name"}), name=name)
    db.add(category)
    db.commit()
    db.refresh(category)
    log_action(db, operator, "expense_category_changed", "expense_category", category.id, category.name, after=snapshot(category, ["name", "default_amount", "is_variable", "is_active", "reminder_day", "sort_order"]))
    return category


@router.patch("/{category_id}", response_model=ExpenseCategoryRead)
def update_expense_category(
    category_id: int,
    payload: ExpenseCategoryUpdate,
    db: Session = Depends(get_db),
    operator: Operator = Depends(require_admin),
):
    category = db.get(ExpenseCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Категория расходов не найдена")
    before = snapshot(category, ["name", "default_amount", "is_variable", "is_active", "reminder_day", "sort_order"])
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        data["name"] = data["name"].strip()
        existing = db.query(ExpenseCategory).filter(ExpenseCategory.name == data["name"], ExpenseCategory.id != category_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Категория с таким названием уже существует")
    for key, value in data.items():
        setattr(category, key, value)
    db.add(category)
    db.commit()
    db.refresh(category)
    log_action(db, operator, "expense_category_changed", "expense_category", category.id, category.name, before=before, after=snapshot(category, ["name", "default_amount", "is_variable", "is_active", "reminder_day", "sort_order"]))
    return category
