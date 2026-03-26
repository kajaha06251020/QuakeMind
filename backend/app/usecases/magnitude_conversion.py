"""マグニチュードスケール統一変換。ML/Mb/Ms→Mw。"""
import logging
logger = logging.getLogger(__name__)

def convert_to_mw(magnitude: float, scale: str = "ML") -> dict:
    """Scordilis (2006) + 経験的変換式。"""
    conversions = {
        "ML": lambda m: 0.67*m+1.17 if m<=6.5 else 0.81*m+0.28,
        "mb": lambda m: 0.85*m+1.03 if m<=6.2 else 1.38*m-2.21,
        "Ms": lambda m: 0.67*m+2.07 if m<=6.1 else 0.99*m+0.08,
        "Mw": lambda m: m,
        "Mjma": lambda m: m-0.171 if m<5 else 0.78*m+1.08,
    }
    func = conversions.get(scale, conversions["ML"])
    mw = round(func(magnitude), 2)
    return {"original_magnitude": magnitude, "original_scale": scale, "mw": mw, "formula": f"Scordilis(2006)" if scale in ("ML","mb","Ms") else "identity" if scale=="Mw" else "JMA empirical"}
