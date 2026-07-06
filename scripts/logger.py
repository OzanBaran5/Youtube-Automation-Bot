"""
logger.py — Merkezi loglama modülü.
Konsola ve günlük log dosyasına aynı anda yazar.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# Logs dizinini belirle (config'i import etmeden, circular import önlemi)
_PROJECT_ROOT = Path(__file__).parent.parent
_LOGS_DIR = _PROJECT_ROOT / "logs"
_LOGS_DIR.mkdir(parents=True, exist_ok=True)


def setup_logger(name: str = "yt_shorts") -> logging.Logger:
    """
    Hem konsola (INFO) hem dosyaya (DEBUG) yazan logger döndürür.
    Aynı isimle birden fazla kez çağrılsa da handler tekrarlanmaz.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Handler yoksa ekle (tekrar çağrılmaya karşı)
    if logger.handlers:
        return logger

    _fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Konsol handler (INFO ve üstü)
    _console = logging.StreamHandler(sys.stdout)
    _console.setLevel(logging.INFO)
    _console.setFormatter(_fmt)
    logger.addHandler(_console)

    # Dosya handler (DEBUG ve üstü)
    _today = datetime.now().strftime("%Y-%m-%d")
    _log_file = _LOGS_DIR / f"{_today}.log"
    _file = logging.FileHandler(_log_file, encoding="utf-8")
    _file.setLevel(logging.DEBUG)
    _file.setFormatter(_fmt)
    logger.addHandler(_file)

    return logger


# Proje genelinde kullanılacak tek logger örneği
logger = setup_logger()
