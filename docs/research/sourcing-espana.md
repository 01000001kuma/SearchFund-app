# Research: ecosistema search funds España y cómo construyen sus listas

> Fuente: research del usuario (2026-09-10) — listas de fondos activos,
> canales de sourcing y fuentes de datos. Base para el roadmap v1.2/v1.3.

## 1. Directorio: ~50 search funds activos en España

**Ya con adquisiciones cerradas (2014–2023):**
Ariol Capital · Axias Partners · Nobis Capital · Surca Capital · Almond Capital ·
Albion Capital · Arcadio Investments · Aretê Management & Capital Partners ·
Luceiro Capital · Somontano Capital · Versa Capital · Verus Inversiones ·
Taurus Capital · Antesala Capital · Albatros Equity · Emptio Capital ·
Road Capital · Ventura · Sotavento Capital · Novastone (Jan Nikolaisen) ·
Eon Partners · D'Ella Capital · Tilden Capital · Signatus Capital ·
Arista Partners · Navega Capital · Bogo Inversión · Vesta Capital Partners ·
Ibérica Partners · Baluarte Capital · Namencis Capital · Vigía Capital ·
Tagus Capital · A&M Partners · Asta Capital · Syna Capital · Sachem Partners ·
Transición · N Capital · Elcano Partners

**Añadidos (searching activo / referencias LinkedIn):**
Itaca Capital Partners · Imagine+ Inversión · Lemnos Capital ·
Bitacora Partners · Rigi Capital · KG Capital · Candor Equity ·
Eureka Capital · T&R Capital · Viriato Capital

**Datos de contexto:** 60–70 searchers activos en España · 67 search funds
primeros ligados a IESE · varios registrados como SCR (ej. BEKA ALPHA
SEARCH FUNDS SCR SA).

**Fuentes para validar/extender:** registros SCR/FCR de la CNMV · IESE
International Search Fund Center · Search Funds News · Capittal.

## 2. Cómo buscan candidatas (canales)

1. **Propietaria / off-market (espinazo del flujo):** universo de 1.000–3.000
   PYMES que encajan en el "buy box" (EBITDA ~0,5–3M€, ingresos recurrentes,
   baja concentración de clientes, sectores sin disrupción tecnológica).
   Contacto multicanal personalizado: email personalizado, teléfono
   (múltiples intentos), LinkedIn, carta física, visitas in person.
   El mensaje habla de sucesión y legado, no de ingeniería financiera.
2. **Brokers y asesores M&A:** boutiques regionales del rango 1–10M€ EV;
   estar en sus listas de compradores con un "buy box" claro.
3. **Asesores profesionales como fuente:** gestorías/auditores, abogados
   de planificación sucesoria, gestores de banco, consultores de empresa
   familiar — que avisan cuando un cliente "no sabe quién tomará el relevo".
4. **Redes, eventos e inbound:** asociaciones sectoriales, ferias, webinars
   y contenido dirigido a propietarios que valoran una salida parcial.
5. **Herramientas de datos y automatización ligera:** registros (BORME,
   Registro Mercantil), bases comerciales, enriquecimiento de contactos,
   CRM para trackear miles de toques durante 18–24 meses.

**Matemática del pipeline:** 1.000–3.000 prospectos → contacto multicanal
→ decenas de conversaciones serias → varias LOIs → 1 adquisición.

## 3. Fuentes de datos que usan

| Capa | Fuentes | Qué dan |
|---|---|---|
| Registros públicos | BORME (boe.es), opendata.registradores.org, registradores.org (€2,60+ nota), INE DIRCE | nombre, CIF, forma, sede, CNAE, capital, administradores, estado, cuentas |
| Bases comerciales | SABI (≈2,9M), Informa D&B, Axesor (3M+), Iberinform, Camerdata | balances, ratios, propiedad, auditores, grupos |
| Enriquecimiento | LinkedIn Sales Navigator, ZoomInfo, Apollo, webs corporativas | owner/decisor, emails, teléfonos |
| Acceso programático | APIs de BORME/Registro, scrapers (Apify) | JSON automatizado de administradores, CNAE, estado |

**Workflow:** buy box → universo (5.000–50.000 registros) → limpieza
(grupos/holdings fuera) → enriquecimiento (LinkedIn + registros) →
priorización por riesgo de sucesión → CRM → secuencias multicanal 18–24 meses.
