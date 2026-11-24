# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Inferred from PLAN.md, not restated in the landing interview: a developer running a local language model who needs to measure how that inference performs.

## Product Purpose

InferBench is an engineering platform for measuring local LLM inference performance. Success is a working bench the developer can open after reading that purpose.

## Positioning

The bench measures local inference and keeps the result. It is not a chatbot.

## Operating Context

The site opens on a landing route that states the purpose, then replaces itself with the existing dashboard. The dashboard talks to a local FastAPI service and Ollama. New runs are stored locally.

## Capabilities and Constraints

Confirmed for this surface: the landing page states one sentence, then the dashboard that already exists replaces it on its own. The landing page does not add a second explanation.

The sentence is: "An engineering platform for measuring local LLM inference performance."

The dashboard still measures and shows stored latency, throughput, hardware samples, comparisons, and routing. It does not invent a latency. Explanatory dashboard sentences do not rank a winner.

## Brand Commitments

The product name is InferBench. The dashboard already in the repo is the page the landing opens onto.

## Evidence on Hand

PLAN.md states the product. The running dashboard is the existing interface. There are no testimonials, customers, or press assets. Do not invent timings, model rankings, or quotes.

## Product Principles

- State the purpose in the confirmed sentence, then get out of the way.
- The dashboard is the product. The landing page does not replace its job.
- Show stored measurements only. A blank value stays unset.
- Keep technical names. Do not rank one result above another.
