import json
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from backend.storage.database import Database
from backend.models.company import Company, Administrator, BormeData
from backend.models.financial import FinancialData

db = Database()

companies = [
    Company(
        cif="B12345678", name="Metalúrgica del Sureste S.L.", slug="metallurgica-del-sureste",
        legal_form="SL", status="Activa", address="Polígono Industrial Sur, 12",
        city="Murcia", province="Murcia", postal_code="30012",
        founded_date="1985-03-15", website="www.metalurgica-sureste.es",
        phone="968 123 456", email="info@metalurgica-sureste.es",
        administrators=[Administrator(name="Antonio García López", role="Administrador Único", since="1985-03-15")],
        borme=BormeData(acts_count=3, last_activity="2025-01-15"),
        financial=FinancialData(revenue=12_500_000, ebitda=2_100_000, employees=85, source="manual", year=2024, confidence=0.9),
        score=82, data_sources=["openmercantil", "manual"], tags=["industrial", "familiar"],
    ),
    Company(
        cif="B87654321", name="Logística Express Madrid S.A.", slug="logistica-express-madrid",
        legal_form="SA", status="Activa", address="Calle Industrial, 45",
        city="Getafe", province="Madrid", postal_code="28906",
        founded_date="1992-07-20", website="www.logistica-express.es",
        phone="916 789 012", email="contacto@logistica-express.es",
        administrators=[Administrator(name="María Fernández Ruiz", role="Consejera Delegada", since="1992-07-20")],
        borme=BormeData(acts_count=5, last_activity="2025-06-10"),
        financial=FinancialData(revenue=14_800_000, ebitda=2_850_000, employees=120, source="manual", year=2024, confidence=0.85),
        score=91, data_sources=["openmercantil", "manual"], tags=["logística", "familiar"],
    ),
    Company(
        cif="A11223344", name="Alimentos del Norte S.L.", slug="alimentos-del-norte",
        legal_form="SL", status="Activa", address="Polígono Larrondo, s/n",
        city="Bilbao", province="Vizcaya", postal_code="48180",
        founded_date="1978-11-05", website="www.alimentos-norte.es",
        phone="944 567 890", email="info@alimentos-norte.es",
        administrators=[Administrator(name="José Miguel Etxeberria", role="Administrador", since="1978-11-05")],
        borme=BormeData(acts_count=8, last_activity="2025-03-22"),
        financial=FinancialData(revenue=18_200_000, ebitda=3_200_000, employees=150, source="manual", year=2024, confidence=0.92),
        score=75, data_sources=["openmercantil", "manual"], tags=["alimentación", "familiar", "exportador"],
    ),
    Company(
        cif="B55667788", name="Construcciones Alonso Hnos.", slug="construcciones-alonso",
        legal_form="SL", status="Activa", address="Avenida de la Industria, 78",
        city="Valencia", province="Valencia", postal_code="46015",
        founded_date="1988-04-12", website="www.construccionalonso.es",
        phone="963 456 789", email="obra@construccionalonso.es",
        administrators=[
            Administrator(name="Pedro Alonso Martínez", role="Administrador", since="1988-04-12"),
            Administrator(name="Luis Alonso Martínez", role="Consejero", since="1988-04-12"),
        ],
        borme=BormeData(acts_count=2, last_activity="2024-11-08"),
        financial=FinancialData(revenue=8_900_000, ebitda=1_650_000, employees=65, source="manual", year=2024, confidence=0.8),
        score=88, data_sources=["openmercantil", "manual"], tags=["construcción", "familiar"],
    ),
    Company(
        cif="C99887766", name="Textil Costa Blanca S.L.", slug="textil-costa-blanca",
        legal_form="SL", status="Activa", address="Calle Mayor, 123",
        city="Alicante", province="Alicante", postal_code="03013",
        founded_date="1975-09-01", website="www.textilcostablanca.es",
        phone="965 234 567", email="ventas@textilcostablanca.es",
        administrators=[Administrator(name="Carmen Domínguez Sánchez", role="Administradora Única", since="1975-09-01")],
        borme=BormeData(acts_count=1, last_activity="2023-05-15"),
        financial=FinancialData(revenue=6_500_000, ebitda=980_000, employees=42, source="manual", year=2024, confidence=0.75),
        score=64, data_sources=["openmercantil", "manual"], tags=["textil", "familiar"],
    ),
    Company(
        cif="A33445566", name="Químicos Ibéricos S.A.", slug="quimicos-ibericos",
        legal_form="SA", status="Activa", address="Polígono Químico, 5",
        city="Tarragona", province="Tarragona", postal_code="43006",
        founded_date="1990-02-28", website="www.quimicosibericos.es",
        phone="977 678 901", email="info@quimicosibericos.es",
        administrators=[Administrator(name="Jordi Pujol Vilà", role="Director General", since="1995-01-10")],
        borme=BormeData(acts_count=4, last_activity="2025-02-18"),
        financial=FinancialData(revenue=22_100_000, ebitda=4_500_000, employees=180, source="manual", year=2024, confidence=0.88),
        score=55, data_sources=["openmercantil", "manual"], tags=["química", "industrial"],
    ),
    Company(
        cif="B77889900", name="Transportes Vega Baja S.L.", slug="transportes-vega-baja",
        legal_form="SL", status="Activa", address="Ctra. Nacional, km 45",
        city="Orihuela", province="Alicante", postal_code="03189",
        founded_date="1982-06-18", website="www.transportesvegabaja.es",
        phone="965 345 678", email="admin@transportesvegabaja.es",
        administrators=[Administrator(name="Francisco Javier González", role="Administrador Único", since="1982-06-18")],
        borme=BormeData(acts_count=6, last_activity="2025-04-05"),
        financial=FinancialData(revenue=11_300_000, ebitda=1_950_000, employees=72, source="manual", year=2024, confidence=0.82),
        score=85, data_sources=["openmercantil", "manual"], tags=["transporte", "familiar"],
    ),
    Company(
        cif="C22334455", name="Envasados del Mediterráneo S.L.", slug="envasados-mediterraneo",
        legal_form="SL", status="Activa", address="Calle del Progreso, 34",
        city="Castellón", province="Castellón", postal_code="12003",
        founded_date="1995-10-22", website="www.envasadosmediterraneo.es",
        phone="964 567 890", email="comercial@envasadosmediterraneo.es",
        administrators=[Administrator(name="Isabel Ruiz Gómez", role="Administradora", since="2005-03-01")],
        borme=BormeData(acts_count=2, last_activity="2025-01-30"),
        financial=FinancialData(revenue=7_200_000, ebitda=1_100_000, employees=38, source="manual", year=2024, confidence=0.78),
        score=71, data_sources=["openmercantil", "manual"], tags=["envasados", "alimentación"],
    ),
    Company(
        cif="A44556677", name="Maquinaria Agrícola del Sur S.A.", slug="maquinaria-agricola-sur",
        legal_form="SA", status="Activa", address="Polígono La Campiña, 10",
        city="Córdoba", province="Córdoba", postal_code="14013",
        founded_date="1968-01-15", website="www.maquinariaagricola-sur.es",
        phone="957 789 012", email="info@maquinariaagricola-sur.es",
        administrators=[Administrator(name="Rafael Moreno Delgado", role="Presidente", since="1968-01-15")],
        borme=BormeData(acts_count=7, last_activity="2025-05-12"),
        financial=FinancialData(revenue=16_700_000, ebitda=2_900_000, employees=95, source="manual", year=2024, confidence=0.9),
        score=79, data_sources=["openmercantil", "manual"], tags=["agricultura", "familiar", "maquinaria"],
    ),
    Company(
        cif="B66778899", name="Frigoríficos del Ebro S.L.", slug="frigorificos-ebro",
        legal_form="SL", status="Activa", address="Avda. de la Industria, 89",
        city="Zaragoza", province="Zaragoza", postal_code="50012",
        founded_date="1987-08-30", website="www.frigorificosebro.es",
        phone="976 123 456", email="compras@frigorificosebro.es",
        administrators=[
            Administrator(name="Manuel Serrano Pérez", role="Administrador", since="1987-08-30"),
            Administrator(name="Elena Serrano López", role="Consejera", since="2010-01-01"),
        ],
        borme=BormeData(acts_count=4, last_activity="2025-02-28"),
        financial=FinancialData(revenue=19_500_000, ebitda=3_400_000, employees=140, source="manual", year=2024, confidence=0.91),
        score=93, data_sources=["openmercantil", "manual"], tags=["alimentación", "familiar", "refrigeración"],
    ),
]

