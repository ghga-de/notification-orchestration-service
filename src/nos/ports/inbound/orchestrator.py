# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
#

"""Contains the definition of the Orchestrator class"""

from abc import ABC, abstractmethod


class OrchestratorPort(ABC):
    """A class that creates notification events from incoming event data."""

    class UserMissingError(RuntimeError):
        """Raised when a user is not found in the database.

        The notification title is included to aid in debugging.
        """

        def __init__(self, *, user_id: str, notification_name: str) -> None:
            message = (
                f"Unable to publish '{notification_name}' notification as user ID"
                + " '{user_id}' was not found in the database."
            )
            super().__init__(message)

    @abstractmethod
    async def process_access_request_created(self, *, user_id: str, dataset_id: str):
        """Processes an Access Request Created event.

        One notification is sent to the data requester to confirm that their request
        was created.

        Another notification is sent to the data steward to inform them of the request.
        """

    @abstractmethod
    async def process_access_request_allowed(self, *, user_id: str, dataset_id: str):
        """Process an Access Request Allowed event.

        One notification is sent to the data requester to inform them that the request
        has been approved/allowed.

        Another notification is sent to the data steward confirming that the request
        was allowed.
        """

    @abstractmethod
    async def process_access_request_denied(self, *, user_id: str, dataset_id: str):
        """Process an Access Request Denied event.

        One notification is sent to the data requester telling them that the request
        was denied.

        Another confirmation notification is sent to the data steward.
        """
