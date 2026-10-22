
import time
import streamlit as st


class VoicePipeline:
    def __init__(self, llm, tts):
        self.llm = llm
        self.tts = tts
        self.last_spoken_at = 0
        self.cooldown_seconds = 4

    def _find_form_issue(self, exercise, metrics):
        if not isinstance(metrics, dict):
            return None

        if metrics.get("issue"):
            return metrics["issue"]

        if exercise == "Squats":
            depth = metrics.get("depth_status", "")
            back_angle = metrics.get("back_angle", 180)

            if depth == "TOO HIGH":
                return (
                    "The user's squat is not deep enough. "
                    "Encourage them to bend their knees sufficiently."
                )

            if (
                isinstance(back_angle, (int, float))
                and back_angle < 130
            ):
                return (
                    "The user is leaning too far forward during "
                    "the squat. Encourage a more upright torso."
                )

        elif exercise == "Push-ups":
            alignment = metrics.get("body_alignment", "")
            hip_status = metrics.get("hip_status", "")

            if alignment == "Poor Form":
                return (
                    "The user's body is not straight during "
                    "the push-up."
                )

            if hip_status == "SAGGING":
                return "The user's hips are sagging. Keep the body straight."

            if hip_status == "PIKED UP":
                return (
                    "The user's hips are too high. "
                    "Maintain a straight body line."
                )

        elif exercise in ("Biceps", "Biceps Curls (Dumbbell)"):
            swing = metrics.get("swing_status", "")
            shoulder = metrics.get("shoulder_status", "")

            if swing == "SWINGING":
                return (
                    "The user's torso is swinging during the curl. "
                    "Keep the body still."
                )

            if shoulder == "ELBOW DRIFTING":
                return (
                    "The user's elbow is drifting away from their side."
                )

        elif exercise == "Shoulder Press":
            back_arch = metrics.get("back_arch_status", "")

            if back_arch == "Excessive Arch":
                return (
                    "The user is arching their lower back excessively."
                )

            if back_arch == "Slight Arch":
                return (
                    "A slight back arch is detected. "
                    "Encourage the user to brace their core."
                )

        elif exercise == "Lunges":
            balance = metrics.get("balance_status", "")

            if balance == "OFF BALANCE":
                return (
                    "The user is losing balance during the lunge. "
                    "Keep the feet about hip-width apart."
                )

        return None

    def process_event(self, event, exercise, metrics):
        issue = self._find_form_issue(exercise, metrics)

        now = time.time()

        major_events = {
            "workout_started",
            "set_completed",
            "workout_completed",
        }

        is_major_event = event in major_events

        # Only speak for major events or detected form issues.
        if not is_major_event:
            if not issue:
                return None

            # Avoid repeating coaching too frequently.
            if now - self.last_spoken_at < self.cooldown_seconds:
                return None

        try:
            text = self.llm.give_feedback(event, issue)

            if not text or not text.strip():
                return None

            voice = self.tts.speak(text)

            # Update cooldown only after feedback generation.
            self.last_spoken_at = time.time()

            return voice, text.strip()

        except Exception as error:
            print(f"Voice pipeline error: {error}")
            return None


def autoplay_audio(audio_bytes):
    if not audio_bytes:
        return None

    st.markdown(
        "<style>[data-testid='stAudio'] {display:none;}</style>",
        unsafe_allow_html=True,
    )

    # Do not pass key: the installed Streamlit version
    # does not support it for st.audio().
    st.audio(
        audio_bytes,
        format="audio/mp3",
        autoplay=True,
    )
