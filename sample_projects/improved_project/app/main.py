import logging
from fastapi import FastAPI, HTTPException, Depends
from app.config import settings

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.PROJECT_NAME)

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}

@app.post("/tasks/execute")
def execute_task(task_id: str):
    if not task_id:
        raise HTTPException(status_code=400, detail="task_id is required")
    logger.info(f"Executing task: {task_id}")
    return {"task_id": task_id, "status": "completed"}
