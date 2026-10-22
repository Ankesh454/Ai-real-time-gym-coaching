
import time
import streamlit as st

from services.config.workout_config import METRICS_FIELDS
from services.persistence.exercise_repo import add_exercise


def _queue_feedback(result):
    """Save generated coaching feedback and audio in session state."""
    if not result:
        return

    audio_bytes, feedback = result

    st.session_state.coach_feedback = feedback

    # Keep pending audio instead of overwriting it with another event.
    if audio_bytes and not st.session_state.get("audio_to_play"):
        st.session_state.audio_to_play = audio_bytes


def sync_metrics_update(context):
    if (
        not context
        or not hasattr(context, "state")
        or not context.state.playing
    ):
        return

    processor = getattr(context, "video_processor", None)
    if not processor:
        return

    exercise = st.session_state.get("exercise_type")
    if not exercise:
        return

    processor.set_exercise(exercise)

    latest_metrics = processor.get_latest_metrics()
    if not isinstance(latest_metrics, dict) or not latest_metrics:
        return

    # Safely handle missing rep counts.
    raw_reps = latest_metrics.get("reps")

    if raw_reps is None:
        reps = st.session_state.get("reps", 0) or 0
        print("WARNING: reps is None in latest_metrics")
    else:
        try:
            reps = max(0, int(raw_reps))
        except (TypeError, ValueError):
            reps = st.session_state.get("reps", 0) or 0
            print(f"WARNING: Invalid reps value: {raw_reps!r}")

    st.session_state.reps = reps

    fields = METRICS_FIELDS.get(exercise)
    if not fields:
        return

    for key, default in fields.items():
        st.session_state[key] = latest_metrics.get(key, default)

    # Validate workout targets before division.
    try:
        reps_per_set = int(st.session_state.get("reps_per_set") or 0)
        target_sets = int(st.session_state.get("target_sets") or 0)
    except (TypeError, ValueError):
        reps_per_set = 0
        target_sets = 0

    if reps_per_set > 0 and target_sets > 0:
        sets_completed = reps // reps_per_set
        current_set_reps = reps % reps_per_set
        workout_completed = sets_completed >= target_sets
    else:
        sets_completed = 0
        current_set_reps = reps
        workout_completed = False

    st.session_state.sets_completed = sets_completed
    st.session_state.current_set_reps = current_set_reps
    st.session_state.workout_completed = workout_completed

    last_saved_sets = st.session_state.get(
        "last_saved_sets_completed", 0
    ) or 0

    # Save newly completed sets once.
    if (
        reps_per_set > 0
        and target_sets > 0
        and sets_completed > last_saved_sets
    ):
        newly_completed = sets_completed - last_saved_sets

        now_ts = time.time()
        started_at = st.session_state.get(
            "set_cycle_started_at", now_ts
        )
        time_taken = max(0, now_ts - started_at)
        user_id = st.session_state.get("user_id", 0)

        add_exercise(
            user_id,
            exercise,
            newly_completed * reps_per_set,
            newly_completed,
            time_taken,
        )

        st.session_state.set_cycle_started_at = now_ts
        st.session_state.last_saved_sets_completed = sets_completed

        voice_pipeline = st.session_state.get("voice_pipeline")
        if voice_pipeline:
            result = voice_pipeline.process_event(
                event="set_completed",
                exercise=exercise,
                metrics=latest_metrics,
            )
            _queue_feedback(result)

    # Announce workout completion once.
    if (
        workout_completed
        and not st.session_state.get(
            "last_notified_workout_complete", False
        )
    ):
        st.session_state.last_notified_workout_complete = True

        voice_pipeline = st.session_state.get("voice_pipeline")
        if voice_pipeline:
            result = voice_pipeline.process_event(
                event="workout_completed",
                exercise=exercise,
                metrics=latest_metrics,
            )
            _queue_feedback(result)

    voice_pipeline = st.session_state.get("voice_pipeline")
    if not voice_pipeline:
        return

    # Give feedback when no pose is detected.
    pose_detected = latest_metrics.get("pose_detected", True)

    if not pose_detected:
        result = voice_pipeline.process_event(
            event="no_pose_detected",
            exercise=exercise,
            metrics={
                "issue": (
                    "No pose detected! "
                    "Please step into the camera frame."
                )
            },
        )
        _queue_feedback(result)
        return

    # Check the user's current exercise form.
    result = voice_pipeline.process_event(
        event="ongoing_form_check",
        exercise=exercise,
        metrics=latest_metrics,
    )
    _queue_feedback(result)
