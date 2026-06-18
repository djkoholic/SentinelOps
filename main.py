
from agents import parse_time_range, run_investigator
from data_collector import collect_data

if __name__ == '__main__':
    query = input("What is your query?\n")
    print(f"[DEBUG] User query: {query}")
    # User enters: Some of the requests between 11:30 to 12:00 PM Failed. Investigate what happened.
    # Agent queries the dataset first from 11:30 to 12:00 PM.
    # Agent analyzes the data and identifies the failed requests along with why they failed
    start_time, end_time = parse_time_range(query)
    print(f"[DEBUG] Parsed time range - Start: {start_time}, End: {end_time}")
    all_data = collect_data(start_time, end_time)
    print(f"[DEBUG] Collected data - Requests: {len(all_data['requests'])}, Logs: {len(all_data['application_logs'])}, Metrics: {len(all_data['request_metrics'])}")
    #context = build_context(all_data)
    answer = run_investigator(query, all_data)
    print("[DEBUG] Investigation complete")
    print()
    for key, value in answer.items():
        print(f"{key.upper()}:")
        print(value)
        print()