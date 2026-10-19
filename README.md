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

## ✨ Features

Every feature below is implemented in `pawpal_system.py`, used by the Streamlit app (`app.py`) and the terminal demo (`main.py`), and covered by `tests/test_pawpal.py`.

- **Multi-pet daily planning within a time budget.** `Scheduler.create_plan()` gathers every due, incomplete task across all of the owner's pets and fits them into the owner's available minutes. A task that doesn't fit is skipped with a reason, and planning continues, so a shorter task can still use the leftover time.
- **Priority-first scheduling.** Tasks are stable-sorted high → medium → low before placement, so important care claims the time budget first. Tasks with equal priority keep the order they were added.
- **Set-time tasks and gap filling.** Tasks with a `fixed_time` (medication, a vet call) are pinned to that time. Flexible tasks are then placed in the earliest free gap that's long enough, starting from the day's start time (`_find_open_slot`). No two entries ever overlap, and nothing is allowed to run past midnight.
- **Sorting by time.** `Scheduler.sort_by_time()` orders tasks by duration, shortest or longest first. The sort is stable and doesn't modify the input. `DailyPlan.sorted_entries()` shows the finished schedule in clock order.
- **Filtering.** `Scheduler.filter_tasks()` / `Owner.filter_tasks()` narrow tasks by pet, by completion status, or both. The results can be passed straight into `sort_by_time()`.
- **Conflict warnings.** `Scheduler.detect_conflicts()` compares every pair of set-time tasks and flags any whose time spans overlap: partial overlaps, one task inside another, and identical start times. Back-to-back tasks don't count. Each warning names both pets, both tasks and their times, tagged `[same pet]` or `[different pets]`. In the plan, the higher-priority task keeps the slot. The app explains which task was kept and suggests a time to move the other one to (`Scheduler.find_conflict_pairs()`).
- **Daily and weekly recurrence.** Completing a task with `Pet.complete_task()` or `Scheduler.mark_task_complete()` keeps it as history and adds a fresh copy due 1 day (daily) or 7 days (weekly) later, using `timedelta`, so month ends, year ends and leap days roll over correctly. One-time tasks don't repeat.
- **Due-date carry-over.** `Task.is_due()` keeps future occurrences out of today's plan, while a missed task stays in the plan until it's done.
- **Explained decisions.** Every scheduled entry carries a plain-language reason (for example, "set for 09:00 (high priority)" or "scheduled first because it is high priority"), and every skipped task says why it was left out.
- **Input validation.** Empty names, non-positive durations, unknown priorities and negative time budgets are rejected with clear errors.

The final class design is in [`diagrams/uml_final.mmd`](diagrams/uml_final.mmd) (rendered: [`diagrams/uml_final.png`](diagrams/uml_final.png)).

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
python -m pytest

# Show each test by name:
python -m pytest -v
```

### What the tests cover

The 36 tests in `tests/test_pawpal.py` cover both happy paths (everything works) and edge cases:

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
collected 36 items

tests\test_pawpal.py ....................................                [100%]

============================= 36 passed in 0.07s ==============================
```

(The run also printed one `PytestConfigWarning` about `asyncio_mode`. It comes from a `pyproject.toml` outside this project and doesn't affect the tests, so it's left out above.)

### Confidence level: ★★★★☆ (4/5)

All 36 tests pass, including the three core behaviors (chronological sorting, daily recurrence and conflict detection) and the main edge cases. It isn't 5 stars because a few behaviors are known but not yet decided or tested:

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

### Main UI features

Run the app with `streamlit run app.py`. The page is one column, top to bottom:

| Section | What you can do |
|---|---|
| **Owner and available time** | Set your name, how many minutes of care time you have today, and when your day starts. |
| **Add a pet** | Add a pet with a name and species (dog, cat or other). Duplicates and blank names are rejected with an error. |
| **Add a care task** | Choose a pet, then enter a description, duration, priority (low, medium, high) and frequency (daily, weekly, once). Tick **Must happen at a set time** to pin the task to a clock time. |
| **Current tasks** | View every task in a table, then filter by pet and status, or sort by duration (shortest or longest first). If any set-time tasks clash, a warning appears here straight away. Mark a task complete from the dropdown, and a repeating task shows when its next copy is due. |
| **Today's schedule** | Click **Generate schedule** to see the tasks scheduled and minutes used and free, then the plan in clock order with a reason for each task, a warning for each conflict, and a "Not scheduled" table explaining anything left out. If everything fits, a green success message says so. |

### Example workflow

1. **Set the day.** Leave the owner as *Jordan*, set available time to **90** minutes and start the day at **08:00**.
2. **Add two pets.** Add *Mochi* (dog), then *Luna* (cat). Each appears under "Your pets" with a success message.
3. **Add flexible tasks.** For Mochi: *Morning walk*, 30 min, high. For Luna: *Play and enrichment*, 20 min, medium.
4. **Add two set-time tasks that clash.** For Mochi: *Give medication*, 5 min, high, set time **09:00**. For Luna: *Vet video call*, 15 min, medium, set time **09:00**. A warning appears under Current tasks right away: *"1 set-time conflict – Mochi's Give medication (09:00–09:05) overlaps Luna's Vet video call (09:00–09:15)."*
5. **Sort and filter.** Set "Sort by duration" to *Longest first*, and the walk moves to the top. Set "Show pet" to *Luna* to see only her tasks.
6. **Generate today's schedule.** Click **Generate schedule**. Flexible tasks are placed in priority order: the walk runs 08:00–08:30 and play 08:30–08:50. The medication runs at 09:00 as set. A warning explains: *"You can't be with two pets at once … PawPal+ kept Give medication because it's high priority, and left out Vet video call. 💡 To fit both, move Vet video call to 09:05 or later."* The vet call is listed under "Not scheduled" with the reason *conflicts with Give medication*.
7. **Complete a task.** Under "Mark a task complete", choose *Mochi: Morning walk* and click **Mark complete**. A success message reads *"Completed Morning walk. Next one is due …"* with tomorrow's date, and the table now shows the finished walk and a new one to do.

