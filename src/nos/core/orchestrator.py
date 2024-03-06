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

"""Contains the implementation of the Orchestrator class"""

import logging

from nos.core import notifications
from nos.core.models import User
from nos.ports.inbound.orchestrator import OrchestratorPort
from nos.ports.outbound.dao import ResourceNotFoundError, UserDaoPort
from nos.ports.outbound.notification_emitter import NotificationEmitterPort

log = logging.getLogger(__name__)


class Orchestrator(OrchestratorPort):
    """The Orchestrator class"""

    def __init__(
        self,
        *,
        config,
        user_dao: UserDaoPort,
        notification_emitter: NotificationEmitterPort,
    ):
        self._config = config
        self._user_dao = user_dao
        self._notification_emitter = notification_emitter

    async def _retrieve_user_details(self, user_id) -> User:
        """Retrieve user details"""
        try:
            return await self._user_dao.get_by_id(user_id)
        except ResourceNotFoundError as err:
            log.error(f"User with id {user_id} not found", extra={"error_message": err})
            raise

    async def process_access_request_created(self, *, user_id: str, dataset_id: str):
        """Processes an Access Request Created event.

        One notification is sent to the data requester to confirm that their request
        was created.

        Another notification is sent to the data steward to inform them of the request.
        """
        try:
            user: User = await self._retrieve_user_details(user_id)
        except ResourceNotFoundError as err:
            error = self.UserMissingError(
                user_id=user_id, notification_name="Access Request Created"
            )
            log.error(error, extra={"user_id": user_id, "dataset_id": dataset_id})
            raise error from err

        # Send a confirmation email notification to the Data Requester
        log.info("Sending Access Request Created notification to data requester")
        await self._notification_emitter.notify(
            email=user.email,
            full_name=user.name,
            subject=notifications.REQUEST_CREATED_TO_USER.subject,
            text=notifications.REQUEST_CREATED_TO_USER.text.format(
                dataset_id=dataset_id
            ),
        )

        # Send a notification to the data steward
        log.info("Sending Access Request Created notification to data steward")
        await self._notification_emitter.notify(
            email=self._config.central_data_steward_email,
            full_name="Data Steward",
            subject=notifications.REQUEST_CREATED_TO_DS.subject,
            text=notifications.REQUEST_CREATED_TO_DS.text.format(
                full_user_name=user.name, email=user.email, dataset_id=dataset_id
            ),
        )

    async def process_access_request_allowed(self, *, user_id: str, dataset_id: str):
        """Process an Access Request Allowed event.

        One notification is sent to the data requester to inform them that the request
        has been approved/allowed.

        Another notification is sent to the data steward confirming that the request
        was allowed.
        """
        try:
            user: User = await self._retrieve_user_details(user_id)
        except ResourceNotFoundError as err:
            error = self.UserMissingError(
                user_id=user_id, notification_name="Access Request Allowed"
            )
            log.error(error, extra={"user_id": user_id, "dataset_id": dataset_id})
            raise error from err

        # Send a notification to the data requester
        log.info("Sending Access Request Allowed notification to data requester")
        await self._notification_emitter.notify(
            email=user.email,
            full_name=user.name,
            subject=notifications.REQUEST_ALLOWED_TO_USER.subject,
            text=notifications.REQUEST_ALLOWED_TO_USER.text.format(
                dataset_id=dataset_id
            ),
        )

        # Send a confirmation email to the data steward
        log.info("Sending Access Request Allowed notification to data steward")
        await self._notification_emitter.notify(
            email=self._config.central_data_steward_email,
            full_name="Data Steward",
            subject=notifications.REQUEST_ALLOWED_TO_DS.subject,
            text=notifications.REQUEST_ALLOWED_TO_DS.text.format(
                full_user_name=user.name, dataset_id=dataset_id
            ),
        )

    async def process_access_request_denied(self, *, user_id: str, dataset_id: str):
        """Process an Access Request Denied event.

        One notification is sent to the data requester telling them that the request
        was denied.

        Another confirmation notification is sent to the data steward.
        """
        try:
            user: User = await self._retrieve_user_details(user_id)
        except ResourceNotFoundError as err:
            error = self.UserMissingError(
                user_id=user_id, notification_name="Access Request Denied"
            )
            log.error(error, extra={"user_id": user_id, "dataset_id": dataset_id})
            raise error from err

        # Send a notification to the data requester
        log.info("Sending Access Request Denied notification to data requester")
        await self._notification_emitter.notify(
            email=user.email,
            full_name=user.name,
            subject=notifications.REQUEST_DENIED_TO_USER.subject,
            text=notifications.REQUEST_DENIED_TO_USER.text.format(
                dataset_id=dataset_id
            ),
        )

        # Send a confirmation email to the data steward
        log.info("Sending Access Request Denied notification to data steward")
        await self._notification_emitter.notify(
            email=self._config.central_data_steward_email,
            full_name="Data Steward",
            subject=notifications.REQUEST_DENIED_TO_DS.subject,
            text=notifications.REQUEST_DENIED_TO_DS.text.format(
                full_user_name=user.name, dataset_id=dataset_id
            ),
        )
