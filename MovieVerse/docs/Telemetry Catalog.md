# Telemetry Catalog: MovieVerse Production Platform

**Author:** Senior Site Reliability Engineer / Observability Lead

**Scope:** Core Recommendation Engine Telemetry

**Purpose:** Define the canonical observability standard for metrics, logs, and distributed traces to enable SentinelOps (AI SRE) and human engineers to quickly diagnose production incidents.

---

# Frontend (Client Apps)

## Purpose

Render the UI, capture user telemetry, and initiate recommendation requests.

## Metrics

* **Metric Name:** `page_load_time_ms`
* **Description:** Total time taken to render the dashboard.
* **Type:** Histogram
* **Unit:** Milliseconds
* **Healthy Range:** P95 < 1200ms
* **Labels:** `client_type` (ios/android/web), `app_version`


* **Metric Name:** `client_error_count`
* **Description:** Count of unhandled exceptions or failed API calls on the client.
* **Type:** Counter
* **Unit:** Integer
* **Labels:** `error_type`, `client_type`, `app_version`



## Logs

* **Event:** Client API Error
* **Level:** ERROR
* **Example:** `Failed to fetch recommendations: HTTP 504 Gateway Timeout.`
* **Fields:** `user_id`, `client_type`, `app_version`, `endpoint`, `status_code`



## Distributed Traces

* **Span Name:** `user_interaction`
* **Parent Span:** None (Root Span)
* **Description:** Represents the user's action (e.g., "Load Dashboard").



## Debugging Value

Spikes in client errors with specific `app_version` labels indicate a bad frontend release. High page load times with normal backend latency indicate CDN, network, or heavy JS payload issues.

## Common Failure Signals

* **Bad Release:** `client_error_count` ↑ for a specific `app_version`.
* **Backend Down:** Client logs show massive spikes in `HTTP 5xx` errors.

---

# API Gateway

## Purpose

Single point of entry, routing, rate limiting, and SSL termination.

## Metrics

* **Metric Name:** `gateway_requests_total`
* **Description:** Total incoming HTTP requests.
* **Type:** Counter
* **Unit:** Requests
* **Labels:** `method`, `route`, `status_code`


* **Metric Name:** `gateway_request_duration_ms`
* **Description:** End-to-end latency from gateway perspective.
* **Type:** Histogram
* **Unit:** Milliseconds
* **Healthy Range:** P95 < 300ms
* **Labels:** `route`


* **Metric Name:** `rate_limit_drops_total`
* **Description:** Requests dropped due to rate limiting.
* **Type:** Counter
* **Unit:** Requests
* **Labels:** `client_ip`



## Logs

* **Event:** Access Log
* **Level:** INFO
* **Example:** `GET /api/v1/recommendations 200 OK 245ms`
* **Fields:** `trace_id`, `method`, `path`, `status_code`, `latency_ms`, `user_agent`, `client_ip`


* **Event:** Rate Limit Exceeded
* **Level:** WARN
* **Example:** `Rate limit exceeded for IP 192.168.1.50 on /api/v1/recommendations`
* **Fields:** `client_ip`, `route`, `limit_threshold`



## Distributed Traces

* **Span Name:** `api_gateway_request`
* **Parent Span:** `user_interaction` (from client)
* **Description:** The gateway's processing time, including routing and rate limiting.



## Debugging Value

The gateway is the ultimate truth for user-facing latency and error rates. If gateway latency is high but backend latency is low, the issue is at the network/proxy layer.

## Common Failure Signals

* **DDoS / Aggressive Scraping:** `rate_limit_drops_total` ↑↑
* **Backend Outage:** `gateway_requests_total` with `status_code="502" or "504"` ↑

---

# Authentication Service

## Purpose

Verify user identity and issue/validate tokens.

## Metrics

* **Metric Name:** `token_validation_latency_ms`
* **Description:** Time taken to validate a JWT.
* **Type:** Histogram
* **Unit:** Milliseconds
* **Healthy Range:** P99 < 15ms
* **Labels:** `auth_provider`


* **Metric Name:** `auth_failures_total`
* **Description:** Number of failed authentication attempts.
* **Type:** Counter
* **Unit:** Requests
* **Labels:** `failure_reason` (expired, invalid_signature, revoked)



## Logs

* **Event:** Token Validation Failed
* **Level:** WARN
* **Example:** `JWT validation failed: signature expired.`
* **Fields:** `trace_id`, `user_id`, `failure_reason`



## Distributed Traces

* **Span Name:** `validate_token`
* **Parent Span:** `api_gateway_request`
* **Description:** Time spent validating the user's JWT before routing.



## Debugging Value

Helps isolate if "unauthorized" errors are due to expired tokens, bad client configurations, or an outage of the 3rd-party auth provider.

## Common Failure Signals

