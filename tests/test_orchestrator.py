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
#
"""Tests for event sub/pub"""

from typing import Any
from uuid import uuid4

import pytest
from ghga_event_schemas import pydantic_ as event_schemas
from hexkit.providers.akafka.testutils import ExpectedEvent
from logot import Logot, logged
from pydantic import UUID4

from nos.core import notifications
from tests.conftest import TEST_USER
from tests.fixtures.joint import JointFixture
from tests.fixtures.utils import DATASET_ID, make_access_request

pytestmark = pytest.mark.asyncio()


def iva_state_payload(user_id: UUID4, state: event_schemas.IvaState) -> dict[str, Any]:
    """Succinctly create the payload for an IVA state change event."""
    return event_schemas.UserIvaState(
        user_id=user_id,
        state=state,
        value=None,
        type=None,
    ).model_dump()


@pytest.mark.parametrize(
    "user_notification_content, user_kwargs, ds_notification_content, ds_kwargs, status",
    [
        (  # Test access request created
            notifications.ACCESS_REQUEST_CREATED_TO_USER,
            {"dataset_id": DATASET_ID},
            notifications.ACCESS_REQUEST_CREATED_TO_DS,
            {
                "full_user_name": TEST_USER.name,
                "email": TEST_USER.email,
                "dataset_id": DATASET_ID,
                "dataset_title": "A Great Dataset",
                "dac_alias": "Some DAC",
                "dac_email": "dac@some.org",
                "request_text": "Please grant me access to this data.",
            },
            "pending",
        ),
        (  # Test access request allowed
            notifications.ACCESS_REQUEST_ALLOWED_TO_USER,
            {
                "dataset_id": DATASET_ID,
                "note_to_requester": "\nThe Data Steward has also included the following note:\nThank you",
            },
            notifications.ACCESS_REQUEST_ALLOWED_TO_DS,
            {
                "full_user_name": TEST_USER.name,
                "dataset_id": DATASET_ID,
                "ticket_id": "#123456",
            },
            "allowed",
        ),
        (  # Test access request denied
            notifications.ACCESS_REQUEST_DENIED_TO_USER,
            {
                "dataset_id": DATASET_ID,
                "note_to_requester": "\nThe Data Steward has also included the following note:\nThank you",
            },
            notifications.ACCESS_REQUEST_DENIED_TO_DS,
            {
                "full_user_name": TEST_USER.name,
                "dataset_id": DATASET_ID,
                "ticket_id": "#123456",
            },
            "denied",
        ),
    ],
    ids=["created", "allowed", "denied"],
)
async def test_access_request(
    joint_fixture: JointFixture,
    user_notification_content: notifications.Notification,
    user_kwargs: dict[str, Any],
    ds_notification_content: notifications.Notification,
    ds_kwargs: dict[str, Any],
    status: str,
):
    """Test that the access request created event is processed correctly.

    Test will also check idempotence.
    """
    test_user = await joint_fixture.user_dao.get_by_id(TEST_USER.user_id)

    user_notification = event_schemas.Notification(
        recipient_email=test_user.email,
        subject=user_notification_content.subject.format(**user_kwargs),
        recipient_name=test_user.name,
        plaintext_body=user_notification_content.text.format(**user_kwargs),
    )

    data_steward_notification = event_schemas.Notification(
        recipient_email=joint_fixture.config.central_data_stewardship_email,
        subject=ds_notification_content.subject.format(**ds_kwargs),
        recipient_name="Data Steward",
        plaintext_body=ds_notification_content.text.format(**ds_kwargs),
    )

    expected = [
        ExpectedEvent(
            payload=user_notification.model_dump(),
            type_=joint_fixture.config.notification_type,
            key=test_user.email,
        ),
        ExpectedEvent(
            payload=data_steward_notification.model_dump(),
            type_=joint_fixture.config.notification_type,
            key=joint_fixture.config.central_data_stewardship_email,
        ),
    ]

    # Create the kafka event that would be published by the access request service
    payload = make_access_request(test_user.user_id, status).model_dump()
    await joint_fixture.kafka.publish_event(
        payload=payload,
        type_="upserted",
        topic=joint_fixture.config.access_request_topic,
    )

    # Consume the event, triggering the generation of two notifications
    async with joint_fixture.kafka.expect_events(
        events=expected,
        in_topic=joint_fixture.config.notification_topic,
    ):
        await joint_fixture.event_subscriber.run(forever=False)

    # Publish and consume event again to check idempotence
    await joint_fixture.kafka.publish_event(
        payload=payload,
        type_="upserted",
        topic=joint_fixture.config.access_request_topic,
    )

    async with joint_fixture.kafka.record_events(
        in_topic=joint_fixture.config.notification_topic
    ) as recorder:
        await joint_fixture.event_subscriber.run(forever=False)
    assert not recorder.recorded_events


