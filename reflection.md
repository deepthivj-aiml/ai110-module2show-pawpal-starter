# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

My initial design separates owner and pet information from the scheduling process. `Owner` stores the owner's name, preferences, and available time. `Pet` stores the pet's basic information and its care tasks. `Task` represents an individual care activity, including its description, duration, frequency, completion status, priority, and category. I chose dataclasses for these objects because they primarily hold structured data.

`Scheduler` is responsible for evaluating tasks against the available time and preferences and creating a plan. `DailyPlan` holds the selected schedule entries and time totals. Each `ScheduleEntry` connects a care task to its start and end times and records why it was chosen. This division gives the scheduler a clear responsibility and lets the plan retain the information needed to display and explain the day's schedule.

**b. Design changes**

After asking AI to review the skeleton for missing relationships and potential logic bottlenecks, I made four changes based on its feedback. First, I added a pet collection to `Owner` to represent the UML relationship where one owner can care for multiple pets. Second, I changed `Scheduler.create_plan()` to accept the `Owner` and read its available time and preferences rather than accepting separate, potentially inconsistent scheduling inputs. The scheduler specifically retrieves tasks through `Owner.get_all_tasks()` so it can schedule across pets. Third, `DailyPlan` stores the available-time budget and derives scheduled and unused time from its entries, rather than storing totals that could become stale when entries change. Finally, `ScheduleEntry` uses Python's `time` type for start and end times instead of strings, making the intended time data explicit and avoiding ad hoc string parsing. In the Streamlit UI, pet creation now goes through `Owner.add_pet()`, and tasks are created as `Task` objects and added through the selected pet's `add_task()` method.

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler reads the owner's shared time budget and retrieves the incomplete tasks for all pets through `Owner.get_all_tasks()`. It sorts tasks by priority, schedules what fits within the time budget, and continues considering shorter tasks if a longer one does not fit. The `Task` model also records frequency and completion status. Preferences are stored on the owner, but are not yet used to rank tasks; that is a future improvement.

**b. Tradeoffs**

A reasonable tradeoff is to schedule high-priority tasks first, even if that means a lower-priority task is left out when the owner's available time runs out. If a task does not fit, the scheduler skips it and checks whether a shorter task can use the remaining time. This favors important care while respecting the hard time budget.

A second tradeoff is in how the scheduler handles tasks pinned to a set time. Conflict detection compares full durations, not just matching start times. A 9:00–9:10 nail trim and a 9:05 vet call are flagged even though they start at different times, and back-to-back tasks (one ends at 9:10, the next starts at 9:10) are not flagged. When two set-time tasks do overlap, the scheduler keeps the higher-priority one and skips the other with a warning, rather than moving it to the next open slot. I chose this because a set time usually means the time matters. Medication or a vet call shouldn't quietly slide to 9:20, so the owner decides what to do instead of the program guessing. The cost is that a lower-priority task can drop out of the day even when there is free time later. Conflicts are also reported against the times the owner asked for, not the final schedule, so a warning can mention a task that was already skipped. To keep the check easy to read, it compares every pair of set-time tasks (O(n²)) instead of using a faster sorted sweep. With the handful of timed tasks a pet owner has in a day, that cost is too small to notice.

## 3. AI Collaboration

**a. How you used AI**

I used an AI assistant to review the starter files, identify missing relationships and consistency risks, and help implement the data models, multi-pet scheduler, terminal demo, and focused tests. The AI suggested storing pets on `Owner`, having the scheduler retrieve all tasks through `Owner.get_all_tasks()`, deriving plan totals rather than storing duplicate values, and using typed `time` values for schedule entries. I accepted these changes because they align the class relationships and reduce opportunities for inconsistent data. I also accepted the requested `mark_complete()` API while retaining `mark_completed()` as a compatibility alias. I did not implement preference-based task ranking or recurrence-based filtering: preferences are stored but the current scheduler ranks by priority, and recurrence rules need a clearer definition of which tasks are due today.

**b. Judgment and verification**

I verified the implementation by running the focused pytest checks: the scheduler tests passed, including aggregation across pets, use of `Owner.get_all_tasks()`, priority ordering, exclusion of completed tasks, and time-budget handling; the two simple tests for marking a task complete and adding a pet task also passed. I ran `main.py` and confirmed its printed schedule includes both pets and their task times. The Streamlit interface now calls the backend methods for adding pets and tasks and for generating the schedule.

## 4. Testing and Verification

**a. What you tested**

I added focused tests for retrieving tasks from multiple pets, confirming the scheduler uses the owner's aggregate-task method, excluding completed tasks, ordering by priority, fitting tasks to the time budget, generating sequential times, rejecting invalid inputs, and summarizing the plan. The Streamlit UI calls the same backend methods to add pets, add tasks, and create a schedule.

**b. Confidence**

I have reasonable confidence in the core scheduling behavior after the focused tests pass. Next I would test preference-based ranking and recurrence rules, and add automated UI-level coverage to verify submitted forms and displayed schedules end to end.

## 5. Reflection

**a. What went well**

The starter UI gives a clear starting point: it collects owner and pet information and lets the user add tasks with a duration and priority. Those inputs map directly to several of the project's core requirements and make it easier to see what the backend will need.

**b. What you would improve**

My next step would be to add preference-based ranking and define how weekly tasks become due on a particular day. I would also add UI-level tests for the pet and task forms and the displayed multi-pet schedule.

**c. Key takeaway**

An app's interface is not the same as its underlying system behavior. Separating the requirements, model, scheduling logic, and UI—and verifying each against the code—helps avoid mistaking a working-looking screen for a complete, tested solution.