### Key Scheduler behaviors shown

- **Priority ordering:** high-priority tasks are placed first, and low-priority tasks are the first to be skipped when time runs out (*Brush coat* below).
- **Gap filling:** flexible tasks fill the time around set-time tasks (*Refresh water* runs at 09:20, after the vet call).
- **Sorting:** by duration in the task list and the CLI demo, and by clock time in the generated schedule.
- **Filtering:** by pet and completion status, and combined with sorting.
- **Conflict warnings:** for the same pet and for different pets, with the higher-priority task keeping the slot.
- **Recurrence:** a daily task's next copy is due tomorrow, and a weekly task's next copy is due in 7 days.

### Sample CLI output (`python main.py`)

The terminal demo builds two pets with six tasks, shows sorting and filtering, adds three overlapping set-time tasks, generates the plan, and then completes a daily and a weekly task. The dates shown come from a run on 2026-10-19.

```
$ python main.py

All tasks (insertion order)
  - Morning walk (30 min, high priority, daily, incomplete)
  - Brush coat (15 min, low priority, daily, incomplete)
  - Breakfast (10 min, high priority, daily, incomplete)
  - Play and enrichment (20 min, medium priority, daily, incomplete)
  - Refresh water (5 min, medium priority, daily, incomplete)
  - Clean litter box (10 min, medium priority, daily, completed)

Sorted by time, shortest first
  - Refresh water (5 min, medium priority, daily, incomplete)
  - Breakfast (10 min, high priority, daily, incomplete)
  - Clean litter box (10 min, medium priority, daily, completed)
  - Brush coat (15 min, low priority, daily, incomplete)
  - Play and enrichment (20 min, medium priority, daily, incomplete)
  - Morning walk (30 min, high priority, daily, incomplete)

Sorted by time, longest first
  - Morning walk (30 min, high priority, daily, incomplete)
  - Play and enrichment (20 min, medium priority, daily, incomplete)
  - Brush coat (15 min, low priority, daily, incomplete)
  - Breakfast (10 min, high priority, daily, incomplete)
  - Clean litter box (10 min, medium priority, daily, completed)
  - Refresh water (5 min, medium priority, daily, incomplete)

Filtered: Mochi only
  - Morning walk (30 min, high priority, daily, incomplete)
  - Brush coat (15 min, low priority, daily, incomplete)
  - Breakfast (10 min, high priority, daily, incomplete)

Filtered: completed
  - Clean litter box (10 min, medium priority, daily, completed)

Filtered + sorted: Luna's incomplete tasks, shortest first
  - Refresh water (5 min, medium priority, daily, incomplete)
  - Play and enrichment (20 min, medium priority, daily, incomplete)

Conflict check
  WARNING: Mochi's 'Give medication' (09:00-09:05) overlaps Mochi's 'Trim nails' (09:00-09:10) [same pet]
  WARNING: Mochi's 'Trim nails' (09:00-09:10) overlaps Luna's 'Vet video call' (09:05-09:20) [different pets]

Today's Schedule
Daily PawPal+ plan:
- 08:00-08:30 - Mochi: Morning walk (30 min; scheduled first because it is high priority)
- 08:30-08:40 - Mochi: Breakfast (10 min; scheduled first because it is high priority)
- 08:40-09:00 - Luna: Play and enrichment (20 min; scheduled because it fits the remaining time (medium priority))
- 09:00-09:05 - Mochi: Give medication (5 min; set for 09:00 (high priority))
- 09:05-09:20 - Luna: Vet video call (15 min; set for 09:05 (medium priority))
- 09:20-09:25 - Luna: Refresh water (5 min; scheduled because it fits the remaining time (medium priority))
Scheduled 85 of 90 available minutes (5 minutes remaining).
Not scheduled:
- Mochi: Trim nails (conflicts with Give medication)
- Mochi: Brush coat (needs 15 min, only 5 min left)
Conflicts:
- Mochi's 'Give medication' (09:00-09:05) overlaps Mochi's 'Trim nails' (09:00-09:10) [same pet]
- Mochi's 'Trim nails' (09:00-09:10) overlaps Luna's 'Vet video call' (09:05-09:20) [different pets]

Recurring tasks
  Completed 'Morning walk' (daily).
  Next occurrence created, due 2026-10-20.
  Completed 'Bath' (weekly).
  Next occurrence created, due 2026-10-26.

Mochi's tasks now
  - Morning walk (30 min, high priority, daily, completed)
  - Brush coat (15 min, low priority, daily, incomplete)
  - Breakfast (10 min, high priority, daily, incomplete)
  - Give medication (5 min, high priority, daily, incomplete)
  - Trim nails (10 min, medium priority, daily, incomplete)
  - Morning walk (30 min, high priority, daily, incomplete)
  - Bath (25 min, medium priority, weekly, completed)
  - Bath (25 min, medium priority, weekly, incomplete)
```
