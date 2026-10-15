"""A request-time, fail-closed robots gate. Site/content-use permission remains separate."""
from urllib.parse import urlsplit
from .discovery_transport import Purpose, USER_AGENT


class RobotsDenied(ValueError):
    def __init__(self, url, reason):
        super().__init__(reason)
        self.url, self.reason = url, reason


class RobotsPolicy:
    """Use only rules already loaded for this exact host; unknown hosts never inherit rules."""
    def __init__(self, rules, decisions=None):
        self.rules = rules
        self.decisions = decisions if decisions is not None else []

    def __call__(self, url, purpose):
        if purpose is Purpose.ROBOTS:
            return  # bootstrapping robots is scope/budget guarded by the transport itself
        rule = self.rules.get(urlsplit(url).hostname)
        reason = 'robots_unavailable' if rule is None else None
        if rule is not None and not rule.can_fetch(USER_AGENT, url):
            reason = 'robots_disallow'
        self.decisions.append({'url': url, 'purpose': purpose.value, 'allowed': reason is None, 'reason': reason})
        if reason:
            raise RobotsDenied(url, reason)
