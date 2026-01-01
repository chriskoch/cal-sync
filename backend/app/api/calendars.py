from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Literal, Optional, Dict, Any
from googleapiclient.discovery import build
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.api.auth import get_current_user
from app.api.oauth import get_credentials_from_db

router = APIRouter(prefix="/calendars", tags=["calendars"])


class CalendarItem(BaseModel):
    id: str
    summary: str
    description: str = ""
    time_zone: str = ""
    access_role: str = ""
    is_primary: bool = False
    background_color: str = ""
    color_id: str = ""


class CalendarListResponse(BaseModel):
    calendars: List[CalendarItem]


class EventDateTime(BaseModel):
    dateTime: str
    timeZone: str = "UTC"


class CreateEventRequest(BaseModel):
    calendar_id: str
    summary: str
    description: Optional[str] = ""
    start: EventDateTime
    end: EventDateTime


class UpdateEventRequest(BaseModel):
    calendar_id: str
    event_id: str
    summary: Optional[str] = None
    description: Optional[str] = None
    start: Optional[EventDateTime] = None
    end: Optional[EventDateTime] = None


class DeleteEventRequest(BaseModel):
    calendar_id: str
    event_id: str


class ListEventsRequest(BaseModel):
    calendar_id: str
    time_min: str
    time_max: str
    query: Optional[str] = None


@router.get("/{account_type}/list", response_model=CalendarListResponse)
def list_calendars(
    account_type: Literal["source", "destination"],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all calendars for the specified account (source or destination).

    Fetches calendars from Google Calendar API using stored OAuth credentials.
    """
    # Get credentials from database
    creds = get_credentials_from_db(str(current_user.id), account_type, db)

    if not creds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No OAuth connection found for {account_type} account. Please connect your account first.",
        )

    # Build Calendar API service
    try:
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)

        # Fetch calendar list
        calendar_list_result = service.calendarList().list().execute()
        calendar_items = calendar_list_result.get("items", [])

        calendars = [
            CalendarItem(
                id=item.get("id", ""),
                summary=item.get("summary", ""),
                description=item.get("description", ""),
                time_zone=item.get("timeZone", ""),
                access_role=item.get("accessRole", ""),
                is_primary=item.get("primary", False),
                background_color=item.get("backgroundColor", ""),
                color_id=item.get("colorId", ""),
            )
            for item in calendar_items
        ]

        return {"calendars": calendars}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch calendars: {str(e)}",
        )


@router.post("/{account_type}/events/create")
def create_event(
    account_type: Literal["source", "destination"],
    request: CreateEventRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Create an event in the specified calendar.

    This is a test helper endpoint to create events programmatically.
    """
    # Get credentials
    creds = get_credentials_from_db(current_user.id, account_type, db)

    if not creds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No OAuth connection found for {account_type} account",
        )

    try:
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)

        event_body = {
            "summary": request.summary,
            "description": request.description,
            "start": {
                "dateTime": request.start.dateTime,
                "timeZone": request.start.timeZone,
            },
            "end": {
                "dateTime": request.end.dateTime,
                "timeZone": request.end.timeZone,
            },
        }

        event = service.events().insert(
            calendarId=request.calendar_id,
            body=event_body
        ).execute()

        return event

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create event: {str(e)}",
        )


@router.post("/{account_type}/events/update")
def update_event(
    account_type: Literal["source", "destination"],
    request: UpdateEventRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Update an event in the specified calendar.

    This is a test helper endpoint to update events programmatically.
    """
    # Get credentials
    creds = get_credentials_from_db(current_user.id, account_type, db)

    if not creds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No OAuth connection found for {account_type} account",
        )

    try:
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)

        # Build update payload with only provided fields
        update_body = {}
        if request.summary is not None:
            update_body["summary"] = request.summary
        if request.description is not None:
            update_body["description"] = request.description
        if request.start is not None:
            update_body["start"] = {
                "dateTime": request.start.dateTime,
                "timeZone": request.start.timeZone,
            }
        if request.end is not None:
            update_body["end"] = {
                "dateTime": request.end.dateTime,
                "timeZone": request.end.timeZone,
            }

        event = service.events().patch(
            calendarId=request.calendar_id,
            eventId=request.event_id,
            body=update_body
        ).execute()

        return event

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update event: {str(e)}",
        )


@router.post("/{account_type}/events/delete")
def delete_event(
    account_type: Literal["source", "destination"],
    request: DeleteEventRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete an event from the specified calendar.

    This is a test helper endpoint to delete events programmatically.
    """
    # Get credentials
    creds = get_credentials_from_db(current_user.id, account_type, db)

    if not creds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No OAuth connection found for {account_type} account",
        )

    try:
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)

        service.events().delete(
            calendarId=request.calendar_id,
            eventId=request.event_id
        ).execute()

        return {"status": "deleted"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete event: {str(e)}",
        )


@router.post("/{account_type}/events/list")
def list_events(
    account_type: Literal["source", "destination"],
    request: ListEventsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    List events in the specified calendar.

    This is a test helper endpoint to list events programmatically.
    """
    # Get credentials
    creds = get_credentials_from_db(current_user.id, account_type, db)

    if not creds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No OAuth connection found for {account_type} account",
        )

    try:
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)

        params = {
            "calendarId": request.calendar_id,
            "timeMin": request.time_min,
            "timeMax": request.time_max,
            "singleEvents": True,
            "orderBy": "startTime",
        }

        if request.query:
            params["q"] = request.query

        events_result = service.events().list(**params).execute()

        return events_result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list events: {str(e)}",
        )