* **Auth Provider Down:** `token_validation_latency_ms` ↑ and logs show "Provider Timeout".

---

# Recommendation Service (Orchestrator)

## Purpose

Orchestrate the multi-stage recommendation pipeline.

## Metrics

* **Metric Name:** `recommendation_pipeline_latency_ms`
* **Description:** Total time to execute the end-to-end pipeline.
* **Type:** Histogram
* **Unit:** Milliseconds
* **Healthy Range:** P95 < 250ms
* **Labels:** `fallback_triggered` (true/false)


* **Metric Name:** `pipeline_fallback_count`
* **Description:** Number of times the ML pipeline failed and static "popular" movies were served.
* **Type:** Counter
* **Unit:** Requests
* **Labels:** `failure_stage` (candidate_gen, ranking, feature_store)



## Logs

* **Event:** Pipeline Fallback Triggered
* **Level:** ERROR
* **Example:** `Recommendation pipeline failed at ranking stage. Serving fallback popular movies.`
* **Fields:** `trace_id`, `user_id`, `failure_stage`, `error_message`



## Distributed Traces

* **Span Name:** `recommendation_pipeline` (Parent: `api_gateway_request`)
* **Child Spans:** `fetch_features`, `generate_candidates`, `rank_candidates`, `apply_rules`, `hydrate_metadata`



## Debugging Value

As the orchestrator, its traces show exactly which downstream service is causing a bottleneck. The `pipeline_fallback_count` is the primary business health metric.

## Common Failure Signals

* **Downstream Timeout:** `recommendation_pipeline_latency_ms` hits exactly 250ms (timeout config), `pipeline_fallback_count` ↑, CPU is normal.

---

# Candidate Generation Service

## Purpose

Quickly narrow down the full catalog to a manageable subset using an ANN index.

## Metrics

* **Metric Name:** `ann_index_query_latency_ms`
* **Description:** Time to retrieve nearest neighbors from the index.
* **Type:** Histogram
* **Unit:** Milliseconds
* **Healthy Range:** P99 < 50ms


* **Metric Name:** `empty_candidate_list_total`
* **Description:** Count of queries that returned 0 candidates.
* **Type:** Counter
* **Unit:** Requests



## Logs

* **Event:** Empty Candidates Returned
* **Level:** WARN
* **Example:** `ANN index returned 0 candidates for user embedding.`
* **Fields:** `trace_id`, `user_id`, `index_version`



## Distributed Traces

* **Span Name:** `generate_candidates` (Parent: `recommendation_pipeline`)
* **Span Name:** `query_ann_index` (Parent: `generate_candidates`)

## Debugging Value

High latency indicates index bloat or memory pressure. Empty candidate lists indicate a failure to sync vectors or a cold-start logic failure.

## Common Failure Signals

* **Index Sync Failure:** `empty_candidate_list_total` ↑ after a scheduled index update.

---

# Ranking Service

## Purpose

Predict user engagement probability for candidates by calling the Model Serving Platform.

## Metrics

* **Metric Name:** `ranking_latency_ms`
* **Description:** Time spent scoring the candidate list.
* **Type:** Histogram
* **Unit:** Milliseconds
* **Healthy Range:** P95 < 100ms
* **Labels:** `model_version`, `batch_size`


* **Metric Name:** `ranking_errors_total`
* **Description:** Failures during the ranking process.
* **Type:** Counter
* **Unit:** Requests
* **Labels:** `error_type` (timeout, invalid_features)



## Logs

* **Event:** Ranking Failed
* **Level:** ERROR
* **Example:** `Failed to rank candidates: Model serving timeout after 100ms.`
* **Fields:** `trace_id`, `model_version`, `candidate_count`



## Distributed Traces

* **Span Name:** `rank_candidates` (Parent: `recommendation_pipeline`)
* **Span Name:** `call_model_serving` (Parent: `rank_candidates`)

## Debugging Value

Separates business logic errors in ranking from pure ML inference errors.

## Common Failure Signals

* **Feature Mismatch:** `ranking_errors_total` ↑ with `error_type="invalid_features"` right after a new model deployment.

---

# Business Rules Engine

## Purpose

Apply product and compliance rules to the ranked list.

## Metrics

* **Metric Name:** `rules_evaluation_latency_ms`
* **Description:** Time to apply all filters.
* **Type:** Histogram
* **Unit:** Milliseconds
* **Healthy Range:** P99 < 15ms


* **Metric Name:** `items_filtered_total`
* **Description:** Number of movies dropped from the ranked list.
* **Type:** Counter
* **Unit:** Items
* **Labels:** `rule_name` (already_watched, age_restricted)



## Logs

* **Event:** Rule Triggered
* **Level:** DEBUG
* **Example:** `Dropped movie_id 9923: Failed age_restricted rule.`
* **Fields:** `trace_id`, `user_id`, `movie_id`, `rule_name`



