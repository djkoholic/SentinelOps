POSSIBLE_HYPOTHESIS = {
    "user_input_issue":
        """
        The failures are caused by the requests themselves rather than the system.
        Users may be submitting off-topic questions, excessively long prompts,
        malformed requests, unsupported queries, or content that violates
        validation rules. The system is behaving correctly by rejecting these
        requests.
        """,

    "application_bug":
        """
        The failures are caused by a bug in the application code.
        Requests that should have succeeded are failing due to exceptions,
        incorrect business logic, validation bugs, integration issues,
        database errors, or unexpected edge cases in the implementation.
        """,

    "traffic_spike":
        """
        The failures are caused by an unusual increase in traffic volume.
        A sudden surge in requests may overwhelm the application, increase
        latency, exhaust resources, trigger rate limits, or cause request
        timeouts and degraded performance.
        """,

    "model_quality_issue":
        """
        The system is operational, but the model output quality is poor.
        Users may be dissatisfied with responses, confidence scores may be low,
        answers may be inaccurate or incomplete, or there may be a noticeable
        degradation in model performance despite successful request processing.
        """
}

POSSIBLE_ACTIONS = {
    "get_user_requests":
        """
        Retrieve the user requests that occurred during the investigation
        window. This action is useful for understanding what users were
        asking, identifying unusual request patterns, detecting off-topic
        questions, and investigating whether failures originated from the
        requests themselves.
        """,

    "get_application_logs":
        """
        Retrieve application logs generated during the investigation window.
        This action is useful for identifying exceptions, validation failures,
        stack traces, processing errors, warnings, and other events that can
        explain why requests failed or behaved unexpectedly.
        """,

    "get_request_metrics":
        """
        Retrieve request-level metrics for the investigation window.
        This action is useful for analyzing success rates, failure rates,
        latency, confidence scores, user satisfaction scores, throughput,
        and other indicators of application and model performance.
        """,

    "get_pod_metrics":
        """
        Retrieve infrastructure and pod-level metrics for the investigation
        window. This action is useful for detecting resource bottlenecks such
        as high CPU utilization, memory pressure, pod restarts, scaling
        events, and other infrastructure-related issues that may impact
        application performance.
        """
}

HYPOTHESIS_TO_TOOL_RANKED = {
    "user_input_issue": [
        "get_user_requests",
        "get_application_logs"
    ],

    "application_bug": [
        "get_application_logs",
        "get_request_metrics"
    ],

    "traffic_spike": [
        "get_request_metrics",
        "get_pod_metrics"
    ],

    "model_quality_issue": [
        "get_request_metrics",
        "get_user_requests"
    ]
}


ACTION_REGISTRY = {
    "get_user_requests": "requests",
    "get_application_logs": "application_logs",
    "get_request_metrics": "request_metrics",
    "get_pod_metrics": "pod_metrics"
}