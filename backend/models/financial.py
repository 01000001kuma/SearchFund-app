from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class FinancialData(BaseModel):
    """Datos financieros de la empresa (multi-source)"""
    
    # Datos principales
    revenue: Optional[float] = None          # Facturación anual (€)
    ebitda: Optional[float] = None           # EBITDA (€)
    ebitda_margin: Optional[float] = None    # Margen EBITDA (%)
    net_profit: Optional[float] = None       # Beneficio neto (€)
    employees: Optional[int] = None          # Número de empleados
    
    # Metadatos
    source: Optional[str] = None             # "empresief", "web", "manual", "borme"
    year: Optional[int] = None               # Año de los datos financieros
    last_updated: Optional[datetime] = None  # Última actualización
    
    # Control de calidad
    confidence: Optional[float] = None       # Nivel de confianza (0-1)
    notes: Optional[str] = None              # Notas adicionales
    
    def is_complete(self) -> bool:
        """Verificar si hay datos suficientes para scoring financiero"""
        return self.revenue is not None and self.ebitda is not None
    
    def has_partial_data(self) -> bool:
        """Verificar si hay algún dato financiero"""
        return any([
            self.revenue is not None,
            self.ebitda is not None,
            self.employees is not None
        ])
    
    def get_score_range(self) -> str:
        """Determinar rango de scoring según EBITDA"""
        if not self.ebitda:
            return "unknown"
        
        if 1_500_000 <= self.ebitda <= 3_000_000:
            return "optimal"      # 1.5M - 3M EBITDA (rango ideal)
        elif 500_000 <= self.ebitda < 1_500_000:
            return "acceptable"   # 500k - 1.5M
        elif self.ebitda > 3_000_000:
            return "large"        # > 3M (puede ser demasiado grande)
        elif self.ebitda > 0:
            return "small"        # < 500k
        else:
            return "negative"     # EBITDA negativo
    
    def format_ebitda(self) -> str:
        """Formatear EBITDA para mostrar"""
        if self.ebitda is None:
            return "No disponible"
        
        if self.ebitda >= 1_000_000:
            return f"{self.ebitda / 1_000_000:.2f}M€"
        elif self.ebitda >= 1_000:
            return f"{self.ebitda / 1_000:.1f}k€"
        else:
            return f"{self.ebitda:.0f}€"
    
    def format_revenue(self) -> str:
        """Formatear facturación para mostrar"""
        if self.revenue is None:
            return "No disponible"
        
        if self.revenue >= 1_000_000:
            return f"{self.revenue / 1_000_000:.2f}M€"
        elif self.revenue >= 1_000:
            return f"{self.revenue / 1_000:.1f}k€"
        else:
            return f"{self.revenue:.0f}€"
