# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Verify functionality related to the consumption of KafkaOutbox events."""

import pytest
from hexkit.protocols.dao import ResourceNotFoundError

from tests.fixtures.joint import JointFixture

CHANGE_EVENT_TYPE = "upserted"
DELETE_EVENT_TYPE = "deleted"


@pytest.mark.parametrize("user_id", ["test_id", "does_not_exist"])
@pytest.mark.asyncio
async def test_user_data_deletion(joint_fixture: JointFixture, user_id: str):
    """Ensure that the `delete` function works correctly.

    The event should trigger the deletion of the user data via the orchestrator.
    The user_id 'test_id' should be found and deleted.
    The user_id 'does_not_exist' should not be found but also not raise an error.
    """
    # 1. Prepare the test by setting up the core and the event subscriber.
    if user_id == "test_id":
        assert await joint_fixture.user_dao.get_by_id(user_id)

    # 2. Publish the event.
    await joint_fixture.kafka.publish_event(
        payload={},
        type_=DELETE_EVENT_TYPE,
        topic=joint_fixture.config.user_data_event_topic,
        key=user_id,
    )

    # 3. Run the outbox subscriber.
    await joint_fixture.outbox_subscriber.run(forever=False)

    # 4. Check that the user data is not found.
    with pytest.raises(ResourceNotFoundError):
        await joint_fixture.user_dao.get_by_id(user_id)
