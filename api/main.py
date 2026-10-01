"""Mock ticketing API (FastAPI, in-memory storage)."""
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, field_validator

VALID_STATUSES = ("OPEN", "RESOLVED", "CLOSED")

app = FastAPI(title="Mock Ticketing API")
tickets: dict[str, dict] = {}


class TicketCreate(BaseModel):
    title: str
    description: str

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Title must not be blank.")
        return value


class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    resolution: Optional[str] = None
    comment: Optional[str] = None

    @field_validator("title")
    @classmethod
    def updated_title_must_not_be_blank(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            raise ValueError("Title must not be blank.")
        return value


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_status(status: str) -> str:
    normalized = status.strip().upper()
    if normalized not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{status}'. Valid statuses are: {', '.join(VALID_STATUSES)}.",
        )
    return normalized


def get_or_404(ticket_id: str) -> dict:
    ticket = tickets.get(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket with id '{ticket_id}' not found.")
    return ticket


@app.post("/tickets", status_code=201)
def create_ticket(body: TicketCreate):
    ticket = {
        "id": str(uuid4()),
        "title": body.title,
        "description": body.description,
        "created": now(),
        "status": "OPEN",
        "resolution": None,
        "comments": [],
        "updated_at": None,
    }
    tickets[ticket["id"]] = ticket
    return ticket


@app.get("/tickets")
def list_tickets(status: Optional[str] = None, has_resolution: Optional[bool] = None):
    result = list(tickets.values())
    if status is not None:
        status = validate_status(status)
        result = [t for t in result if t["status"] == status]
    if has_resolution is not None:
        result = [t for t in result if bool(t["resolution"]) == has_resolution]
    return result


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str):
    return get_or_404(ticket_id)


@app.patch("/tickets/{ticket_id}")
def update_ticket(ticket_id: str, body: TicketUpdate):
    ticket = get_or_404(ticket_id)

    new_status = validate_status(body.status) if body.status is not None else None
    resolution = body.resolution if body.resolution is not None else ticket["resolution"]

    if new_status == "RESOLVED" and not (resolution and resolution.strip()):
        raise HTTPException(
            status_code=422,
            detail="A resolution note is required when setting status to RESOLVED.",
        )

    if new_status is not None:
        ticket["status"] = new_status
    if body.title is not None:
        ticket["title"] = body.title
    if body.description is not None:
        ticket["description"] = body.description
    if body.resolution is not None:
        ticket["resolution"] = body.resolution
    if body.comment is not None:
        ticket["comments"].append({"text": body.comment, "created": now()})
    ticket["updated_at"] = now()
    return ticket


@app.delete("/tickets/{ticket_id}", status_code=204)
def delete_ticket(ticket_id: str):
    get_or_404(ticket_id)
    del tickets[ticket_id]
    return Response(status_code=204)
