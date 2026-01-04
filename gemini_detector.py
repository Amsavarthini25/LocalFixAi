from google import genai
from google.genai import types
import os
import json
from dotenv import load_dotenv
load_dotenv()


# Load API key and initialize client
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables!")

client = genai.Client(api_key=api_key)


def detect_issue(image_path, user_text):
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    prompt = f"""
You are a civic issue classification AI.

From the image and user description, identify:
- issue_type (one word: pothole, garbage, water_leakage, streetlight, drainage, sewer)
- department (Choose ONLY from: Electrical, Sanitation, Water Supply, Roads,
Parks & Landscaping, Health, Education, Transport, Fire & Emergency Services, Building / Zoning)

Assign realistic priority:
High → safety, fire, electric, water burst
Medium → service disruption
Low → cosmetic / non-urgent

Return ONLY valid JSON. NO markdown. NO backticks.

User description: {user_text}
"""

    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=[
            prompt,
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
        ]
    )

    raw = response.text.strip()
    print("RAW GEMINI:", raw)

    # 🔥 REMOVE ```json ``` wrappers if Gemini adds them
    if raw.startswith("```"):
        raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        result = json.loads(raw)
    except Exception as e:
        print("JSON PARSE FAILED:", raw)
        return {}

    return result

