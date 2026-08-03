# Role 1 Demo Guide - Architecte solution

Use this during the oral defense. Your job is to defend the big-picture
architecture: objectives, constraints, context, and solution strategy.

## My Role

I am responsible for:

- Sections 1 to 4 of Arc42
- 4+1: use-case view and macro logical view
- system goals, constraints, context, and solution strategy
- why Phase 2 moves from mostly synchronous REST to event-driven collaboration

My key idea:

> I defend why this architecture exists and how the major choices answer the
> course objectives and quality constraints.

## My 60-90 Second Script

> In Phase 1, CanTelcoX was mainly a set of microservices coordinated by
> synchronous REST through an API Gateway. That was simple and readable, but it
> couples long business flows to the availability and latency of every
> downstream service.
>
> In Phase 2, we preserved the same implemented use cases and the same six core
> services. The main architectural change is the collaboration style: public
> commands are accepted quickly, then internal progress happens asynchronously
> through Kafka, Transactional Outbox, idempotent consumers, and a choreographed
> saga.
>
> The system boundary is clear: users enter through the NGINX API Gateway and
> `/v1` REST APIs. External systems like HLR/HSS and PortabilityHub stay outside
> the core domain and are integrated through adapters. The trade-off is more
> operational complexity, but better decoupling, resilience, and traceability for
> long-running telecom workflows.

## If Time Is Short

> Phase 2 keeps the Phase 1 services and use cases, but changes the collaboration
> model. REST still accepts public requests, while Kafka, Outbox, idempotent
> consumers, and a choreographed saga handle the long-running workflow
> asynchronously.

## Sections To Defend

| Section | What to say |
|---|---|
| Section 1 | The goal is to adapt existing Phase 1 use cases to an event-driven Phase 2 architecture. |
| Section 2 | Constraints include course-supplied external systems, Docker Compose, Kafka, MySQL, and no new use cases. |
| Section 3 | Context: customers/API Gateway on one side; external HLR/HSS and PortabilityHub on the other. |
| Section 4 | Strategy: keep microservices, add Kafka, Outbox, saga, idempotence, observability, and retry/DLQ. |

## Strong Points

- We preserved six existing services instead of rewriting the system.
- We did not add UC-04, UC-07, or UC-08.
- The public API remains REST and versioned under `/v1`.
- Internal propagation uses Kafka events.
- External systems remain synchronous where their supplied contracts are synchronous.
- MySQL is preserved as the implementation database.

## If The Teacher Asks

Question: Why microservices and not a modular monolith?

Answer:

> The case study already separates telecom capabilities into independent
> services. Phase 2 keeps that boundary because each context owns different
> data and has different availability and integration concerns. A modular
> monolith would simplify operations, but it would hide the distributed
> collaboration concerns that Phase 2 specifically asks us to address.

Question: What quality attributes drove the solution?

Answer:

> The main drivers are resilience, traceability, modifiability, and eventual
> consistency. Kafka and Outbox help with temporary failures; audit and tracing
> improve traceability; bounded services and adapters improve modifiability.

Question: What is the main trade-off?

Answer:

> We traded simplicity for resilience and decoupling. Phase 1 REST flows are
> easier to understand, but a long synchronous chain fails if one downstream
> service is unavailable. Phase 2 needs more infrastructure, but it handles
> long-running workflows more explicitly.

Question: What is inside and outside the system boundary?

Answer:

> Inside: CanTelcoX services, MySQL schemas, Kafka, Outbox, audit, observability.
> Outside: users, HLR/HSS/free5GC, PortabilityHub, and payment gateway
> simulation.

## Anchor Sentence

> My role is to explain why the Phase 2 architecture keeps the Phase 1 service
> boundaries but changes the collaboration model from synchronous chains to
> asynchronous, traceable, event-driven workflows.