@pytest.mark.parametrize(
    "status, ds_notification",
    [
        ("allowed", notifications.ACCESS_REQUEST_ALLOWED_TO_DS),
        ("denied", notifications.ACCESS_REQUEST_DENIED_TO_DS),
    ],
    ids=["allowed", "denied"],
)
async def test_access_request_no_ticket_id(
    joint_fixture: JointFixture,
    status: str,
    ds_notification: notifications.Notification,
):
    """Test that the GHGA Ticket ID is set to "Missing" in the data steward notification
    when the access request is published without a ticket ID. Only affects the
    allowed/denied notifications, not the created notification.
    """
    # Create an access request payload and clear out the ticket
    access_request = make_access_request(TEST_USER.user_id, status=status).model_dump()
    access_request["ticket_id"] = ""

    # Publish the access request event
    await joint_fixture.kafka.publish_event(
        payload=access_request,
        type_="upserted",
        topic=joint_fixture.config.access_request_topic,
    )

    # Both allowed/denied notifications use the same kwargs for the data steward
    ds_kwargs = {
        "full_user_name": TEST_USER.name,
        "dataset_id": DATASET_ID,
        "ticket_id": "Missing",
    }

    # Define the event that should be published by the NOS when the trigger is consumed
    expected_notification = event_schemas.Notification(
        recipient_email=joint_fixture.config.central_data_stewardship_email,
        subject=ds_notification.subject.format(**ds_kwargs),
        recipient_name="Data Steward",
        plaintext_body=ds_notification.text.format(**ds_kwargs),
    )

    # Consume the message and check the recorded events to check the subject line
    # of the published notification
    async with joint_fixture.kafka.record_events(
        in_topic=joint_fixture.config.notification_topic
    ) as recorder:
        await joint_fixture.event_subscriber.run(forever=False)
    assert recorder.recorded_events
    assert len(recorder.recorded_events) == 2  # One for the user, one for the ds
    for event in recorder.recorded_events:
        if event.key == joint_fixture.config.central_data_stewardship_email:
            assert event.payload == expected_notification.model_dump()


async def test_missing_user_id_access_requests(
    joint_fixture: JointFixture, logot: Logot
):
    """Test for error handling in case of invalid user id, specifically for the access
    request events.
    """
    payload = make_access_request(uuid4()).model_dump()
    await joint_fixture.kafka.publish_event(
        payload=payload,
        type_="upserted",
        topic=joint_fixture.config.access_request_topic,
    )

    async with joint_fixture.kafka.record_events(
        in_topic=joint_fixture.config.kafka_dlq_topic, capture_headers=True
    ) as recorder:
        await joint_fixture.event_subscriber.run(forever=False)
    assert recorder.recorded_events
    assert recorder.recorded_events[0].headers is not None
    assert (
        recorder.recorded_events[0].headers.get("exc_class", "") == "MissingUserError"
    )
    logot.assert_logged(
        logged.error(
            "Unable to publish 'Access Request Created' notification as"
            + f" user ID {payload['user_id']!r} was not found in the database."
        )
    )


