import sqlite3
import logging

logger = logging.getLogger(__name__)

def query_requests_table(cursor, start_time, end_time):
    logger.info(f"Querying requests table for time range: {start_time} to {end_time}")
    query = """
    SELECT * FROM requests
    WHERE timestamp BETWEEN ? AND ?
    """
    cursor.execute(query, (start_time, end_time))
    results = cursor.fetchall()
    logger.info(f"Found {len(results)} requests")
    return results

def query_application_logs_table(cursor, request_ids):
    logger.info(f"Querying application_logs for {len(request_ids)} request IDs")
    query = """
    SELECT * FROM application_logs
    WHERE request_id IN ({})
    """.format(','.join('?' for _ in request_ids))
    cursor.execute(query, request_ids)
    results = cursor.fetchall()
    logger.info(f"Found {len(results)} application logs")
    return results

def query_request_metrics_table(cursor, request_ids):
    logger.info(f"Querying request_metrics for {len(request_ids)} request IDs")
    query = """
    SELECT * FROM request_metrics
    WHERE request_id IN ({})
    """.format(','.join('?' for _ in request_ids))
    cursor.execute(query, request_ids)
    results = cursor.fetchall()
    logger.info(f"Found {len(results)} request metrics")
    return results

def query_pod_metrics_table(cursor, start_time, end_time):
    logger.info(f"Querying pod_metrics for time range: {start_time} to {end_time}")
    query = """
    SELECT * FROM pod_metrics
    WHERE timestamp BETWEEN ? AND ?
    """
    cursor.execute(query, (start_time, end_time))
    results = cursor.fetchall()
    logger.info(f"Found {len(results)} pod metrics")
    return results

def query_database(cursor, start_time, end_time):
    requests = query_requests_table(cursor, start_time, end_time)
    request_ids = [request[0] for request in requests]
    application_logs = query_application_logs_table(cursor, request_ids)
    request_metrics = query_request_metrics_table(cursor, request_ids)
    pod_metrics = query_pod_metrics_table(cursor, start_time, end_time)

    return {
        "requests": requests,
        "application_logs": application_logs,
        "request_metrics": request_metrics,
        "pod_metrics": pod_metrics
    }

def collect_data(start_time, end_time):
    logger.info("Opening database connection")
    conn = sqlite3.connect("/home/djkoholic/Projects/SentinelOps/data-store/sentinelops.db")
    cursor = conn.cursor()
    data = query_database(cursor, start_time, end_time)
    conn.close()
    logger.info("Database connection closed")
    return data