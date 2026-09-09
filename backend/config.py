"""
Configuración del proyecto Search Fund Tool.

Permite el uso HÍBRIDO de LLM:
- Por defecto usa Ollama local (gratuito, offline, sin API key).
- Si se define LLM_PROVIDER=openai (u otro compatible con la API OpenAI),
  usa un modelo de pago en la nube. Se puede cambiar en caliente por entorno.

Variables de entorno soportadas (ver .env):
  LLM_PROVIDER       : "ollama" (default) | "openai" | "anthropic"
  OLLAMA_BASE_URL    : http://127.0.0.1:11434 (default)
  OLLAMA_MODEL       : llama3.1:8b (default)
  OPENAI_API_KEY     : clave (solo si LLM_PROVIDER != ollama)
  OPENAI_BASE_URL    : https://api.openai.com/v1 (default)
  OPENAI_MODEL       : gpt-4o-mini (default)
  ANTHROPIC_API_KEY  : clave (solo si LLM_PROVIDER == anthropic)
  ANTHROPIC_MODEL    : claude-3-5-haiku-latest (default)
"""
import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv

# Carga variables de entorno desde .env si existe
load_dotenv()


def _get_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class LLMSettings:
    """Configuración del proveedor LLM (híbrido)"""
    provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "ollama").lower())

    # Ollama local
    ollama_base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.1:8b"))
    # Modelo "rápido" para extracciones estructuradas (contactos, fit score),
    # más pequeño y veloz en CPU. Vacío => se reutiliza el modelo principal.
    ollama_fast_model: str = field(default_factory=lambda: os.getenv("OLLAMA_FAST_MODEL", ""))  # vacío = usa el modelo principal

    # API de pago (OpenAI-compatible)
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_base_url: str = field(default_factory=lambda: os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))

    # API de pago (Anthropic)
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    anthropic_model: str = field(default_factory=lambda: os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"))

    # Parámetros generación
    temperature: float = field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.2")))
    max_tokens: int = field(default_factory=lambda: int(os.getenv("LLM_MAX_TOKENS", "2048")))
    timeout: float = field(default_factory=lambda: float(os.getenv("LLM_TIMEOUT", "300.0")))

    @property
    def use_cloud(self) -> bool:
        """True si se usa un proveedor de pago en la nube"""
        return self.provider != "ollama"

    def describe(self) -> dict:
        """Descripción legible de la configuración actual (sin exponer claves)"""
        return {
            "provider": self.provider,
            "model": (
                self.ollama_model if self.provider == "ollama"
                else self.openai_model if self.provider == "openai"
                else self.anthropic_model
            ),
            "fast_model": (
                self.ollama_fast_model if self.provider == "ollama" else None
            ),
            "use_cloud": self.use_cloud,
            "ollama_base_url": self.ollama_base_url if self.provider == "ollama" else None,
            "cloud_api_configured": bool(
                (self.provider == "openai" and self.openai_api_key)
                or (self.provider == "anthropic" and self.anthropic_api_key)
            ),
        }


@dataclass
class Settings:
    """Configuración global del proyecto"""
    llm: LLMSettings = field(default_factory=LLMSettings)
    db_path: str = field(default_factory=lambda: os.getenv("DB_PATH", "data/search_fund.db"))
    cors_origins: List[str] = field(default_factory=lambda: [
        o.strip() for o in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:5173,http://localhost:5174,null,file://",
        ).split(",") if o.strip()
    ])

    # Búsqueda de candidatas (criterios Cabiedes)
    search_max_results: int = field(default_factory=lambda: int(os.getenv("SEARCH_MAX_RESULTS", "8")))
    search_provinces: List[str] = field(default_factory=lambda: [p.strip() for p in
        os.getenv("SEARCH_PROVINCES", "").split(",") if p.strip()])
    # Sectores/CNAE a explorar
    search_sectors: List[str] = field(default_factory=lambda: [s.strip() for s in
        os.getenv("SEARCH_SECTORS", "transportes,construcciones,alimentacion,industrial").split(",") if s.strip()])

    def describe(self) -> dict:
        return {
            "llm": self.llm.describe(),
            "db_path": self.db_path,
            "search_max_results": self.search_max_results,
            "search_provinces": self.search_provinces,
            "search_sectors": self.search_sectors,
        }


# Instancia global reutilizable
settings = Settings()
