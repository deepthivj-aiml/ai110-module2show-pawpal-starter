from datetime import date

import streamlit as st

from pawpal_system import (
    DEFAULT_DAY_START,
    DEFAULT_FREQUENCY,
    DEFAULT_PRIORITY,
    FREQUENCIES,
    MINUTES_PER_DAY,
    PRIORITIES,
    SPECIES,
    DailyPlan,
    Owner,
    Pet,
    Scheduler,
    Task,
    TimedTask,
)

DEFAULT_OWNER_NAME = "Jordan"
DEFAULT_AVAILABLE_MINUTES = 90
DEFAULT_TASK_MINUTES = 20
MAX_TASK_MINUTES = 240
TIME_STEP_MINUTES = 15
ALL_OPTION = "All"
STATUS_FILTERS = {ALL_OPTION: None, "Incomplete": False, "Complete": True}
# Maps each sort choice to the ``reverse`` flag of Scheduler.sort_by_time.
SORT_OPTIONS = {"Order added": None, "Shortest first": False, "Longest first": True}
PRIORITY_LABELS = {"high": "🔴 High", "medium": "🟡 Medium", "low": "🟢 Low"}


def _clock(minutes: int) -> str:
    """Format minutes after midnight as HH:MM."""
    return f"{minutes // 60 % 24:02d}:{minutes % 60:02d}"


def _label(item: TimedTask) -> str:
    """Name a set-time task with its pet and time span."""
    return (
        f"**{item.pet.name}'s {item.task.description}** "
        f"({_clock(item.start)}–{_clock(item.end)})"
    )


def show_conflict(a: TimedTask, b: TimedTask, plan: DailyPlan) -> None:
    """Explain one clash in plain language, which task won and how to fix it."""
    if a.pet is b.pet:
        title = f"{a.pet.name} is booked for two things at once"
    else:
        title = "You can't be with two pets at once"
    body = f"{_label(a)} overlaps {_label(b)}."

    scheduled = {id(entry.task): entry for entry in plan.entries}
    kept = next((x for x in (a, b) if id(x.task) in scheduled), None)
    if kept is None:
        body += "\n\nNeither task made it into today's plan."
    else:
        dropped = b if kept is a else a
        why = (
            f"it's {kept.task.priority} priority"
            if kept.task.priority != dropped.task.priority
            else "it was added first and both have the same priority"
        )
        free_at = f"{scheduled[id(kept.task)].end_time:%H:%M}"
        body += (
            f"\n\nPawPal+ kept **{kept.task.description}** because {why}, "
            f"and left out **{dropped.task.description}**."
            f"\n\n💡 To fit both, move {dropped.task.description} "
            f"to {free_at} or later."
        )
    st.warning(body, icon="⚠️", title=title)

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

if "owner" not in st.session_state:
    st.session_state["owner"] = Owner(
        name=DEFAULT_OWNER_NAME, available_minutes=DEFAULT_AVAILABLE_MINUTES
    )

owner: Owner = st.session_state["owner"]
today = date.today()

st.title("🐾 PawPal+")
st.markdown(
    "Plan daily care for all your pets, using task priority and your available time."
)

st.subheader("Owner and available time")
owner_name = st.text_input("Owner name", value=owner.name)
if owner_name.strip():
    owner.name = owner_name.strip()
available_minutes = st.number_input(
    "Available care time today (minutes)",
    min_value=0,
    max_value=MINUTES_PER_DAY,
    value=owner.available_minutes,
    step=TIME_STEP_MINUTES,
)
owner.set_available_time(int(available_minutes))
day_start = st.time_input(
    "Start the day at",
    value=DEFAULT_DAY_START,
    step=TIME_STEP_MINUTES * 60,
)

st.divider()
st.subheader("Add a pet")
with st.form("add_pet_form", clear_on_submit=True):
    pet_name = st.text_input("Pet name")
    species = st.selectbox("Species", SPECIES)
    add_pet_submitted = st.form_submit_button("Add pet")

if add_pet_submitted:
    try:
        owner.add_pet(Pet(name=pet_name.strip(), species=species))
    except ValueError as error:
        st.error(str(error))
    else:
        st.success(f"Added {pet_name.strip()}.")

pets = owner.list_pets()
if pets:
    st.subheader("Your pets")
    for pet in pets:
        st.markdown(f"**{pet.name}** ({pet.species})")
else:
    st.info("Add a pet before entering care tasks.")

