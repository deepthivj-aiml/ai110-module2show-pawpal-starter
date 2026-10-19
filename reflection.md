# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

My initial design separates owner and pet information from the scheduling process. `Owner` stores the owner's name, preferences, and available time. `Pet` stores the pet's basic information and its care tasks. `Task` represents an individual care activity, including its description, duration, frequency, completion status, priority, and category. I chose dataclasses for these objects because they primarily hold structured data.

`Scheduler` is responsible for evaluating tasks against the available time and preferences and creating a plan. `DailyPlan` holds the selected schedule entries and time totals. Each `ScheduleEntry` connects a care task to its start and end times and records why it was chosen. This division gives the scheduler a clear responsibility and lets the plan retain the information needed to display and explain the day's schedule.

**b. Design changes**

After asking AI to review the skeleton for missing relationships and potential logic bottlenecks, I made four changes based on its feedback. First, I added a pet collection to `Owner` to represent the UML relationship where one owner can care for multiple pets. Second, I changed `Scheduler.create_plan()` to accept the `Owner` and read its available time from there, rather than accepting separate, potentially inconsistent scheduling inputs. The scheduler retrieves `(pet, task)` pairs through `Owner.get_pet_tasks()` so it can schedule across pets. (Preferences are stored on the owner, but the final scheduler doesn't read them.) Third, `DailyPlan` stores the available-time budget and derives scheduled and unused time from its entries, rather than storing totals that could become stale when entries change. Finally, `ScheduleEntry` uses Python's `time` type for start and end times instead of strings, making the intended time data explicit and avoiding ad hoc string parsing. In the Streamlit UI, pet creation now goes through `Owner.add_pet()`, and tasks are created as `Task` objects and added through the selected pet's `add_task()` method.

During the build the design grew further. `Task` gained `due_date` and `fixed_time`, `DailyPlan` gained `skipped` and `conflicts`, and two small classes appeared: `SkippedTask` (a task left out, with the reason) and `TimedTask` (a set-time task's span in minutes, used for conflict checks). The scheduler also picked up static helpers for sorting, filtering, conflict detection and completing recurring tasks. The final diagram is in `diagrams/uml_final.mmd`, and the Phase 1 draft is kept in `diagrams/uml_draft.mmd` for comparison.

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler reads the owner's shared time budget and collects every task, across all pets, that is incomplete and due on the plan date. It sorts them by priority (high, medium, low, keeping insertion order for ties) and places set-time tasks at their requested times first. Flexible tasks then go into the earliest free gap after the day's start time. A task that would exceed the remaining budget or run past midnight is skipped with a reason, and the scheduler keeps going, so a shorter task can still use the leftover time. Preferences are stored on the owner but are not yet used to rank tasks; that is a future improvement.

**b. Tradeoffs**

A reasonable tradeoff is to schedule high-priority tasks first, even if that means a lower-priority task is left out when the owner's available time runs out. If a task does not fit, the scheduler skips it and checks whether a shorter task can use the remaining time. This favors important care while respecting the hard time budget.

A second tradeoff is in how the scheduler handles tasks pinned to a set time. Conflict detection compares full durations, not just matching start times. A 9:00–9:10 nail trim and a 9:05 vet call are flagged even though they start at different times, and back-to-back tasks (one ends at 9:10, the next starts at 9:10) are not flagged. When two set-time tasks do overlap, the scheduler keeps the higher-priority one and skips the other with a warning, rather than moving it to the next open slot. I chose this because a set time usually means the time matters. Medication or a vet call shouldn't quietly slide to 9:20, so the owner decides what to do instead of the program guessing. The cost is that a lower-priority task can drop out of the day even when there is free time later. Conflicts are also reported against the times the owner asked for, not the final schedule, so a warning can mention a task that was already skipped. To keep the check easy to read, it compares every pair of set-time tasks (O(n²)) instead of using a faster sorted sweep. With the handful of timed tasks a pet owner has in a day, that cost is too small to notice.

## 3. AI Collaboration

**a. How you used AI**

I used an AI assistant to review the starter files, identify missing relationships and consistency risks, and help implement the data models, multi-pet scheduler, terminal demo, and focused tests. The AI suggested storing pets on `Owner`, having the scheduler retrieve all tasks through `Owner.get_all_tasks()`, deriving plan totals rather than storing duplicate values, and using typed `time` values for schedule entries. I accepted these changes because they align the class relationships and reduce opportunities for inconsistent data. I also accepted the requested `mark_complete()` API while retaining `mark_completed()` as a compatibility alias. Early on I held off on recurrence until I had a clear rule for which tasks are due on a given day. Once I settled that rule (a task is due on or after its `due_date`, and completing a daily or weekly task creates the next copy 1 or 7 days later), I had the AI implement it. I still haven't implemented preference-based ranking: preferences are stored, but the scheduler ranks by priority.

In later phases I used the AI to plan and write edge-case tests, connect the `Scheduler` methods to the Streamlit UI, rewrite the conflict warnings for pet owners, bring the UML diagram up to date with the code, and draft the README features list and demo walkthrough.

**b. Judgment and verification**

I verified the implementation by running the full pytest suite after each change, running `main.py` to check the printed schedule, and driving the Streamlit app headlessly with Streamlit's `AppTest` to confirm the forms, tables and warnings behave as described in the README.

**c. AI strategy**

*Most effective features.* The most useful thing was letting the assistant run code, not just write it. Before drafting tests, it wrote a throwaway script to see what the scheduler *actually* did with a pet that had no tasks, or two tasks at exactly 09:00, so the tests were based on observed behavior rather than guesses. That probing also found four behaviors I hadn't decided on: completing a task twice, identical tasks for one pet, an unsupported "monthly" frequency, and overlaps across midnight. Other helpful features were attaching or opening the relevant file so its answers referenced real line numbers, running the test suite after every edit, and rendering the Mermaid diagram to check that it actually drew.

*A suggestion I modified.* When I asked whether my UML still matched the code, the AI's first rewrite removed the `Scheduler → Pet` and `Scheduler → Task` arrows, saying the scheduler only reached them through `Owner`. Checking against the code showed that was wrong: `Scheduler.mark_task_complete()` calls `pet.complete_task()` directly, and `sort_by_time()` and `explain_choice()` work on `Task` objects. I had it restore both arrows with accurate labels. In a similar spirit, I didn't let it write tests for the four undecided behaviors above. A test would have locked in whatever the code happened to do, so those stay listed as open questions until I decide what they should do. And for the UI, rather than have the app parse the conflict warning strings, I added a small `Scheduler.find_conflict_pairs()` method that returns the overlapping tasks as data. That kept the formatting in the UI and the logic in the scheduler.

*Separate chat sessions per phase.* Keeping each phase (UML design, implementation, testing, UI, documentation) in its own session kept the assistant focused on one job at a time and stopped decisions from an earlier phase leaking in as unstated assumptions. Starting fresh also forced me to restate the current state of the design. That's how I noticed the Phase 1 UML no longer matched the code, and that my own reflection still claimed the scheduler read owner preferences.

*Being the lead architect.* The AI is fast and usually right, but it is confidently wrong often enough that I have to own the design decisions and the checking. My job was to set the rules (what counts as "due", which task wins a conflict, what a warning should tell an owner), decide which behaviors were bugs and which were features, and verify each claim against the code or a test run before accepting it. The AI made it cheap to try things and to check them; it did not make it safe to skip checking.

## 4. Testing and Verification

**a. What you tested**

The suite in `tests/test_pawpal.py` has 36 passing tests, split between happy paths and edge cases. Happy paths: priority ordering, flexible tasks filling gaps around set-time tasks across pets, sorting by duration, filtering by pet and status, and daily and weekly recurrence. Edge cases: a pet with no tasks, an owner with no pets, two tasks at exactly the same time (for the same pet and for different pets), a zero budget, a task that exactly fills the budget, tasks ending at 23:59 versus midnight, recurrence across year ends and leap days, and overdue tasks. These matter because a scheduler's bugs hide at the boundaries: an off-by-one at midnight or a missed overlap check would quietly produce a wrong plan rather than crash.

**b. Confidence**

4 out of 5. All 36 tests pass, including the three required behaviors (chronological sorting, daily recurrence and conflict detection). I'm not at 5 because four behaviors are known but undecided and untested: completing the same task twice, two identical tasks for one pet, the unsupported "monthly" frequency, and conflicts that cross midnight. Next I would decide those, add preference-based ranking, and add UI-level tests to the suite (I've only checked the UI with one-off `AppTest` runs so far).

## 5. Reflection

**a. What went well**

The starter UI gives a clear starting point: it collects owner and pet information and lets the user add tasks with a duration and priority. Those inputs map directly to several of the project's core requirements and make it easier to see what the backend will need.

**b. What you would improve**

My next step would be to add preference-based ranking and settle the four open behaviors listed above. I'd also check that the suggested "move it to HH:MM" time in a conflict warning is actually free, since right now it only checks against the task that was kept. Finally, I'd add UI-level tests for the pet and task forms and the displayed multi-pet schedule.

**c. Key takeaway**

An app's interface is not the same as its underlying system behavior. Separating the requirements, model, scheduling logic, and UI—and verifying each against the code—helps avoid mistaking a working-looking screen for a complete, tested solution.
