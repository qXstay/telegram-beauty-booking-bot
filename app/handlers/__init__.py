from app.handlers.booking import router as booking_router
from app.handlers.common import router as common_router
from app.handlers.records import router as records_router


def get_routers():
    return [common_router, records_router, booking_router]
