# jd_parser.py
"""Utilities to convert raw job description text into a structured
``JobDescription`` instance using the Groq LLM.

The workflow follows exactly what you have practiced:

1. Build a *system prompt* that contains the JSON schema generated
   from the ``JobDescription`` Pydantic model.
2. Provide the raw job description as the *user prompt*.
3. Request the model to respond with a JSON object
   (``response_format = {"type": "json_object"}``).
4. Parse the returned JSON string and validate it with Pydantic.

If anything goes wrong we raise a clear ``ValueError`` with the
raw model output so you can see what the LLM actually returned.
"""

import json
from typing import Any

from groq import Groq
from pydantic import ValidationError

from models import JobDescription


def _build_system_prompt() -> str:
    """Create the system prompt that includes the JSON schema.

    The schema is inserted directly into the prompt so the LLM knows
    exactly which fields to output.  We ``json.dumps`` the schema with
    indentation for readability.
    """
    schema = JobDescription.model_json_schema()
    schema_str = json.dumps(schema, indent=2)
    return (
        "You are an expert HR assistant.\n"
        "Read the provided job description and extract the relevant information "
        "according to the following JSON schema. Return **only** the JSON object.\n"
        f"Schema:\n{schema_str}\n"
    )


def parse_job_description(
    job_text: str,
    *,
    client: Groq,
    model: str = "openai/gpt-oss-120b",
    max_tokens: int = 500,
) -> JobDescription:
    """Parse a raw job description into a ``JobDescription`` model.

    Parameters
    ----------
    job_text:
        The plain‑text job description supplied by the HR user.
    client:
        An instantiated ``Groq`` client (already configured with the API key).
    model:
        The name of the LLM model to use. Adjust as needed.
    max_tokens:
        Upper bound for the LLM's completion length.

    Returns
    -------
    JobDescription
        A populated Pydantic model (fields missing from the LLM output will be ``None``).
    """
    system_prompt = _build_system_prompt()
    user_prompt = f"Analyze the following job description:\n\n{job_text}"

    response_format = {"type": "json_object"}

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=response_format,
        max_tokens=max_tokens,
    )

    raw_json = response.choices[0].message.content
    # Debug: you may print raw_json to see the exact output.
    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Failed to decode JSON from LLM response: {exc}\nRaw output: {raw_json}"
        )

    try:
        return JobDescription.parse_obj(parsed)
    except ValidationError as exc:
        raise ValueError(
            f"LLM output does not match JobDescription schema: {exc}\nParsed JSON: {parsed}"
        )
