import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import AuditLog, Operator, OperatorRole
from app.services.audit import log_action
from app.services.auth import hash_password


class AuditPolicyTest(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)
        self.db = self.Session()

    def tearDown(self) -> None:
        self.db.close()

    def test_root_actions_are_not_logged(self) -> None:
        root = Operator(username="root", full_name="Root", role=OperatorRole.ADMIN, password_hash=hash_password("Wenom_123"))
        operator = Operator(username="operator", full_name="Operator", role=OperatorRole.ADMIN, password_hash=hash_password("Vamos_123"))
        self.db.add_all([root, operator])
        self.db.commit()

        self.assertIsNone(log_action(self.db, root, "root_action", "operator", root.id, root.full_name))
        self.assertIsNotNone(log_action(self.db, operator, "operator_action", "operator", operator.id, operator.full_name))

        logs = self.db.query(AuditLog).all()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].operator_name, "Operator")


if __name__ == "__main__":
    unittest.main()
