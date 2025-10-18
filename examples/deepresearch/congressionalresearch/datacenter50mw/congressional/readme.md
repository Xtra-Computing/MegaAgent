# Congressional Birthplace Analysis — Multi‑Agent Run Summary

## Overview
- **Goal**: Identify all current U.S. Congress members (House + Senate) who were born outside the state they represent and compile them into `ans.txt`.
- **Outcome**: The final product captured **80+ members** born outside their represented state.
- **Baseline comparison**: Perplexity’s deep research surfaced only **26** members (based on a 25-member foreign-born list plus a well-known domestic example, e.g., Nancy Pelosi — born in Maryland while representing California). The multi-agent system significantly exceeded this.

## Team and Roles
The system bootstrapped a CEO agent and five specialist researchers, coordinated via `examples/congressional/agent.py` with prompts from `examples/congressional/config.py`.

- **Bob (CEO/Coordinator)**
  - Split the task, recruited sub-agents, set deliverables and formats, reviewed intermediate files, and triggered final aggregation into `ans.txt`.
  - Key actions visible in `logs/Bob.log`.

- **Alice (Senators A–L researcher)**
  - Task: Research senators with last names A–L; output entries where birth state ≠ represented state.
  - Output: `files/senators_a_l.txt`.

- **Ben (Senators M–Z researcher)**
  - Task: Research senators with last names M–Z; output entries where birth state ≠ represented state.
  - Output: `files/senators_m_z.txt`.

- **Carol (House A–H researcher)**
  - Task: Research representatives with last names A–H; output entries where birth state ≠ represented state.
  - Planned output: `files/house_a_h.txt` and helper list `files/house_a_h_list.txt`.

- **Dave (House I–Q researcher)**
  - Task: Research representatives with last names I–Q; output entries where birth state ≠ represented state.
  - Output: `files/house_i_q.txt`.

- **Eve (House R–Z researcher)**
  - Task: Research representatives with last names R–Z; output entries where birth state ≠ represented state.
  - Output: `files/house_r_z.txt`.

All agents used the `perplexity_search` tool and wrote to the shared `files/` directory as instructed by `config.py`.

## What They Did Over Time
- **Initialization**
  - `main.py` created the CEO (`Bob`) using `config.initial_prompt`, parsed sub-agent prompts, and added agents as subordinates to Bob.
  - Bob assigned explicit scopes and file deliverables to Alice, Ben, Carol, Dave, Eve (see `logs/Bob.log`).

- **Research phase (parallel)**
  - Each researcher queried Perplexity with targeted prompts and wrote intermediate/final results to `files/*.txt`.
  - Evidence in per-agent logs: `logs/Alice.log`, `logs/Ben.log`, `logs/Carol.log`, `logs/Dave.log`, `logs/Eve.log`.

- **Review and aggregation**
  - Bob repeatedly used `read_file` to review partial outputs and tracked status via `files/status_*.txt` and `files/todo_*.txt`.
  - After sufficient coverage (80+ qualifying members), Bob compiled into `files/ans.txt`.

- **Follow-ups and reminders**
  - Bob sent reminders when certain files lagged (e.g., `house_a_h.txt`), ensuring completion coverage across the alphabetic/state slices before or during aggregation.

## Produced Artifacts (files/)
- **Final**
  - `ans.txt` — consolidated list of congress members born outside their represented state.

- **Senate slices**
  - `senators_a_l_list.txt` — list helper
  - `senators_a_l.txt` — final out-of-state subset (Alice)
  - `senators_m_z_list.txt` — list helper
  - `senators_m_z.txt` — final out-of-state subset (Ben)

- **House slices**
  - `house_a_h_list.txt` — list helper (Carol)
  - `house_a_h.txt` — final out-of-state subset (Carol)
  - `house_i_q_list.txt` — list helper
  - `house_i_q.txt` — final out-of-state subset (Dave)
  - `house_r_z.txt` — final out-of-state subset (Eve)

- **Global helpers and traces**
  - `congress_list.txt` — a compiled list of current members used to drive research
  - `bio_n_z.txt` — biographical scratchpad slice used during research
  - `status_*.txt`, `todo_*.txt` — per-agent progress tracking

Note: Some helper files may have been regenerated multiple times as the agents refined queries and verified entries.

## Results Summary
- The multi-agent approach produced a comprehensive list with **80+ entries** of out-of-state births across House and Senate.
- This substantially improves on Perplexity deep research’s **26** surfaced names.
- Example high-salience case: **Nancy Pelosi** is correctly identified as born in Maryland while serving California, alongside many less publicized domestic out-of-state cases.

## Methodology Highlights
- **Decomposition**: Alphabetical segmentation for Senate (A–L, M–Z) and House (A–H, I–Q, R–Z) enabled parallel research.
- **Tooling**: All discovery used `perplexity_search` with targeted, follow-up queries and higher token limits for biographical detail when needed.
- **Verification**: Cross-checks and iterative updates captured both foreign-born and domestic out-of-state births.
- **Auditability**: Per-agent logs (`logs/*.log`) and intermediate files in `files/` enable traceability of each finding.

## How to Reproduce
1. In `examples/congressional/`, run:
   ```bash
   python main.py
   ```
2. The run will:
   - Initialize agents and logs in `logs/`
   - Write intermediate and final results to `files/`
   - Produce `files/ans.txt` upon aggregation

Requirements and LLM/tool configuration are defined in `examples/congressional/config.py`.

## Limitations and Next Steps
- Some alphabetic slices occasionally lagged; the CEO agent issued reminders to ensure coverage. You can re-run `main.py` to regenerate or update slices.
- Consider a final automatic consistency pass that validates each `*.txt` entry (name matching and state normalization) before writing `ans.txt`.
- Add a simple script to count unique members in `ans.txt` and export a CSV with normalized columns for downstream analysis.
