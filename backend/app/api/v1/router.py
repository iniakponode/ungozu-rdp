from fastapi import APIRouter
from app.api.v1.endpoints import auth, rdp, rdp_builder, rdp_catalogue, rdp_completion, rdp_record_lifecycle, rdp_learning_resources
api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(rdp.router)

api_router.include_router(rdp_builder.router)

api_router.include_router(rdp_catalogue.router)

api_router.include_router(rdp_completion.router)

api_router.include_router(rdp_record_lifecycle.router)
api_router.include_router(rdp_learning_resources.router)
