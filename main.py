"""
Updated Main Application with Design Rule Checker
Date: 2025-08-29 01:49:46 UTC
User: HarrisonKuo47
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import logging

# Import route modules
from routes.upload_routes import router as upload_router
from routes.view_routes import router as view_router
from routes.design_rule_routes import router as design_rule_router  # ✅ New import

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Lead Frame Mapping Tool",
    description="Lead Frame and Handler Kit Analysis Tool with Design Rule Checker",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/css", StaticFiles(directory="static/css"), name="css")
app.mount("/js", StaticFiles(directory="static/js"), name="js")

# Include routers
app.include_router(upload_router, tags=["Upload"])
app.include_router(view_router, tags=["Views"])
app.include_router(design_rule_router, tags=["Design Rules"])  # ✅ New router

@app.get("/")
async def home():
    """Home page redirect"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/handler_kit_database")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Lead Frame Mapping Tool with Design Rule Checker - HarrisonKuo47 at 2025-08-29 01:49:46")
    uvicorn.run(app, host="0.0.0.0", port=8000)