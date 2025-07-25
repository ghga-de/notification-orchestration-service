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

"""Test to make sure that the DLQ is correctly set up for this service."""

import pytest
from ghga_event_schemas import pydantic_ as event_schemas

from tests.conftest import TEST_USER
from tests.fixtures.joint import JointFixture

pytestmark = pytest.mark.asyncio()


async def test_event_subscriber_dlq(joint_fixture: JointFixture):
    """Verify that if we get an error when consuming an event, it gets published to the DLQ."""
    config = joint_fixture.config
    assert config.kafka_enable_dlq

    # Publish an event with a bogus payload to a topic/type this service expects
    await joint_fixture.kafka.publish_event(
        payload={"some_key": "some_value"},
        type_="upserted",
        topic=config.access_request_topic,
        key="test",
    )
    async with joint_fixture.kafka.record_events(
        in_topic=config.kafka_dlq_topic
    ) as recorder:
        await joint_fixture.event_subscriber.run(forever=False)
    assert recorder.recorded_events
    assert len(recorder.recorded_events) == 1
    event = recorder.recorded_events[0]
    assert event.key == "test"
    assert event.payload == {"some_key": "some_value"}


async def test_combined_subscriber_types(joint_fixture: JointFixture):
    """Test if running normal and outbox subscribers simultaneously breaks the
    retry topic functionality.

    The purpose is to make sure this service is set up to correctly consume both
    kinds of events simultaneously, e.g. by using the ComboTranslator class.
    """
    config = joint_fixture.config
    assert config.kafka_enable_dlq

    # Publish a normal event with a valid payload to the retry topic
    payload = event_schemas.UserID(user_id=TEST_USER.user_id).model_dump()
    await joint_fixture.kafka.publish_event(
        payload=payload,
        type_=config.second_factor_recreated_type,
        topic=f"retry-{config.service_name}",
        key="test",
        headers={"original_topic": config.access_request_topic},
    )

    # Publish an outbox event with a valid payload to the retry topic
    await joint_fixture.kafka.publish_event(
        payload=TEST_USER.model_dump(),
        type_="upserted",
        topic=f"retry-{config.service_name}",
        key=str(TEST_USER.user_id),
        headers={"original_topic": config.user_topic},
    )

    # Run the event subscriber so it receives the events
    await joint_fixture.event_subscriber.run(forever=False)
    await joint_fixture.event_subscriber.run(forever=False)
