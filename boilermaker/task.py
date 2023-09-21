import datetime
import typing

from pydantic import BaseModel
from . import retries


class Task(BaseModel):
    # Whether we should dead-letter a failing message
    should_dead_letter: bool = True
    # At-most-once vs at-least-once (default)
    acks_late: bool = True
    # function name for this task
    function_name: str
    # Records how many attempts for this task (if previous)
    attempts: retries.RetryAttempts
    # For retries, we want a policy to govern how we retry this task
    policy: retries.RetryPolicy
    # Represents actual arguments: must be jsonable!
    payload: typing.Dict[str, typing.Any]
    # Eventhub event metadata below
    # opentelemetry parent trace id is included here
    diagnostic_id: typing.Optional[str]

    @classmethod
    def default(cls, function_name: str, **kwargs):
        attempts = retries.RetryAttempts(
            attempts=0, last_retry=datetime.datetime.now(datetime.timezone.utc)
        )
        return cls(
            attempts=attempts,
            function_name=function_name,
            policy=retries.RetryPolicy.default(),
            payload={},
            diagnostic_id=None,
            **kwargs,
        )

    @property
    def acks_early(self):
        return not self.acks_late

    @property
    def can_retry(self):
        return self.attempts.attempts <= self.policy.max_tries

    def get_next_delay(self):
        return self.policy.get_delay_interval(self.attempts.attempts)

    def record_attempt(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        return self.attempts.inc(now)
