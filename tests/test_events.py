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
"""Tests for event sub/pub"""

from typing import Any

import pytest
from ghga_event_schemas.pydantic_ import Notification
from hexkit.providers.akafka.testutils import ExpectedEvent

from nos.adapters.inbound.event_sub import AccessRequestDetails
from nos.core import notifications
from tests.conftest import TEST_USER
from tests.fixtures.joint import JointFixture

DATASET_ID = "dataset1"


def access_request_payload(user_id: str) -> dict[str, Any]:
    """Succinctly create the payload for an access request event."""
    return AccessRequestDetails(user_id=user_id, dataset_id=DATASET_ID).model_dump()


@pytest.mark.parametrize(
    "user_notification_content, user_kwargs, ds_notification_content, ds_kwargs, event_type",
    [
        (  # Test access request created
            notifications.REQUEST_CREATED_TO_USER,
            {"dataset_id": DATASET_ID},
            notifications.REQUEST_CREATED_TO_DS,
            {
                "full_user_name": TEST_USER.name,
                "email": TEST_USER.email,
                "dataset_id": DATASET_ID,
            },
            "created",
        ),
        (  # Test access request allowed
            notifications.REQUEST_ALLOWED_TO_USER,
            {"dataset_id": DATASET_ID},
            notifications.REQUEST_ALLOWED_TO_DS,
            {
                "full_user_name": TEST_USER.name,
                "dataset_id": DATASET_ID,
            },
            "allowed",
        ),
        (  # Test access request denied
            notifications.REQUEST_DENIED_TO_USER,
            {"dataset_id": DATASET_ID},
            notifications.REQUEST_DENIED_TO_DS,
            {
                "full_user_name": TEST_USER.name,
                "dataset_id": DATASET_ID,
            },
            "denied",
        ),
    ],
)
@pytest.mark.asyncio(scope="module")
async def test_access_request(
    joint_fixture: JointFixture,
    user_notification_content: notifications.Notification,
    user_kwargs: dict[str, Any],
    ds_notification_content: notifications.Notification,
    ds_kwargs: dict[str, Any],
    event_type: str,
):
    """Test that the access request created event is processed correctly.

    Test will also check idempotence.
    """
    assert joint_fixture.test_user is not None

    event_type_to_use = ""
    if event_type == "created":
        event_type_to_use = joint_fixture.config.access_request_created_type
    elif event_type == "allowed":
        event_type_to_use = joint_fixture.config.access_request_allowed_type
    elif event_type == "denied":
        event_type_to_use = joint_fixture.config.access_request_denied_type

    assert event_type_to_use

    user_notification = Notification(
        recipient_email=joint_fixture.test_user.email,
        subject=user_notification_content.subject,
        recipient_name=joint_fixture.test_user.name,
        plaintext_body=user_notification_content.text.format(**user_kwargs),
    )

    data_steward_notification = Notification(
        recipient_email=joint_fixture.config.central_data_steward_email,
        subject=ds_notification_content.subject,
        recipient_name="Data Steward",
        plaintext_body=ds_notification_content.text.format(**ds_kwargs),
    )

    expected = [
        ExpectedEvent(
            payload=user_notification.model_dump(),
            type_=joint_fixture.config.notification_event_type,
        ),
        ExpectedEvent(
            payload=data_steward_notification.model_dump(),
            type_=joint_fixture.config.notification_event_type,
        ),
    ]

    # Create the kafka event that would be published by the access request service
    await joint_fixture.kafka.publish_event(
        payload=access_request_payload(joint_fixture.test_user.id),
        type_=event_type_to_use,
        topic=joint_fixture.config.access_request_events_topic,
    )

    # Consume the event, triggering the generation of two notifications
    async with joint_fixture.kafka.expect_events(
        events=expected,
        in_topic=joint_fixture.config.notification_event_topic,
    ):
        await joint_fixture.event_subscriber.run(forever=False)

    # Publish and consume event again to check idempotence
    await joint_fixture.kafka.publish_event(
        payload=access_request_payload(joint_fixture.test_user.id),
        type_=event_type_to_use,
        topic=joint_fixture.config.access_request_events_topic,
    )

    async with joint_fixture.kafka.expect_events(
        events=expected,
        in_topic=joint_fixture.config.notification_event_topic,
    ):
        await joint_fixture.event_subscriber.run(forever=False)


@pytest.mark.asyncio(scope="module")
async def test_missing_user_id(joint_fixture: JointFixture):
    """Test for error handling in case of invalid user id."""
    payload = access_request_payload("bogus_user_id")
    for event_type in [
        joint_fixture.config.access_request_created_type,
        joint_fixture.config.access_request_allowed_type,
        joint_fixture.config.access_request_denied_type,
    ]:
        await joint_fixture.kafka.publish_event(
            payload=payload,
            type_=event_type,
            topic=joint_fixture.config.access_request_events_topic,
        )

        with pytest.raises(joint_fixture.orchestrator.UserMissingError):
            await joint_fixture.event_subscriber.run(forever=False)
