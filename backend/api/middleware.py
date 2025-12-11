"""
Custom middleware for the Smart Attendance System API.
"""

import time
import logging
from typing import Dict, Any
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware for API requests."""
    
    # Public endpoints that don't require authentication
    PUBLIC_PATHS = {
        "/api/v1/health",
        "/api/v1/docs",
        "/api/v1/redoc",
        "/api/v1/openapi.json",
        "/api/v1/auth/login",
        "/",
        "/api/v1/students",  # Allow student registration
        "/api/v1/students/",  # Allow student registration
        "/api/v1/face-recognition",  # Allow face recognition
        "/api/v1/attendance",  # Allow attendance operations
    }
    
    async def dispatch(self, request: Request, call_next):
        """Process request through authentication middleware."""
        
        # Skip authentication for public paths
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)
        
        # Skip authentication for student and face recognition endpoints (development only)
        if request.url.path.startswith("/api/v1/students") or \
           request.url.path.startswith("/api/v1/face-recognition") or \
           request.url.path.startswith("/api/v1/attendance"):
            return await call_next(request)
        
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Check for Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing or invalid authorization header"}
            )
        
        # Continue with request processing
        response = await call_next(request)
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware to prevent API abuse."""
    
    def __init__(self, app, requests_per_minute: int = 100):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.redis_client = None
    
    async def get_redis_client(self):
        """Get Redis client for rate limiting."""
        if not self.redis_client:
            try:
                self.redis_client = redis.from_url("redis://localhost:6379/1")
            except Exception as e:
                logger.warning(f"Redis not available for rate limiting: {e}")
                return None
        return self.redis_client
    
    async def dispatch(self, request: Request, call_next):
        """Process request through rate limiting middleware."""
        
        # Skip rate limiting for health checks
        if request.url.path == "/api/v1/health":
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host
        
        # Try to apply rate limiting with Redis
        redis_client = await self.get_redis_client()
        if redis_client:
            try:
                # Create rate limit key
                rate_limit_key = f"rate_limit:{client_ip}"
                
                # Get current request count
                current_requests = await redis_client.get(rate_limit_key)
                
                if current_requests is None:
                    # First request from this IP
                    await redis_client.setex(rate_limit_key, 60, 1)
                else:
                    current_count = int(current_requests)
                    if current_count >= self.requests_per_minute:
                        return JSONResponse(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            content={
                                "detail": "Rate limit exceeded. Please try again later.",
                                "retry_after": 60
                            }
                        )
                    
                    # Increment request count
                    await redis_client.incr(rate_limit_key)
                
            except Exception as e:
                logger.warning(f"Rate limiting error: {e}")
                # Continue without rate limiting if Redis fails
        
        # Continue with request processing
        response = await call_next(request)
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logging middleware for API requests and responses."""
    
    async def dispatch(self, request: Request, call_next):
        """Process request through logging middleware."""
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"from {request.client.host}"
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"Response: {response.status_code} "
            f"processed in {process_time:.3f}s"
        )
        
        # Add processing time header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware."""
    
    async def dispatch(self, request: Request, call_next):
        """Process request through error handling middleware."""
        try:
            response = await call_next(request)
            return response
            
        except HTTPException:
            # Re-raise HTTP exceptions (handled by FastAPI)
            raise
            
        except Exception as e:
            # Log unexpected errors
            logger.error(f"Unexpected error processing request: {e}", exc_info=True)
            
            # Return generic error response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "Internal server error",
                    "error_id": str(int(time.time()))
                }
            )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to responses."""
    
    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response