async def test_missing_user_id_iva_state_changes(
    joint_fixture: JointFixture, logot: Logot
):
    """Test for error handling in case of missing user id, specifically for the IVA
    state change events.
    """
    payloads = (
        iva_state_payload(uuid4(), event_schemas.IvaState.CODE_REQUESTED),
        iva_state_payload(uuid4(), event_schemas.IvaState.CODE_TRANSMITTED),
        iva_state_payload(uuid4(), event_schemas.IvaState.UNVERIFIED),
    )

    event_types = (
        joint_fixture.config.iva_state_changed_type,  # requested
        joint_fixture.config.iva_state_changed_type,  # transmitted
        joint_fixture.config.iva_state_changed_type,  # unverified
    )
    notification_names = (
        "IVA Code Requested",
        "IVA Code Transmitted",
        "IVA Unverified",
    )
    for payload, event_type, notification_name in zip(
        payloads, event_types, notification_names, strict=True
    ):
        await joint_fixture.kafka.publish_event(
            payload=payload,
            type_=event_type,
            topic=joint_fixture.config.iva_state_changed_topic,
        )

        async with joint_fixture.kafka.record_events(
            in_topic=joint_fixture.config.kafka_dlq_topic, capture_headers=True
        ) as recorder:
            await joint_fixture.event_subscriber.run(forever=False)
        assert recorder.recorded_events
        assert recorder.recorded_events[0].headers is not None
        assert (
            recorder.recorded_events[0].headers.get("exc_class", "")
            == "MissingUserError"
        )
        logot.assert_logged(
            logged.error(
                f"Unable to publish '{notification_name}' notification as user"
                + f" ID {payload['user_id']!r} was not found in the database."
            )
        )


@pytest.mark.parametrize(
    "iva_state,expected_user_notification,expected_ds_notification",
    [
        (
            event_schemas.IvaState.CODE_REQUESTED,
            notifications.IVA_CODE_REQUESTED_TO_USER,
            notifications.IVA_CODE_REQUESTED_TO_DS,
        ),
        (
            event_schemas.IvaState.CODE_TRANSMITTED,
            notifications.IVA_CODE_TRANSMITTED_TO_USER,
            None,
        ),
        (
            event_schemas.IvaState.UNVERIFIED,
            notifications.IVA_UNVERIFIED_TO_USER,
            notifications.IVA_UNVERIFIED_TO_DS,
        ),
    ],
)
async def test_iva_state_change(
    joint_fixture: JointFixture,
    iva_state: event_schemas.IvaState,
    expected_user_notification: notifications.Notification | None,
    expected_ds_notification: notifications.Notification | None,
):
    """Test that the IVA state change events are translated into the proper notification.

    This does not check the wording or content of the notifications, only that the
    correct notifications are generated for each state change.
    """
    # Prepare triggering event (the IVA state change event).
    trigger_event = event_schemas.UserIvaState(
        user_id=TEST_USER.user_id,
        state=iva_state,
        value=None,
        type=event_schemas.IvaType.FAX,
    )

    # Publish the trigger event
    await joint_fixture.kafka.publish_event(
        payload=trigger_event.model_dump(),
        type_=joint_fixture.config.iva_state_changed_type,
        topic=joint_fixture.config.iva_state_changed_topic,
        key=str(TEST_USER.user_id),
    )

    # Build a notification payload for the user, if applicable
    user_notification = (
        event_schemas.Notification(
            recipient_email=TEST_USER.email,
            subject=expected_user_notification.subject,
            recipient_name=TEST_USER.name,
            plaintext_body=expected_user_notification.text.format(
                helpdesk_email=joint_fixture.config.helpdesk_email,
            ),
        )
        if expected_user_notification
        else None
    )

    # Build a notification payload for the data steward, if applicable
    data_steward_notification = (
        event_schemas.Notification(
            recipient_email=joint_fixture.config.central_data_stewardship_email,
            subject=expected_ds_notification.subject,
            recipient_name="Data Steward",
            plaintext_body=expected_ds_notification.text.format(
                full_user_name=TEST_USER.name,
                email=TEST_USER.email,
                type=trigger_event.type.value.lower(),
            ),
        )
        if expected_ds_notification
        else None
    )

    if (
        data_steward_notification
        and expected_ds_notification == notifications.IVA_UNVERIFIED_TO_DS
    ):
        assert data_steward_notification.plaintext_body.startswith("\nThe 'fax' IVA")

    # Combine the two notifications into a list of expected events
    expected_events = []
    for notification in [user_notification, data_steward_notification]:
        if notification:
            expected_events.append(
                ExpectedEvent(
                    payload=notification.model_dump(),
                    type_=joint_fixture.config.notification_type,
                )
            )

    # Consume the event and verify that the expected events are published
    async with joint_fixture.kafka.expect_events(
        events=expected_events,
        in_topic=joint_fixture.config.notification_topic,
    ):
        await joint_fixture.event_subscriber.run(forever=False)