# Insert companies
for c in companies:
    db._save_company_sync(c)
    print(f"  ✓ {c.name} ({c.cif})")

# Create lists
conn = db._get_conn()
conn.execute("INSERT INTO lists (name, description) VALUES ('Top Candidatos', 'Empresas con mayor score de adquisición')")
conn.execute("INSERT INTO lists (name, description) VALUES ('Pendiente Revisión', 'Empresas que necesitan más datos financieros')")
list_id_1 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
conn.execute("INSERT INTO lists (name, description) VALUES ('Descartadas', 'Empresas que no cumplen criterios')")
list_id_2 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
conn.execute("INSERT INTO lists (name, description) VALUES ('En Negociación', 'Empresas en proceso de contacto')")
list_id_3 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

# Add companies to lists
conn.execute("INSERT INTO list_items (list_id, cif, notes) VALUES (?, 'B66778899', 'Score 93 - ideal')", (list_id_1,))
conn.execute("INSERT INTO list_items (list_id, cif, notes) VALUES (?, 'B87654321', 'Score 91 - logística')", (list_id_1,))
conn.execute("INSERT INTO list_items (list_id, cif, notes) VALUES (?, 'B55667788', 'Score 88 - construcción')", (list_id_1,))
conn.execute("INSERT INTO list_items (list_id, cif, notes) VALUES (?, 'B77889900', 'Score 85 - transporte')", (list_id_1,))
conn.execute("INSERT INTO list_items (list_id, cif, notes) VALUES (?, 'B12345678', 'Score 82 - industrial')", (list_id_1,))
conn.execute("INSERT INTO list_items (list_id, cif) VALUES (?, 'C99887766')", (list_id_2,))
conn.execute("INSERT INTO list_items (list_id, cif) VALUES (?, 'C22334455')", (list_id_2,))
conn.execute("INSERT INTO list_items (list_id, cif) VALUES (?, 'A33445566')", (list_id_3,))
conn.execute("INSERT INTO list_items (list_id, cif) VALUES (?, 'A11223344')", (list_id_3,))

# Add search history
conn.execute("INSERT INTO search_history (query, results_count) VALUES ('empresas Murcia', 1)")
conn.execute("INSERT INTO search_history (query, results_count) VALUES ('logística Madrid', 1)")
conn.execute("INSERT INTO search_history (query, results_count) VALUES ('alimentación', 2)")
conn.execute("INSERT INTO search_history (query, results_count) VALUES ('EBITDA 2M', 4)")

conn.commit()
print(f"\n✅ 10 empresas + 4 listas + 4 búsquedas insertadas")
