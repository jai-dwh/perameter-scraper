from google import genai

class GeminiClient:

    def __init__(self, api_key):

        self.client = genai.Client(
            api_key=api_key
        )

    def enrich(self, prompt):

        response = (
            self.client.models
            .generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
        )

        return response.text