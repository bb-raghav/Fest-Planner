import json
import os
from pathlib import Path
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
from .validator import validate_schedule

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
        return Response(
            {"error": "Message is required"},
            status=400
        )

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

    prompt = f"""
You are a College Fest Planner.

Use the provided information to create a feasible schedule.

{context}

USER REQUEST:
{message}

Return ONLY valid JSON in this exact format:

{{
    "schedule": [
        {{
            "activity": "Activity name",
            "venue": "Venue name",
            "start": "HH:MM",
            "end": "HH:MM"
        }}
    ]
}}

Do not add markdown.
Do not add explanations.
Do not invent activities or venues.
"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a reliable scheduling assistant that outputs valid JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.1,
        max_tokens=800
    )

    raw_response = response.choices[0].message.content

    try:
        result = json.loads(raw_response)
    except json.JSONDecodeError:
        return Response({
            "error": "AI returned invalid JSON",
            "raw_response": raw_response
        }, status=500)

    schedule = result.get("schedule", [])

    validation = validate_schedule(
        schedule,
        venues,
        activities,
        budget
    )

    return Response({
        "schedule": schedule,
        "validation": validation
    })

@api_view(["POST"])
def upload_files(request):

    data_dir = Path(__file__).resolve().parent.parent / "data"
    data_dir.mkdir(exist_ok=True)

    files = {
        "guidelines": "fest_guidelines.pdf",
        "venues": "venues.xlsx",
        "activities": "activities.xlsx",
    }

    uploaded = []

    for field, filename in files.items():

        file = request.FILES.get(field)

        if not file:
            continue

        extension = Path(file.name).suffix.lower()

        if filename.endswith(".pdf") and extension != ".pdf":
            return Response(
                {"error": f"{field} must be a PDF file."},
                status=400
            )

        if filename.endswith(".xlsx") and extension != ".xlsx":
            return Response(
                {"error": f"{field} must be an XLSX file."},
                status=400
            )

        destination = data_dir / filename

        with open(destination, "wb+") as output:
            for chunk in file.chunks():
                output.write(chunk)

        uploaded.append(filename)

    if not uploaded:
        return Response(
            {"error": "No valid files uploaded."},
            status=400
        )

    return Response({
        "message": "Files uploaded successfully.",
        "files": uploaded
    })