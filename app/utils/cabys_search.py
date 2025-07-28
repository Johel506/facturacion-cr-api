"""
CABYS Code Search Engine

Advanced search functionality for CABYS codes using PostgreSQL full-text search
with Spanish language support and performance optimizations.

This module provides sophisticated search capabilities including:
- Full-text search with Spanish stemming and stop words
- Fuzzy matching and typo tolerance
- Category-based filtering
- Performance optimizations with GIN indexes
- Search result ranking and relevance scoring

Requirements: 11.2, 11.3, 17.1
"""
import re
import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_, or_, desc
from sqlalchemy.exc import SQLAlchemyError

from app.models.cabys_code import CabysCode

logger = logging.getLogger(__name__)


class CabysSearchEngine:
    """
    Advanced CABYS code search engine with PostgreSQL full-text search
    
    Provides sophisticated search capabilities optimized for Spanish language
    content with performance optimizations using GIN indexes.
    """
    
    def __init__(self):
        self.spanish_stop_words = {
            'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'le',
            'da', 'su', 'por', 'son', 'con', 'para', 'al', 'del', 'los', 'las', 'una', 'como',
            'pero', 'sus', 'han', 'fue', 'ser', 'está', 'son', 'muy', 'más', 'sin', 'sobre',
            'todo', 'también', 'hasta', 'hay', 'donde', 'quien', 'desde', 'todos', 'durante',
            'otros', 'otro', 'esta', 'estas', 'este', 'estos', 'entre', 'cuando', 'mucho',
            'muchos', 'muchas', 'poco', 'pocos', 'pocas', 'tanto', 'tantos', 'tantas'
        }
    
    def _prepare_search_query(self, query: str) -> str:
        """
        Prepare search query for PostgreSQL full-text search
        
        Args:
            query: Raw search query
            
        Returns:
            Processed query string for tsquery
        """
        if not query:
            return ""
        
        # Clean and normalize the query
        query = query.strip().lower()
        
        # Remove special characters but keep spaces and hyphens
        query = re.sub(r'[^\w\s\-áéíóúñü]', ' ', query)
        
        # Split into words
        words = query.split()
        
        # Filter out stop words and short words
        filtered_words = [
            word for word in words 
            if len(word) >= 2 and word not in self.spanish_stop_words
        ]
        
        if not filtered_words:
            return ""
        
        # Join with AND operator for PostgreSQL tsquery
        # Use prefix matching for the last word to handle partial typing
        if len(filtered_words) == 1:
            return f"{filtered_words[0]}:*"
        else:
            # All words except last with exact match, last word with prefix match
            exact_words = " & ".join(filtered_words[:-1])
            prefix_word = f"{filtered_words[-1]}:*"
            return f"{exact_words} & {prefix_word}"
    
    def _prepare_fuzzy_query(self, query: str) -> str:
        """
        Prepare fuzzy search query for typo tolerance
        
        Args:
            query: Raw search query
            
        Returns:
            Fuzzy query string
        """
        if not query or len(query) < 3:
            return query
        
        # For fuzzy search, we'll use similarity with trigrams
        # This is handled in the SQL query with pg_trgm extension
        return query.strip().lower()
    
    async def search_by_text(
        self,
        session: Session,
        query: str,
        limit: int = 20,
        offset: int = 0,
        category_filter: Optional[str] = None,
        category_level: int = 1,
        only_active: bool = True,
        min_similarity: float = 0.3
    ) -> List[CabysCode]:
        """
        Perform full-text search for CABYS codes
        
        Args:
            session: SQLAlchemy session
            query: Search query string
            limit: Maximum number of results
            offset: Number of results to skip
            category_filter: Optional category filter
            category_level: Category level for filtering (1-4)
            only_active: Whether to include only active codes
            min_similarity: Minimum similarity score for fuzzy matching
            
        Returns:
            List of matching CabysCode objects ordered by relevance
        """
        if not query or len(query.strip()) < 2:
            return []
        
        try:
            # Prepare search queries
            tsquery = self._prepare_search_query(query)
            fuzzy_query = self._prepare_fuzzy_query(query)
            
            # Build base query
            base_query = session.query(CabysCode)
            
            # Apply active filter
            if only_active:
                base_query = base_query.filter(CabysCode.activo == True)
            
            # Apply category filter
            if category_filter and 1 <= category_level <= 8:
                category_column = getattr(CabysCode, f'categoria_nivel_{category_level}')
                base_query = base_query.filter(
                    category_column.ilike(f"%{category_filter}%")
                )
            
            # Primary search using full-text search
            if tsquery:
                primary_results = base_query.filter(
                    text("to_tsvector('spanish', descripcion || ' ' || "
                         "COALESCE(categoria_nivel_1, '') || ' ' || "
                         "COALESCE(categoria_nivel_2, '') || ' ' || "
                         "COALESCE(categoria_nivel_3, '') || ' ' || "
                         "COALESCE(categoria_nivel_4, '')) @@ to_tsquery('spanish', :query)")
                ).params(query=tsquery).order_by(
                    text("ts_rank(to_tsvector('spanish', descripcion || ' ' || "
                         "COALESCE(categoria_nivel_1, '') || ' ' || "
                         "COALESCE(categoria_nivel_2, '') || ' ' || "
                         "COALESCE(categoria_nivel_3, '') || ' ' || "
                         "COALESCE(categoria_nivel_4, '')), "
                         "to_tsquery('spanish', :query)) DESC, "
                         "veces_usado DESC")
                ).params(query=tsquery).offset(offset).limit(limit).all()
                
                # If we have enough results from primary search, return them
                if len(primary_results) >= limit:
                    return primary_results
            
            # Fallback to fuzzy search if primary search doesn't yield enough results
            remaining_limit = limit - len(primary_results) if tsquery else limit
            remaining_offset = max(0, offset - len(primary_results)) if tsquery else offset
            
            # Get codes already found to avoid duplicates
            found_codes = {code.codigo for code in primary_results} if tsquery else set()
            
            # Fuzzy search using trigram similarity
            fuzzy_results = base_query.filter(
                text("similarity(descripcion, :fuzzy_query) > :min_similarity")
            ).params(
                fuzzy_query=fuzzy_query,
                min_similarity=min_similarity
            ).filter(
                ~CabysCode.codigo.in_(found_codes) if found_codes else True
            ).order_by(
                text("similarity(descripcion, :fuzzy_query) DESC, veces_usado DESC")
            ).params(fuzzy_query=fuzzy_query).offset(remaining_offset).limit(remaining_limit).all()
            
            # Combine results
            if tsquery:
                return primary_results + fuzzy_results
            else:
                return fuzzy_results
                
        except SQLAlchemyError as e:
            logger.error(f"Database error in CABYS text search: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in CABYS text search: {str(e)}")
            return []
    
    async def get_search_count(
        self,
        session: Session,
        query: str,
        category_filter: Optional[str] = None,
        category_level: int = 1,
        only_active: bool = True,
        min_similarity: float = 0.3
    ) -> int:
        """
        Get total count of search results for pagination
        
        Args:
            session: SQLAlchemy session
            query: Search query string
            category_filter: Optional category filter
            category_level: Category level for filtering (1-4)
            only_active: Whether to include only active codes
            min_similarity: Minimum similarity score for fuzzy matching
            
        Returns:
            Total number of matching results
        """
        if not query or len(query.strip()) < 2:
            return 0
        
        try:
            # Prepare search queries
            tsquery = self._prepare_search_query(query)
            fuzzy_query = self._prepare_fuzzy_query(query)
            
            # Build base query
            base_query = session.query(func.count(CabysCode.codigo))
            
            # Apply active filter
            if only_active:
                base_query = base_query.filter(CabysCode.activo == True)
            
            # Apply category filter
            if category_filter and 1 <= category_level <= 8:
                category_column = getattr(CabysCode, f'categoria_nivel_{category_level}')
                base_query = base_query.filter(
                    category_column.ilike(f"%{category_filter}%")
                )
            
            # Count primary search results
            primary_count = 0
            if tsquery:
                primary_count = base_query.filter(
                    text("to_tsvector('spanish', descripcion || ' ' || "
                         "COALESCE(categoria_nivel_1, '') || ' ' || "
                         "COALESCE(categoria_nivel_2, '') || ' ' || "
                         "COALESCE(categoria_nivel_3, '') || ' ' || "
                         "COALESCE(categoria_nivel_4, '')) @@ to_tsquery('spanish', :query)")
                ).params(query=tsquery).scalar() or 0
            
            # Count fuzzy search results (excluding primary results)
            fuzzy_count = 0
            if primary_count < 100:  # Only do fuzzy search if primary results are limited
                # Get primary result codes to exclude from fuzzy search
                if tsquery and primary_count > 0:
                    primary_codes_query = session.query(CabysCode.codigo)
                    if only_active:
                        primary_codes_query = primary_codes_query.filter(CabysCode.activo == True)
                    if category_filter and 1 <= category_level <= 4:
                        category_column = getattr(CabysCode, f'categoria_nivel_{category_level}')
                        primary_codes_query = primary_codes_query.filter(
                            category_column.ilike(f"%{category_filter}%")
                        )
                    
                    primary_codes = primary_codes_query.filter(
                        text("to_tsvector('spanish', descripcion || ' ' || "
                             "COALESCE(categoria_nivel_1, '') || ' ' || "
                             "COALESCE(categoria_nivel_2, '') || ' ' || "
                             "COALESCE(categoria_nivel_3, '') || ' ' || "
                             "COALESCE(categoria_nivel_4, '')) @@ to_tsquery('spanish', :query)")
                    ).params(query=tsquery).all()
                    
                    found_codes = {code[0] for code in primary_codes}
                    
                    fuzzy_count = base_query.filter(
                        text("similarity(descripcion, :fuzzy_query) > :min_similarity")
                    ).params(
                        fuzzy_query=fuzzy_query,
                        min_similarity=min_similarity
                    ).filter(
                        ~CabysCode.codigo.in_(found_codes)
                    ).scalar() or 0
                else:
                    fuzzy_count = base_query.filter(
                        text("similarity(descripcion, :fuzzy_query) > :min_similarity")
                    ).params(
                        fuzzy_query=fuzzy_query,
                        min_similarity=min_similarity
                    ).scalar() or 0
            
            return primary_count + fuzzy_count
            
        except SQLAlchemyError as e:
            logger.error(f"Database error in CABYS search count: {str(e)}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected error in CABYS search count: {str(e)}")
            return 0
    
    async def search_suggestions(
        self,
        session: Session,
        query: str,
        limit: int = 10,
        only_active: bool = True
    ) -> List[str]:
        """
        Get search suggestions based on partial query
        
        Args:
            session: SQLAlchemy session
            query: Partial search query
            limit: Maximum number of suggestions
            only_active: Whether to include only active codes
            
        Returns:
            List of suggested search terms
        """
        if not query or len(query.strip()) < 2:
            return []
        
        try:
            query = query.strip().lower()
            
            # Build base query
            base_query = session.query(CabysCode.descripcion)
            
            if only_active:
                base_query = base_query.filter(CabysCode.activo == True)
            
            # Find descriptions that start with or contain the query
            suggestions = base_query.filter(
                or_(
                    CabysCode.descripcion.ilike(f"{query}%"),
                    CabysCode.descripcion.ilike(f"% {query}%")
                )
            ).order_by(
                CabysCode.veces_usado.desc()
            ).limit(limit * 2).all()  # Get more to filter unique words
            
            # Extract unique words/phrases that match the query
            suggestion_set = set()
            for desc_tuple in suggestions:
                description = desc_tuple[0].lower()
                words = description.split()
                
                # Find words that start with the query
                for word in words:
                    if word.startswith(query) and len(word) > len(query):
                        suggestion_set.add(word)
                
                # Also add the full description if it's relevant
                if query in description and len(description) <= 50:
                    suggestion_set.add(description)
                
                if len(suggestion_set) >= limit:
                    break
            
            return sorted(list(suggestion_set))[:limit]
            
        except Exception as e:
            logger.error(f"Error getting CABYS search suggestions: {str(e)}")
            return []
    
    async def search_by_code_pattern(
        self,
        session: Session,
        pattern: str,
        limit: int = 20,
        only_active: bool = True
    ) -> List[CabysCode]:
        """
        Search CABYS codes by code pattern matching
        
        Args:
            session: SQLAlchemy session
            pattern: Code pattern (can include wildcards)
            limit: Maximum number of results
            only_active: Whether to include only active codes
            
        Returns:
            List of matching CabysCode objects
        """
        if not pattern:
            return []
        
        try:
            # Clean pattern - only allow digits and wildcards
            clean_pattern = re.sub(r'[^0-9%_]', '', pattern)
            
            if not clean_pattern:
                return []
            
            # Build query
            base_query = session.query(CabysCode)
            
            if only_active:
                base_query = base_query.filter(CabysCode.activo == True)
            
            # Apply pattern matching
            results = base_query.filter(
                CabysCode.codigo.like(clean_pattern)
            ).order_by(
                CabysCode.codigo,
                CabysCode.veces_usado.desc()
            ).limit(limit).all()
            
            return results
            
        except Exception as e:
            logger.error(f"Error in CABYS code pattern search: {str(e)}")
            return []
    
    async def get_related_codes(
        self,
        session: Session,
        codigo: str,
        limit: int = 10,
        only_active: bool = True
    ) -> List[CabysCode]:
        """
        Get CABYS codes related to a given code (same category)
        
        Args:
            session: SQLAlchemy session
            codigo: Reference CABYS code
            limit: Maximum number of results
            only_active: Whether to include only active codes
            
        Returns:
            List of related CabysCode objects
        """
        if not CabysCode.validate_code_format(codigo):
            return []
        
        try:
            # Get the reference code
            ref_code = session.query(CabysCode).filter(
                CabysCode.codigo == codigo
            ).first()
            
            if not ref_code:
                return []
            
            # Build query for related codes
            base_query = session.query(CabysCode).filter(
                CabysCode.codigo != codigo  # Exclude the reference code itself
            )
            
            if only_active:
                base_query = base_query.filter(CabysCode.activo == True)
            
            # Find codes in the same categories (prioritize more specific levels)
            conditions = []
            
            # Level 4 match (most specific)
            if ref_code.categoria_nivel_4:
                conditions.append(
                    and_(
                        CabysCode.categoria_nivel_1 == ref_code.categoria_nivel_1,
                        CabysCode.categoria_nivel_2 == ref_code.categoria_nivel_2,
                        CabysCode.categoria_nivel_3 == ref_code.categoria_nivel_3,
                        CabysCode.categoria_nivel_4 == ref_code.categoria_nivel_4
                    )
                )
            
            # Level 3 match
            if ref_code.categoria_nivel_3:
                conditions.append(
                    and_(
                        CabysCode.categoria_nivel_1 == ref_code.categoria_nivel_1,
                        CabysCode.categoria_nivel_2 == ref_code.categoria_nivel_2,
                        CabysCode.categoria_nivel_3 == ref_code.categoria_nivel_3,
                        CabysCode.categoria_nivel_4 != ref_code.categoria_nivel_4
                    )
                )
            
            # Level 2 match
            if ref_code.categoria_nivel_2:
                conditions.append(
                    and_(
                        CabysCode.categoria_nivel_1 == ref_code.categoria_nivel_1,
                        CabysCode.categoria_nivel_2 == ref_code.categoria_nivel_2,
                        CabysCode.categoria_nivel_3 != ref_code.categoria_nivel_3
                    )
                )
            
            # Level 1 match (least specific)
            if ref_code.categoria_nivel_1:
                conditions.append(
                    and_(
                        CabysCode.categoria_nivel_1 == ref_code.categoria_nivel_1,
                        CabysCode.categoria_nivel_2 != ref_code.categoria_nivel_2
                    )
                )
            
            if not conditions:
                return []
            
            # Execute query with priority ordering
            results = base_query.filter(
                or_(*conditions)
            ).order_by(
                # Prioritize by category level match, then by usage
                desc(func.case(
                    (and_(
                        CabysCode.categoria_nivel_1 == ref_code.categoria_nivel_1,
                        CabysCode.categoria_nivel_2 == ref_code.categoria_nivel_2,
                        CabysCode.categoria_nivel_3 == ref_code.categoria_nivel_3,
                        CabysCode.categoria_nivel_4 == ref_code.categoria_nivel_4
                    ), 4),
                    (and_(
                        CabysCode.categoria_nivel_1 == ref_code.categoria_nivel_1,
                        CabysCode.categoria_nivel_2 == ref_code.categoria_nivel_2,
                        CabysCode.categoria_nivel_3 == ref_code.categoria_nivel_3
                    ), 3),
                    (and_(
                        CabysCode.categoria_nivel_1 == ref_code.categoria_nivel_1,
                        CabysCode.categoria_nivel_2 == ref_code.categoria_nivel_2
                    ), 2),
                    else_=1
                )),
                CabysCode.veces_usado.desc(),
                CabysCode.codigo
            ).limit(limit).all()
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting related CABYS codes for {codigo}: {str(e)}")
            return []