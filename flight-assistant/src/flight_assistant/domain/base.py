"""Shared base types for the domain tool contract.

Every capability returns a subclass of :class:`ToolResult`, which guarantees a
``disclaimer`` field is always present. Capabilities may override the default
disclaimer text — e.g. a future pricing capability would carry a different
caveat than historical route connectivity.
"""

from __future__ import annotations

from pydantic import BaseModel

# Default caveat for everything derived from the OpenFlights datasets.
OPENFLIGHTS_DISCLAIMER = (
    "Based on historical OpenFlights connectivity data. This is NOT a live "
    "schedule and does not reflect current availability, timings, pricing, or "
    "bookings. Verify with an airline or booking provider before travel."
)


class ToolResult(BaseModel):
    """Base class for all tool outputs.

    Carries a mandatory data-limitation disclaimer so the assistant can never
    present results without the appropriate caveat.
    """

    disclaimer: str = OPENFLIGHTS_DISCLAIMER
