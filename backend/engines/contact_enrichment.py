"""
Enriquecimiento de contactos de una empresa mediante búsqueda en internet
+ extracción LLM.

Dado el nombre (y opcionalmente CIF) de una PYME, este módulo:
1. Busca en internet (DuckDuckGo HTML, gratuito, sin API key).
2. Recoge texto relevante de los resultados (título + snippet).
3. El LLM (Ollama local o nube) extrae estructura: website, phone, email.

Devuelve un dict limpio que se puede guardar en Company (via /contact).
"""
import logging
import re
from typing import Dict, Optional, List

import httpx

from .llm import get_llm_engine, LLMError

logger = logging.getLogger(__name__)

DDG_URL = "https://html.duckduckgo.com/html/"

# Prompt de sistema para extraer contactos en JSON estricto
EXTRACT_SYSTEM = """
Eres un asistente especializado en extraer datos de contacto de PYMES españolas
para un search fund. A partir del texto de resultados de búsqueda web de una
empresa, devuelve un objeto JSON con estas claves (usa null si no aparece):

{
  "website": "https://dominio.com" o null,
  "phone": "número teléfono (formato español, con prefijo si existe)" o null,
  "email": "email de contacto" o null
}

Reglas:
- website: solo un dominio principal de la empresa (no directorios).
- phone: solo teléfonos reales de la empresa (fijos 9xx, móviles 6xx/7xx o +34).
- email: solo correos que pertenezcan al dominio de la empresa u oficiales.
- No inventes datos: si no está en el texto, pon null.
"""


def _clean_text(text: str, max_len: int = 800) -> str:
    """Limpiar y truncar texto."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()[:max_len]


class ContactEnricher:
    """Busca datos de contacto de una empresa en internet y los extrae con LLM."""

    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout

    async def search_web(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Buscar en DuckDuckGo HTML (gratuito). Devuelve lista de
        {title, snippet} que servirá de contexto para el LLM.
        """
        results: List[Dict] = []
        params = {"q": query, "kl": "es-es"}
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.get(DDG_URL, params=params, headers=headers)
                resp.raise_for_status()
                html = resp.text

                # Trocear por resultados: los enlaces de resultado vienen en <a class="result__a">
                for m in re.finditer(
                    r'<a[^>]*class="result__a"[^>]*>(.*?)</a>.*?'
                    r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
                    html, re.S
                ):
                    title = _clean_text(re.sub(r"<[^>]+>", "", m.group(1)))
                    snippet = _clean_text(re.sub(r"<[^>]+>", "", m.group(2)))
                    results.append({"title": title, "snippet": snippet})
                    if len(results) >= max_results:
                        break
        except Exception as e:
            logger.warning("Error en búsqueda web para %r: %s", query, e)

        return results

    async def enrich(self, company_name: str, cif: str = None,
                     website_hint: str = None) -> Dict[str, Optional[str]]:
        """
        Enriquecer contactos de una empresa.

        Args:
            company_name: nombre registral de la empresa
            cif: CIF (opcional, para afinar la búsqueda)
            website_hint: web conocida (opcional)

        Returns:
            {"website": ..., "phone": ..., "email": ...} (null si no se encuentra)
        """
        # Construir una query bien afinada: nombre + CIF (si hay) + objetivo
        query_parts = [company_name]
        if cif:
            query_parts.append(cif)
        query_parts.append("teléfono email contacto")
        query = " ".join(query_parts)

        # Una sola búsqueda con contexto suficiente
        results = await self.search_web(query, max_results=8)

        # Si no salió nada, reintento con la web como pista
        if not results and website_hint and website_hint not in query:
            results = await self.search_web(f"{company_name} {website_hint}", max_results=5)

        # Reducir el contexto a los primeros resultados: ya suelen contener
        # teléfono/email/web y así la generación LLM es más rápida.
        context = [
            f"- {t['title']}: {t['snippet']}" for t in results if t.get("title")
        ][:4]
        if not context:
            return {"website": None, "phone": None, "email": None}

        # Una sola extracción LLM de todo el contexto
        content = "\n".join(context)
        try:
            data = await get_llm_engine().extract_json(EXTRACT_SYSTEM, content)
        except LLMError as e:
            logger.warning("LLM falló extrayendo contactos de %r: %s", company_name, e)
            return {"website": website_hint, "phone": None, "email": None}

        # Sanear
        website = self._sanitize_website(data.get("website") or (website_hint if website_hint else None))
        phone = self._sanitize_phone(data.get("phone"))
        email = self._sanitize_email(data.get("email"))

        return {"website": website, "phone": phone, "email": email}

    @staticmethod
    def _sanitize_website(v) -> Optional[str]:
        if not v:
            return None
        v = str(v).strip().rstrip("/")
        if v.startswith("http"):
            return v
        return f"https://{v}" if "." in v else None

    @staticmethod
    def _sanitize_phone(v) -> Optional[str]:
        if not v:
            return None
        v = str(v).strip()
        # teléfonos españoles
        if re.search(r"\+?34?\s?[6-9]\d{8}", v) or re.search(r"\+34\s?\d{9}", v):
            return v
        return v if re.search(r"\d{9,}", v) else None

    @staticmethod
    def _sanitize_email(v) -> Optional[str]:
        if not v:
            return None
        v = str(v).strip()
        return v if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v) else None


# Instancia global
contact_enricher = ContactEnricher()
