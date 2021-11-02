import time

import uprate as up

class RateLimited(up.RateLimitError):
    def __init__(self, retry_after: float, *args):
        super(up.RateLimitError, self).__init__(*args)
        self.retry_after = retry_after

class DynamicRateLimit:
    def __init__(self, reset_at: int, uses: int, remaining: int = None):
        self.uses = uses
        self.rem = remaining if remaining is not None else uses
        self.reset_at = reset_at

    def update(self, reset_at: int, remaining: int = None):
        self.rem = remaining if remaining is not None else self.uses
        self.reset_at = reset_at

    async def acquire(self):
        self.rem -= 1

        if self.rem < 0:
            delta = self.reset_at - time.time()

            if delta <= 0:
                self.reset()
                self.rem -= 1
                return
            else:
                raise RateLimited(delta)
        return

    def reset(self):
        self.rem = self.uses

class DynamicRateLimitGroup:
    def __init__(self, *limits: DynamicRateLimit):
        self.limits = set(limits)

    async def acquire(self,):
        ...

class RateLimitHandler:
    ...