import os

from dotenv import load_dotenv
from openai import OpenAI
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .rag import (
    load_guidelines,
    create_chunks,
    retrieve,
    load_data,
)

load_dotenv()

client = OpenAI(
    api_key=os.getenv("FOUNDRY_API_KEY"),
    base_url=os.getenv("FOUNDRY_BASE_URL")
)

model = os.getenv("FOUNDRY_MODEL")


@api_view(["POST"])
def chat(request):

    message = request.data.get("message")

    if not message:
        return Response({"error": "Message is required"}, status=400)

    guidelines = load_guidelines()
    chunks = create_chunks(guidelines)
    relevant = retrieve(message, chunks)

    venues, activities, budget = load_data()

    context = f"""
FEST GUIDELINES:
{chr(10).join(relevant)}

VENUES:
{venues.to_string(index=False)}

ACTIVITIES:
{activities.to_string(index=False)}

BUDGET:
{budget.to_string(index=False)}
"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a college fest planning assistant. Use only the provided information."
            },
            {
                "role": "user",
                "content": f"{context}\n\nUSER REQUEST:\n{message}"
            }
        ],
        temperature=0.2,
        max_tokens=800
    )

    return Response({
        "response": response.choices[0].message.content
    })