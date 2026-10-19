# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## Implementation Summary

The backend in `pawpal_system.py` models care activities with `Task`, pets and their task lists with `Pet`, and an owner's pets, preferences, and available time with `Owner`. `Owner.get_all_tasks()` gathers tasks across every registered pet, and `Scheduler` uses that method to include incomplete tasks from all pets in a shared daily plan. It prioritizes high-priority tasks, skips tasks that do not fit the remaining time, and records scheduled times and explanations in `ScheduleEntry` objects. `DailyPlan` keeps the entries and calculates its scheduled and remaining minutes from them. The Streamlit UI in `app.py` uses the owner and pet methods to add pets and tasks, then generates the multi-pet schedule. The terminal demo in `main.py` also exercises the models and scheduler.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

```
(.venv) PS C:\Projects\Codepath\ai110-module2show-pawpal-starter>  python main.py
Today's Schedule
Daily PawPal+ plan:
- 08:00-08:30 - Mochi: Morning walk (30 min; scheduled first because it is high priority)
- 08:30-08:40 - Mochi: Breakfast (10 min; scheduled first because it is high priority)
- 08:40-09:00 - Luna: Play and enrichment (20 min; scheduled because it fits the remaining time (medium priority))
- 09:00-09:05 - Luna: Refresh water (5 min; scheduled because it fits the remaining time (medium priority))
Scheduled 65 of 90 available minutes (25 minutes remaining).
(.venv) PS C:\Projects\Codepath\ai110-module2show-pawpal-starter>
```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
python -m pytest

# Show each test by name:
python -m pytest -v
```

### What the tests cover

The 35 tests in `tests/test_pawpal.py` cover both happy paths (everything works) and edge cases:

- **Sorting:** `sort_by_time()` orders tasks by duration, keeps ties in insertion order, supports `reverse=True` and handles an empty list. `sorted_entries()` returns the plan in clock order even when set-time tasks were stored first.
- **Priority scheduling:** high-priority tasks are placed first and win a tight time budget. Flexible tasks fill the gaps around set-time tasks, across multiple pets.
- **Recurring tasks:** completing a daily task creates a new one due the next day; weekly tasks repeat after 7 days; one-time tasks don't repeat. Due dates roll over month ends, year ends and leap days. An overdue task stays in the plan until it's done, and its next copy is due one interval after the day it was completed.
- **Conflict detection:** two tasks at the exact same time are flagged, tagged `[same pet]` or `[different pets]`. The higher-priority task keeps the slot (or the first one added, if priorities match). Back-to-back, completed and flexible tasks are not flagged.
- **Edge cases:** a pet with no tasks, an owner with no pets, a zero time budget, a task that exactly fills the budget, and tasks ending at 23:59 (scheduled) or at midnight (skipped).
- **Filtering and validation:** filtering by pet and completion status, and rejecting invalid priorities.

### Test results

```
$ python -m pytest
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
collected 35 items

tests\test_pawpal.py ...................................                 [100%]

============================= 35 passed in 0.23s ==============================
```

(The run also printed one `PytestConfigWarning` about `asyncio_mode`. It comes from a `pyproject.toml` outside this project and doesn't affect the tests, so it's left out above.)

### Confidence level: ★★★★☆ (4/5)

All 35 tests pass, including the three core behaviors (chronological sorting, daily recurrence and conflict detection) and the main edge cases. It isn't 5 stars because a few behaviors are known but not yet decided or tested:

- Completing the same task twice raises an error after the task is already marked complete.
- Two tasks with identical details can't be added to the same pet (for example, two "Feed" tasks with no set time).
- A frequency such as `"monthly"` counts as recurring but never creates a next task.
- Conflict detection doesn't catch overlaps that cross midnight.

## 📐 Smarter Scheduling

All scheduling logic lives in `pawpal_system.py`. Each feature is covered by tests in `tests/test_pawpal.py` and demonstrated in `main.py`.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Scheduler.sort_by_time()`, `DailyPlan.sorted_entries()` | Tasks by duration (shortest or longest first); schedule entries by clock time |
| Filtering | `Scheduler.filter_tasks()`, `Owner.filter_tasks()` | By pet name, completion status, or both |
| Conflict handling | `Scheduler.detect_conflicts()` | Overlapping set-time tasks for the same pet or different pets; returns warnings, never crashes |
| Recurring tasks | `Scheduler.mark_task_complete()`, `Pet.complete_task()`, `Task.next_occurrence()`, `Task.is_due()` | Completing a daily/weekly task creates the next one, due +1 / +7 days |

