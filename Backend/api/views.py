

# Create your views here.
import os

from dotenv import load_dotenv
from openai import OpenAI
from rest_framework.decorators import api_view
from rest_framework.response import Response

load_dotenv()


api_key = os.getenv("FOUNDRY_API_KEY")
base_url = os.getenv("FOUNDRY_BASE_URL")
model = os.getenv("FOUNDRY_MODEL")

client = OpenAI(
    api_key=api_key,
    base_url=base_url
)


@api_view(["POST"])
def chat(request):

    message = request.data.get("message")

    if not message:
        return Response(
            {"error": "Message is required"},
            status=400
        )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful College Fest Planner assistant."
            },
            {
                "role": "user",
                "content": message
            }
        ],
        temperature=0.7,
        max_tokens=500
    )

    return Response({
        "response": response.choices[0].message.content
    })