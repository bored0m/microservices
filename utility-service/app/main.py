import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import CORS_ORIGINS
from .database import Base, engine, get_db
from .deps import CurrentUser, get_current_user, require_admin
from .models import Issue
from .schemas import IssueCreate, IssueOut, IssueStatus, IssueStatusUpdate

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("utility")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    log.info("Utility service started, tables ready")
    yield


app = FastAPI(
    title="Utility Service",
    description="Заявки ЖКХ. Токены проверяются через Auth Service по HTTP.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"]
)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}


@app.post("/issues", response_model=IssueOut, status_code=status.HTTP_201_CREATED, tags=["issues"])
def create_issue(
    data: IssueCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    issue = Issue(
        **data.model_dump(mode="json"),
        author_id=user.id,
        author_username=user.username,
        status="new",
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)
    log.info("Issue created id=%s author=%s category=%s", issue.id, user.id, issue.category)
    return issue


@app.get("/issues", response_model=list[IssueOut], tags=["issues"])
def list_issues(
    status_filter: IssueStatus | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Житель видит свои заявки, администратор — все."""
    stmt = select(Issue).order_by(Issue.created_at.desc())
    if not user.is_admin:
        stmt = stmt.where(Issue.author_id == user.id)
    if status_filter:
        stmt = stmt.where(Issue.status == status_filter.value)
    return db.scalars(stmt).all()


@app.put("/issues/{issue_id}", response_model=IssueOut, tags=["issues"])
def update_issue_status(
    issue_id: int,
    data: IssueStatusUpdate,
    db: Session = Depends(get_db),
    admin: CurrentUser = Depends(require_admin),
):
    issue = db.get(Issue, issue_id)
    if issue is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue not found")
    old = issue.status
    issue.status = data.status.value
    db.commit()
    db.refresh(issue)
    log.info("Issue id=%s status %s -> %s by admin=%s", issue.id, old, issue.status, admin.id)
    return issue
