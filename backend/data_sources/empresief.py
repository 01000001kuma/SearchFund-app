from .base import DataSource
from typing import Optional, Dict, Any, List

class EmpresiFSource(DataSource):
    """
    Fuente de datos financieros EmpresiF
    
    Proporciona datos financieros detallados:
    - Facturación
    - EBITDA
    - Balances
    - Evolución financiera
    
    Requiere suscripción (€30-50/mes)
    """
    
    def __init__(self):
        self.api_key = None  # Se configurará cuando haya suscripción
        self.base_url = "https://api.empresief.com/v1"  # URL ficticia - cambiar cuando tengamos la real
    
    @property
    def name(self) -> str:
        return "empresief"
    
    @property
    def is_free(self) -> bool:
        return False  # Requiere suscripción
    
    @property
    def provides_financial_data(self) -> bool:
        return True  # Proporciona EBITDA, facturación, etc.
    
    def is_configured(self) -> bool:
        """Solo activo cuando haya API key configurada"""
        return self.api_key is not None
    
    def configure(self, api_key: str):
        """Configurar API key de EmpresiF"""
        self.api_key = api_key
    
    async def get_company(self, identifier: str) -> Optional[Dict[str, Any]]:
        """
        Obtener datos financieros de EmpresiF
        
        Args:
            identifier: CIF de la empresa
            
        Returns:
            Diccionario con datos financieros o None
        """
        if not self.is_configured():
            return None
        
        # TODO: Implementar cuando tengamos API key y URL real
        # Por ahora retorna None (placeholder)
        
        # Ejemplo de implementación futura:
        # try:
        #     url = f"{self.base_url}/company/{identifier}"
        #     headers = {"Authorization": f"Bearer {self.api_key}"}
        #     response = await self.client.get(url, headers=headers)
        #     if response.status_code == 200:
        #         data = response.json()
        #         return self._format_response(data)
        #     return None
        # except Exception as e:
        #     logger.error(f"Error en EmpresiF: {e}")
        #     return None
        
        return None
    
    async def search_companies(self, query: str, filters: Dict = None,
                               cached_lookup: Any = None) -> List[Dict]:
        """
        Buscar empresas (no disponible en EmpresiF)
        
        EmpresiF solo permite buscar por CIF, no por texto libre
        """
        # EmpresiF no tiene búsqueda por texto
        return []
    
    def _format_response(self, raw_data: Dict) -> Optional[Dict]:
        """Formatear respuesta de EmpresiF"""
        if not raw_data:
            return None
        
        # TODO: Adaptar cuando tengamos la respuesta real de la API
        return {
            "financial": {
                "revenue": raw_data.get("revenue"),
                "ebitda": raw_data.get("ebitda"),
                "ebitda_margin": raw_data.get("ebitda_margin"),
                "net_profit": raw_data.get("net_profit"),
                "employees": raw_data.get("employees"),
                "source": "empresief",
                "year": raw_data.get("year"),
                "confidence": 0.9  # Alta confianza en datos oficiales
            }
        }
