import logging
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.core.rate_limit import limiter, rate_limit_exceeded_handler
from app.api.v1.router import api_router

logger=logging.getLogger(__name__)
def create_application()->FastAPI:
    app=FastAPI(title=settings.PROJECT_NAME,version=settings.VERSION,docs_url='/docs' if settings.DEBUG else None,redoc_url='/redoc' if settings.DEBUG else None,openapi_url='/openapi.json' if settings.DEBUG else None)
    app.state.limiter=limiter
    app.add_exception_handler(RateLimitExceeded,rate_limit_exceeded_handler)
    app.add_middleware(CORSMiddleware,allow_origins=settings.CORS_ORIGINS,allow_credentials=True,allow_methods=['GET','POST','PUT','PATCH','DELETE','OPTIONS'],allow_headers=['Authorization','Content-Type','Accept','Origin','X-Requested-With'])
    @app.exception_handler(StarletteHTTPException)
    async def http_exc(request:Request,exc:StarletteHTTPException): return JSONResponse(status_code=exc.status_code,content={'detail':exc.detail})
    @app.exception_handler(RequestValidationError)
    async def val_exc(request:Request,exc:RequestValidationError): return JSONResponse(status_code=422,content={'detail':jsonable_encoder(exc.errors())})
    @app.exception_handler(Exception)
    async def unhandled(request:Request,exc:Exception):
        logger.exception('Unhandled exception: %s',exc); return JSONResponse(status_code=500,content={'detail':'An unexpected error occurred.'})
    app.include_router(api_router,prefix='/api/v1')
    return app
app=create_application()
@app.get('/health', tags=['system'])
@app.get('/api/v1/health', tags=['system'])
async def health():
    return {'status': 'ok', 'version': settings.VERSION, 'service': 'ungozu-rdp-api'}
