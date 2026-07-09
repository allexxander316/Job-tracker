import sqlite3

connection = sqlite3.connect("job_tracker.db")


def create_vacancies_table(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vacancies (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            header      TEXT    NOT NULL,
            description TEXT    NOT NULL,
            url         TEXT    NOT NULL,
            external_id INTEGER NOT NULL UNIQUE,
            created_at  TIMESTAMP NOT NULL,
            updated_at  TIMESTAMP NOT NULL,
            status      TEXT    NOT NULL DEFAULT 'NEW',
            salary_from INTEGER DEFAULT 0,
            salary_to   INTEGER DEFAULT 0,
            area        INTEGER DEFAULT 0,
            experience  INTEGER
        )
    """)

    connection.commit()


def select_vacancies(connection: sqlite3.Connection) -> list:
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM vacancies")

    vacancies = cursor.fetchall()
    return vacancies


def get_by_external_id(connection: sqlite3.Connection, external_id: int) -> dict | None:
    cursor = connection.cursor()
    cursor.execute(
        "SELECT * FROM vacancies WHERE external_id = ?",
        (external_id,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "header": row[1],
        "description": row[2],
        "url": row[3],
        "external_id": row[4],
        "created_at": row[5],
        "updated_at": row[6],
        "status": row[7],
        "salary_from": row[8],
        "salary_to": row[9],
        "area": row[10],
        "experience": row[11],
    }


def insert_vacancy(connection: sqlite3.Connection, vacancy_data: dict) -> None:
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO vacancies (
            header, description, url, external_id,
            created_at, updated_at, status,
            salary_from, salary_to, area, experience
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            vacancy_data['header'],
            vacancy_data['description'],
            vacancy_data['url'],
            vacancy_data['external_id'],
            vacancy_data['created_at'],
            vacancy_data['updated_at'],
            vacancy_data['status'],
            vacancy_data['salary_from'],
            vacancy_data['salary_to'],
            vacancy_data['area'],
            vacancy_data['experience'],
        ),
    )

    connection.commit()


def update_vacancy(connection: sqlite3.Connection, vacancy_data: dict) -> None:
    cursor = connection.cursor()
    cursor.execute(
        """
        UPDATE vacancies
        SET header = ?,
            description = ?,
            url = ?,
            created_at = ?,
            updated_at = ?,
            status = ?,
            salary_from = ?,
            salary_to = ?,
            area = ?,
            experience = ?
        WHERE external_id = ?
        """,
        (
            vacancy_data['header'],
            vacancy_data['description'],
            vacancy_data['url'],
            vacancy_data['created_at'],
            vacancy_data['updated_at'],
            vacancy_data['status'],
            vacancy_data['salary_from'],
            vacancy_data['salary_to'],
            vacancy_data['area'],
            vacancy_data['experience'],
            vacancy_data['external_id'],
        ),
    )

    connection.commit()


def delete_vacancy(connection: sqlite3.Connection, external_id: int) -> None:
    cursor = connection.cursor()
    cursor.execute(
        "DELETE FROM vacancies WHERE external_id = ?",
        (external_id,),
    )

    connection.commit()
