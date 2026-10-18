from fastapi import FastAPI, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Task
from app.user_models import User
from app.schemas import TaskCreate, TaskUpdate, TaskResponse
from app.dependencies import get_db, get_current_user
from app.auth_routes import router as auth_router

app = FastAPI(
    title="Task Manager API",
    description="A multi-user Task Manager API with JWT authentication",
    version="2.0.0",
)

app.include_router(auth_router)


# 1. Create a task
@app.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_task = Task(
        title=task_data.title,
        description=task_data.description,
        user_id=current_user.id,
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    return new_task


# 2. Get all tasks with pagination and filtering
@app.get("/tasks", response_model=list[TaskResponse])
def get_tasks(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    completed: bool | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Task).filter(
        Task.user_id == current_user.id
    )

    if completed is not None:
        query = query.filter(Task.completed == completed)

    return (
        query
        .order_by(Task.id)
        .offset(skip)
        .limit(limit)
        .all()
    )


# 3. Get one task
@app.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = (
        db.query(Task)
        .filter(
            Task.id == task_id,
            Task.user_id == current_user.id,
        )
        .first()
    )

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return task


# 4. Update a task
@app.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = (
        db.query(Task)
        .filter(
            Task.id == task_id,
            Task.user_id == current_user.id,
        )
        .first()
    )

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    update_data = task_data.model_dump(exclude_unset=True)

    if "title" in update_data and update_data["title"] is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Title cannot be null",
        )

    if "completed" in update_data and update_data["completed"] is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Completed cannot be null",
        )

    for field, value in update_data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)

    return task


# 5. Delete a task
@app.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = (
        db.query(Task)
        .filter(
            Task.id == task_id,
            Task.user_id == current_user.id,
        )
        .first()
    )

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    db.delete(task)
    db.commit()

    return {
        "message": "Task deleted successfully",
        "task_id": task_id,
    }