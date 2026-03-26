import numpy as np
from app.usecases.lyapunov import estimate_lyapunov

def test_chaotic():
    # ロジスティック写像（カオス領域 r=3.9）
    x = np.zeros(200)
    x[0] = 0.1
    for i in range(1, 200):
        x[i] = 3.9 * x[i-1] * (1 - x[i-1])
    result = estimate_lyapunov(x)
    assert result["lyapunov_exponent"] > 0
    assert result["system_type"] == "chaotic"

def test_stable():
    # 正弦波（安定）
    x = np.sin(np.linspace(0, 20 * np.pi, 200))
    result = estimate_lyapunov(x)
    assert result["system_type"] in ("stable", "edge_of_chaos")

def test_short():
    result = estimate_lyapunov(np.array([1, 2, 3]))
    assert "error" in result
