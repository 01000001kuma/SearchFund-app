"""
Motor LLM híbrido para Search Fund Tool.

Dos proveedores con la misma interfaz:
- OllamaLLMProvider: local y gratuito (por defecto).
- OpenAILLMProvider: compatible con la API OpenAI (chat completions),
  sirve para OpenAI, y para cualquier proveedor compatible (Ollama también
  expone un endpoint OpenAI-compatible en /v1, pero aquí usamos el nativo).

El proveedor activo se elige por configuración (backend.config.LLMSettings),
sin tocar el resto del código. Esto permite pasar de local a nube en caliente.
"""
import json
import logging
from typing import Optional, List, Dict, Any

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Error genérico del LLM"""


class BaseLLMProvider:
    """Interfaz base de un proveedor LLM"""

    name: str = "base"

    async def chat(self, messages: List[Dict[str, str]],
                   temperature: Optional[float] = None,
                   max_tokens: Optional[int] = None) -> str:
        """Enviar una conversación y devolver el texto de respuesta."""
        raise NotImplementedError

    async def complete(self, prompt: str,
                       temperature: Optional[float] = None,
                       max_tokens: Optional[int] = None) -> str:
        """Generar texto a partir de un prompt único."""
        return await self.chat(
            [{"role": "user", "content": prompt}],
            temperature=temperature, max_tokens=max_tokens,
        )


class OllamaLLMProvider(BaseLLMProvider):
    """Proveedor local vía Ollama (API nativa /api/chat)"""

    name = "ollama"

    def __init__(self, base_url: str = None, model: str = None):
        cfg = settings.llm
        self.base_url = (base_url or cfg.ollama_base_url).rstrip("/")
        self.model = model or cfg.ollama_model
        self.timeout = cfg.timeout

    async def chat(self, messages: List[Dict[str, str]],
                   temperature: Optional[float] = None,
                   max_tokens: Optional[int] = None) -> str:
        cfg = settings.llm
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else cfg.temperature,
                "num_predict": max_tokens if max_tokens is not None else cfg.max_tokens,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return (data.get("message") or {}).get("content", "").strip()
        except httpx.HTTPStatusError as e:
            raise LLMError(f"Ollama HTTP {e.response.status_code}: {e.response.text[:300]}") from e
        except Exception as e:
            raise LLMError(f"Ollama error: {e}") from e


class OpenAILLMProvider(BaseLLMProvider):
    """Proveedor de nube compatible con la API OpenAI (chat completions)"""

    name = "openai"

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        cfg = settings.llm
        self.api_key = api_key or cfg.openai_api_key
        self.base_url = (base_url or cfg.openai_base_url).rstrip("/")
        self.model = model or cfg.openai_model
        self.timeout = cfg.timeout

        if not self.api_key:
            raise LLMError("OPENAI_API_KEY no configurada para el proveedor openai")

    async def chat(self, messages: List[Dict[str, str]],
                   temperature: Optional[float] = None,
                   max_tokens: Optional[int] = None) -> str:
        cfg = settings.llm
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else cfg.temperature,
            "max_tokens": max_tokens if max_tokens is not None else cfg.max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                return (data["choices"][0]["message"]["content"] or "").strip()
        except httpx.HTTPStatusError as e:
            raise LLMError(f"OpenAI HTTP {e.response.status_code}: {e.response.text[:300]}") from e
        except Exception as e:
            raise LLMError(f"OpenAI error: {e}") from e


class LLMEngine:
    """Fachada sobre el proveedor activo configurado.

    Mantiene dos proveedores:
    - ``provider`` (chat/generación completa) usando el modelo principal.
    - ``fast_provider`` (extracción estructurada de JSON) usando un modelo
      pequeño y rápido en local, o el mismo proveedor en la nube.
    """

    def __init__(self):
        cfg = settings.llm
        if cfg.provider == "ollama":
            self.provider: BaseLLMProvider = OllamaLLMProvider()
            fast_model = cfg.ollama_fast_model or cfg.ollama_model
            self.fast_provider = OllamaLLMProvider(model=fast_model)
        else:
            if cfg.provider == "openai":
                self.provider = OpenAILLMProvider()
            else:
                # Por simplicidad, tratamos cualquier otro proveedor (anthropic
                # incluido) mediante la API OpenAI-compatible configurada.
                logger.warning("LLM_PROVIDER %r -> usando shape OpenAI", cfg.provider)
                self.provider = OpenAILLMProvider()
            self.fast_provider = self.provider

    @property
    def provider_name(self) -> str:
        return self.provider.name

    async def chat(self, messages, **kwargs) -> str:
        return await self.provider.chat(messages, **kwargs)

    async def complete(self, prompt, **kwargs) -> str:
        return await self.provider.complete(prompt, **kwargs)

    async def fast_complete(self, prompt, **kwargs) -> str:
        """Generación con el modelo rápido (extracción estructurada).

        Si el modelo rápido no existe en Ollama (p. ej. fue borrado o el
        default cambió), reintenta una vez con el modelo principal.
        """
        try:
            return await self.fast_provider.complete(prompt, **kwargs)
        except LLMError as e:
            if "not found" in str(e) and self.fast_provider is not self.provider:
                logger.warning(
                    "Modelo rápido %r no disponible; usando el modelo principal %r",
                    getattr(self.fast_provider, "model", "?"), self.model,
                )
                self.fast_provider = self.provider
                return await self.provider.complete(prompt, **kwargs)
            raise

    async def health(self) -> Dict[str, Any]:
        """Comprobar que el LLM está disponible."""
        try:
            await self.provider.complete("Responde solo: ok")
            return {"configured": True, "provider": self.provider_name}
        except Exception as e:
            return {"configured": False, "provider": self.provider_name, "error": str(e)}

    async def extract_json(self, system_prompt: str, content: str) -> Dict[str, Any]:
        """
        Pedir al LLM que devuelva JSON estricto. Se intenta parsear el JSON
        de la respuesta; útil para extracción estructurada (p.ej. contactos).
        Usa el modelo rápido (más veloz en CPU) y limita los tokens de salida.
        """
        raw = await self.fast_provider.complete(
            f"{system_prompt}\n\nCONTENIDO:\n{content}\n\n"
            "Devuelve ÚNICAMENTE JSON válido, sin markdown ni texto extra.",
            max_tokens=300,
        )
        return self._parse_json(raw)

    @staticmethod
    def _parse_json(raw: str) -> Dict[str, Any]:
        """Parsear JSON robusto (tolera ```json ... ``` y texto alrededor)."""
        s = raw.strip()
        # quitar fences markdown
        if s.startswith("```"):
            s = s.strip("`")
            if s.startswith("json"):
                s = s[4:]
            s = s.strip()
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            # intentar extraer primer objeto { ... }
            start = s.find("{")
            end = s.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(s[start:end + 1])
                except json.JSONDecodeError:
                    pass
            raise LLMError(f"No se pudo parsear JSON del LLM: {s[:300]}")


# Lazy singleton — no se instancia en import para evitar crash si falta OPENAI_API_KEY
_llm_engine: Optional["LLMEngine"] = None


def get_llm_engine() -> "LLMEngine":
    global _llm_engine
    if _llm_engine is None:
        _llm_engine = LLMEngine()
    return _llm_engine
