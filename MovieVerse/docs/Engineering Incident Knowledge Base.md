# Engineering Incident Knowledge Base (EIKB)

**Version:** 1.0

**Purpose**

This document serves as the engineering knowledge repository used to construct realistic failure scenarios for SentinelOps.

Rather than inventing synthetic incidents, SentinelOps derives its scenarios from real production incidents published by engineering organizations. Each incident is translated into the context of the target product (MovieVerse in Phase 1) while preserving the underlying engineering failure pattern.

The goal is not to replicate another company's infrastructure but to capture how experienced engineers investigate failures in real systems.

---

# Incident EIKB-001

## Source

**Company:** GitHub

**Incident Date:** February 9

**Source Type:** Public Engineering Postmortem

---

# Incident Summary

A production database responsible for authentication and user management became overloaded during peak traffic.

The outage was not caused by a single failure but by multiple independent changes that interacted unexpectedly:

- A new client application generated over 10× more read traffic than expected.
- A cache refresh TTL was reduced from 12 hours to 2 hours during a model rollout.
- Monday morning peak traffic amplified both effects.
- The combined read and write load overwhelmed the database cluster.
- Dependent services experienced cascading failures.

---

# Engineering Pattern

**Category**

Database Overload

**Failure Pattern**

Configuration Change + Traffic Growth + Architectural Coupling

---

# Root Cause

A reduction in cache TTL significantly increased database write traffic while newly released client applications simultaneously generated an unexpected increase in read traffic.

The database cluster exceeded its operating capacity under normal peak production load.

---

# Contributing Factors

- Unexpected increase in client read traffic
- Cache refresh frequency increased by 6×
- Peak weekday traffic
- Recent model rollout
- Shared database serving multiple critical services
- Lack of early warning metrics
- Limited traffic shedding mechanisms

---

# User Impact

- Authentication failures
- User management unavailable
- Multiple downstream services affected
- Elevated latency
- Increased request failures

---

# Engineering Investigation

An engineer investigating the incident would likely follow a workflow similar to:

1. Observe elevated user-facing errors.
2. Check request latency.
3. Observe database latency increase.
4. Check database CPU utilization.
5. Inspect database connection count.
6. Observe abnormal write volume.
7. Inspect cache metrics.
8. Identify unusually frequent cache refreshes.
9. Investigate recent configuration changes.
10. Discover reduced cache TTL.
11. Observe read traffic continuing to increase.
12. Analyze API request volume.
13. Identify newly released client applications generating unexpected traffic.
14. Confirm combined read/write amplification as the root cause.

---

# Observable Symptoms

## Metrics

- API latency ↑
- Database CPU ↑
- Database connection count ↑
- Database write QPS ↑
- Database read QPS ↑
- Cache refresh rate ↑
- Cache hit rate ↓
- Request error rate ↑

---

## Logs

Possible log messages include:

- Database connection timeout
- Connection pool exhausted
- Query timeout
- Cache refresh timeout
- Retry attempts exceeded
- Request deadline exceeded

---

# Resolution

Immediate

- Reduce incoming traffic.
- Restore previous cache TTL.
- Block excessive client traffic.
- Increase database capacity.

Long Term

- Redesign cache architecture.
- Separate critical databases.
- Improve load shedding.
- Improve observability.
- Improve capacity planning.
- Increase architectural isolation.

---

# Prevention

- Better monitoring of cache write amplification
- Early detection of abnormal client traffic
- Capacity validation before rollout
- Canary configuration deployments
- Better dependency isolation
- Automated load shedding

---

# Translation Notes (MovieVerse)

This incident will later be adapted into the MovieVerse domain.

GitHub Components

- Authentication Database
- User Settings Cache
- GitHub Client Applications

MovieVerse Equivalent

- Recommendation Metadata Database
- Recommendation Feature Cache
- MovieVerse Mobile Application

The engineering failure remains identical while the business context changes.

---

# Telemetry Requirements

This incident requires the following telemetry to be available:

Metrics

- recommendation_latency_ms
- recommendation_requests_total
- database_cpu_percent
- database_connection_count
- database_read_qps
- database_write_qps
- cache_hit_rate
- cache_refresh_rate
- cache_evictions
- api_error_rate

Logs

- recommendation-service
- cache-service
- recommendation-db
- api-gateway

---

# Difficulty

Medium

Requires correlating multiple independent signals rather than identifying a single failing component.

---

# SentinelOps Learning Objective

SentinelOps should learn that:

- Multiple small changes can combine into a large production failure.
- The first symptom is not necessarily the root cause.
- Engineers must correlate metrics across multiple services.
- Configuration changes should always be considered during investigation.
- Infrastructure failures often propagate through shared dependencies.