## Distributed Traces

* **Span Name:** `apply_business_rules` (Parent: `recommendation_pipeline`)

## Debugging Value

If users complain about bad or repetitive recommendations, checking `items_filtered_total` can reveal if the `already_watched` rule is failing or if catalog starvation is occurring.

## Common Failure Signals

* **Profile Fetch Failure:** All rules pass unconditionally because the user profile (watch history) couldn't be loaded, resulting in users seeing movies they already watched.

---

# User Profile Service

## Purpose

Serve real-time user state (watch history, explicit preferences).

## Metrics

* **Metric Name:** `profile_fetch_latency_ms`
* **Description:** Latency of fetching user profile from DB.
* **Type:** Histogram
* **Unit:** Milliseconds
* **Healthy Range:** P95 < 20ms


* **Metric Name:** `profile_not_found_total`
* **Description:** Count of requested profiles that do not exist.
* **Type:** Counter
* **Unit:** Requests



## Logs

* **Event:** Database Connection Error
* **Level:** ERROR
* **Example:** `Failed to connect to primary DB pool.`
* **Fields:** `trace_id`, `db_host`



## Distributed Traces

* **Span Name:** `fetch_user_profile` (Parent: `apply_business_rules`)

## Debugging Value

Identifies state storage bottlenecks. High DB query latency usually points to missing indexes, lock contention, or connection pool exhaustion.

## Common Failure Signals

* **Database Overload:** `profile_fetch_latency_ms` ↑↑, connection timeout logs appear.

---

# Feature Store

## Purpose

Serve low-latency ML features for online inference.

## Metrics

* **Metric Name:** `feature_lookup_latency_ms`
* **Description:** Time to fetch feature vectors from online storage.
* **Type:** Histogram
* **Unit:** Milliseconds
* **Healthy Range:** P99 < 10ms


* **Metric Name:** `null_feature_rate`
* **Description:** Percentage of lookups returning null/missing features.
* **Type:** Gauge
* **Unit:** Percent
* **Labels:** `feature_namespace`



## Logs

* **Event:** Features Missing
* **Level:** WARN
* **Example:** `Missing real-time features for user_id 4412.`
* **Fields:** `trace_id`, `user_id`, `feature_namespace`



## Distributed Traces

* **Span Name:** `fetch_features` (Parent: `recommendation_pipeline` or `rank_candidates`)

## Debugging Value

A high `null_feature_rate` is the #1 cause of degraded ML model performance. It indicates that the streaming pipeline updating the Feature Store is lagging or broken.

## Common Failure Signals

* **Stale Features:** Kafka consumer lag (in Event Bus) causes Feature Store updates to delay, resulting in users seeing stale recommendations. `null_feature_rate` ↑.

---

# Movie Metadata Database

## Purpose

Store and serve factual data about movies (title, cast, poster URL).

## Metrics

* **Metric Name:** `metadata_query_latency_ms`
* **Description:** Database query execution time.
* **Type:** Histogram
* **Unit:** Milliseconds
* **Healthy Range:** P95 < 15ms



## Logs

* **Event:** Metadata Missing
* **Level:** ERROR
* **Example:** `Requested metadata for movie_id 8821 but not found in DB.`
* **Fields:** `trace_id`, `movie_id`



## Distributed Traces

* **Span Name:** `hydrate_metadata` (Parent: `recommendation_pipeline`)

## Debugging Value

Identifies if the 3rd-party catalog sync is failing, leaving valid candidate IDs without titles/posters.

## Common Failure Signals

* **Sync Failure:** Logs show "Metadata Missing" for newly released movies.

---

# Redis Cache

## Purpose

Reduce latency and DB/Model load for repetitive requests.

## Metrics

* **Metric Name:** `cache_hit_rate`
* **Description:** Percentage of cache hits vs total requests.
* **Type:** Gauge
* **Unit:** Percent
* **Healthy Range:** > 60%


* **Metric Name:** `cache_memory_usage_bytes`
* **Description:** Total memory consumed by Redis.
* **Type:** Gauge
* **Unit:** Bytes


* **Metric Name:** `cache_evictions_total`
* **Description:** Keys evicted due to maxmemory policies.
* **Type:** Counter
* **Unit:** Keys



## Logs

* **Event:** Redis OOM Warning
* **Level:** WARN
* **Example:** `Redis approaching maxmemory limit (95%). Evictions starting.`
* **Fields:** `memory_percent`, `eviction_policy`



## Distributed Traces

* **Span Name:** `redis_get` / `redis_set` (Parents: `recommendation_pipeline`, `fetch_features`)

## Debugging Value

Cache hit rate directly inversely correlates with pipeline latency and infrastructure cost.

## Common Failure Signals

