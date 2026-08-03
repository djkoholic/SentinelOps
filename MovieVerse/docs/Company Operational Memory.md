## 1. Product Overview

MovieVerse is an AI-powered movie recommendation platform that operates as a real-time discovery engine rather than a streaming service. It dynamically updates user profiles based on continuous activity ingestion to serve highly personalized movie suggestions. The platform supports approximately 500,000 monthly active users and relies on a multi-stage machine learning pipeline to generate, rank, and filter recommendations.

---

## 2. Core Components

* **API Gateway**
* **Purpose:** Single point of entry, handles routing, rate limiting, and SSL termination.


* **Major responsibilities:** Intercepts client requests, validates tokens, applies rate limits, and routes to microservices.


* **Upstream:** Frontend Client Apps.


* **Downstream:** Authentication Service, Recommendation Service, Event Bus.




* **Authentication Service**
* **Purpose:** Verifies user identity and validates tokens.


* **Major responsibilities:** Issues and validates JWTs.


* **Upstream:** API Gateway.


* **Downstream:** External Auth Provider.




* **Recommendation Service (Orchestrator)**
* **Purpose:** Orchestrates the multi-stage recommendation pipeline.


* **Major responsibilities:** Checks cache, coordinates user profile fetches, candidate generation, ranking, rule application, and metadata hydration.


* **Upstream:** API Gateway.


* **Downstream:** Redis Cache, User Profile Service, Feature Store, Candidate Generation Service, Ranking Service, Business Rules Engine, Movie Metadata Database.




* **Candidate Generation Service**
* **Purpose:** Narrows down the full movie catalog to a subset of ~500 relevant candidates.


* **Major responsibilities:** Queries an Approximate Nearest Neighbor (ANN) index using user embeddings.


* **Upstream:** Recommendation Service.


* **Downstream:** Vector Index / Nearest Neighbor Cache.




* **Ranking Service & Model Serving Platform**
* **Purpose:** Predicts user engagement probability for candidates and hosts ML models for real-time inference.


* **Major responsibilities:** Fetches movie features, scores candidates using deployed ML models, and sorts the list.


* **Upstream:** Recommendation Service.


* **Downstream:** Feature Store, Model Registry.




* **Business Rules Engine**
* **Purpose:** Applies product and compliance rules to recommendations.


* **Major responsibilities:** Filters watched content, enforces age restrictions, and applies diversity constraints.


* **Upstream:** Recommendation Service.


* **Downstream:** User Profile Service.




* **Feature Store**
* **Purpose:** Serves low-latency ML features for online inference.


* **Major responsibilities:** Provides real-time user and movie feature vectors.


* **Upstream:** Recommendation Service, Ranking Service.


* **Downstream:** Event Bus (streaming updates), Data Warehouse (batch updates).




* **User Profile Service**
* **Purpose:** Serves real-time user state.


* **Major responsibilities:** Provides watch history and explicit preferences.


* **Upstream:** Recommendation Service, Business Rules Engine.


* **Downstream:** Primary transactional database.




* **Event Bus (Kafka)**
* **Purpose:** Provides asynchronous transport for telemetry, clicks, and state changes.


* **Major responsibilities:** Streams user events to the Data Lake and streaming feature pipelines.


* **Upstream:** API Gateway, Frontend.


* **Downstream:** Feature Store, Data Lake.




* **Redis Cache**
* **Purpose:** Reduces latency and load for repetitive requests.


* **Major responsibilities:** Stores pre-computed or recently served recommendations.


* **Upstream:** Recommendation Service.


* **Downstream:** None.





---

## 3. Critical User Flows

### Core Recommendation Discovery Flow

* **User Client → API Gateway:** The user loads the dashboard, triggering a `GET /recommendations` request that the gateway intercepts for JWT validation and rate limiting.


* **API Gateway → Recommendation Service:** The gateway routes the request to the orchestrator, which first checks the Redis Cache for an existing response.


* **Recommendation Service → User Profile & Feature Store:** On a cache miss, the orchestrator retrieves the user's historical state and ML context.


* **Recommendation Service → Candidate Generation:** The orchestrator requests ~500 highly relevant candidate movie IDs based on the user's vector.


* **Recommendation Service → Ranking Service (Model Serving):** The candidate IDs and user features are scored and sorted by the champion ML model.


* **Recommendation Service → Business Rules Engine:** The ranked list is filtered to remove watched movies or age-restricted content.


* **Recommendation Service → Movie Metadata DB → Redis Cache → User:** The final IDs are hydrated with factual metadata, cached in Redis, and returned as a JSON payload to the client.



### Asynchronous Telemetry & Feature Update Flow

* **User Client → API Gateway → Event Bus (Kafka):** User interactions (clicks, watches, ignores) are captured and pushed to the async transport.


* **Event Bus → Feature Store & Data Lake:** Events update the user's real-time features in the Feature Store and sink into the Data Lake for offline model training.



---

## 4. Important Telemetry

### API Gateway

* **Metrics:** `gateway_request_duration_ms` (P95 < 300ms), `gateway_requests_total`, `rate_limit_drops_total`.


