from dataclasses import dataclass, field
from datetime import datetime
from os import getenv
from typing import cast, Any, Dict, Sequence
import random

import requests

from . import Rule


class DoResolveRule(Rule):
    def value(self, market) -> bool:
        raise NotImplementedError()


@dataclass
class NegateRule(DoResolveRule):
    child: DoResolveRule

    def value(self, market) -> bool:
        return not self.child.value(market)


@dataclass
class EitherRule(DoResolveRule):
    rule1: DoResolveRule
    rule2: DoResolveRule

    def value(self, market) -> bool:
        return self.rule1.value(market) or self.rule2.value(market)


@dataclass
class BothRule(DoResolveRule):
    rule1: DoResolveRule
    rule2: DoResolveRule

    def value(self, market) -> bool:
        return self.rule1.value(market) and self.rule2.value(market)


@dataclass
class ResolveAtTime(DoResolveRule):
    resolve_at: datetime

    def value(self, market) -> bool:
        try:
            return datetime.utcnow() >= self.resolve_at
        except TypeError:
            return datetime.now() >= self.resolve_at


@dataclass
class ResolveWithPR(DoResolveRule):
    owner: str
    repo: str
    number: int

# curl \
#   -H "Accept: application/vnd.github+json" \
#   -H "Authorization: token <TOKEN>" \
#   https://api.github.com/repos/OWNER/REPO/issues/ISSUE_NUMBER

    def value(self, market) -> bool:
        response = requests.get(
            url=f"https://api.github.com/repos/{self.owner}/{self.repo}/issues/{self.number}",
            headers={"Accept": "application/vnd.github+json", "Authorization": getenv('GithubAPIKey')}
        )
        json = response.json()
        return "pull_request" in json and json["pull_request"].get("merged_at") is not None


class ResolutionValueRule(Rule):
    ...


@dataclass
class ResolveRandomSeed(ResolutionValueRule):
    seed: Any
    method: str = 'random'
    rounds: int = 1
    args: Sequence[Any] = ()
    kwargs: Dict[str, Any] = field(default_factory=dict)

    def value(self, market) -> float:
        source = random.Random(self.seed)
        method = getattr(source, self.method)
        for _ in range(self.rounds):
            ret = method(*self.args, **self.kwargs)
        return ret


class ResolveRandomIndex(ResolveRandomSeed):
    def __init__(self, seed, size, rounds=1):
        super().__init__(seed, 'randrange', rounds, (0, size))

    def value(self, market) -> int:
        return cast(int, super().value(market))


@dataclass
class ResolveToPR(ResolutionValueRule):
    owner: str
    repo: str
    number: int

# curl \
#   -H "Accept: application/vnd.github+json" \
#   -H "Authorization: token <TOKEN>" \
#   https://api.github.com/repos/OWNER/REPO/issues/ISSUE_NUMBER

    def value(self, market) -> bool:
        response = requests.get(
            url=f"https://api.github.com/repos/{self.owner}/{self.repo}/issues/{self.number}",
            headers={"Accept": "application/vnd.github+json", "Authorization": getenv('GithubAPIKey')}
        )
        json = response.json()
        return "pull_request" in json and json["pull_request"].get("merged_at") is not None


@dataclass
class ResolveToPRDelta(ResolutionValueRule):
    owner: str
    repo: str
    number: int
    start: datetime

# curl \
#   -H "Accept: application/vnd.github+json" \
#   -H "Authorization: token <TOKEN>" \
#   https://api.github.com/repos/OWNER/REPO/issues/ISSUE_NUMBER

    def value(self, market) -> float:
        response = requests.get(
            url=f"https://api.github.com/repos/{self.owner}/{self.repo}/issues/{self.number}",
            headers={"Accept": "application/vnd.github+json", "Authorization": getenv('GithubAPIKey')}
        )
        json = response.json()
        if "pull_request" not in json or json["pull_request"].get("merged_at") is None:
            return market.market.max
        return (self.start - datetime.fromisoformat(json["pull_request"].get("merged_at"))).days
