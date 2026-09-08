import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from ..models.company import Company

logger = logging.getLogger(__name__)


class ScoreCalculator:
    """
    Calcula score de candidatura alineado con el Plan Maestro del Proyecto.
    
    Fórmula:
    Score = Σ(Puntos criterios BORME) + Σ(Puntos criterios Financieros)
    
    Ponderación final sugerida: 60% BORME / 40% Financiero
    """

    # Pesos exactos del Plan Maestro
    WEIGHTS = {
        'borme': 0.6,
        'financial': 0.4,
    }

    # Puntos específicos del Plan Maestro
    POINTS = {
        'admin_age_high': 40,     # > 70 años
        'admin_age_med': 30,      # > 65 años
        'admin_age_low': 20,       # > 55 años
        'borme_stability': 15,    # > 5 años sin cambios
        'family_business': 20,    # Mismo apellido admins
        'no_external_council': 10, # Sin consejo externo
        'cnae_compatible': 10,    # Industrial/Logística/B2B
        'revenue_range': 15,       # 10-15M€
        'borme_recent': 25,        # Cambio reciente de admin
    }

    def calculate(self, company: Company) -> Dict[str, Any]:
        # 1. Score BORME (0-100)
        borme_details = self._calculate_borme_score(company)
        borme_score = borme_details['total']

        # 2. Score Financiero (0-100)
        financial_score = None
        if company.financial and company.financial.is_complete():
            financial_score = self._calculate_financial_score(company)

        # 3. Combinación final
        if financial_score is not None:
            final_score = (
                borme_score * self.WEIGHTS['borme'] +
                financial_score * self.WEIGHTS['financial']
            )
            has_financial_data = True
        else:
            final_score = borme_score
            has_financial_data = False

        final_score = round(final_score, 1)
        
        return {
            'total': final_score,
            'borme': round(borme_score, 1),
            'financial': round(financial_score, 1) if financial_score is not None else None,
            'has_financial_data': has_financial_data,
            'interpretation': self._get_interpretation(final_score),
            'breakdown': {
                'borme': borme_details['breakdown'],
                'financial': self._build_financial_breakdown(company, financial_score)
            },
        }

    def _calculate_borme_score(self, company: Company) -> Dict[str, Any]:
        points = 0
        breakdown = {}

        # --- Edad Administrador (Proxy Don/Doña) ---
        age_points = 0
        if company.administrators:
            has_honorific = any(
                any(p in a.name.upper() for p in ("DON ", "DOÑA ", "D. ", "D.ÑA.")) 
                for a in company.administrators
            )
            if has_honorific:
                age_points = self.POINTS['admin_age_med'] # +30 por defecto
        
        points += age_points
        breakdown['admin_age'] = age_points

        # --- Antigüedad sin cambios BORME ---
        stability_points = 0
        if company.borme.last_activity:
            try:
                last_date = datetime.strptime(company.borme.last_activity[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                years_since = (datetime.now(timezone.utc) - last_date).days / 365.25
                if years_since > 5:
                    stability_points = self.POINTS['borme_stability']
            except (ValueError, IndexError):
                pass
        points += stability_points
        breakdown['stability'] = stability_points

        # --- Empresa Familiar ---
        family_points = 0
        if len(company.administrators) >= 1:
            last_names = []
            for a in company.administrators:
                parts = a.name.split()
                if parts:
                    last_names.append(parts[-1].upper())
            
            if len(last_names) > 1:
                from collections import Counter
                most_common = Counter(last_names).most_common(1)[0]
                if most_common[1] >= 2:
                    family_points = self.POINTS['family_business']
        
        points += family_points
        breakdown['family'] = family_points

        # --- Sin Consejo Externo ---
        council_points = 0
        has_council = any("CONSEJO" in a.role.upper() for a in company.administrators)
        if not has_council:
            council_points = self.POINTS['no_external_council']
        
        points += council_points
        breakdown['no_council'] = council_points

        # --- CNAE Compatible ---
        cnae_points = 0
        if company.cnae:
            compatible_keywords = ("INDUSTRIAL", "LOGISTICA", "B2B", "SERVICIOS", "SaaS", "MANUFACTURA")
            if any(k in company.cnae.upper() for k in compatible_keywords):
                cnae_points = self.POINTS['cnae_compatible']
        
        points += cnae_points
        breakdown['cnae'] = cnae_points

        # --- Actividad BORME Reciente ---
        recent_points = 0
        if company.borme.last_activity:
            try:
                last_date = datetime.strptime(company.borme.last_activity[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                days_since = (datetime.now(timezone.utc) - last_date).days
                if days_since <= 365:
                    recent_points = self.POINTS['borme_recent']
            except (ValueError, IndexError):
                pass
        points += recent_points
        breakdown['recent_activity'] = recent_points

        return {
            'total': min(points, 100),
            'breakdown': breakdown
        }

    def _calculate_financial_score(self, company: Company) -> float:
        financial = company.financial
        points = 0
        
        if financial.ebitda:
            if 1_500_000 <= financial.ebitda <= 3_000_000:
                points += 40
            elif 500_000 <= financial.ebitda < 1_500_000:
                points += 25
            elif financial.ebitda > 3_000_000:
                points += 20
            else:
                points += 10
        
        if financial.revenue:
            if 10_000_000 <= financial.revenue <= 15_000_000:
                points += 30
            elif 5_000_000 <= financial.revenue < 10_000_000:
                points += 20
            else:
                points += 10
        
        if financial.ebitda_margin:
            if financial.ebitda_margin >= 20:
                points += 30
            elif financial.ebitda_margin >= 15:
                points += 20
            else:
                points += 10
                
        return min(points, 100)

    def _get_interpretation(self, score: float) -> str:
        if score >= 80: return "MUY BUEN CANDIDATO - Alta probabilidad de transición"
        if score >= 60: return "BUEN CANDIDATO - Posible candidato a investigar"
        if score >= 40: return "CANDIDATO MODERADO - Requiere más información"
        if score >= 20: return "CANDIDATO BAJO - Poca probabilidad de venta"
        return "NO RECOMENDADO - No parece candidato"

    def _build_financial_breakdown(self, company: Company, score: Optional[float]) -> Optional[Dict]:
        if score is None or not company.financial:
            return None
        return {
            'ebitda': company.financial.ebitda,
            'revenue': company.financial.revenue,
            'margin': company.financial.ebitda_margin,
            'score': score
        }

    def get_score_indicators(self, company: Company) -> list:
        indicators = []
        if company.administrators:
            has_honorific = any(any(p in a.name.upper() for p in ("DON ", "DOÑA ")) for a in company.administrators)
            if has_honorific: indicators.append("Administradores con perfil senior (Don/Doña)")
        
        if company.financial and company.financial.is_complete():
            indicators.append(f"EBITDA: {company.financial.format_ebitda()}")
            indicators.append(f"Facturación: {company.financial.format_revenue()}")
            
        if company.borme.acts_count > 0:
            indicators.append(f"{company.borme.acts_count} actos registrados en BORME")
            
        return indicators
