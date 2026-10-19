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
    Owner,
    Pet,
    Scheduler,
    Task,
)

DEFAULT_OWNER_NAME = "Jordan"
DEFAULT_AVAILABLE_MINUTES = 90
DEFAULT_TASK_MINUTES = 20
MAX_TASK_MINUTES = 240
TIME_STEP_MINUTES = 15
ALL_OPTION = "All"
STATUS_FILTERS = {ALL_OPTION: None, "Incomplete": False, "Complete": True}

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
    filter_pet_col, filter_status_col = st.columns(2)
    pet_filter = filter_pet_col.selectbox(
        "Show pet", [ALL_OPTION] + [pet.name for pet in pets]
    )
    status_filter = filter_status_col.selectbox("Show status", list(STATUS_FILTERS))
    filtered = owner.filter_tasks(
        pet_name=None if pet_filter == ALL_OPTION else pet_filter,
        completed=STATUS_FILTERS[status_filter],
    )
    if filtered:
        st.table(
            [
                {
                    "Pet": pet.name,
                    "Task": task.description,
                    "Duration (min)": task.duration_minutes,
                    "Priority": task.priority,
                    "Frequency": task.frequency,
                    "Set time": f"{task.fixed_time:%H:%M}" if task.fixed_time else "",
                    "Due": str(task.due_date or today),
                    "Status": "Complete" if task.completed else "Incomplete",
                }
                for pet, task in filtered
            ]
        )
    else:
        st.caption("No tasks match these filters.")

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
        for conflict in plan.conflicts:
            st.warning(f"Conflict: {conflict}")
        if plan.entries:
            st.table(
                [
                    {
                        "Time": f"{e.start_time:%H:%M}-{e.end_time:%H:%M}",
                        "Pet": e.pet.name,
                        "Task": e.task.description,
                        "Why": e.reason,
                    }
                    for e in plan.sorted_entries()
                ]
            )
            st.caption(
                f"Scheduled {plan.total_scheduled_minutes} of "
                f"{plan.available_minutes} minutes "
                f"({plan.unused_minutes} remaining)."
            )
        else:
            st.info("No incomplete tasks fit into today's available time.")
        if plan.skipped:
            st.markdown("**Not scheduled**")
            for skipped in plan.skipped:
                st.markdown(f"- {skipped.format_for_display()}")
