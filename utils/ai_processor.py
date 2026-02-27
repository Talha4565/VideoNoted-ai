import os
import json
import google.generativeai as genai

# Configure Gemini on import
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-flash-latest")

SYSTEM_PROMPT = """You are a professional content analyst and summarization assistant.
Analyze video transcripts and produce structured, high-quality outputs.
Rules:
- Be concise but comprehensive
- Avoid repetition
- Do not invent information not present in the transcript
- Use clear, readable formatting
- Return valid JSON only
- Do not include any text, explanation, or markdown outside the JSON object"""

USER_PROMPT_TEMPLATE = """Analyze the following YouTube video transcript.

Generate:
1. A clear 5-8 sentence summary
2. 8-12 key bullet points
3. 5 important timestamps with short descriptions (use the actual times from the transcript if available)
4. 3 key takeaways
5. 5 tweet-length hooks (under 280 characters each, no hashtags)
6. A 500-word SEO-friendly blog draft with a title

Return ONLY this exact JSON format with no other text:
{{
  "summary": "string",
  "key_points": ["string", "string"],
  "timestamps": [{{"time": "MM:SS", "note": "string"}}],
  "takeaways": ["string", "string", "string"],
  "hooks": ["string", "string"],
  "blog_draft": "string"
}}

Transcript:
{transcript}"""


def generate_content(transcript_text: str) -> dict:
    """
    Send transcript to Gemini Flash and return structured JSON result.

    Returns:
        { "success": True, "data": { summary, key_points, timestamps, ... } }
        or
        { "success": False, "error": "human-readable error" }
    """
    try:
        prompt = f"{SYSTEM_PROMPT}\n\n{USER_PROMPT_TEMPLATE.format(transcript=transcript_text)}"

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.4,
                max_output_tokens=4096,
            ),
        )

        raw_text = response.text.strip()

        # Strip markdown code fences if Gemini wraps in ```json ... ```
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.strip()

        parsed = json.loads(raw_text)

        # Validate required keys
        required_keys = ["summary", "key_points", "timestamps", "takeaways", "hooks", "blog_draft"]
        for key in required_keys:
            if key not in parsed:
                parsed[key] = [] if key != "summary" and key != "blog_draft" else ""

        return {"success": True, "data": parsed}

    except json.JSONDecodeError:
        return {
            "success": False,
            "error": "AI returned an unexpected format. Please try again.",
        }
    except Exception as e:
        error_str = str(e).lower()

        if "quota" in error_str or "rate" in error_str:
            return {
                "success": False,
                "error": "AI processing capacity reached. Please try again in a moment.",
            }
        elif "timeout" in error_str or "deadline" in error_str:
            return {
                "success": False,
                "error": "AI processing timed out. Please try again.",
            }
        elif "api_key" in error_str or "invalid" in error_str:
            return {
                "success": False,
                "error": "AI service configuration error. Please contact support.",
            }
        else:
            return {
                "success": False,
                "error": "AI processing failed. Please try again.",
            }
