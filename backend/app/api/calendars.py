from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Literal
from googleapiclient.discovery import build

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


class CalendarListResponse(BaseModel):
    calendars: List[CalendarItem]


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
            )
            for item in calendar_items
        ]

        return {"calendars": calendars}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch calendars: {str(e)}",
        )
