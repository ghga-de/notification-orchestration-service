# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utils for Fixture handling."""

from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from ghga_event_schemas import pydantic_ as event_schemas
from ghga_service_commons.utils.utc_dates import now_as_utc
from pydantic import UUID4

BASE_DIR = Path(__file__).parent.resolve()

STATIC_ACCESS_REQUEST_ID = UUID("5a927649-087f-4c4c-90f7-2ee01fa347a7")
DATASET_ID = "dataset1"


def access_request_payload(user_id: UUID4, status: str = "pending") -> dict[str, Any]:
    """Succinctly create the payload for an access request event."""
    start = now_as_utc()
    end = start + timedelta(days=180)
    return event_schemas.AccessRequestDetails(
        id=STATIC_ACCESS_REQUEST_ID,
        user_id=user_id,
        dataset_id=DATASET_ID,
        dataset_title="A Great Dataset",
        dataset_description="Some Dataset",
        dac_alias="Some DAC",
        dac_email="dac@some.org",
        status=status,
        request_text="Please grant me access to this data.",
        note_to_requester="Thank you",
        access_starts=start,
        access_ends=end,
        ticket_id="123456",
    ).model_dump()
