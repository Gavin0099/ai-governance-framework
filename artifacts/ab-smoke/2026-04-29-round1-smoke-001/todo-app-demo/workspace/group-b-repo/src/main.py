"""
Todo App — 示範用 FastAPI 應用
配合 AI Governance Framework examples/ 使用
"""
from fastapi import FastAPI

app = FastAPI(title="Todo API", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok"}


# TODO: 實作 /todos CRUD 路由（Phase A Sprint 1）
