# MovieVerse Incident Scenario

**Incident ID:** MV-INC-001

**Version:** 1.0

**Status:** Ground Truth

---

# Incident Overview

MovieVerse users begin reporting that movie recommendations are loading extremely slowly during the Monday evening peak.

The recommendation service remains available, but response latency increases dramatically and recommendation requests begin timing out. Some users receive empty recommendation carousels while others experience page load failures.

The incident is ultimately traced back to a recommendation feature cache configuration change combined with an unexpected increase in traffic from a newly released mobile application.

---

# Source Inspiration

Adapted from:

GitHub Engineering Incident (February 9)

Engineering Pattern:

Configuration Change + Traffic Growth + Cache Write Amplification + Database Overload

---

# Business Context

MovieVerse recently released:

- Recommendation Model v2.1
- MovieVerse Mobile App v5.4

To support rapid experimentation, engineers reduced the Recommendation Feature Cache refresh TTL from **12 hours** to **2 hours**.

At approximately the same time, the new mobile application unintentionally generated significantly more recommendation requests than previous versions.

Neither issue caused problems independently.

The combination of both caused the recommendation metadata database to become overloaded during peak evening traffic.

---

# Customer Impact

Users experience:

- Slow homepage loading
- Recommendation requests timing out
- Empty recommendation carousels
- Increased API failures

Business impact:

- Recommendation CTR drops
- Session abandonment increases
- Recommendation latency exceeds SLA

---

# Affected Components

## Primary

- Recommendation API
- Recommendation Metadata Database
- Recommendation Feature Cache

## Secondary

- User Profile Service
- Ranking Service
- Recommendation Gateway

---

# Ground Truth Root Cause

The Recommendation Feature Cache refresh TTL was reduced from 12 hours to 2 hours during deployment of Recommendation Model v2.1.

Simultaneously, MovieVerse Mobile App v5.4 generated approximately 8× more recommendation requests than anticipated.

During Monday evening peak traffic, the increased cache refresh frequency combined with elevated recommendation traffic overwhelmed the Recommendation Metadata Database.

The database became saturated, increasing latency throughout the recommendation pipeline.

---

# Timeline

## 17:00

System healthy.

Recommendation latency stable.

Database utilization normal.

---

## 17:15

Recommendation Model v2.1 deployed.

Recommendation Feature Cache TTL reduced:

12 hours

↓

2 hours

Deployment successful.

No immediate impact observed.

---

## 17:45

Traffic from MovieVerse Mobile App v5.4 begins increasing.

API request rate gradually rises.

No alerts triggered.

---

## 18:30

Peak evening traffic begins.

Recommendation request rate continues increasing.

Cache refresh operations become noticeably more frequent.

---

## 18:40

Database write throughput increases.

Recommendation metadata database CPU rises above 75%.

Connection pool utilization increases.

---

## 18:50

Database write latency increases.

Cache refresh requests begin queueing.

Recommendation API latency exceeds warning threshold.

---

## 18:55

Recommendation requests begin timing out.

Users report slow homepage loading.

5xx error rate increases.

---

## 19:05

Recommendation Metadata Database reaches connection limit.

Recommendation API experiences widespread failures.

---

## 19:20

Engineering investigation begins.

---

## 20:10

Recommendation Feature Cache TTL identified.

---

## 20:40

Unexpected mobile app traffic identified.

---

## 21:00

Cache TTL restored.

Traffic throttling enabled.

System gradually recovers.

---

# Expected Telemetry

## Metrics

Recommendation API

- recommendation_requests_total
- recommendation_latency_ms
- recommendation_error_rate

Database

- db_cpu_percent
- db_connection_count
- db_read_qps
- db_write_qps
- db_query_latency_ms

Cache

- cache_hit_rate
- cache_refresh_rate
- cache_evictions

Infrastructure

- pod_cpu_percent
- pod_memory_percent

Business

- recommendation_ctr
- homepage_load_time

---

# Expected Metric Behaviour

| Metric | Expected Behaviour |
|----------|-------------------|
| recommendation_requests_total | Gradual increase |
| recommendation_latency_ms | Sharp increase |
| recommendation_error_rate | Sharp increase |
| db_cpu_percent | Continuous increase |
| db_connection_count | Continuous increase |
| db_write_qps | Large increase |
| db_query_latency_ms | Continuous increase |
| cache_hit_rate | Gradual decrease |
| cache_refresh_rate | Large increase |
| recommendation_ctr | Decrease |

---

# Expected Logs

Recommendation Service

```
Recommendation request timeout
Retrying recommendation fetch
Database query exceeded timeout
Failed to retrieve recommendation features
```

Database

```
Connection pool exhausted
Slow query detected
Write timeout
Maximum connections reached
```

Cache

```
Refreshing recommendation features
Cache miss
Cache refresh timeout
```

Deployment

```
Recommendation Model v2.1 deployed
Recommendation Feature Cache TTL updated
```

---

# Alerts

Expected alerts include:

- Recommendation Latency High
- Database CPU High
- Database Connections High
- Recommendation Error Rate High
- Cache Hit Rate Low

---

# Expected Investigation Path

An experienced platform engineer should investigate in approximately this order:

1. Confirm user-facing impact.
2. Check recommendation latency.
3. Inspect recommendation error rate.
4. Check recommendation metadata database.
5. Observe elevated CPU.
6. Observe increased connection count.
7. Observe abnormal write throughput.
8. Inspect cache metrics.
9. Identify increased cache refresh frequency.
10. Review recent deployments.
11. Discover TTL configuration change.
12. Continue investigation.
13. Observe abnormal recommendation traffic.
14. Identify new mobile application rollout.
15. Correlate cache writes and increased traffic.
16. Conclude combined load caused database saturation.

---

# Recommended Resolution

Immediate

- Restore cache TTL.
- Throttle recommendation traffic.
- Increase database capacity.
- Flush unhealthy cache queues.

Long Term

- Isolate recommendation metadata database.
- Improve cache architecture.
- Introduce traffic shedding.
- Add deployment validation.
- Add alerts for cache refresh amplification.
- Improve recommendation service observability.

---

# Evaluation Criteria

SentinelOps should successfully identify:

✅ Recommendation latency increase

✅ Database overload

✅ Cache refresh amplification

✅ Recent configuration change

✅ Increased client traffic

✅ Combined causal relationship

The investigation should conclude that **no single component failed independently**; the outage resulted from multiple interacting changes that collectively exceeded the capacity of the recommendation platform.