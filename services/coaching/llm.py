
from services.config.workout_config import PROMPT


class LLMCoach:
    def __init__(self, groq_client):
        self.client = groq_client
        self.history = []
        self.system_prompt = PROMPT

    def give_feedback(self, event, issue=None):
        prompt = f"Event: {event}"

        if issue:
            prompt += f"\nForm Issue: {issue}"

        messages = [
            {"role": "system", "content": self.system_prompt},
            *self.history[-10:],
            {"role": "user", "content": prompt},
        ]

        try:
            response = self.client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=messages,
                temperature=0.4,
            )

            text = response.choices[0].message.content

            if not text or not text.strip():
                return "Keep going and maintain proper form."

            text = text.strip()

            # Save both user prompt and assistant response.
            self.history.extend([
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": text},
            ])

            # Keep recent conversation history bounded.
            self.history = self.history[-10:]

            return text

        except Exception as error:
            print(f"LLM coaching error: {error}")
            return "Focus on your form and perform the exercise with control."
