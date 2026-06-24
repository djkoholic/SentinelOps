import sqlite3
import logging

logger = logging.getLogger(__name__)

DATABASE_PATH = "/home/djkoholic/Projects/SentinelOps/data-store/sentinelops.db"

class DataCollector:
    
    def __init__(self, start_time=None, end_time=None, request_ids=[]):
        self.connection = sqlite3.connect(DATABASE_PATH)
        self.request_ids = request_ids
        self.start_time = start_time
        self.end_time = end_time

    def _create_query(self, table_name):
        query = f"SELECT * FROM {table_name}"
        conditions = []
        params = []

        if self.start_time and self.end_time:
            conditions.append("timestamp BETWEEN ? AND ?")
            params.extend([self.start_time, self.end_time])

        if self.request_ids:
            placeholders = ",".join(["?"] * len(self.request_ids))
            conditions.append(f"request_id IN ({placeholders})")
            params.extend(self.request_ids)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        return query, params

    def _query_database(self, query, params):
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return columns, rows

    def _format_results(self, columns, rows):
        return [dict(zip(columns, row)) for row in rows]

    def collect_data(self, table_name):
        query, params = self._create_query(table_name)
        columns, rows = self._query_database(query, params)
        formatted_results = self._format_results(columns, rows)
        return formatted_results

    def close_connection(self):
        self.connection.close()