from pathlib import Path
import json
import pandas as pd
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
UPLOAD_MANIFEST = DATA_DIR / "uploaded_inputs.json"


def uploaded_inputs():
    """Return the current uploaded input files, or None until a full upload exists."""
    if not UPLOAD_MANIFEST.exists():
        return None

    try:
        inputs = json.loads(UPLOAD_MANIFEST.read_text())
    except (OSError, json.JSONDecodeError):
        return None

    required = ("guidelines", "venues", "activities")
    if not all(inputs.get(field) and (DATA_DIR / inputs[field]).exists() for field in required):
        return None
    return inputs


def load_guidelines(inputs=None):
    inputs = inputs or uploaded_inputs()
    if not inputs:
        raise FileNotFoundError("Upload the required fest files before planning.")
    reader = PdfReader(DATA_DIR / inputs["guidelines"])
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def create_chunks(text, size=500):
    words = text.split()
    return [
        " ".join(words[i:i + size])
        for i in range(0, len(words), size)
    ]


def retrieve(query, chunks, top_k=3):
    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform(chunks)
    query_vector = vectorizer.transform([query])

    scores = cosine_similarity(query_vector, vectors)[0]
    indices = scores.argsort()[-top_k:][::-1]

    return [chunks[i] for i in indices if scores[i] > 0]


def _read_table(path, sheet_name=0):
    return pd.read_csv(path) if path.suffix.lower() == ".csv" else pd.read_excel(path, sheet_name=sheet_name)


def load_data(inputs=None):
    inputs = inputs or uploaded_inputs()
    if not inputs:
        raise FileNotFoundError("Upload the required fest files before planning.")

    venues_path = DATA_DIR / inputs["venues"]
    activities_path = DATA_DIR / inputs["activities"]
    venues = _read_table(venues_path)
    activities = _read_table(activities_path, sheet_name="Activities")

    if activities_path.suffix.lower() == ".csv":
        budget_column = next((column for column in ("Budget (INR)", "Max Budget (INR)", "Fest Budget (INR)") if column in activities.columns), None)
        if not budget_column:
            raise ValueError("Activities CSV must include a Budget (INR), Max Budget (INR), or Fest Budget (INR) column.")
        budget = pd.DataFrame({"Amount (INR)": [activities[budget_column].dropna().iloc[0]]})
    else:
        budget = pd.read_excel(activities_path, sheet_name="Budget")

    return venues, activities, budget
