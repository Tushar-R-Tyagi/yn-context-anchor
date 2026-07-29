# Motivation & Project Background

## Discovering Y/N

I first stumbled upon **Y/N** while browsing [Work at a Startup](https://www.workatastartup.com/). Intrigued by the concept of dynamic interactive fiction, I downloaded the app, and was instantly hooked. Within just two weeks, I logged **over 40 hours** on the platform.

### Why Y/N Stands Out
What makes Y/N so incredibly addictive and unique is its core UX philosophy: **unmatched user autonomy and creative freedom**. It allows users to step directly into their favorite screenplays, interact with iconic characters, and co-write stories in real time.

From an engineering perspective, Y/N represents one of the few consumer applications where **Generative AI creates genuine, irreplaceable value**:
* ❌ It is **not** another generic AI note-taking app.
* ❌ It is **not** a basic document summarizer or routine workflow automation wrapper.
* 🟢 It is an **immersive narrative engine** that leverages LLMs to turn passive consumers into active storytellers.

---

## 🔬 The Problem: Noticing State Decay at Scale

After spending dozens of hours interacting with deep, multi-turn storylines (40+ turns), I began noticing structural limitations inherent to standard state-less LLM chat implementations:

1. **Memory Amnesia (MECW Collapse):** Over extended sessions, key inventory items, past events, and physical locations fade as older context scrolls past the model's active window.
2. **Identity Drift ("Y/N" Placeholder Leakage):** As context grows long, character identity, gender markers, and user naming conventions can occasionally bleed back into generic raw template variables (e.g., rendering `"Y/N"` directly to the screen).
3. **Fact & Inventory Hallucinations:** When forced to rely on fuzzy textual memory rather than structured database state, models frequently invent or duplicate items.

---

## 🛠️ The Mission: Don't Just Point Out Bugs—Build the Fix

Rather than just logging feedback or pointing out these edge cases, I wanted to **actively contribute to solving them**.

This repository is an **experimental proof-of-concept**, not a benchmarked production system, built to test a simple thesis:

> *"By decoupling creative prose generation (Narrator) from deterministic state tracking (Auditor) into an isolated Dual-LLM + SQLite architecture, we can drive state hallucinations and identity drift toward zero, with minimal added latency from the background tracking calls."*

This repo documents the architecture and proof-of-concept codebase built to explore context decay in multi-turn interactive fiction engines. It's a starting point for the idea, not a finished, benchmarked solution.
