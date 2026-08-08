import os
import sys
import time
import json

sys.stdout.reconfigure(encoding='utf-8')
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from app.services.rag_service import dual_rag_pipeline
from app.models.schemas import RAGRequest

TEST_SUITE = [
    # --- DOMAIN 1: Labour Rights ---
    {"domain": "Labour Rights",            "id": "L1", "q": "What are the legal working hour limits and overtime compensation rules for factory workers in India?"},
    {"domain": "Labour Rights",            "id": "L2", "q": "What legal recourse does an employee have if an employer wrongfully terminates them without notice pay?"},
    {"domain": "Labour Rights",            "id": "L3", "q": "Are contract laborers entitled to equal pay for equal work under Indian labor law?"},
    {"domain": "Labour Rights",            "id": "L4", "q": "What maternity leave benefits are mandated for female employees under the Maternity Benefit Act?"},
    {"domain": "Labour Rights",            "id": "L5", "q": "How can an unorganized worker register and file a complaint for unpaid minimum wages?"},
    # --- DOMAIN 2: Crime ---
    {"domain": "Crime",                    "id": "C1", "q": "What is the difference between cognizable and non-cognizable offenses under BNSS?"},
    {"domain": "Crime",                    "id": "C2", "q": "What are the legal conditions and procedure for obtaining anticipatory bail?"},
    {"domain": "Crime",                    "id": "C3", "q": "What constitutes cyber fraud under the IT Act and how can a victim report it?"},
    {"domain": "Crime",                    "id": "C4", "q": "What is the punishment for criminal breach of trust under the Indian legal code?"},
    {"domain": "Crime",                    "id": "C5", "q": "What rights does an arrested person have during police interrogation?"},
    # --- DOMAIN 3: Women Violence / Marriage ---
    {"domain": "Women Violence & Marriage","id": "W1", "q": "What legal remedies are available to a woman facing domestic violence under PWDVA?"},
    {"domain": "Women Violence & Marriage","id": "W2", "q": "What are the legal grounds for divorce under the Hindu Marriage Act?"},
    {"domain": "Women Violence & Marriage","id": "W3", "q": "What constitutes dowry harassment under Section 498A IPC and what are the penalties?"},
    {"domain": "Women Violence & Marriage","id": "W4", "q": "What protection does the POSH Act provide to women against workplace sexual harassment?"},
    {"domain": "Women Violence & Marriage","id": "W5", "q": "Can a married woman claim interim maintenance from her husband under Section 125 CrPC?"},
    # --- DOMAIN 4: Land Dispute ---
    {"domain": "Land Dispute",             "id": "LD1","q": "How can a property owner resolve an illegal encroachment dispute on agricultural land?"},
    {"domain": "Land Dispute",             "id": "LD2","q": "What documents are mandatory to verify clear title before purchasing ancestral land?"},
    {"domain": "Land Dispute",             "id": "LD3","q": "What is adverse possession under Indian property law and what is the statutory time limit?"},
    {"domain": "Land Dispute",             "id": "LD4","q": "How are land inheritance and succession rights determined for daughters under the Hindu Succession Amendment Act?"},
    {"domain": "Land Dispute",             "id": "LD5","q": "What is the procedure for filing a civil suit for partition of joint family property?"},
    # --- DOMAIN 5: Anonymous / General ---
    {"domain": "Anonymous / General",      "id": "A1", "q": "How do I renew my driver's license online in India?"},
    {"domain": "Anonymous / General",      "id": "A2", "q": "What are the steps to register a small business as an MSME?"},
    {"domain": "Anonymous / General",      "id": "A3", "q": "Can a landlord increase residential rent without prior notice?"},
    {"domain": "Anonymous / General",      "id": "A4", "q": "How do I file an RTI application to check government scheme status?"},
    {"domain": "Anonymous / General",      "id": "A5", "q": "What is the process to get a passport reissued if it expires?"},
]

SCORE_BANDS = [
    (5.0,  float('inf'), "EXCELLENT — Highly relevant legal passage"),
    (2.0,  5.0,          "GOOD      — Relevant but partial match"),
    (0.0,  2.0,          "FAIR      — Marginal relevance"),
    (-3.0, 0.0,          "POOR      — Low relevance / partial corpus gap"),
    (float('-inf'), -3.0,"OFF-DOMAIN — Query rejected correctly (fallback to LLM)"),
]

def classify_score(score, passages):
    if passages == 0:
        return "NO PASSAGES RETURNED"
    for lo, hi, label in SCORE_BANDS:
        if lo <= score < hi:
            return label
    return "UNKNOWN"

