import pandas as pd
from langchain_core.tools import tool

DATA_DIR = "/home/djkoholic/Projects/SentinelOps/MovieVerse/datasets"


def _load_and_filter(filename: str, start_time, end_time, filters: dict | None = None) -> list[dict]:
    df = pd.read_csv(f"{DATA_DIR}/{filename}", index_col=0)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    start_t = start_time.time()
    end_t = end_time.time()
    mask = (df["timestamp"].dt.time >= start_t) & (df["timestamp"].dt.time <= end_t)

    if filters:
        for col, val in filters.items():
            if val is not None:
                mask &= (df[col] == val)

    return df.loc[mask].to_dict(orient="records")


def build_tools(start_time, end_time):
    """
    Builds the evidence-gathering toolset scoped to this investigation's time window.
    start_time/end_time are baked into the closure, NOT exposed as LLM-controlled
    arguments — the LLM should never pick the time range, that's Time_Parse_Node's job.
    All other filters below ARE LLM-controlled, to let it narrow evidence instead of
    always pulling the entire window.
    """

    @tool
    def get_alerts(component: str | None = None, severity: str | None = None) -> list[dict]:
        """
        Fetch alerts raised during the incident window.

        Args:
            component: Filter to one component. Valid values: "recommendation-db",
                "recommendation-api", "recommendation-cache". Omit to get all components.
            severity: Filter to one severity level. Valid values: "WARN", "CRITICAL".
                Omit to get all severities.
        """
        return _load_and_filter("alerts.csv", start_time, end_time, {
            "component": component,
            "severity": severity,
        })

    @tool
    def get_api_requests(status_code: int | None = None, min_response_time_ms: float | None = None) -> list[dict]:
        """
        Fetch raw API request records for the /api/v1/recommendations endpoint.

        Args:
            status_code: Filter to one HTTP status code, e.g. 200, 500, 504.
                Omit to get all status codes.
            min_response_time_ms: Only return requests slower than this threshold,
                in milliseconds. Use this to find slow/degraded requests instead of
                pulling every request in the window. Omit to get all requests.
        """
        df = pd.read_csv(f"{DATA_DIR}/api_requests.csv", index_col=0)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        start_t, end_t = start_time.time(), end_time.time()
        mask = (df["timestamp"].dt.time >= start_t) & (df["timestamp"].dt.time <= end_t)

        if status_code is not None:
            mask &= (df["status_code"] == status_code)
        if min_response_time_ms is not None:
            mask &= (df["response_time_ms"] >= min_response_time_ms)

        return df.loc[mask].to_dict(orient="records")

    @tool
    def get_deployments(service: str | None = None) -> list[dict]:
        """
        Fetch deployment/config-change events during the incident window.

        Args:
            service: Filter to one service. Valid values: "recommendation-api",
                "recommendation-cache", "mobile-client-app". Omit to get all services.
        """
        return _load_and_filter("deployments.csv", start_time, end_time, {
            "service": service,
        })

    @tool
    def get_logs(service: str | None = None, level: str | None = None) -> list[dict]:
        """
        Fetch service logs during the incident window.

        Args:
            service: Filter to one service. Valid values: "recommendation-api",
                "recommendation-cache", "recommendation-db". Omit to get all services.
            level: Filter to one log level, e.g. "INFO", "WARN", "ERROR". Omit to get
                all levels. Prefer filtering to "ERROR" or "WARN" first if you're
                looking for problems, rather than pulling all logs including routine INFO.
        """
        return _load_and_filter("logs.csv", start_time, end_time, {
            "service": service,
            "level": level,
        })

    @tool
    def get_metrics(component: str | None = None, metric_name: str | None = None) -> list[dict]:
        """
        Fetch time-series metrics during the incident window. This dataset is large —
        always filter by component and/or metric_name rather than fetching everything.

        Args:
            component: Filter to one component. Valid values: "business",
                "ranking-service", "recommendation-api", "recommendation-cache",
                "recommendation-db". Omit to get all components (not recommended,
                very large).
            metric_name: Filter to one specific metric. Valid values depend on
                component:
                - business: "recommendation_ctr", "homepage_load_time"
                - ranking-service: "pod_cpu_percent", "pod_memory_percent"
                - recommendation-api: "recommendation_requests_total",
                  "recommendation_latency_ms", "recommendation_error_rate"
                - recommendation-cache: "cache_hit_rate", "cache_refresh_rate",
                  "cache_evictions"
                - recommendation-db: "db_cpu_percent", "db_connection_count",
                  "db_read_qps", "db_write_qps", "db_query_latency_ms"
                Omit to get all metrics for the given component.
        """
        return _load_and_filter("metrics.csv", start_time, end_time, {
            "component": component,
            "metric_name": metric_name,
        })

    return [get_alerts, get_api_requests, get_deployments, get_logs, get_metrics]