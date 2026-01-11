from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api import chat, user
from backend.app.errors import setup_logging, register_error_handlers
import os

# Setup logging
log_level = os.getenv("LOG_LEVEL", "INFO")
logger = setup_logging(log_level=log_level, log_dir="logs")

app = FastAPI(title="AI Study Buddy API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register error handlers
register_error_handlers(app)

# Register routes
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(user.router, prefix="/api", tags=["user"])

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
