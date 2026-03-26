"""自動科学論文生成。学術論文形式で研究成果を構造化する。"""
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def generate_paper(
    title: str,
    analyses: dict,
    region: str | None = None,
) -> dict:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    abstract = f"本報告では、QuakeMind自律研究エージェントによる{region or '日本全域'}の地震活動分析結果を報告する。"
    if "unified_probability" in analyses:
        abstract += f" 統合ベイズ確率は{analyses['unified_probability']:.2%}と推定された。"

    sections = {
        "title": title,
        "authors": ["QuakeMind Autonomous Research Agent"],
        "date": now,
        "abstract": abstract,
        "introduction": f"日本列島は複数のプレート境界に位置し、世界有数の地震多発地帯である。本研究では、{region or '対象地域'}における最新の地震活動を多角的に分析した。",
        "methodology": "本分析では以下の手法を適用した: (1) Gutenberg-Richter b値解析, (2) ETAS余震モデル, (3) ベイズ変化点検出, (4) マルチモデルアンサンブル, (5) 統一ベイズネットワーク。",
        "results": {},
        "discussion": "",
        "conclusion": "",
        "references": [
            "Ogata, Y. (1988). Statistical models for earthquake occurrences. JASA.",
            "Dieterich, J. (1994). A constitutive law for rate of earthquake production. JGR.",
            "Gutenberg, B. & Richter, C.F. (1944). Frequency of earthquakes in California. BSSA.",
        ],
    }

    # Results セクション
    results = []
    if "b_value" in analyses:
        results.append(f"b値は{analyses['b_value']:.2f}と推定された。")
    if "n_clusters" in analyses:
        results.append(f"{analyses['n_clusters']}個のクラスタが検出された。")
    if "criticality_index" in analyses:
        results.append(f"臨界指標は{analyses['criticality_index']:.3f}であった。")
    sections["results"] = " ".join(results) if results else "特筆すべき異常は検出されなかった。"

    # Discussion
    risk = analyses.get("risk_level", "normal")
    if risk in ("critical", "high"):
        sections["discussion"] = "複数の指標が地震活動の活発化を示しており、継続的な監視が強く推奨される。"
    else:
        sections["discussion"] = "現在の活動は背景レベルの範囲内であるが、定期的なモニタリングの継続が重要である。"

    sections["conclusion"] = f"本分析により、{region or '対象地域'}の地震リスクは「{risk}」レベルと評価された。"

    # Markdown形式で出力
    markdown = f"""# {sections['title']}

**Authors:** {', '.join(sections['authors'])}
**Date:** {sections['date']}

## Abstract
{sections['abstract']}

## 1. Introduction
{sections['introduction']}

## 2. Methodology
{sections['methodology']}

## 3. Results
{sections['results']}

## 4. Discussion
{sections['discussion']}

## 5. Conclusion
{sections['conclusion']}

## References
""" + "\n".join(f"- {r}" for r in sections["references"])

    return {"sections": sections, "markdown": markdown, "word_count": len(markdown.split())}
