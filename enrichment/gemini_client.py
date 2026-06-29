from openai import OpenAI
from config.settings import MODEL_BASE_URL,OPENROUTER_API_KEY,OPENROUTER_MODEL_NAME
class GeminiClient:

    def __init__(self, api_key=None):
        self.client = OpenAI(
            base_url=MODEL_BASE_URL,
            api_key=OPENROUTER_API_KEY
        )

    def enrich(self, prompt):

        response = self.client.chat.completions.create(
            model=OPENROUTER_MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            extra_body={
                "think":False,
                "keep_alive": "30m"
            }
        )

        return response.choices[0].message.content