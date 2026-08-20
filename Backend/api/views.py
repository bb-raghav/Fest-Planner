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
    uploaded_inputs,
)
from .validator import validate_schedule

load_dotenv()

client = OpenAI(
    api_key=os.getenv("FOUNDRY_API_KEY"),
    base_url=os.getenv("FOUNDRY_BASE_URL")
)

model = os.getenv("FOUNDRY_MODEL")


@api_view(["GET"])
def health(request):
    """Small dependency-free endpoint for verifying the frontend connection."""
    return Response({"status": "ok"})


@api_view(["POST"])
def help_chat(request):
    """General product help; intentionally isolated from fest uploads and RAG context."""
    message = request.data.get("message", "").strip()
    if not message:
        return Response({"error": "Message is required"}, status=400)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are FestPilot Help, a friendly concise assistant. Answer general questions about using the FestPilot interface, event planning basics, registrations, prizes, budgets, and schedules. Do not access, mention, infer from, or use any uploaded fest guidelines, venues, activities, budgets, or planner data. If asked for specific uploaded-plan information, explain that the user should use the Planner workspace instead.",
                },
                {"role": "user", "content": message},
            ],
            temperature=0.4,
            max_tokens=350,
        )
    except Exception:
        return Response({"error": "The AI help service is unavailable. Verify the Foundry configuration and try again."}, status=502)
    return Response({"reply": response.choices[0].message.content or "I couldn't produce a reply. Please try again."})


@api_view(["POST"])
def chat(request):

    message = request.data.get("message")

    if not message:
        return Response(
            {"error": "Message is required"},
            status=400
        )

    inputs = uploaded_inputs()
    if not inputs:
        return Response(
            {"error": "Upload fest guidelines, venues, and activities before generating a plan."},
            status=409,
        )

    try:
        guidelines = load_guidelines(inputs)
        venues, activities, budget = load_data(inputs)
        chunks = create_chunks(guidelines)
        relevant = retrieve(message, chunks)
    except (FileNotFoundError, ValueError, IndexError) as error:
        return Response({"error": str(error)}, status=400)
    except Exception:
        return Response({"error": "The uploaded files could not be processed. Check their format and try uploading them again."}, status=400)

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
            "end": "HH:MM",
            "registration_fee": 0,
            "prize_pool": 0,
            "max_participants": 0,
            "team_size": "Individual or 2-4 members",
            "registration_deadline": "YYYY-MM-DD or TBA",
            "required_resources": ["Resource"],
            "coordinator_notes": "Short operational note"
        }}
    ],
    "summary": "Two short sentences covering plan readiness, budget, and operations."
}}

Do not add markdown.
Do not add explanations.
Do not invent activities or venues.
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": """You are FestPilot, a meticulous college-fest operations planner. Create complete, practical event plans from only the supplied documents and tables. For every scheduled activity, assign a valid venue and time, respect capacity, equipment, duration, venue availability, the 6 PM finish, conflicts, and the stated budget. Always include registration fee, prize pool, maximum participants, team-size rule, registration deadline, required resources, and concise coordinator notes. Use values explicitly supplied by the inputs whenever available. If a business detail is not supplied, use a conservative clearly labelled estimate (or TBA for a date); never invent activities or venues. Return strictly valid JSON only, with no Markdown or extra text."""
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=800,
        )
    except Exception:
        return Response({"error": "The AI planner service is unavailable. Verify the Foundry configuration and try again."}, status=502)

    raw_response = response.choices[0].message.content

    try:
        result = json.loads(raw_response)
    except json.JSONDecodeError:
        return Response({
            "error": "AI returned invalid JSON",
            "raw_response": raw_response
        }, status=500)

    schedule = result.get("schedule", [])

    try:
        validation = validate_schedule(schedule, venues, activities, budget)
    except Exception:
        return Response({"error": "The AI returned a schedule that could not be validated. Please try again."}, status=502)

    return Response({
        "schedule": schedule,
        "validation": validation,
        "summary": result.get("summary", "Review registrations, prizes, resources, and coordinator notes before publishing."),
    })

@api_view(["POST"])
def upload_files(request):

    data_dir = Path(__file__).resolve().parent.parent / "data"
    data_dir.mkdir(exist_ok=True)

    files = {
        "guidelines": {"extensions": {".pdf"}, "label": "a PDF"},
        "venues": {"extensions": {".xlsx", ".csv"}, "label": "an XLSX or CSV"},
        "activities": {"extensions": {".xlsx", ".csv"}, "label": "an XLSX or CSV"},
    }

    missing = [field for field in files if not request.FILES.get(field)]
    if missing:
        return Response({"error": "Upload all three required files: guidelines, venues, and activities."}, status=400)

    validated = {}
    for field, rule in files.items():
        uploaded_file = request.FILES[field]
        extension = Path(uploaded_file.name).suffix.lower()
        if extension not in rule["extensions"]:
            return Response({"error": f"{field} must be {rule['label']}."}, status=400)
        validated[field] = (uploaded_file, extension)

    uploaded = []
    manifest = {}
    for field, (uploaded_file, extension) in validated.items():
        filename = f"uploaded_{field}{extension}"
        destination = data_dir / filename

        with open(destination, "wb+") as output:
            for chunk in uploaded_file.chunks():
                output.write(chunk)

        uploaded.append(filename)
        manifest[field] = filename

    (data_dir / "uploaded_inputs.json").write_text(json.dumps(manifest))

    return Response({
        "message": "Files uploaded successfully. Planning is now enabled.",
        "files": uploaded
    })
