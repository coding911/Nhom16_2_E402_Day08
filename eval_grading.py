import json
from groq import Groq

# =========================
# CONFIG
# =========================
INPUT_QUESTIONS = "grading_questions.json"
INPUT_RESULTS = "grading_results.json"
OUTPUT_FILE = "grading_scores.json"

MODEL = "openai/gpt-oss-120b"  

client = Groq(api_key="gsk_...")


# =========================
# LOAD
# =========================
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# =========================
# LLM JUDGE
# =========================
def llm_grade(question, answer, sources, criteria, max_points):
    system_prompt = """
Bạn là giám khảo chấm hệ thống RAG.

CHỈ được chấm theo rule sau:

- Full: đáp ứng TẤT CẢ criteria → 100%
- Partial: ≥50% criteria, không hallucinate → 50%
- Zero: <50% criteria → 0
- Penalty: nếu có hallucination → -50%

Hallucination = thông tin KHÔNG có trong tài liệu.

Output JSON format:
{
  "grade": "Full | Partial | Zero | Penalty",
  "reason": "...",
  "score": number
}
"""

    user_prompt = f"""
Question:
{question}

Answer:
{answer}

Sources:
{sources}

Grading Criteria:
{criteria}

Max Points: {max_points}

Hãy chấm điểm.
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()}
        ],
        temperature=0
    )

    text = response.choices[0].message.content.strip()

    try:
        result = json.loads(text)
    except:
        # fallback nếu model trả sai format
        return {
            "grade": "Zero",
            "score": 0,
            "reason": "Invalid LLM output"
        }

    return result


# =========================
# MAIN
# =========================
def main():
    questions = load_json(INPUT_QUESTIONS)
    results = load_json(INPUT_RESULTS)

    result_map = {r["id"]: r for r in results}

    final_scores = []
    total_score = 0
    max_total = 0

    for q in questions:
        qid = q["id"]
        max_points = q["points"]
        max_total += max_points

        result = result_map.get(qid, {})
        answer = result.get("answer", "")
        sources = result.get("sources", [])

        judge = llm_grade(
            question=q["question"],
            answer=answer,
            sources=sources,
            criteria=q.get("grading_criteria", []),
            max_points=max_points
        )

        score = judge.get("score", 0)
        total_score += score

        final_scores.append({
            "id": qid,
            "grade": judge.get("grade"),
            "score": score,
            "max_score": max_points,
            "reason": judge.get("reason")
        })

        print(f"{qid}: {judge.get('grade')} ({score}/{max_points})")

    # =========================
    # SUMMARY
    # =========================
    summary = {
        "total_score": total_score,
        "max_score": max_total,
        "percentage": (total_score / max_total) * 100 if max_total else 0
    }

    output = {
        "results": final_scores,
        "summary": summary
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("\n📊 FINAL SCORE:")
    print(summary)


if __name__ == "__main__":
    main()