* **Cache Stampede:** `cache_hit_rate` drops to 0%, backend CPU spikes to 100%, and latencies skyrocket across all services.
* **OOM/Evictions:** `cache_evictions_total` ↑ indicates the cluster needs to be scaled up.

---

# Event Bus (Kafka)

## Purpose

Asynchronous transport for telemetry, clicks, and state changes.

## Metrics

* **Metric Name:** `kafka_consumer_lag`
* **Description:** Number of messages behind the head of the partition.
* **Type:** Gauge
* **Unit:** Messages
* **Labels:** `topic`, `consumer_group`


* **Metric Name:** `kafka_bytes_in_per_sec`
* **Description:** Throughput of incoming messages.
* **Type:** Gauge
* **Unit:** Bytes/second



## Logs

* **Event:** Consumer Rebalance
* **Level:** INFO
* **Example:** `Consumer group feature-updater rebalancing partitions.`
* **Fields:** `consumer_group`, `topic`



## Distributed Traces

* **Span Name:** `publish_event` (Parent: `user_interaction` via API)
* **Span Name:** `consume_event` (Async, no trace parent)

## Debugging Value

Consumer lag is the critical health metric for the asynchronous platform. High lag means real-time features and analytics are delayed.

## Common Failure Signals

* **Hot Partition:** `kafka_consumer_lag` spikes for a single partition while others are fine, usually due to a bad partitioning key (e.g., all traffic routing to one movie ID).

---

# Offline Training Pipeline

## Purpose

Train and evaluate new ML models on historical data.

## Metrics

* **Metric Name:** `training_job_duration_seconds`
* **Description:** Total time for the nightly batch training job.
* **Type:** Gauge
* **Unit:** Seconds


* **Metric Name:** `model_offline_ndcg`
* **Description:** Normalized Discounted Cumulative Gain (ranking quality metric) on holdout data.
* **Type:** Gauge
* **Unit:** Float



## Logs

* **Event:** Data Drift Detected
* **Level:** WARN
* **Example:** `Feature distribution for user_age shifted by > 15% compared to baseline.`
* **Fields:** `feature_name`, `drift_score`



## Distributed Traces

*(Not typically traced with distributed tracing; monitored via DAG/Workflow orchestrator metrics)*

## Debugging Value

If offline metrics drop suddenly, upstream ETL jobs likely produced corrupted features or data drift occurred.

## Common Failure Signals

* **Failed Training:** `model_offline_ndcg` drops below the deployment threshold, preventing the pipeline from registering a new model version.

---

# Model Registry

## Purpose

Version control and artifact storage for ML models.

## Metrics

* **Metric Name:** `model_download_latency_ms`
* **Description:** Time taken for the serving platform to pull an artifact.
* **Type:** Histogram
* **Unit:** Milliseconds
* **Healthy Range:** Depends on size, generally < 5000ms



## Logs

* **Event:** Model Promoted
* **Level:** INFO
* **Example:** `Model ranking_v1.4 promoted to production.`
* **Fields:** `model_name`, `version`, `author`



## Distributed Traces

* **Span Name:** `download_model_artifact` (Parent: Serving pod startup)

## Debugging Value

Tracks the exact lifecycle of ML artifacts. Correlating a "Model Promoted" log timestamp with an increase in `ranking_errors_total` instantly identifies a bad model deployment.

## Common Failure Signals

* **Storage Outage:** `model_download_latency_ms` times out, causing new Model Serving pods to CrashLoopBackOff during scaling events.

---

# Model Serving Platform

## Purpose

Host ML models and expose them for real-time inference.

## Metrics

* **Metric Name:** `inference_latency_ms`
* **Description:** Raw execution time of the tensor graph.
* **Type:** Histogram
* **Unit:** Milliseconds
* **Healthy Range:** P95 < 40ms
* **Labels:** `model_name`, `version`


* **Metric Name:** `gpu_utilization_percent`
* **Description:** Percentage of GPU compute capacity used.
* **Type:** Gauge
* **Unit:** Percent



## Logs

* **Event:** Input Shape Mismatch
* **Level:** ERROR
* **Example:** `Inference failed: Expected input shape (batch, 128), got (batch, 64).`
* **Fields:** `trace_id`, `model_name`, `version`, `expected_shape`, `actual_shape`



## Distributed Traces

* **Span Name:** `execute_tensor_graph` (Parent: `call_model_serving`)

## Debugging Value

Critical for ML operations. GPU utilization near 100% paired with high latency means horizontal pod autoscaling needs to trigger.

## Common Failure Signals

* **Resource Starvation:** `inference_latency_ms` ↑ smoothly as `gpu_utilization_percent` hits 100%.
* **Incompatible Deployment:** Heavy spikes in "Input Shape Mismatch" logs immediately after a Feature Store schema update or new model rollout.