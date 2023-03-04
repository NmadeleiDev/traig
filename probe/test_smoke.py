import os
import random
import string

import pytest
from utils import PrefixUrlHttpSession, poll_for


@pytest.fixture
def email():
    return (
        "".join([random.choice(string.ascii_lowercase) for _ in range(10)])
        + "@mail.com"
    )


@pytest.fixture
def service_url():
    env = os.environ.get("ENV", "docker")
    return {
        "docker": "http://local.traigserver.io",
        "prod": "https://traig.io/api/v1",
    }[env]


@pytest.fixture
def client(service_url):
    with PrefixUrlHttpSession(service_url) as session:
        yield session


def create_account(client: PrefixUrlHttpSession, email: str) -> dict:
    return client.post(
        "system/signup",
        json={
            "email": email,
            "password": "string",
            "github_personal_api_token": os.getenv("TEST_GITHUB_TOKEN"),
        },
    ).json()


def create_repo(client: PrefixUrlHttpSession) -> dict:
    return client.post(
        "repo",
        json={
            "owner": os.getenv("TEST_GITHUB_REPO_OWNER"),
            "name": os.getenv("TEST_GITHUB_REPO_NAME"),
        },
    ).json()


def get_statistics(client: PrefixUrlHttpSession, repo_id: int) -> list[dict]:
    return client.get(f"statistics/{repo_id}").json()


def test_smoke(client, email):
    _ = create_account(client, email)
    repo = create_repo(client)

    for _ in poll_for("commits fetched", ttl=5):
        stats = get_statistics(client, repo["id"])
        if len(stats) > 0:
            break

    count_success = 0
    for _ in poll_for("stats ready", ttl=60):
        stats = get_statistics(client, repo["id"])
        assert len(stats) > 0

        count_success = 0
        all_done = True
        for stat in stats:
            if stat["processed"] is False:
                all_done = False
                continue
            if stat["run_ok"] is True:
                assert stat["json_run_result"] is not None
                count_success += 1

        if all_done:
            break

    assert count_success > 0
