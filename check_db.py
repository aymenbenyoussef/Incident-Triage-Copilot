import sqlite3
from pathlib import Path


DATABASE = Path(__file__).parent / "data" / "prod.db"


def main() -> None:
    if not DATABASE.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE}. "
            "Run 'python -m sim.generate --scenario bad_deploy' first."
        )

    with sqlite3.connect(DATABASE) as connection:
        cursor = connection.execute(
            "SELECT ts, service, level, message "
            "FROM logs "
            "ORDER BY ts DESC"
        )
        rows = cursor.fetchall()

        print(f"Database: {DATABASE}")
        print("Logs:")
        print(" | ".join(column[0] for column in cursor.description))
        for row in rows:
            print(" | ".join(str(value) for value in row))
        print(f"\nTotal logs: {len(rows)}")


if __name__ == "__main__":
    main()
