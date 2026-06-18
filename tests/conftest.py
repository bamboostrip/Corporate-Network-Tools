"""pytest 全局 fixtures。"""
import sys
from pathlib import Path

# 确保 src 在 path 中（pyproject.toml 已配 pythonpath，这里双保险）
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