async def test_all_ivas_reset(joint_fixture: JointFixture):
    """Test that the 'all IVA invalidated' events are translated into a notification."""
    # Prepare triggering event (the IVA state change event).
    trigger_event = event_schemas.UserIvaState(
        user_id=TEST_USER.user_id,
        state=event_schemas.IvaState.UNVERIFIED,
        value=None,
        type=None,
    )

    # Publish the trigger event
    await joint_fixture.kafka.publish_event(
        payload=trigger_event.model_dump(),
        type_=joint_fixture.config.iva_state_changed_type,
        topic=joint_fixture.config.iva_state_changed_topic,
        key=f"all-{TEST_USER.user_id}",
    )

    # Define the event that should be published by the NOS when the trigger is consumed
    helpdesk_email = joint_fixture.config.helpdesk_email
    expected_notification = event_schemas.Notification(
        recipient_email=TEST_USER.email,
        recipient_name=TEST_USER.name,
        subject="Contact Address Invalidation",
        plaintext_body=f"""
All of your registered contact addresses now need re-verification due to the establishment
of a new 2nd authentication factor.

If you have any questions, please contact the GHGA Helpdesk: {helpdesk_email}
""",
    )

    expected_event = ExpectedEvent(
        payload=expected_notification.model_dump(),
        type_=joint_fixture.config.notification_type,
    )

    # consume the event and verify that the expected event is published
    async with joint_fixture.kafka.expect_events(
        events=[expected_event],
        in_topic=joint_fixture.config.notification_topic,
    ):
        await joint_fixture.event_subscriber.run(forever=False)


async def test_second_factor_recreated_notification(joint_fixture: JointFixture):
    """Test that the second factor recreated event is translated into a notification."""
    # Prepare triggering event (the second factor recreated event).
    payload = event_schemas.UserID(user_id=TEST_USER.user_id)

    # Publish the trigger event
    await joint_fixture.kafka.publish_event(
        payload=payload.model_dump(),
        type_=joint_fixture.config.second_factor_recreated_type,
        topic=joint_fixture.config.auth_topic,
        key=str(TEST_USER.user_id),
    )

    # Define the event that should be published by the NOS when the trigger is consumed
    expected_notification_content = (
        notifications.SECOND_FACTOR_RECREATED_TO_USER.formatted(
            helpdesk_email=joint_fixture.config.helpdesk_email
        )
    )

    expected_notification = event_schemas.Notification(
        recipient_email=TEST_USER.email,
        recipient_name=TEST_USER.name,
        subject=expected_notification_content.subject,
        plaintext_body=expected_notification_content.text,
    )

    expected_event = ExpectedEvent(
        payload=expected_notification.model_dump(),
        type_=joint_fixture.config.notification_type,
    )

    # consume the event and verify that the expected event is published
    async with joint_fixture.kafka.expect_events(
        events=[expected_event],
        in_topic=joint_fixture.config.notification_topic,
    ):
        await joint_fixture.event_subscriber.run(forever=False)


async def test_iva_verified_event_sub(joint_fixture: JointFixture):
    """Test that the IVA verified event is quietly ignored. This is a regression test
    for having removed the notification.
    """
    # Prepare triggering event (the IVA state change event).
    iva_event = iva_state_payload(uuid4(), event_schemas.IvaState.VERIFIED)

    # Publish the trigger event
    await joint_fixture.kafka.publish_event(
        payload=iva_event,
        type_=joint_fixture.config.iva_state_changed_type,
        topic=joint_fixture.config.iva_state_changed_topic,
        key=str(TEST_USER.user_id),
    )

    async with joint_fixture.kafka.record_events(
        in_topic=joint_fixture.config.kafka_dlq_topic
    ) as recorder:
        # Run the event subscriber to process the event
        await joint_fixture.event_subscriber.run(forever=False)

    assert not recorder.recorded_events, "IVA Verified event would be sent to DLQ!"
