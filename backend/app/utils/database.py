"""
Ocean Sentinel - Database Utilities
Supabase client and database helper functions
"""

import logging
from typing import Optional, Dict, Any, List
from supabase import create_client, Client
import asyncpg
from contextlib import asynccontextmanager

from app.config import settings

logger = logging.getLogger(__name__)

def create_supabase_client() -> Client:
    """Create and configure Supabase client"""
    try:
        supabase: Client = create_client(
            settings.supabase_url, 
            settings.supabase_anon_key
        )
        logger.info("✅ Supabase client created successfully")
        return supabase
    except Exception as e:
        logger.error(f"❌ Failed to create Supabase client: {e}")
        raise

class DatabaseManager:
    """Database management utilities"""
    
    def __init__(self):
        self.supabase = create_supabase_client()
        
    async def execute_query(self, query: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute raw SQL query via Supabase"""
        try:
            if params:
                result = await self.supabase.rpc('execute_sql', {
                    'query': query,
                    'params': params
                }).execute()
            else:
                result = await self.supabase.rpc('execute_sql', {
                    'query': query
                }).execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Database query error: {e}")
            raise
    
    async def get_table_stats(self, table_name: str) -> Dict[str, Any]:
        """Get statistics for a specific table"""
        try:
            result = await self.supabase.table(table_name)\
                .select('*', count='exact')\
                .execute()
            
            return {
                'table_name': table_name,
                'total_rows': result.count,
                'last_updated': 'N/A'  # Would need custom logic
            }
            
        except Exception as e:
            logger.error(f"Error getting table stats for {table_name}: {e}")
            return {'table_name': table_name, 'error': str(e)}
    
    async def cleanup_old_records(self, table_name: str, date_column: str, days_old: int) -> int:
        """Clean up old records from specified table"""
        try:
            from datetime import datetime, timedelta
            
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            result = await self.supabase.table(table_name)\
                .delete()\
                .lt(date_column, cutoff_date.isoformat())\
                .execute()
            
            deleted_count = len(result.data) if result.data else 0
            logger.info(f"🗑️ Cleaned up {deleted_count} old records from {table_name}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up {table_name}: {e}")
            return 0
    
    async def backup_table(self, table_name: str) -> bool:
        """Create backup of table data"""
        try:
            # In production, this would export to cloud storage
            result = await self.supabase.table(table_name)\
                .select('*')\
                .execute()
            
            if result.data:
                logger.info(f"💾 Backup prepared for {table_name}: {len(result.data)} records")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error backing up {table_name}: {e}")
            return False

# Database connection pool for direct PostgreSQL access
class PostgreSQLManager:
    """Direct PostgreSQL connection manager for advanced queries"""
    
    def __init__(self):
        self.connection_string = self._build_connection_string()
        
    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string from Supabase URL"""
        # Extract connection details from Supabase URL
        # Format: postgresql://[user[:password]@][netloc][:port][/dbname]
        url = settings.supabase_url.replace('https://', '')
        
        # This is a simplified approach - in production you'd get actual DB credentials
        return f"postgresql://postgres:{settings.supabase_service_role_key}@db.{url}:5432/postgres"
    
    @asynccontextmanager
    async def get_connection(self):
        """Get PostgreSQL connection with context manager"""
        connection = None
        try:
            connection = await asyncpg.connect(self.connection_string)
            yield connection
        except Exception as e:
            logger.error(f"PostgreSQL connection error: {e}")
            raise
        finally:
            if connection:
                await connection.close()
    
    async def execute_geospatial_query(self, query: str, params: List = None) -> List[Dict]:
        """Execute PostGIS geospatial queries"""
        try:
            async with self.get_connection() as conn:
                if params:
                    results = await conn.fetch(query, *params)
                else:
                    results = await conn.fetch(query)
                
                # Convert Record objects to dictionaries
                return [dict(record) for record in results]
                
        except Exception as e:
            logger.error(f"Geospatial query error: {e}")
            return []
    
    async def get_threats_within_radius(
        self, 
        latitude: float, 
        longitude: float, 
        radius_km: float
    ) -> List[Dict]:
        """Get threats within specified radius using PostGIS"""
        query = """
        SELECT *, 
               ST_Distance(
                   ST_GeogFromText('POINT(%s %s)'), 
                   location::geography
               ) / 1000 as distance_km
        FROM threats 
        WHERE ST_DWithin(
            ST_GeogFromText('POINT(%s %s)'), 
            location::geography, 
            %s * 1000
        )
        ORDER BY distance_km;
        """
        
        params = [longitude, latitude, longitude, latitude, radius_km]
        return await self.execute_geospatial_query(query, params)

# Global database manager instance
db_manager = DatabaseManager()
postgresql_manager = PostgreSQLManager()
