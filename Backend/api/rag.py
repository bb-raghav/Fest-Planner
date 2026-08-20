from pathlib import Path
import pandas as pd
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_guidelines():
    reader = PdfReader(DATA_DIR / "fest_guidelines.pdf")
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


def load_data():
    venues = pd.read_excel(DATA_DIR / "venues.xlsx")
    activities = pd.read_excel(
        DATA_DIR / "activities.xlsx",
        sheet_name="Activities"
    )
    budget = pd.read_excel(
        DATA_DIR / "activities.xlsx",
        sheet_name="Budget"
    )

    return venues, activities, budget