def run_rag_benchmark():
    print("=" * 88)
    print(" PHASE 1: RAG-ONLY RETRIEVAL BENCHMARK (25 QUESTIONS)")
    print(" Measuring: passages returned, top rerank score, RAG status, retrieval time")
    print("=" * 88)
    
    results = []
    domain_stats = {}

    for idx, item in enumerate(TEST_SUITE, start=1):
        domain = item["domain"]
        qid    = item["id"]
        q      = item["q"]

        t0 = time.perf_counter()
        rag_res = dual_rag_pipeline.retrieve_context(RAGRequest(query=q, language="en"))
        rag_ms  = (time.perf_counter() - t0) * 1000

        n_passages  = len(rag_res.passages)
        top_score   = rag_res.passages[0].score if rag_res.passages else 0.0
        top_source  = rag_res.passages[0].source_citation[:60] if rag_res.passages else "N/A"
        quality     = classify_score(top_score, n_passages)
        sources     = [p.source_citation for p in rag_res.passages[:3]]

        row = {
            "idx": idx, "id": qid, "domain": domain,
            "query": q,
            "rag_status": rag_res.status,
            "passages": n_passages,
            "top_score": round(top_score, 4),
            "quality": quality,
            "top_source": top_source,
            "rag_ms": round(rag_ms, 2),
            "sources": sources,
        }
        results.append(row)

        if domain not in domain_stats:
            domain_stats[domain] = {"scores": [], "statuses": []}
        domain_stats[domain]["scores"].append(top_score)
        domain_stats[domain]["statuses"].append(rag_res.status)

        print(f"\n[{idx:2d}/25] {domain:30s} | {qid}")
        print(f"       Q: {q[:90]}")
        print(f"       Passages: {n_passages} | Top Score: {top_score:+.4f} | Status: {rag_res.status} | Time: {rag_ms:.1f}ms")
        print(f"       Quality: {quality}")
        print(f"       Top Source: {top_source}")

    # ---- Summary Table ----
    print("\n\n" + "=" * 88)
    print(" BENCHMARK SUMMARY BY DOMAIN")
    print("=" * 88)
    print(f"  {'Domain':<30} {'Avg Score':>10} {'Min':>8} {'Max':>8} {'Status Mix'}")
    print(f"  {'-'*30} {'-'*10} {'-'*8} {'-'*8} {'-'*25}")
    
    for dom, stats in domain_stats.items():
        scores    = stats["scores"]
        avg_score = sum(scores) / len(scores)
        statuses  = stats["statuses"]
        status_str = f"suf={statuses.count('sufficient')} | needs_cl={statuses.count('needs_clarification')} | abs={statuses.count('abstain')}"
        print(f"  {dom:<30} {avg_score:>+10.4f} {min(scores):>+8.4f} {max(scores):>+8.4f}  {status_str}")

    # Overall scoring distribution
    all_scores  = [r["top_score"] for r in results]
    all_statuses = [r["rag_status"] for r in results]
    print("\n  Overall Average Rerank Score:", round(sum(all_scores)/len(all_scores), 4))
    print(f"  Status Distribution: sufficient={all_statuses.count('sufficient')} | needs_clarification={all_statuses.count('needs_clarification')} | abstain={all_statuses.count('abstain')}")
    
    # Verdict — based on real CrossEncoder (ms-marco-MiniLM-L-6-v2) scores
    print("\n" + "=" * 88)
    avg_all    = sum(all_scores)/len(all_scores)
    n_suf      = all_statuses.count('sufficient')
    n_ood      = sum(1 for s in all_scores if s < -3.0)
    ood_correct = sum(1 for r in results if r['domain'] == 'Anonymous / General' and r['top_score'] < -3.0)

    print(f" CROSS-ENCODER: ms-marco-MiniLM-L-6-v2 (real semantic scores)")
    print(f" Sufficient (score >= 0):    {n_suf}/25 queries")
    print(f" Off-domain rejected (<-3):  {n_ood}/25 queries  (out-of-domain correctly rejected: {ood_correct}/5)")
    print()
    if n_suf >= 10 and ood_correct >= 4:
        verdict = "RAG IS WORKING — Strong in-domain retrieval + correct out-of-domain rejection."
    elif n_suf >= 6:
        verdict = "RAG IS PARTIALLY WORKING — Core domains covered; some corpus gaps remain."
    else:
        verdict = "RAG NEEDS MORE DATA — Too many in-domain queries scoring below threshold."
    print(f" VERDICT: {verdict}")
    print(f"\n CORPUS GAPS: Queries that scored POOR/OFF-DOMAIN within target domains need more documents:")
    for r in results:
        if r['domain'] != 'Anonymous / General' and r['top_score'] < 0.0:
            print(f"   - [{r['id']}] {r['query'][:75]}  (score: {r['top_score']:+.2f})")
    print("=" * 88)

    # Save JSON
    out_path = os.path.join(base_dir, "benchmark_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n Raw results saved to: {out_path}\n")

if __name__ == "__main__":
    run_rag_benchmark()