### Sorting

- **`Scheduler.sort_by_time(tasks, reverse=False)`** returns a new list of tasks ordered by `Task.time`, which is the duration in minutes, shortest first. Pass `reverse=True` for longest first. The sort is stable, so tasks with the same duration keep the order they were added in, and the original list is not modified.
- **`DailyPlan.sorted_entries()`** returns the generated schedule in clock order by `start_time`. This matters because set-time tasks are placed before flexible ones. `summarize()` and the Streamlit schedule table both use this order.
- The plan itself (`Scheduler.create_plan()`) still ranks tasks by **priority**: high, then medium, then low. Ties keep the order the tasks were added in.

### Filtering

- **`Scheduler.filter_tasks(owner, pet_name=None, completed=None)`** returns the matching `Task` objects. Each filter applies only when it is given:
  - `pet_name="Luna"`: only Luna's tasks
  - `completed=False`: only unfinished tasks; `completed=True`: only finished ones
  - both together, e.g. Mochi's unfinished tasks
- **`Owner.filter_tasks(...)`** does the same filtering but returns `(pet, task)` pairs. The app uses it for the "Show pet" / "Show status" filters above the task table, where the pet name is needed for display.
- The output of `Scheduler.filter_tasks()` can go straight into `sort_by_time()`, e.g. `Scheduler.sort_by_time(Scheduler.filter_tasks(owner, completed=False))`.
- When the plan is built, completed tasks and tasks not yet due are filtered out automatically by `Scheduler._due_tasks()`.

### Conflict detection

- **`Scheduler.detect_conflicts(owner, plan_date=None)`** checks every task that has a set time (`Task.fixed_time`) and returns one warning string per overlapping pair, for example:

  ```
  Mochi's 'Give medication' (09:00-09:05) overlaps Mochi's 'Trim nails' (09:00-09:10) [same pet]
  Mochi's 'Trim nails' (09:00-09:10) overlaps Luna's 'Vet video call' (09:05-09:20) [different pets]
  ```

- **Lightweight by design:** it returns messages instead of raising errors, so the program keeps running and the caller decides how to show them. `main.py` prints them; the app shows `st.warning` boxes. An empty list means no conflicts.
- **Durations are compared, not just start times.** Two tasks overlap when each one starts before the other ends. So 09:00–09:10 and 09:05–09:20 conflict, while back-to-back tasks (one ends at 09:10, the next starts at 09:10) do not.
- Only incomplete, due, set-time tasks are checked. Flexible tasks are placed in free gaps by `Scheduler._find_open_slot()`, so they can never clash.
- **Inside `create_plan()`:** set-time tasks are placed first in priority order. When two clash, the higher-priority one keeps the slot and the other is listed under "Not scheduled" with the reason `conflicts with ...`. The same warnings are stored in `DailyPlan.conflicts`.

### Recurring tasks

- **`Scheduler.mark_task_complete(owner, task, on=None)`** marks a task done. It finds which pet owns the task and calls **`Pet.complete_task()`**. For a recurring task, that adds the next occurrence to the same pet and returns it.
- **`Task.next_occurrence(completed_on)`** creates the new task with `dataclasses.replace()`: same description, duration, priority and set time, marked incomplete, with a new `due_date`:
  - `daily`: `completed_on + timedelta(days=1)`
  - `weekly`: `completed_on + timedelta(days=7)`
  - `once`: no next occurrence (returns `None`)

  `timedelta` rolls over month ends, year ends and leap days correctly. For example, `2026-12-31` → `2027-01-01`.
- **`Task.is_due(on)`** keeps future occurrences out of today's plan. A task is due when it has no `due_date` or its due date is on or before the plan date, so a missed task carries over until it's done.
- In the app, the **Mark complete** form calls `Pet.complete_task()` and shows when the next occurrence is due.

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
