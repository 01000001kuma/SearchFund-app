from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

class DataSource(ABC):
    """Clase base abstracta para todas las fuentes de datos"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre de la fuente"""
        pass
    
    @property
    @abstractmethod
    def is_free(self) -> bool:
        """Si es gratuita"""
        pass
    
    @property
    @abstractmethod
    def provides_financial_data(self) -> bool:
        """Si proporciona datos financieros (EBITDA, facturación)"""
        pass
    
    @abstractmethod
    async def get_company(self, identifier: str) -> Optional[Dict[str, Any]]:
        """
        Obtener datos de empresa
        
        Args:
            identifier: CIF, slug, o NIF de la empresa
            
        Returns:
            Diccionario con datos de la empresa o None si no se encuentra
        """
        pass
    
    @abstractmethod
    async def search_companies(self, query: str, filters: Dict = None,
                               cached_lookup: Any = None) -> List[Dict]:
        """
        Buscar empresas
        
        Args:
            query: Texto de búsqueda
            filters: Filtros opcionales
            
        Returns:
            Lista de diccionarios con datos de empresas
        """
        pass
    
    def is_configured(self) -> bool:
        """Verificar si la fuente está configurada y lista para usar"""
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado de la fuente"""
        return {
            "name": self.name,
            "is_free": self.is_free,
            "provides_financial_data": self.provides_financial_data,
            "is_configured": self.is_configured()
        }

    async def close(self):
        """Cerrar conexiones de la fuente (override si es necesario)"""
        pass
