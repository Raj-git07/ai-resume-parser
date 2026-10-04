# main.py
"""Full pipeline: parse JD → read resumes → match → save results.

Run:
    python main.py

Requires GROQ_API_KEY in the environment or a .env file in the project root.
"""

import json
import os
import sys

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

from jd_parser import parse_job_description
from matcher import match_resume
from models import JobDescription, Resume
from resume_parser import read_resume


# ---------------------------------------------------------------------------
# Sample job description – edit this or load from a file as needed.
# ---------------------------------------------------------------------------
SAMPLE_JD = """
SDE Intern — Software Development Engineer Intern
Company: TechNova Labs
Role: Software Development Engineer Intern
Location: Bengaluru / Hyderabad / Remote
Duration: 3–6 months
Job Type: Internship
Stipend: ₹30,000–₹60,000/month
Experience: 0–1 years / Freshers
Expected Graduation: 2027–2028

About the Role
We are looking for a motivated Software Development Engineer Intern to join our
engineering team and work on scalable web applications, backend services, APIs,
and AI-powered products.

Responsibilities
- Develop and maintain backend services and REST APIs using Python, Node.js, Java, or similar technologies.
- Build responsive and user-friendly web interfaces using React.js or similar frontend frameworks.
- Write clean, maintainable, and well-tested code.
- Design and interact with SQL and NoSQL databases.
- Debug software issues and improve application performance.
- Work with Git and participate in collaborative software development.
- Write unit tests and participate in code reviews.
- Integrate third-party APIs and external services.
- Deploy applications using cloud or containerized infrastructure.
- Explore and integrate AI/LLM APIs into software products where appropriate.
- Participate in system design discussions and contribute to technical documentation.

Required Skills
- Strong programming fundamentals in C++, Java, Python, or JavaScript/TypeScript.
- Good understanding of Data Structures and Algorithms.
- Knowledge of Object-Oriented Programming.
- Understanding of DBMS and SQL.
- Familiarity with Operating Systems and Computer Networks.
- Experience with Git/GitHub.
- Basic understanding of REST APIs and backend development.
- Problem-solving and debugging skills.
- Ability to learn new technologies quickly.

Preferred Skills
- Experience with React.js.
- Experience with Node.js / Express.js or FastAPI.
- Familiarity with MongoDB or PostgreSQL.
- Knowledge of Docker and cloud platforms such as AWS, Azure, or GCP.
- Familiarity with CI/CD and GitHub Actions.
- Experience working with AI/LLM APIs such as OpenAI, Gemini, or Groq.
- Understanding of basic system design and scalable application architecture.
- Previous internship, hackathon, open-source contribution, or significant personal project experience.

Qualifications
- Currently pursuing a B.Tech/B.E. in Computer Science, Electrical Engineering, Electronics, or a related technical field.
- Expected graduation in 2027 or 2028.
- Strong academic and programming fundamentals.
- Candidates with strong projects and competitive programming experience are encouraged to apply.

What We Look For
- Strong analytical and problem-solving ability.
- Ability to write clean and understandable code.
- Curiosity and willingness to learn.
- Good communication and teamwork.
- Ability to take ownership of tasks.
- Interest in building real-world software products.
"""


def _fallback_parse(jd_text: str) -> JobDescription:
    """Minimal heuristic parser used when the LLM fails."""
    lines = jd_text.splitlines()
    role = lines[0].strip() if lines else "Unknown Role"
    required_skills: list[str] = []
    capture = False
    for line in lines:
        if line.strip().lower().startswith("required skills"):
            capture = True
            continue
        if capture:
            stripped = line.strip()
            if stripped.startswith("-"):
                skill = stripped.lstrip("- ").split(",")[0].strip()
                required_skills.append(skill)
            elif stripped:
                break  # stop at next non-empty, non-bullet line
    return JobDescription(role=role, required_skills=required_skills)


def main() -> None:
    # ------------------------------------------------------------------
    # 0. Validate API key
    # ------------------------------------------------------------------
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    client = Groq(api_key=api_key)

    # ------------------------------------------------------------------
    # 1. Parse Job Description
    # ------------------------------------------------------------------
    print("Parsing job description …")
    try:
        job: JobDescription = parse_job_description(SAMPLE_JD, client=client, max_tokens=2000)
    except Exception as exc:
        print(f"LLM parsing failed ({exc}). Falling back to heuristic extraction.", file=sys.stderr)
        job = _fallback_parse(SAMPLE_JD)

    print("\n=== Parsed Job Description ===")
    print(job)
    print(f"\nRequired skills detected: {len(job.required_skills)}")
    for s in job.required_skills:
        print(f"  • {s}")

    # ------------------------------------------------------------------
    # 2. Process resumes
    # ------------------------------------------------------------------
    results = []
    resumes_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resumes")

    if not os.path.isdir(resumes_dir):
        print("\nNo 'resumes/' folder found – skipping resume matching.", file=sys.stderr)
    else:
        resume_files = [
            f for f in os.listdir(resumes_dir)
            if os.path.isfile(os.path.join(resumes_dir, f))
        ]
        if not resume_files:
            print("\n'resumes/' folder is empty – no resumes to process.", file=sys.stderr)
        else:
            print(f"\nFound {len(resume_files)} resume(s) in '{resumes_dir}'.\n")
            for filename in resume_files:
                file_path = os.path.join(resumes_dir, filename)
                text = read_resume(file_path)
                if text is None:
                    print(f"  [SKIP] Could not read: {filename}", file=sys.stderr)
                    continue
                resume = Resume(filename=filename, raw_text=text)
                result = match_resume(job, resume)
                results.append(result)
                print(f"=== {filename} ===")
                print(f"  Score         : {result.score:.2%}")
                print(f"  Matched skills: {', '.join(result.matched_skills) or 'None'}")

    # ------------------------------------------------------------------
    # 3. Save results to JSON
    # ------------------------------------------------------------------
    results_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "match_results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump([r.model_dump() for r in results], f, ensure_ascii=False, indent=2)
    print(f"\nMatch results saved -> {results_path}\n")


if __name__ == "__main__":
    main()
