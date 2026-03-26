"""多言語出力。日本語と英語の両方で研究成果を生成。"""
import logging
logger = logging.getLogger(__name__)

_TEMPLATES = {
    "risk_summary": {
        "ja": "地震リスク評価: {region}地域のリスクレベルは「{level}」です。統合確率: {prob:.1%}。",
        "en": "Seismic Risk Assessment: The risk level for {region} is '{level}'. Unified probability: {prob:.1%}.",
    },
    "anomaly_alert": {
        "ja": "{region}で異常な地震活動を検出しました（p={p_value:.4f}）。直近の発生率は背景の{gain:.1f}倍です。",
        "en": "Anomalous seismic activity detected in {region} (p={p_value:.4f}). Recent rate is {gain:.1f}x background.",
    },
    "forecast": {
        "ja": "今後{hours}時間以内にM{threshold}以上が発生する確率: {prob:.1%}",
        "en": "Probability of M{threshold}+ within {hours} hours: {prob:.1%}",
    },
}

def translate(template_key: str, language: str = "ja", **kwargs) -> str:
    templates = _TEMPLATES.get(template_key, {})
    template = templates.get(language, templates.get("ja", "テンプレートが見つかりません"))
    try: return template.format(**kwargs)
    except KeyError as e: return f"翻訳エラー: 不足パラメータ {e}"

def bilingual_output(template_key: str, **kwargs) -> dict:
    return {"ja": translate(template_key, "ja", **kwargs), "en": translate(template_key, "en", **kwargs)}
