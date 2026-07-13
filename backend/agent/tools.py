import pandas as pd
from langchain_core.tools import tool

DATA_DIR = "/home/djkoholic/Projects/SentinelOps/MovieVerse/datasets"  # adjust to wherever the CSVs live

def _load_and_filter(filename: str, start_time, end_time) -> list[dict]:
    df = pd.read_csv(f"{DATA_DIR}/{filename}", index_col=0)  # index_col=0 drops the stray unnamed index column
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    start_t = start_time.time()
    end_t = end_time.time()

    mask = (df["timestamp"].dt.time >= start_t) & (df["timestamp"].dt.time <= end_t)
    return df.loc[mask].to_dict(orient="records")

def build_tools(start_time, end_time):
    """
    Builds the evidence-gathering toolset scoped to this investigation's time window.
    Called once per investigation (or once per evidence_gatherer call) — start_time/
    end_time are baked into the closure, NOT exposed as LLM-controlled arguments.
    The LLM should never get to pick the time range; that's Time_Parse_Node's job.
    """

    @tool
    def get_alerts() -> list[dict]:
        """Fetch alerts (severity, alert_name, component, description) fired during the incident window."""
        return _load_and_filter("alerts.csv", start_time, end_time)

    @tool
    def get_api_requests() -> list[dict]:
        """Fetch raw API request records (endpoint, status_code, response_time_ms, client_version) during the incident window."""
        return _load_and_filter("api_requests.csv", start_time, end_time)

    @tool
    def get_deployments() -> list[dict]:
        """Fetch deployment events (service, version, description) during the incident window."""
        return _load_and_filter("deployments.csv", start_time, end_time)

    @tool
    def get_logs() -> list[dict]:
        """Fetch service logs (service, level, message) during the incident window."""
        return _load_and_filter("logs.csv", start_time, end_time)

    @tool
    def get_metrics() -> list[dict]:
        """Fetch time-series metrics (component, metric_name, value, unit) during the incident window."""
        return _load_and_filter("metrics.csv", start_time, end_time)

    return [get_alerts, get_api_requests, get_deployments, get_logs, get_metrics]