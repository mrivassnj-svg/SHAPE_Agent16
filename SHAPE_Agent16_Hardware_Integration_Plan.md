# SHAPE Agent 16 — Hardware Integration Plan

**Project:** SHAPE, Agent 16 — ITAI2376, Houston Community College, Group ITAI2376_14562
**Final deadline:** December 7, 2026. **Proposal deadline:** November 13, 2026.

## 1. Principle

Hardware is a later milestone, not the first one. The core application — Colab notebook, orchestrator, agents, tools, adaptive policy, evaluation — must work completely without any physical device. Hardware integration must never jeopardize the core application.

## 2. Planned devices

| Device | Quantity | Role |
|---|---|---|
| Raspberry Pi Zero 2 W | 2 | Handheld companion: runs the handheld client, talks to the central host over Wi-Fi, drives a display. |
| Raspberry Pi Pico W | 2 | Handheld companion / sensor and button input: sends small events, receives short prompts. |
| CYD display boards (Cheap Yellow Display, ESP32-based) | 2 | Handheld screen: lesson navigation, short prompts, progress indicators, feedback, challenge selection. |
| 3D-printed enclosures / mounts | As needed | Protect the boards and make the handhelds usable in a classroom. |

Exact board revisions, pin assignments, and enclosure designs are **TODO — to be filled by the member doing the hardware work** when the devices are in hand. Do not invent pin numbers or enclosure dimensions in this plan.

## 3. What runs where

| Component | Where it runs | Why |
|---|---|---|
| LLM and orchestration backend | Central host — Google Colab or a computer | The LLM, the orchestrator, the four agent roles, the tools, and SQLite all need far more memory and compute than a Pi Zero 2 W or a Pico W can provide. Low-power microcontrollers do **not** run the LLM. |
| Gradio application, database, adaptive policy | Central host | Same reason; also the place where longer code entry happens. |
| Handheld client | Pi Zero 2 W / Pico W / CYD | Sends and receives small events only. |
| Code entry | Browser or computer | Longer code entry stays on a full keyboard and screen. Handheld screens are not for typing code. |

## 4. What handheld screens are for

- Lesson navigation (next / previous / select a lesson).
- Short prompts (one-line questions, concept checks).
- Progress indicators (lessons completed, current streak).
- Feedback (correct / try again, hint available).
- Challenge selection (choose a practice or challenge exercise).
- Device interaction (button presses, simple navigation choices).

What handheld screens are **not** for: code editing, long explanations, evaluation charts, or report generation. Those stay on the central host.

## 5. Device communication architecture

Proposed architecture (not yet implemented — see Section 8):

```
CYD / Pico W / Pi Zero 2 W (handheld client)
        │  Wi-Fi, small JSON events only
        ▼
Central host (Colab or computer)
  HTTP endpoint / event queue ──► Orchestrator ──► Gradio UI / SQLite
        ▲
        │  small JSON responses (prompt, progress, feedback)
```

- The host exposes one small event endpoint (or, for the mock, an in-app event log). Handhelds poll it or post to it; they do not open a direct database connection.
- Messages are small (under 1 KB), infrequent (one per learner action), and idempotent where practical (a repeated "next lesson" event does not skip two lessons).
- If the host is unreachable, the handheld shows "host unavailable — try again" and keeps its last known lesson and progress locally. It does not invent progress.
- No API keys are stored on any handheld device. The handheld never calls the LLM provider directly.

## 6. JSON message contract

Every device message uses this shape. Fields not listed here are not part of the contract.

```json
{"device_id": "cyd-01", "event": "lesson_select", "lesson_id": "py-01", "action": "next", "timestamp": "2026-12-01T10:00:00Z"}
```

| Field | Type | Required | Meaning |
|---|---|---|---|
| `device_id` | string | Yes | Unique per device, e.g. `cyd-01`, `pico-01`, `zero-01`. Assigned when the device is set up; record the assignment in the team log. |
| `event` | string | Yes | One of: `lesson_select`, `lesson_next`, `lesson_previous`, `prompt_answer`, `hint_request`, `challenge_select`, `progress_request`, `heartbeat`. |
| `lesson_id` | string | When relevant | Lesson the event refers to, e.g. `py-01`. Omit or set to `null` for `heartbeat` and `progress_request`. |
| `action` | string | When relevant | The learner's choice, e.g. `"next"`, `"A"`, `"hint"`. Omit or set to `null` when there is no choice. |
| `timestamp` | string (ISO 8601, UTC) | Yes | When the event happened on the device. |

Host responses use the same envelope with `event` set to `prompt`, `progress`, `feedback`, or `error`, and include only the fields the handheld needs to display (short text, lesson title, progress counts).

Example response:

```json
{"device_id": "cyd-01", "event": "feedback", "lesson_id": "py-01", "action": "correct", "timestamp": "2026-12-01T10:00:05Z"}
```

## 7. Mock hardware mode (default)

Mock mode works without any physical device and is the default for the Colab demonstration:

- The notebook includes a mock device panel (in the Agent Workspace / Team Workspace area) that sends the same JSON events as a real device would, using a virtual device ID such as `mock-cyd-01`.
- Mock events go through the same orchestrator path as real events, so a demo can show lesson navigation, a prompt answer, and a progress update without hardware.
- Mock events are labelled "mock" in the event log, so a mock demonstration is never presented as a physical-device demonstration.
- **Hardware is not required for the initial Colab demonstration.** Do not let a hardware delay block Milestones 2–4.

## 8. Future integration checklist

- [ ] Devices in hand; device IDs assigned and recorded (`cyd-01`, `cyd-02`, `pico-01`, `pico-02`, `zero-01`, `zero-02` or as assigned).
- [ ] Wi-Fi connectivity tested from each device to the central host.
- [ ] Host event endpoint running and accepting the JSON contract in Section 6; invalid messages rejected with an error response.
- [ ] Handheld client displays lesson navigation, a short prompt, and a progress indicator from host data.
- [ ] A prompt answer sent from a handheld appears as an attempt / event in the central log.
- [ ] Host-unavailable behaviour tested: handheld shows an error and does not invent progress.
- [ ] Enclosure / mount printed and fitted; device is usable without a loose cable or exposed board in normal handling.
- [ ] Mock mode still works after real-device code is added (regression check).
- [ ] Demo video segment for hardware, if any, is labelled mock or physical honestly.

## 9. Risks

- **Compatibility:** Pi Zero 2 W, Pico W, and CYD boards have different toolchains; a library that works on one may not work on another. Test one device at a time.
- **Wi-Fi in a classroom:** The host and the devices must be on the same network. Have the mock-mode demo ready as the fallback for the final presentation.
- **Power:** Handhelds need a tested power source for the full demo length; do not discover a dead battery during the recording.
- **Scope:** Hardware is Milestone 5, after the working prototype (Milestone 2), agent/tool integration (Milestone 3), and evaluation (Milestone 4). If time runs short, ship mock mode and document the physical integration as future work — do not cut the core application to chase hardware.
