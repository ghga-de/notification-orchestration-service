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

"""DAO translator constructor"""

from ghga_event_schemas import pydantic_ as event_schemas
from hexkit.protocols.dao import DaoFactoryProtocol

from nos.models import EventId
from nos.ports.outbound.dao import AccessRequestDaoPort, EventIdDaoPort, UserDaoPort


async def get_user_dao(*, dao_factory: DaoFactoryProtocol) -> UserDaoPort:
    """Construct a UserDaoPort from the provided dao_factory"""
    return await dao_factory.get_dao(
        name="users",
        dto_model=event_schemas.User,
        id_field="user_id",
    )


async def get_access_request_dao(
    *, dao_factory: DaoFactoryProtocol
) -> AccessRequestDaoPort:
    """Construct a AccessRequestDaoPort from the provided dao_factory"""
    return await dao_factory.get_dao(
        name="accessRequests",
        dto_model=event_schemas.AccessRequestDetails,
        id_field="id",
    )


async def get_event_id_dao(*, dao_factory: DaoFactoryProtocol) -> EventIdDaoPort:
    """Construct an EventIdDaoPort from the provided dao_factory"""
    return await dao_factory.get_dao(
        name="nosEventIds",
        dto_model=EventId,
        id_field="event_id",
    )
