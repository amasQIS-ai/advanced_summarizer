import os
from google import genai
from google.genai import types

# Initialize Google GenAI client with the provided API key
genai_client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

def summarize_common(
    system_prompt: str,
    parts: list[types.Part],
    model_name: str = "gemini-2.0-flash-exp"
) -> str:
    """
    A common utility to generate content from Gemini.
    We feed both a system prompt and a user prompt.
    The `summary_content` can be text or bytes (PDF/image).
    """

    # Create the content list with user role containing the text and document parts
    contents = [
        types.Content(
            role="user",
            parts=parts
        )
    ]

    # Configure the content generation settings
    generate_content_config = types.GenerateContentConfig(
        temperature=0,
        top_p=0.95,
        max_output_tokens=8192,
        response_modalities=["TEXT"],
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
        ],
        system_instruction=[types.Part.from_text(text=system_prompt)],
    )

    # Generate the summarized content using the configured settings
    response = genai_client.models.generate_content(
        model=model_name,
        contents=contents,
        config=generate_content_config,
    )

    # Return the summarized text from the response
    return response.text
