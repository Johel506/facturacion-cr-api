"""
Ministry of Finance API client utilities for Costa Rica Electronic Invoice API
Handles OIDC authentication, HTTP communication, and rate limiting compliance
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Tuple
from urllib.parse import urljoin

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.oauth2 import OAuth2Error

from app.core.config import settings

logger = logging.getLogger(__name__)


class MinistryAPIError(Exception):
    """Base exception for Ministry API errors"""
    pass


class MinistryAuthenticationError(MinistryAPIError):
    """Authentication-related errors"""
    pass


class MinistryRateLimitError(MinistryAPIError):
    """Rate limiting errors"""
    pass


class MinistryValidationError(MinistryAPIError):
    """Document validation errors from Ministry"""
    pass


class MinistryNetworkError(MinistryAPIError):
    """Network-related errors"""
    pass


class MinistryClient:
    """
    Async HTTP client for Costa Rica Ministry of Finance API
    Handles OIDC authentication, rate limiting, and error handling
    """
    
    def __init__(
        self,
        username: str,
        password: str,
        client_id: str,
        client_secret: str = "",
        environment: str = "development",
        timeout: int = 30,
        max_retries: int = 3
    ):
        self.username = username
        self.password = password
        self.client_id = client_id
        self.client_secret = client_secret
        self.environment = environment
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Set URLs based on environment
        if environment == "production":
            self.auth_url = settings.HACIENDA_API_URL_PROD
            self.api_url = settings.MINISTRY_API_URL_PROD
        else:
            self.auth_url = settings.HACIENDA_API_URL_DEV
            self.api_url = settings.MINISTRY_API_URL_DEV
        
        # OAuth endpoints
        if environment == "production":
            self.token_endpoint = urljoin(self.auth_url, "/auth/realms/rut/protocol/openid-connect/token")
        else:
            self.token_endpoint = urljoin(self.auth_url, "/auth/realms/rut-stag/protocol/openid-connect/token")
        
        # HTTP client configuration
        self.client_config = {
            "timeout": httpx.Timeout(timeout),
            "limits": httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20,
                keepalive_expiry=30.0
            ),
            "follow_redirects": True
        }
        
        # Token management
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._oauth_client: Optional[AsyncOAuth2Client] = None
        
        logger.info(f"Ministry client initialized for {environment} environment")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_authenticated()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._oauth_client:
            await self._oauth_client.aclose()
    
    async def _get_oauth_client(self) -> AsyncOAuth2Client:
        """Get or create OAuth2 client"""
        if not self._oauth_client:
            self._oauth_client = AsyncOAuth2Client(
                client_id=self.client_id,
                client_secret=self.client_secret,
                **self.client_config
            )
        return self._oauth_client
    
    async def _authenticate(self) -> Tuple[str, datetime]:
        """
        Authenticate with Ministry OIDC provider using username/password
        Returns access token and expiration time
        """
        try:
            # Prepare authentication data for password grant
            auth_data = {
                "grant_type": "password",
                "username": self.username,
                "password": self.password,
                "client_id": self.client_id
            }
            
            # Add client_secret only if it's not empty
            if self.client_secret:
                auth_data["client_secret"] = self.client_secret
            
            # Make direct HTTP request for token
            async with httpx.AsyncClient(**self.client_config) as client:
                response = await client.post(
                    self.token_endpoint,
                    data=auth_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"Authentication failed with status {response.status_code}: {error_text}")
                    raise MinistryAuthenticationError(f"Authentication failed: {error_text}")
                
                token_response = response.json()
            
            access_token = token_response.get("access_token")
            expires_in = token_response.get("expires_in", 3600)  # Default 1 hour
            
            if not access_token:
                raise MinistryAuthenticationError("No access token received from Ministry")
            
            # Calculate expiration time with 5-minute buffer
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 300)
            
            logger.info("Successfully authenticated with Ministry API")
            return access_token, expires_at
            
        except httpx.RequestError as e:
            logger.error(f"Network error during authentication: {e}")
            raise MinistryNetworkError(f"Authentication network error: {e}")
        except Exception as e:
            logger.error(f"Unexpected authentication error: {e}")
            raise MinistryAuthenticationError(f"Unexpected authentication error: {e}")
    
    async def _ensure_authenticated(self) -> str:
        """Ensure we have a valid access token"""
        now = datetime.utcnow()
        
        # Check if token is expired or about to expire
        if (not self._access_token or 
            not self._token_expires_at or 
            now >= self._token_expires_at):
            
            logger.info("Access token expired or missing, re-authenticating")
            self._access_token, self._token_expires_at = await self._authenticate()
        
        return self._access_token
    
    def _parse_rate_limit_headers(self, response: httpx.Response) -> Dict[str, Any]:
        """Parse rate limit headers from Ministry response"""
        rate_limit_info = {}
        
        # Common rate limit headers
        headers_map = {
            "x-ratelimit-limit": "limit",
            "x-ratelimit-remaining": "remaining",
            "x-ratelimit-reset": "reset",
            "retry-after": "retry_after"
        }
        
        for header, key in headers_map.items():
            value = response.headers.get(header)
            if value:
                try:
                    rate_limit_info[key] = int(value)
                except ValueError:
                    rate_limit_info[key] = value
        
        return rate_limit_info
    
    def _should_retry(self, response: httpx.Response, attempt: int) -> Tuple[bool, int]:
        """
        Determine if request should be retried and calculate delay
        Returns (should_retry, delay_seconds)
        """
        if attempt >= self.max_retries:
            return False, 0
        
        # Retry on server errors (5xx)
        if 500 <= response.status_code < 600:
            delay = min(2 ** attempt, 60)  # Exponential backoff, max 60s
            return True, delay
        
        # Retry on rate limiting (429)
        if response.status_code == 429:
            rate_limit_info = self._parse_rate_limit_headers(response)
            delay = rate_limit_info.get("retry_after", 2 ** attempt)
            return True, min(delay, 300)  # Max 5 minutes
        
        # Retry on authentication errors (401) - token might have expired
        if response.status_code == 401:
            # Clear token to force re-authentication
            self._access_token = None
            self._token_expires_at = None
            return True, 1
        
        return False, 0
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """
        Make authenticated HTTP request to Ministry API with retry logic
        """
        url = urljoin(self.api_url, endpoint)
        request_headers = headers or {}
        
        for attempt in range(self.max_retries + 1):
            try:
                # Ensure we have valid authentication
                access_token = await self._ensure_authenticated()
                request_headers["Authorization"] = f"Bearer {access_token}"
                request_headers["Content-Type"] = "application/json"
                
                # Create new client for each request to avoid connection issues
                async with httpx.AsyncClient(**self.client_config) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        json=data,
                        params=params,
                        headers=request_headers
                    )
                
                # Log rate limit information
                rate_limit_info = self._parse_rate_limit_headers(response)
                if rate_limit_info:
                    logger.info(f"Rate limit info: {rate_limit_info}")
                
                # Check if we should retry
                should_retry, delay = self._should_retry(response, attempt)
                
                if not should_retry:
                    # Handle specific error cases
                    if response.status_code == 429:
                        raise MinistryRateLimitError(
                            f"Rate limit exceeded. {rate_limit_info}"
                        )
                    elif response.status_code == 401:
                        raise MinistryAuthenticationError("Authentication failed")
                    elif response.status_code == 400:
                        # Parse validation errors
                        try:
                            error_data = response.json()
                            raise MinistryValidationError(
                                f"Document validation failed: {error_data}"
                            )
                        except json.JSONDecodeError:
                            raise MinistryValidationError(
                                f"Document validation failed: {response.text}"
                            )
                    elif 400 <= response.status_code < 500:
                        raise MinistryAPIError(
                            f"Client error {response.status_code}: {response.text}"
                        )
                    elif response.status_code >= 500:
                        raise MinistryAPIError(
                            f"Server error {response.status_code}: {response.text}"
                        )
                    
                    return response
                
                # Wait before retry
                if delay > 0:
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{self.max_retries + 1}), "
                        f"retrying in {delay}s. Status: {response.status_code}"
                    )
                    await asyncio.sleep(delay)
                
            except httpx.RequestError as e:
                if attempt == self.max_retries:
                    logger.error(f"Network error after {self.max_retries + 1} attempts: {e}")
                    raise MinistryNetworkError(f"Network error: {e}")
                
                delay = min(2 ** attempt, 60)
                logger.warning(
                    f"Network error (attempt {attempt + 1}/{self.max_retries + 1}), "
                    f"retrying in {delay}s: {e}"
                )
                await asyncio.sleep(delay)
        
        raise MinistryAPIError("Max retries exceeded")
    
    async def submit_document(
        self,
        document_xml: str,
        document_key: str,
        document_type: str = "01",
        callback_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit electronic document to Ministry
        
        Args:
            document_xml: Signed XML document
            document_key: 50-character document key
            document_type: Document type code (01-07)
            callback_url: Optional callback URL for asynchronous responses
        
        Returns:
            Ministry response data
        """
        try:
            # Prepare submission data
            submission_data = {
                "clave": document_key,
                "fecha": datetime.utcnow().isoformat() + "Z",
                "emisor": {
                    "tipoIdentificacion": document_type,
                    "numeroIdentificacion": document_key[14:26]  # Extract issuer ID from key
                },
                "comprobanteXml": document_xml
            }
            
            # Add callback URL if provided
            if callback_url:
                submission_data["callbackUrl"] = callback_url
            
            logger.info(f"Submitting document {document_key} to Ministry")
            
            response = await self._make_request(
                method="POST",
                endpoint="/recepcion",
                data=submission_data
            )
            
            response_data = response.json()
            logger.info(f"Document {document_key} submitted successfully")
            
            return response_data
            
        except Exception as e:
            logger.error(f"Failed to submit document {document_key}: {e}")
            raise
    
    async def check_document_status(self, document_key: str) -> Dict[str, Any]:
        """
        Check document status with Ministry
        
        Args:
            document_key: 50-character document key
        
        Returns:
            Document status information
        """
        try:
            logger.info(f"Checking status for document {document_key}")
            
            response = await self._make_request(
                method="GET",
                endpoint=f"/consulta/{document_key}"
            )
            
            status_data = response.json()
            logger.info(f"Status check completed for document {document_key}")
            
            return status_data
            
        except Exception as e:
            logger.error(f"Failed to check status for document {document_key}: {e}")
            raise
    
    async def submit_receptor_message(
        self,
        message_xml: str,
        document_key: str,
        message_type: int
    ) -> Dict[str, Any]:
        """
        Submit receptor message (acceptance/rejection) to Ministry
        
        Args:
            message_xml: Signed receptor message XML
            document_key: Original document key
            message_type: 1=Accepted, 2=Partial, 3=Rejected
        
        Returns:
            Ministry response data
        """
        try:
            # Prepare message data
            message_data = {
                "clave": document_key,
                "fecha": datetime.utcnow().isoformat() + "Z",
                "mensaje": message_type,
                "mensajeXml": message_xml
            }
            
            logger.info(f"Submitting receptor message for document {document_key}")
            
            response = await self._make_request(
                method="POST",
                endpoint="/receptor",
                data=message_data
            )
            
            response_data = response.json()
            logger.info(f"Receptor message submitted successfully for document {document_key}")
            
            return response_data
            
        except Exception as e:
            logger.error(f"Failed to submit receptor message for document {document_key}: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Ministry API
        
        Returns:
            Health status information
        """
        try:
            response = await self._make_request(
                method="GET",
                endpoint="/health"
            )
            
            return {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds() if response.elapsed else None,
                "environment": self.environment
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "environment": self.environment
            }