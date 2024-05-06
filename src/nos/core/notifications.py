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
"""The content of all notification and confirmation emails."""

import logging
from typing import NamedTuple

log = logging.getLogger(__name__)

__all__ = [
    "Notification",
    "ACCESS_REQUEST_CREATED_TO_USER",
    "ACCESS_REQUEST_CREATED_TO_DS",
    "ACCESS_REQUEST_ALLOWED_TO_USER",
    "ACCESS_REQUEST_ALLOWED_TO_DS",
    "ACCESS_REQUEST_DENIED_TO_USER",
    "ACCESS_REQUEST_DENIED_TO_DS",
    "FILE_REGISTERED_TO_DS",
    "ALL_IVAS_INVALIDATED_TO_USER",
    "IVA_CODE_REQUESTED_TO_USER",
    "IVA_CODE_REQUESTED_TO_DS",
    "IVA_CODE_TRANSMITTED_TO_USER",
    "IVA_CODE_SUBMITTED_TO_DS",
    "IVA_UNVERIFIED_TO_DS",
]


class NotificationError(RuntimeError):
    """Raised for notification-related errors."""


class NotificationInterpolationError(NotificationError):
    """Raised when notification interpolation fails."""

    def __init__(self, interp_args: dict) -> None:
        message = f"Unable to format notification text with kwargs {interp_args}"
        super().__init__(message)


class Notification(NamedTuple):
    """A notification with a subject and a body text."""

    subject: str
    text: str

    def formatted(self, **kwargs) -> "Notification":
        """Perform string interpolation on the `text` attribute.

        Returns a new Notification object with the subject and interpolated
        text of the original.

        Raises a NotificationInterpolationError if the required template keys are not
        provided.
        """
        try:
            return Notification(self.subject, self.text.format(**kwargs))
        except KeyError as err:
            interpolation_error = NotificationInterpolationError(kwargs)
            log.error(interpolation_error)
            raise interpolation_error from err


ACCESS_REQUEST_CREATED_TO_USER = Notification(
    "Your data download access request has been registered",
    """
Your request to download the dataset {dataset_id} has been registered.

You should be contacted by one of our data stewards in the next three workdays.
""",
)

ACCESS_REQUEST_CREATED_TO_DS = Notification(
    "A data download access request has been created",
    """
{full_user_name} requested to download the dataset {dataset_id}.

The specified contact email address is: {email}
""",
)

ACCESS_REQUEST_ALLOWED_TO_USER = Notification(
    "Your data download access request has been accepted",
    """
We are glad to inform you that your request to download the dataset
{dataset_id} has been accepted.

You can now start downloading the dataset as explained in the GHGA Data Portal.
""",
)

ACCESS_REQUEST_ALLOWED_TO_DS = Notification(
    "Data download access has been allowed",
    """
The request by {full_user_name} to download the dataset
{dataset_id} has now been registered as allowed
and the access has been granted.
""",
)

ACCESS_REQUEST_DENIED_TO_USER = Notification(
    "Your data download access request has been rejected",
    """
Unfortunately, your request to download the dataset
{dataset_id} has been rejected.

Please contact our help desk for information about this decision.
""",
)

ACCESS_REQUEST_DENIED_TO_DS = Notification(
    "Data download access has been rejected",
    """
The request by {full_user_name} to download the dataset
{dataset_id} has now been registered as rejected
and the access has not been granted.
""",
)

FILE_REGISTERED_TO_DS = Notification(
    "File upload completed",
    "The file {file_id} has been successfully uploaded.",
)

ALL_IVAS_INVALIDATED_TO_USER = Notification(
    "IVA Invalidation",
    "All of your IVAs have been successfully invalidated.",
)

IVA_CODE_REQUESTED_TO_USER = Notification(
    "IVA Request Received",
    """
Your request for an IVA verification code has been received.

A Data Steward will review your request soon.
""",
)

IVA_CODE_REQUESTED_TO_DS = Notification(
    "IVA Request Received",
    """
{full_user_name} has requested an IVA verification code.

The specified contact email address is: {email}.
""",
)

IVA_CODE_TRANSMITTED_TO_USER = Notification(
    "IVA Verification Code Transmitted",
    """
A Data Steward has transmitted a verification code to the address specified by
your IVA. Please check for the IVA verification code and submit it on the GHGA
Data Portal.
""",
)

IVA_CODE_SUBMITTED_TO_DS = Notification(
    "IVA Verification Code Submitted",
    """
{full_user_name} has submitted an IVA verification code for review.

The specified contact email address is: {email}.
""",
)

IVA_UNVERIFIED_TO_DS = Notification(
    "IVA Unverified",
    """
The '{type}' IVA of {full_user_name} has been marked as unverified, due to too
many failed verification attempts.

The specified contact email address is: {email}.
""",
)