* **Logs:** Access Logs (HTTP status, latency), Rate Limit Exceeded warnings.



### Recommendation Service (Orchestrator)

* **Metrics:** `recommendation_pipeline_latency_ms` (P95 < 250ms), `pipeline_fallback_count`.


* **Logs:** Pipeline Fallback Triggered errors.


* **Traces:** `recommendation_pipeline` (Parent span identifying bottlenecks).



### Ranking Service & Model Serving

* **Metrics:** `ranking_latency_ms` (P95 < 100ms), `inference_latency_ms` (P95 < 40ms), `ranking_errors_total`, `gpu_utilization_percent`.


* **Logs:** Input Shape Mismatch errors, Ranking Failed timeouts.



### Feature Store

* **Metrics:** `feature_lookup_latency_ms` (P99 < 10ms), `null_feature_rate`.


* **Logs:** Features Missing warnings.



### Redis Cache

* **Metrics:** `cache_hit_rate` (Healthy > 60%), `cache_evictions_total`.


* **Logs:** Redis OOM Warnings.



### Event Bus (Kafka)

* **Metrics:** `kafka_consumer_lag`.



---

## 5. Known Failure Modes

### Downstream Dependency Cascade

* **Symptoms:** High pipeline latency resulting in the system serving static "popular" fallback movies.


* **Components Involved:** Recommendation Service, Candidate Gen, Ranking Service.


* **Telemetry Confirmation:** `recommendation_pipeline_latency_ms` hitting exactly 250ms (timeout) combined with a spike in `pipeline_fallback_count`.



### Model Deployment Regression / Shape Mismatch

* **Symptoms:** Complete failure of the ranking stage immediately following a deployment.


* **Components Involved:** Ranking Service, Model Serving Platform.


* **Telemetry Confirmation:** Spikes in `ranking_errors_total` with `error_type="invalid_features"` and "Input Shape Mismatch" logs from the inference server.



### GPU Resource Starvation

* **Symptoms:** Slow recommendation rendering due to inference timeouts.


* **Components Involved:** Model Serving Platform.


* **Telemetry Confirmation:** `gpu_utilization_percent` reaches 100% and `inference_latency_ms` increases smoothly.



### Stale Recommendations / Feature Store Lag

* **Symptoms:** Users receive stale recommendations because real-time behaviors are not updating the model context.


* **Components Involved:** Event Bus (Kafka), Feature Store.


* **Telemetry Confirmation:** A spike in `kafka_consumer_lag` paired with an increasing `null_feature_rate`.



### Cache Stampede

* **Symptoms:** Backend CPU spikes to 100% and latencies skyrocket across all services due to mass expiration or eviction.


* **Components Involved:** Redis Cache, Recommendation Service, Core Databases.


* **Telemetry Confirmation:** `cache_hit_rate` drops to 0% alongside increases in `cache_evictions_total` and Redis OOM logs.



### Candidate Index Sync Failure

* **Symptoms:** Users receive empty recommendation blocks or highly degraded fallback content.


* **Components Involved:** Candidate Generation Service.


* **Telemetry Confirmation:** `empty_candidate_list_total` spikes immediately following a scheduled vector index update.



---

## 6. Investigation Heuristics

* **(Inferred Heuristic):** If `gateway_request_duration_ms` is high but backend traces (like `recommendation_pipeline_latency_ms`) remain normal, isolate the investigation to the API Gateway, SSL layers, or network ingress.


* **(Inferred Heuristic):** If the Recommendation Service triggers a high `pipeline_fallback_count`, immediately check OpenTelemetry traces starting with `recommendation_pipeline` to pinpoint whether Candidate Generation or Ranking caused the 250ms timeout.


* **(Inferred Heuristic):** If `null_feature_rate` is increasing, check `kafka_consumer_lag` before debugging the Feature Store; the streaming ingestion pipeline is likely broken or lagging.


* **(Inferred Heuristic):** If ML models are returning generic predictions or throwing inference errors shortly after a feature schema update or model rollout, check Model Serving logs for "Input Shape Mismatch" and prepare to roll back the model in the Model Registry.


* **(Inferred Heuristic):** If users complain about repetitive recommendations but infrastructure latency is healthy, check the Business Rules Engine's `items_filtered_total` metric. If it drops to zero, the `already_watched` rule is failing, likely due to a User Profile Service database timeout.



---

## 7. Operational Notes

* **Graceful Degradation:** The platform is designed to fail open. If candidate generation, ranking, or feature fetches fail or exceed the 250ms timeout budget, the Recommendation Service will catch the error and serve a static list of popular movies to maintain uptime.


* **Single Source of Traceability:** Every request is stamped with an OpenTelemetry Trace ID at the API Gateway, which is passed through HTTP/gRPC headers to all downstream components. Use this Trace ID in the observability platform to visualize the exact request path and identify microservice bottlenecks.


* **Feedback Loop Criticality:** The ML models rely entirely on the Event Bus to capture user telemetry (clicks, watch times) alongside `recommendation_id`s. If Kafka or the Data Lake ingestion breaks, it will silently degrade offline model training and future production accuracy, even if real-time APIs remain healthy.