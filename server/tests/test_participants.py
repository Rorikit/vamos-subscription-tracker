import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Participant
from app.routers.participants import list_participants


class ParticipantSearchTest(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)
        self.db = self.Session()
        self.db.add_all(
            [
                Participant(full_name="Иван Петров", phone="+7 900 111-22-33"),
                Participant(full_name="Мария Сидорова", phone="+7 900 444-55-66"),
            ]
        )
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()

    def test_search_is_case_insensitive_for_cyrillic_name(self) -> None:
        lower = list_participants(search="иван", db=self.db)
        upper = list_participants(search="ИВАН", db=self.db)

        self.assertEqual([item["full_name"] for item in lower], ["Иван Петров"])
        self.assertEqual([item["full_name"] for item in upper], ["Иван Петров"])

    def test_search_matches_phone(self) -> None:
        result = list_participants(search="444", db=self.db)

        self.assertEqual([item["full_name"] for item in result], ["Мария Сидорова"])


if __name__ == "__main__":
    unittest.main()
