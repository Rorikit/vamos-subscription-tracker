import unittest

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.main import migrate_local_sqlite
from app.models import Teacher


class LocalMigrationTest(unittest.TestCase):
    def test_teacher_legacy_share_percent_column_is_removed(self) -> None:
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        session = sessionmaker(bind=engine)
        db = session()
        try:
            db.execute(
                text(
                    """
                    create table teachers (
                        id integer not null primary key,
                        full_name varchar(255) not null,
                        phone varchar(64),
                        comment text,
                        teacher_share_percent numeric(5, 2) not null,
                        is_active boolean not null,
                        created_at datetime not null,
                        updated_at datetime not null
                    )
                    """
                )
            )
            db.execute(
                text(
                    """
                    insert into teachers (
                        id, full_name, phone, comment, teacher_share_percent, is_active, created_at, updated_at
                    )
                    values (1, 'Старый преподаватель', null, null, 50, 1, current_timestamp, current_timestamp)
                    """
                )
            )
            db.commit()

            migrate_local_sqlite(db)

            columns = {column["name"] for column in inspect(engine).get_columns("teachers")}
            self.assertNotIn("teacher_share_percent", columns)

            db.add(Teacher(full_name="Новый преподаватель", phone="", comment="", is_active=True))
            db.commit()
            self.assertEqual(db.query(Teacher).count(), 2)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
