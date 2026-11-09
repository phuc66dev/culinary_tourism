from typing import Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

TERMINAL_EVENTS = {"audio_completed", "audio_ended"}


class AnalyticsEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    poi_id: str = Field(pattern=r"^[0-9a-fA-F]{24}$")
    kind: Literal[
        "poi_viewed", "search_poi_selected", "audio_started", "audio_completed", "audio_ended"
    ]
    occurred_at: AwareDatetime
    playback_id: UUID | None = None
    language: Literal["vi", "en", "zh", "ja", "ko"] | None = None
    duration_seconds: float | None = Field(default=None, ge=0, le=86400, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_playback_fields(self) -> Self:
        if self.kind.startswith("audio_"):
            if self.playback_id is None or self.language is None:
                raise ValueError("Audio events require playback_id and language")
        elif self.playback_id is not None or self.language is not None:
            raise ValueError("Only audio events can include playback_id and language")
        if (self.kind in TERMINAL_EVENTS) != (self.duration_seconds is not None):
            raise ValueError("Only terminal audio events require duration_seconds")
        return self


class AnalyticsBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consent_status: Literal["granted"]
    events: list[AnalyticsEvent] = Field(min_length=1, max_length=50)
