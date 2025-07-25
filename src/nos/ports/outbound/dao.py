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

"""DAO interface for accessing the database."""

from ghga_event_schemas import pydantic_ as event_schemas
from hexkit.protocols.dao import Dao, ResourceNotFoundError

from nos.models import EventId

__all__ = [
    "AccessRequestDaoPort",
    "EventIdDaoPort",
    "ResourceNotFoundError",
    "UserDaoPort",
]

# ports described by type aliases:
AccessRequestDaoPort = Dao[event_schemas.AccessRequestDetails]
UserDaoPort = Dao[event_schemas.User]
EventIdDaoPort = Dao[EventId]
