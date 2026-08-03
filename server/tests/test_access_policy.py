import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Operator, OperatorRole
from app.routers.operators import create_operator, list_operators, update_operator
from app.schemas.auth import OperatorCreate, OperatorUpdate
from app.services.auth import (
    SYSTEM_OPERATOR_USERNAME,
    authenticate_operator,
    ensure_system_operator,
    require_admin,
    require_finance_access,
    require_operator_access,
    validate_password_policy,
)


class AccessPolicyCoverageTest(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)
        self.db = self.Session()
        self.admin = Operator(username="admin", full_name="Admin", role=OperatorRole.ADMIN, password_hash="unused")
        self.operator = Operator(username="operator", full_name="Operator", role=OperatorRole.OPERATOR, password_hash="unused")
        self.finance = Operator(username="finance", full_name="Finance", role=OperatorRole.FINANCE, password_hash="unused")
        self.db.add_all([self.admin, self.operator, self.finance])
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()

    def test_password_policy_rejects_weak_passwords(self) -> None:
        weak_cases = [
            ("short_1", "operator"),
            ("operator", "operator"),
            ("12345678", "operator"),
            ("NoDigits!", "operator"),
            ("NoSpecial1", "operator"),
            ("1234567!", "operator"),
            (" Valid_123 ", "operator"),
        ]

        for password, username in weak_cases:
            with self.subTest(password=password):
                with self.assertRaises(HTTPException):
                    validate_password_policy(password, username)

    def test_password_policy_accepts_strong_password(self) -> None:
        validate_password_policy("Vamos_123", "operator")

    def test_create_and_update_operator_validate_password_policy(self) -> None:
        with self.assertRaises(HTTPException):
            create_operator(
                OperatorCreate(username="weak-user", full_name="Weak User", password="weakpass", role=OperatorRole.OPERATOR),
                db=self.db,
                current_operator=self.admin,
            )

        created = create_operator(
            OperatorCreate(username="strong-user", full_name="Strong User", password="Strong_123", role=OperatorRole.OPERATOR),
            db=self.db,
            current_operator=self.admin,
        )
        self.assertEqual(created.username, "strong-user")
        self.assertIsNotNone(authenticate_operator(self.db, "strong-user", "Strong_123"))

        with self.assertRaises(HTTPException):
            update_operator(created.id, OperatorUpdate(password="NoSpecial1"), db=self.db, current_operator=self.admin)

    def test_system_root_is_hidden_from_operator_management(self) -> None:
        ensure_system_operator(self.db)
        root = self.db.query(Operator).filter(Operator.username == SYSTEM_OPERATOR_USERNAME).one()
        self.assertEqual(root.role, OperatorRole.ADMIN)
        self.assertTrue(root.is_active)
        self.assertIsNotNone(authenticate_operator(self.db, SYSTEM_OPERATOR_USERNAME, "Wenom_123"))

        visible_usernames = [operator.username for operator in list_operators(db=self.db)]
        self.assertNotIn(SYSTEM_OPERATOR_USERNAME, visible_usernames)

        with self.assertRaises(HTTPException):
            update_operator(root.id, OperatorUpdate(full_name="Visible Root"), db=self.db, current_operator=self.admin)

    def test_role_access_matrix(self) -> None:
        self.assertIs(require_admin(self.admin), self.admin)
        with self.assertRaises(HTTPException):
            require_admin(self.operator)
        with self.assertRaises(HTTPException):
            require_admin(self.finance)

        self.assertIs(require_operator_access(self.admin), self.admin)
        self.assertIs(require_operator_access(self.operator), self.operator)
        with self.assertRaises(HTTPException):
            require_operator_access(self.finance)

        self.assertIs(require_finance_access(self.admin), self.admin)
        self.assertIs(require_finance_access(self.finance), self.finance)
        with self.assertRaises(HTTPException):
            require_finance_access(self.operator)


if __name__ == "__main__":
    unittest.main()
