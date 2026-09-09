import sqlite3
import json
import asyncio
import threading
import logging
from typing import Dict
from pathlib import Path

logger = logging.getLogger(__name__)


class Database:
    """
    Almacenamiento SQLite para empresas y listas.

    Usa una conexión persistente por thread (threading.local) con WAL mode
    y busy_timeout para evitar database is locked bajo concurrencia.
    """

    def __init__(self, db_path: str = None):
        self._local = threading.local()

        if db_path is None:
            base_dir = Path(__file__).parent.parent.parent
            data_dir = base_dir / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / "search_fund.db")

        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Obtener conexión persistente por thread (o crear una nueva)."""
        conn = getattr(self._local, "conn", None)
        if conn is None or not self._is_connection_alive(conn):
            conn = sqlite3.connect(self.db_path, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=5000")
            self._local.conn = conn
        return conn

    @staticmethod
    def _is_connection_alive(conn: sqlite3.Connection) -> bool:
        try:
            conn.execute("SELECT 1")
            return True
        except (sqlite3.ProgrammingError, sqlite3.OperationalError):
            return False

    def _init_db(self):
        """Inicializar tablas de la base de datos"""
        conn = self._get_conn()
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS companies (
                    cif TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    data TEXT NOT NULL,
                    score REAL,
                    has_financial_data INTEGER DEFAULT 0,
                    province TEXT,
                    slug TEXT,
                    last_updated TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS lists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS list_items (
                    list_id INTEGER,
                    cif TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    FOREIGN KEY (list_id) REFERENCES lists(id) ON DELETE CASCADE,
                    PRIMARY KEY (list_id, cif)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    filters TEXT,
                    results_count INTEGER,
                    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("CREATE INDEX IF NOT EXISTS idx_companies_slug ON companies(slug)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_companies_province ON companies(province)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_companies_score ON companies(score)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_list_items_cif ON list_items(cif)")

            cols = [r[1] for r in conn.execute("PRAGMA table_info(companies)").fetchall()]
            if "slug" not in cols:
                conn.execute("ALTER TABLE companies ADD COLUMN slug TEXT")
            if "province" not in cols:
                conn.execute("ALTER TABLE companies ADD COLUMN province TEXT")

    def _save_company_sync(self, company):
        """Guardado síncrono de empresa (preserva created_at, actualiza province)."""
        conn = self._get_conn()
        existing = conn.execute(
            "SELECT created_at FROM companies WHERE cif = ?", (company.cif,)
        ).fetchone()
        created_at = existing[0] if existing else None

        conn.execute(
            """INSERT OR REPLACE INTO companies
               (cif, name, data, score, has_financial_data, province, last_updated, slug, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))""",
            (
                company.cif,
                company.name,
                company.model_dump_json(),
                company.score,
                1 if company.has_financial_data() else 0,
                getattr(company, "province", None),
                company.last_updated.isoformat() if company.last_updated else None,
                getattr(company, "slug", None),
                created_at,
            ),
        )
        conn.commit()

    async def save_company(self, company):
        await asyncio.to_thread(self._save_company_sync, company)

    def _get_company_sync(self, cif: str):
        conn = self._get_conn()
        row = conn.execute(
            "SELECT data FROM companies WHERE cif = ?", (cif,)
        ).fetchone()
        if row:
            try:
                from ..models.company import Company
                return Company.model_validate_json(row[0])
            except Exception as e:
                logger.warning("Failed to parse company %s: %s", cif, e)
                return None
        return None

    async def get_company(self, cif: str):
        return await asyncio.to_thread(self._get_company_sync, cif)

    def _get_company_by_slug_sync(self, slug: str):
        if not slug:
            return None
        conn = self._get_conn()
        row = conn.execute(
            "SELECT data FROM companies WHERE slug = ?", (slug,)
        ).fetchone()
        if row:
            try:
                from ..models.company import Company
                return Company.model_validate_json(row[0])
            except Exception as e:
                logger.warning("Failed to parse company by slug %s: %s", slug, e)
                return None
        return None

    async def get_company_by_slug(self, slug: str):
        return await asyncio.to_thread(self._get_company_by_slug_sync, slug)

    @staticmethod
    def _escape_like(value: str) -> str:
        """Escapar caracteres especiales de LIKE (% y _)."""
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    def _search_local_sync(self, query: str, limit: int = 20):
        if not query:
            return []
        escaped = self._escape_like(query)
        like = f"%{escaped}%"
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT data FROM companies WHERE name LIKE ? ESCAPE '\\' ORDER BY score DESC LIMIT ?",
            (like, limit),
        ).fetchall()
        from ..models.company import Company
        companies = []
        for row in rows:
            try:
                companies.append(Company.model_validate_json(row[0]))
            except Exception as e:
                logger.warning("Failed to parse local company: %s", e)
        return companies

    async def search_local_companies(self, query: str, limit: int = 20):
        return await asyncio.to_thread(self._search_local_sync, query, limit)

    def _search_companies_sync(self, min_score=None, max_score=None, province=None,
                               has_financial_data=None, limit=100, offset=0):
        from ..models.company import Company
        conn = self._get_conn()
        query = "SELECT data FROM companies WHERE 1=1"
        params = []
        if min_score is not None:
            query += " AND score >= ?"
            params.append(min_score)
        if max_score is not None:
            query += " AND score <= ?"
            params.append(max_score)
        if has_financial_data is not None:
            query += " AND has_financial_data = ?"
            params.append(1 if has_financial_data else 0)
        if province is not None:
            query += " AND province = ?"
            params.append(province)
        query += " ORDER BY score DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(query, params).fetchall()
        companies = []
        for row in rows:
            try:
                companies.append(Company.model_validate_json(row[0]))
            except Exception as e:
                logger.warning("Failed to parse company in search: %s", e)
                continue
        return companies

    async def search_companies(self, min_score=None, max_score=None, province=None,
                               has_financial_data=None, limit=100, offset=0):
        return await asyncio.to_thread(
            self._search_companies_sync, min_score, max_score, province,
            has_financial_data, limit, offset,
        )

    def _count_companies_sync(self, min_score=None, max_score=None, province=None,
                              has_financial_data=None):
        conn = self._get_conn()
        query = "SELECT COUNT(*) FROM companies WHERE 1=1"
        params = []
        if min_score is not None:
            query += " AND score >= ?"
            params.append(min_score)
        if max_score is not None:
            query += " AND score <= ?"
            params.append(max_score)
        if has_financial_data is not None:
            query += " AND has_financial_data = ?"
            params.append(1 if has_financial_data else 0)
        if province is not None:
            query += " AND province = ?"
            params.append(province)
        return conn.execute(query, params).fetchone()[0]

    async def count_companies(self, min_score=None, max_score=None, province=None,
                              has_financial_data=None):
        return await asyncio.to_thread(
            self._count_companies_sync, min_score, max_score, province,
            has_financial_data,
        )

    def _get_all_companies_sync(self):
        from ..models.company import Company
        conn = self._get_conn()
        rows = conn.execute("SELECT data FROM companies").fetchall()
        companies = []
        for row in rows:
            try:
                companies.append(Company.model_validate_json(row[0]))
            except Exception as e:
                logger.warning("Failed to parse company: %s", e)
                continue
        return companies

    async def get_all_companies(self):
        return await asyncio.to_thread(self._get_all_companies_sync)

    # ==================== LISTAS ====================

    def _create_list_sync(self, name: str, description: str = None):
        conn = self._get_conn()
        cursor = conn.execute(
            "INSERT INTO lists (name, description) VALUES (?, ?)",
            (name, description),
        )
        conn.commit()
        return cursor.lastrowid

    async def create_list(self, name: str, description: str = None):
        return await asyncio.to_thread(self._create_list_sync, name, description)

    def _get_lists_sync(self):
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, name, description, created_at, updated_at FROM lists ORDER BY name"
        ).fetchall()
        return [
            {"id": r[0], "name": r[1], "description": r[2],
             "created_at": r[3], "updated_at": r[4]}
            for r in rows
        ]

    async def get_lists(self):
        return await asyncio.to_thread(self._get_lists_sync)

    def _get_list_sync(self, list_id: int):
        conn = self._get_conn()
        row = conn.execute(
            "SELECT id, name, description, created_at, updated_at FROM lists WHERE id = ?",
            (list_id,),
        ).fetchone()
        if row:
            return {"id": row[0], "name": row[1], "description": row[2],
                    "created_at": row[3], "updated_at": row[4]}
        return None

    async def get_list(self, list_id: int):
        return await asyncio.to_thread(self._get_list_sync, list_id)

    def _add_to_list_sync(self, list_id: int, cif: str, notes: str = None):
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO list_items (list_id, cif, notes) VALUES (?, ?, ?)",
                (list_id, cif, notes),
            )
            conn.execute(
                "UPDATE lists SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (list_id,),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            return False
        return True

    async def add_to_list(self, list_id: int, cif: str, notes: str = None):
        return await asyncio.to_thread(self._add_to_list_sync, list_id, cif, notes)

    def _remove_from_list_sync(self, list_id: int, cif: str):
        conn = self._get_conn()
        conn.execute(
            "DELETE FROM list_items WHERE list_id = ? AND cif = ?",
            (list_id, cif),
        )
        conn.execute(
            "UPDATE lists SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (list_id,),
        )
        conn.commit()

    async def remove_from_list(self, list_id: int, cif: str):
        await asyncio.to_thread(self._remove_from_list_sync, list_id, cif)

    def _get_list_items_sync(self, list_id: int):
        from ..models.company import Company
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT c.data FROM companies c
               JOIN list_items li ON c.cif = li.cif
               WHERE li.list_id = ?
               ORDER BY c.score DESC""",
            (list_id,),
        ).fetchall()
        companies = []
        for row in rows:
            try:
                companies.append(Company.model_validate_json(row[0]))
            except Exception as e:
                logger.warning("Failed to parse list company: %s", e)
                continue
        return companies

    async def get_list_items(self, list_id: int):
        return await asyncio.to_thread(self._get_list_items_sync, list_id)

    def _delete_list_sync(self, list_id: int):
        conn = self._get_conn()
        conn.execute("DELETE FROM list_items WHERE list_id = ?", (list_id,))
        conn.execute("DELETE FROM lists WHERE id = ?", (list_id,))
        conn.commit()

    async def delete_list(self, list_id: int):
        await asyncio.to_thread(self._delete_list_sync, list_id)

    # ==================== HISTORIAL ====================

    def _save_search_sync(self, query: str, filters: Dict = None, results_count: int = 0):
        query = query or ""
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO search_history (query, filters, results_count) VALUES (?, ?, ?)",
            (query, json.dumps(filters) if filters else None, results_count),
        )
        conn.execute(
            "DELETE FROM search_history WHERE id NOT IN "
            "(SELECT id FROM search_history ORDER BY searched_at DESC LIMIT 500)"
        )
        conn.commit()

    async def save_search(self, query: str, filters: Dict = None, results_count: int = 0):
        await asyncio.to_thread(self._save_search_sync, query, filters, results_count)

    def _get_search_history_sync(self, limit: int = 50):
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT query, filters, results_count, searched_at "
            "FROM search_history ORDER BY searched_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {"query": r[0], "filters": json.loads(r[1]) if r[1] else None,
             "results_count": r[2], "searched_at": r[3]}
            for r in rows
        ]

    async def get_search_history(self, limit: int = 50):
        return await asyncio.to_thread(self._get_search_history_sync, limit)

    # ==================== UTILIDADES ====================

    def _get_stats_sync(self):
        conn = self._get_conn()
        total_companies = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
        companies_with_financial = conn.execute(
            "SELECT COUNT(*) FROM companies WHERE has_financial_data = 1"
        ).fetchone()[0]
        total_lists = conn.execute("SELECT COUNT(*) FROM lists").fetchone()[0]
        total_searches = conn.execute("SELECT COUNT(*) FROM search_history").fetchone()[0]
        companies_today = conn.execute(
            "SELECT COUNT(*) FROM companies WHERE date(created_at, 'localtime') = date('now', 'localtime')"
        ).fetchone()[0]
        financial_today = conn.execute(
            "SELECT COUNT(*) FROM companies WHERE has_financial_data = 1 "
            "AND date(last_updated, 'localtime') = date('now', 'localtime')"
        ).fetchone()[0]
        dist_row = conn.execute(
            """
            SELECT
              COALESCE(SUM(CASE WHEN score >= 60 THEN 1 ELSE 0 END), 0) AS alto,
              COALESCE(SUM(CASE WHEN score >= 40 AND score < 60 THEN 1 ELSE 0 END), 0) AS medio,
              COALESCE(SUM(CASE WHEN score < 40 THEN 1 ELSE 0 END), 0) AS bajo
            FROM companies WHERE score IS NOT NULL
            """
        ).fetchone()
        return {
            "total_companies": total_companies,
            "companies_with_financial_data": companies_with_financial,
            "companies_without_financial_data": total_companies - companies_with_financial,
            "total_lists": total_lists,
            "total_searches": total_searches,
            "score_distribution": {"alto": dist_row[0], "medio": dist_row[1], "bajo": dist_row[2]},
            "companies_today": companies_today,
            "financial_today": financial_today,
        }

    async def get_stats(self):
        return await asyncio.to_thread(self._get_stats_sync)

    def _get_daily_stats_sync(self, days: int = 14):
        conn = self._get_conn()
        rows = conn.execute(
            """
            SELECT date(searched_at) as day, COUNT(*) as searches
            FROM search_history
            WHERE searched_at >= date('now', ? || ' days')
            GROUP BY date(searched_at)
            ORDER BY day ASC
            """,
            (f"-{days}",),
        ).fetchall()
        company_rows = conn.execute(
            """
            SELECT date(created_at) as day, COUNT(*) as companies
            FROM companies
            WHERE created_at >= date('now', ? || ' days')
            GROUP BY date(created_at)
            ORDER BY day ASC
            """,
            (f"-{days}",),
        ).fetchall()
        list_rows = conn.execute(
            """
            SELECT date(created_at) as day, COUNT(*) as lists
            FROM lists
            WHERE created_at >= date('now', ? || ' days')
            GROUP BY date(created_at)
            ORDER BY day ASC
            """,
            (f"-{days}",),
        ).fetchall()

        stats_by_day: Dict = {}
        for row in rows:
            day = row[0]
            stats_by_day.setdefault(day, {"day": day, "searches": 0, "companies": 0, "lists": 0})
            stats_by_day[day]["searches"] = row[1]
        for row in company_rows:
            day = row[0]
            stats_by_day.setdefault(day, {"day": day, "searches": 0, "companies": 0, "lists": 0})
            stats_by_day[day]["companies"] = row[1]
        for row in list_rows:
            day = row[0]
            stats_by_day.setdefault(day, {"day": day, "searches": 0, "companies": 0, "lists": 0})
            stats_by_day[day]["lists"] = row[1]

        return list(stats_by_day.values())

    async def get_daily_stats(self, days: int = 14):
        return await asyncio.to_thread(self._get_daily_stats_sync, days)

    def _clear_cache_sync(self):
        conn = self._get_conn()
        conn.execute("DELETE FROM list_items")
        conn.execute("DELETE FROM lists")
        conn.execute("DELETE FROM companies")
        conn.commit()

    async def clear_cache(self):
        await asyncio.to_thread(self._clear_cache_sync)

    def close(self):
        """Cerrar la conexión del thread actual."""
        conn = getattr(self._local, "conn", None)
        if conn:
            try:
                conn.close()
            except Exception:
                pass
            self._local.conn = None
