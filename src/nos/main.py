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
#
"""Top-level functions for the service"""

import asyncio
import logging

from hexkit.log import configure_logging

from nos.config import Config
from nos.inject import prepare_event_subscriber, prepare_outbox_subscriber

log = logging.getLogger(__name__)


async def consume_events(run_forever: bool = True):
    """Start consuming events with kafka"""
    config = Config()  # type: ignore

    configure_logging(config=config)
    async with (
        prepare_event_subscriber(config=config) as event_subscriber,
        prepare_outbox_subscriber(config=config) as outbox_subscriber,
    ):
        await asyncio.gather(
            event_subscriber.run(forever=run_forever),
            outbox_subscriber.run(forever=run_forever),
        )