st.divider()
st.subheader("Add a care task")
if pets:
    with st.form("add_task_form", clear_on_submit=True):
        selected_pet_index = st.selectbox(
            "Pet",
            options=range(len(pets)),
            format_func=lambda index: f"{pets[index].name} ({pets[index].species})",
        )
        task_description = st.text_input("Task description")
        duration_minutes = st.number_input(
            "Duration (minutes)",
            min_value=1,
            max_value=MAX_TASK_MINUTES,
            value=DEFAULT_TASK_MINUTES,
        )
        priority = st.selectbox(
            "Priority", PRIORITIES, index=PRIORITIES.index(DEFAULT_PRIORITY)
        )
        frequency = st.selectbox(
            "Frequency", FREQUENCIES, index=FREQUENCIES.index(DEFAULT_FREQUENCY)
        )
        has_fixed_time = st.checkbox("Must happen at a set time")
        fixed_time = st.time_input("Set time", value=DEFAULT_DAY_START)
        add_task_submitted = st.form_submit_button("Add task")

    if add_task_submitted:
        selected_pet = pets[selected_pet_index]
        try:
            selected_pet.add_task(
                Task(
                    description=task_description.strip(),
                    duration_minutes=int(duration_minutes),
                    frequency=frequency,
                    priority=priority,
                    fixed_time=fixed_time if has_fixed_time else None,
                )
            )
        except ValueError as error:
            st.error(str(error))
        else:
            st.success(f"Added task to {selected_pet.name}.")

    st.subheader("Current tasks")
    if "flash" in st.session_state:
        st.success(st.session_state.pop("flash"))
    filter_pet_col, filter_status_col, sort_col = st.columns(3)
    pet_filter = filter_pet_col.selectbox(
        "Show pet", [ALL_OPTION] + [pet.name for pet in pets]
    )
    status_filter = filter_status_col.selectbox("Show status", list(STATUS_FILTERS))
    sort_choice = sort_col.selectbox("Sort by duration", list(SORT_OPTIONS))

    filtered = Scheduler.filter_tasks(
        owner,
        pet_name=None if pet_filter == ALL_OPTION else pet_filter,
        completed=STATUS_FILTERS[status_filter],
    )
    if SORT_OPTIONS[sort_choice] is not None:
        filtered = Scheduler.sort_by_time(filtered, reverse=SORT_OPTIONS[sort_choice])
    # Scheduler.filter_tasks returns bare tasks, so look each one's pet back up.
    pet_of = {id(task): pet for pet, task in owner.get_pet_tasks()}

    if filtered:
        st.table(
            [
                {
                    "Pet": pet_of[id(task)].name,
                    "Task": task.description,
                    "Duration": f"{task.duration_minutes} min",
                    "Priority": PRIORITY_LABELS[task.priority],
                    "Repeats": task.frequency,
                    "Set time": f"{task.fixed_time:%H:%M}" if task.fixed_time else "—",
                    "Due": f"{task.due_date or today:%b %d}",
                    "Status": "✅ Done" if task.completed else "⏳ To do",
                }
                for task in filtered
            ],
            hide_index=True,
        )
        st.caption(f"Showing {len(filtered)} of {len(pet_of)} tasks.")
    else:
        st.info("No tasks match these filters.")

    # Give a short heads-up as soon as a clash exists; the schedule below
    # explains which task wins and how to fix it.
    clashes = Scheduler.find_conflict_pairs(owner, today)
    if clashes:
        st.warning(
            "\n".join(f"- {_label(a)} overlaps {_label(b)}" for a, b in clashes)
            + "\n\nGenerate today's schedule to see which task PawPal+ keeps.",
            icon="⚠️",
            title=f"{len(clashes)} set-time conflict{'s' if len(clashes) > 1 else ''}",
        )

    open_tasks = owner.filter_tasks(completed=False)
    if open_tasks:
        with st.form("complete_task_form"):
            completed_index = st.selectbox(
                "Mark a task complete",
                options=range(len(open_tasks)),
                format_func=lambda index: (
                    f"{open_tasks[index][0].name}: {open_tasks[index][1].description}"
                ),
            )
            complete_submitted = st.form_submit_button("Mark complete")
        if complete_submitted:
            done_pet, done_task = open_tasks[completed_index]
            next_task = done_pet.complete_task(done_task, today)
            message = f"Completed {done_task.description}."
            if next_task is not None:
                message += f" Next one is due {next_task.due_date}."
            st.session_state["flash"] = message
            st.rerun()

    st.divider()
    st.subheader("Today's schedule")
    if st.button("Generate schedule"):
        plan = Scheduler(start_time=day_start).create_plan(owner, plan_date=today)

        tasks_col, used_col, free_col = st.columns(3)
        tasks_col.metric("Tasks scheduled", len(plan.entries))
        used_col.metric("Minutes used", plan.total_scheduled_minutes)
        free_col.metric("Minutes free", plan.remaining_time())

        if plan.entries and not plan.skipped:
            st.success(
                f"Everything fits! {len(plan.entries)} "
                f"{'task is' if len(plan.entries) == 1 else 'tasks are'} planned with "
                f"{plan.remaining_time()} minutes to spare.",
                icon="✅",
            )

        for earlier, later in Scheduler.find_conflict_pairs(owner, today):
            show_conflict(earlier, later, plan)

        if plan.entries:
            st.table(
                [
                    {
                        "Time": f"{e.start_time:%H:%M}–{e.end_time:%H:%M}",
                        "Pet": e.pet.name,
                        "Task": e.task.description,
                        "Priority": PRIORITY_LABELS[e.task.priority],
                        "Why": e.reason,
                    }
                    for e in plan.sorted_entries()
                ],
                hide_index=True,
            )
        else:
            st.info("No incomplete tasks fit into today's available time.")

        if plan.skipped:
            st.markdown(f"**Not scheduled ({len(plan.skipped)})**")
            st.table(
                [
                    {
                        "Pet": s.pet.name,
                        "Task": s.task.description,
                        "Priority": PRIORITY_LABELS[s.task.priority],
                        "Reason": s.reason,
                    }
                    for s in plan.skipped
                ],
                hide_index=True,
            )
