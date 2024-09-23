from db import Postgres


class BundleTasks:
    def __init__(self):
        self.db = Postgres.get_instance()

    def create_table(self):
        query = """
            CREATE TABLE IF	NOT EXISTS bundle_tasks (
                id SERIAL PRIMARY KEY,
                start_time INTEGER NOT NULL,
                end_time INTEGER NOT NULL,
                is_done BOOLEAN DEFAULT FALSE,
                count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        self.db.execute(query)

    def create(self, start_time, end_time):
        task = self.get_by_time_range(start_time, end_time)
        if task:
            return task[0][0]
        else:
            query = f"""
                INSERT INTO tasks (start_time, end_time)
                VALUES ({start_time}, {end_time})
                RETURNING id
            """
            return self.db.query(query)[0][0]

    def get_by_time_range(self, start_time, end_time):
        query = f"""
            SELECT id FROM tasks WHERE start_time = {start_time} AND end_time = {end_time}
        """
        return self.db.query(query)

    def get_not_done(self):
        query = """
            SELECT end_time FROM tasks WHERE is_done = FALSE
        """
        return self.db.query(query)

    def update_done(self, task_id, count: int):
        query = f"""
            UPDATE tasks SET is_done = TRUE, count = {count} WHERE id = {task_id}
        """
        self.db.execute(query)