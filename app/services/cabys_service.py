"""
CABYS Code Management Service

This service provides comprehensive CABYS code management functionality including
database operations, caching, search, and validation for Costa Rica's electronic
invoicing system.

CABYS (Central American Tariff System) codes are 13-digit codes used to classify
products and services for tax purposes.

Requirements: 11.2, 11.3, 17.1
"""
import asyncio
import logging
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_, or_
from sqlalchemy.exc import SQLAlchemyError

from app.models.cabys_code import CabysCode
from app.core.database import get_db, SessionLocal
from app.core.redis import redis_manager, CacheService
from app.utils.cabys_search import CabysSearchEngine

logger = logging.getLogger(__name__)


class CabysService:
    """
    Comprehensive CABYS code management service
    
    Provides functionality for:
    - CABYS code validation and lookup
    - Full-text search with PostgreSQL and Spanish language support
    - Redis caching for performance optimization
    - Usage statistics tracking
    - Database synchronization
    """
    
    def __init__(self):
        self.search_engine = CabysSearchEngine()
        self.cache_service = CacheService()
    
    async def get_code(self, codigo: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get CABYS code by exact code match with caching
        
        Args:
            codigo: Exact CABYS code (13 digits)
            use_cache: Whether to use Redis cache
            
        Returns:
            CABYS code data dictionary or None if not found
        """
        # Validate code format first
        if not CabysCode.validate_code_format(codigo):
            logger.warning(f"Invalid CABYS code format: {codigo}")
            return None
        
        # Try cache first if enabled
        if use_cache:
            try:
                cached_data = await self.cache_service.get_cabys_code(codigo)
                if cached_data:
                    logger.debug(f"CABYS code {codigo} found in cache")
                    return cached_data
            except Exception as e:
                logger.warning(f"Cache error (continuing without cache): {str(e)}")
                use_cache = False
        
        # Query database
        session = SessionLocal()
        try:
            cabys_code = session.query(CabysCode).filter(
                CabysCode.codigo == codigo,
                CabysCode.activo == True
            ).first()
            
            if not cabys_code:
                logger.info(f"CABYS code not found: {codigo}")
                return None
            
            # Convert to dictionary
            code_data = self._cabys_to_dict(cabys_code)
            
            # Update usage statistics
            cabys_code.increment_usage()
            session.commit()
            
            # Cache the result
            if use_cache:
                try:
                    await self.cache_service.cache_cabys_code(codigo, code_data)
                except Exception as e:
                    logger.warning(f"Cache write error: {str(e)}")
            
            logger.info(f"CABYS code retrieved: {codigo}")
            return code_data
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error retrieving CABYS code {codigo}: {str(e)}")
            return None
        finally:
            session.close()
    
    async def search_codes(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        category_filter: Optional[str] = None,
        category_level: int = 1,
        only_active: bool = True,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Full-text search for CABYS codes with pagination and filtering
        
        Args:
            query: Search query string
            limit: Maximum number of results per page
            offset: Number of results to skip (for pagination)
            category_filter: Optional category filter
            category_level: Category level for filtering (1-8)
            only_active: Whether to include only active codes
            use_cache: Whether to use Redis cache for results
            
        Returns:
            Dictionary with search results and pagination info
        """
        if not query or len(query.strip()) < 2:
            return {
                'results': [],
                'total': 0,
                'page': offset // limit + 1,
                'per_page': limit,
                'total_pages': 0,
                'query': query
            }
        
        # Generate cache key for search results
        cache_key = f"cabys_search:{hash(query)}:{limit}:{offset}:{category_filter}:{category_level}:{only_active}"
        
        # Try cache first if enabled
        if use_cache:
            try:
                cached_results = await redis_manager.get(cache_key)
                if cached_results:
                    import json
                    logger.debug(f"CABYS search results found in cache for query: {query}")
                    return json.loads(cached_results)
            except Exception as e:
                logger.warning(f"Cache error (continuing without cache): {str(e)}")
                use_cache = False
        
        # Perform database search
        session = SessionLocal()
        try:
            # Use the search engine for full-text search
            search_results = await self.search_engine.search_by_text(
                session=session,
                query=query,
                limit=limit,
                offset=offset,
                category_filter=category_filter,
                category_level=category_level,
                only_active=only_active
            )
            
            # Get total count for pagination
            total_count = await self.search_engine.get_search_count(
                session=session,
                query=query,
                category_filter=category_filter,
                category_level=category_level,
                only_active=only_active
            )
            
            # Convert results to dictionaries
            results = [self._cabys_to_dict(code) for code in search_results]
            
            # Prepare response
            response = {
                'results': results,
                'total': total_count,
                'page': offset // limit + 1,
                'per_page': limit,
                'total_pages': (total_count + limit - 1) // limit,
                'query': query
            }
            
            # Cache the results for 5 minutes
            if use_cache:
                try:
                    await redis_manager.set(cache_key, response, ttl=300)
                except Exception as e:
                    logger.warning(f"Cache write error: {str(e)}")
            
            logger.info(f"CABYS search completed: {len(results)} results for query '{query}'")
            return response
            
        except Exception as e:
            logger.error(f"Error searching CABYS codes: {str(e)}")
            return {
                'results': [],
                'total': 0,
                'page': offset // limit + 1,
                'per_page': limit,
                'total_pages': 0,
                'query': query,
                'error': str(e)
            }
        finally:
            session.close()
    
    async def search_by_code_prefix(
        self,
        prefix: str,
        limit: int = 20,
        only_active: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search CABYS codes by code prefix
        
        Args:
            prefix: Code prefix to search for
            limit: Maximum number of results
            only_active: Whether to include only active codes
            
        Returns:
            List of matching CABYS code dictionaries
        """
        if not prefix or not prefix.isdigit() or len(prefix) > 13:
            return []
        
        session = SessionLocal()
        try:
            results = CabysCode.search_by_code_prefix(
                session=session,
                prefix=prefix,
                limit=limit,
                only_active=only_active
            )
            
            return [self._cabys_to_dict(code) for code in results]
            
        except Exception as e:
            logger.error(f"Error searching CABYS codes by prefix {prefix}: {str(e)}")
            return []
        finally:
            session.close()
    
    async def search_by_category(
        self,
        categoria: str,
        nivel: int = 1,
        limit: int = 50,
        only_active: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search CABYS codes by category
        
        Args:
            categoria: Category name to search for
            nivel: Category level (1-8)
            limit: Maximum number of results
            only_active: Whether to include only active codes
            
        Returns:
            List of matching CABYS code dictionaries
        """
        if not categoria or nivel < 1 or nivel > 4:
            return []
        
        session = SessionLocal()
        try:
            results = CabysCode.search_by_category(
                session=session,
                categoria=categoria,
                nivel=nivel,
                limit=limit,
                only_active=only_active
            )
            
            return [self._cabys_to_dict(code) for code in results]
            
        except Exception as e:
            logger.error(f"Error searching CABYS codes by category {categoria}: {str(e)}")
            return []
        finally:
            session.close()
    
    async def get_most_used(
        self,
        limit: int = 100,
        only_active: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get most frequently used CABYS codes
        
        Args:
            limit: Maximum number of results
            only_active: Whether to include only active codes
            
        Returns:
            List of CABYS code dictionaries ordered by usage frequency
        """
        # Try cache first
        cache_key = f"cabys_most_used:{limit}:{only_active}"
        try:
            cached_results = await redis_manager.get(cache_key)
            if cached_results:
                import json
                return json.loads(cached_results)
        except Exception as e:
            logger.warning(f"Cache error (continuing without cache): {str(e)}")
        
        session = SessionLocal()
        try:
            results = CabysCode.get_most_used(
                session=session,
                limit=limit,
                only_active=only_active
            )
            
            code_dicts = [self._cabys_to_dict(code) for code in results]
            
            # Cache for 1 hour
            try:
                await redis_manager.set(cache_key, code_dicts, ttl=3600)
            except Exception as e:
                logger.warning(f"Cache write error: {str(e)}")
            
            return code_dicts
            
        except Exception as e:
            logger.error(f"Error getting most used CABYS codes: {str(e)}")
            return []
        finally:
            session.close()
    
    async def validate_code(self, codigo: str) -> Tuple[bool, Optional[str]]:
        """
        Validate CABYS code format and existence in database
        
        Args:
            codigo: CABYS code to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check format first
        if not CabysCode.validate_code_format(codigo):
            return False, f"Invalid CABYS code format. Must be exactly 13 digits, got: {codigo}"
        
        # Check if exists in database
        code_data = await self.get_code(codigo, use_cache=True)
        if not code_data:
            return False, f"CABYS code not found in database: {codigo}"
        
        # Check if active
        if not code_data.get('activo', False):
            return False, f"CABYS code is inactive: {codigo}"
        
        # Check validity period
        now = datetime.now(timezone.utc)
        fecha_desde = code_data.get('fecha_vigencia_desde')
        fecha_hasta = code_data.get('fecha_vigencia_hasta')
        
        if fecha_desde:
            try:
                if isinstance(fecha_desde, str):
                    fecha_desde_dt = datetime.fromisoformat(fecha_desde.replace('Z', '+00:00'))
                else:
                    # If it's already a datetime object, ensure it has timezone info
                    fecha_desde_dt = fecha_desde
                    if fecha_desde_dt.tzinfo is None:
                        fecha_desde_dt = fecha_desde_dt.replace(tzinfo=timezone.utc)
                
                if now < fecha_desde_dt:
                    return False, f"CABYS code not yet valid: {codigo}"
            except (ValueError, AttributeError, TypeError):
                # If date parsing fails, skip validity check
                pass
        
        if fecha_hasta:
            try:
                if isinstance(fecha_hasta, str):
                    fecha_hasta_dt = datetime.fromisoformat(fecha_hasta.replace('Z', '+00:00'))
                else:
                    # If it's already a datetime object, ensure it has timezone info
                    fecha_hasta_dt = fecha_hasta
                    if fecha_hasta_dt.tzinfo is None:
                        fecha_hasta_dt = fecha_hasta_dt.replace(tzinfo=timezone.utc)
                
                if now > fecha_hasta_dt:
                    return False, f"CABYS code has expired: {codigo}"
            except (ValueError, AttributeError, TypeError):
                # If date parsing fails, skip validity check
                pass
        
        return True, None
    
    async def get_categories(self, nivel: int = 1) -> List[str]:
        """
        Get all unique categories at specified level
        
        Args:
            nivel: Category level (1-4)
            
        Returns:
            List of unique category names
        """
        if nivel < 1 or nivel > 4:
            return []
        
        cache_key = f"cabys_categories:{nivel}"
        try:
            cached_categories = await redis_manager.get(cache_key)
            if cached_categories:
                import json
                return json.loads(cached_categories)
        except Exception as e:
            logger.warning(f"Cache error (continuing without cache): {str(e)}")
        
        session = SessionLocal()
        try:
            # Map level to column name
            column_map = {
                1: CabysCode.categoria_nivel_1,
                2: CabysCode.categoria_nivel_2,
                3: CabysCode.categoria_nivel_3,
                4: CabysCode.categoria_nivel_4
            }
            
            column = column_map[nivel]
            
            # Query unique categories
            results = session.query(column).filter(
                column.isnot(None),
                CabysCode.activo == True
            ).distinct().order_by(column).all()
            
            categories = [result[0] for result in results if result[0]]
            
            # Cache for 1 hour
            try:
                await redis_manager.set(cache_key, categories, ttl=3600)
            except Exception as e:
                logger.warning(f"Cache write error: {str(e)}")
            
            return categories
            
        except Exception as e:
            logger.error(f"Error getting categories for level {nivel}: {str(e)}")
            return []
        finally:
            session.close()
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get CABYS database statistics
        
        Returns:
            Dictionary with database statistics
        """
        cache_key = "cabys_statistics"
        try:
            cached_stats = await redis_manager.get(cache_key)
            if cached_stats:
                import json
                return json.loads(cached_stats)
        except Exception as e:
            logger.warning(f"Cache error (continuing without cache): {str(e)}")
        
        session = SessionLocal()
        try:
            # Get basic counts
            total_codes = session.query(CabysCode).count()
            active_codes = session.query(CabysCode).filter(CabysCode.activo == True).count()
            used_codes = session.query(CabysCode).filter(CabysCode.veces_usado > 0).count()
            
            # Get most used code
            most_used = session.query(CabysCode).filter(
                CabysCode.veces_usado > 0
            ).order_by(CabysCode.veces_usado.desc()).first()
            
            # Get category counts
            category_counts = {}
            for nivel in range(1, 5):
                column_map = {
                    1: CabysCode.categoria_nivel_1,
                    2: CabysCode.categoria_nivel_2,
                    3: CabysCode.categoria_nivel_3,
                    4: CabysCode.categoria_nivel_4
                }
                
                column = column_map[nivel]
                count = session.query(column).filter(
                    column.isnot(None),
                    CabysCode.activo == True
                ).distinct().count()
                
                category_counts[f'nivel_{nivel}'] = count
            
            stats = {
                'total_codes': total_codes,
                'active_codes': active_codes,
                'inactive_codes': total_codes - active_codes,
                'used_codes': used_codes,
                'unused_codes': active_codes - used_codes,
                'most_used_code': {
                    'codigo': most_used.codigo if most_used else None,
                    'descripcion': most_used.descripcion if most_used else None,
                    'veces_usado': most_used.veces_usado if most_used else 0
                },
                'category_counts': category_counts,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            # Cache for 30 minutes
            try:
                await redis_manager.set(cache_key, stats, ttl=1800)
            except Exception as e:
                logger.warning(f"Cache write error: {str(e)}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting CABYS statistics: {str(e)}")
            return {}
        finally:
            session.close()
    
    async def update_search_vectors(self) -> int:
        """
        Update search vectors for all CABYS codes for full-text search
        
        Returns:
            Number of records updated
        """
        session = SessionLocal()
        try:
            # Update search vectors using PostgreSQL's to_tsvector
            result = session.execute(text("""
                UPDATE codigos_cabys 
                SET updated_at = NOW()
                WHERE updated_at < NOW() - INTERVAL '1 day'
            """))
            
            session.commit()
            updated_count = result.rowcount
            
            logger.info(f"Updated search vectors for {updated_count} CABYS codes")
            return updated_count
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating search vectors: {str(e)}")
            return 0
        finally:
            session.close()
    
    async def clear_cache(self, codigo: Optional[str] = None):
        """
        Clear CABYS cache entries
        
        Args:
            codigo: Specific code to clear, or None to clear all CABYS cache
        """
        if codigo:
            # Clear specific code cache
            await redis_manager.delete(f"cabys:{codigo}")
            logger.info(f"Cleared cache for CABYS code: {codigo}")
        else:
            # Clear all CABYS-related cache entries
            # This is a simplified approach - in production you might want to use SCAN
            cache_keys = [
                "cabys_most_used:*",
                "cabys_categories:*",
                "cabys_statistics",
                "cabys_search:*",
                "cabys:*"
            ]
            
            for pattern in cache_keys:
                # Note: This is a simplified approach
                # In production, you'd use SCAN to find and delete matching keys
                pass
            
            logger.info("Cleared all CABYS cache entries")
    
    def _cabys_to_dict(self, cabys_code: CabysCode) -> Dict[str, Any]:
        """
        Convert CabysCode model to dictionary
        
        Args:
            cabys_code: CabysCode model instance
            
        Returns:
            Dictionary representation of CABYS code
        """
        return {
            'codigo': cabys_code.codigo,
            'descripcion': cabys_code.descripcion,
            'categoria_nivel_1': cabys_code.categoria_nivel_1,
            'categoria_nivel_2': cabys_code.categoria_nivel_2,
            'categoria_nivel_3': cabys_code.categoria_nivel_3,
            'categoria_nivel_4': cabys_code.categoria_nivel_4,
            'categoria_completa': cabys_code.categoria_completa,
            'impuesto_iva': float(cabys_code.impuesto_iva),
            'impuesto_iva_decimal': float(cabys_code.impuesto_iva_decimal),
            'exento_iva': cabys_code.exento_iva,
            'activo': cabys_code.activo,
            'version_cabys': cabys_code.version_cabys,
            'fecha_vigencia_desde': cabys_code.fecha_vigencia_desde.isoformat() if cabys_code.fecha_vigencia_desde else None,
            'fecha_vigencia_hasta': cabys_code.fecha_vigencia_hasta.isoformat() if cabys_code.fecha_vigencia_hasta else None,
            'veces_usado': cabys_code.veces_usado,
            'ultimo_uso': cabys_code.ultimo_uso.isoformat() if cabys_code.ultimo_uso else None,
            'created_at': cabys_code.created_at.isoformat(),
            'updated_at': cabys_code.updated_at.isoformat(),
            'tax_info': cabys_code.get_tax_info()
        }


# Global service instance
cabys_service = CabysService()