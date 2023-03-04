import logging
import os
import shutil
import zipfile

import dateutil.parser
import requests
from exception import ServerFailure
from model import Commit, Repo


class GithubClient:
    def __init__(self, token: str):
        self.token = token

    @staticmethod
    def check_response(response: requests.Response):
        if response.status_code != 200:
            raise ServerFailure(
                f"response from github is not 200 (it is {response.status_code}), text: {response.text}"
            )

    @staticmethod
    def construct_repo_path(repo: Repo):
        save_base_path = os.getenv("REPOS_DOWNLOAD_PATH")
        if not save_base_path:
            raise ServerFailure("REPOS_DOWNLOAD_PATH is not set, unable to save file")
        return os.path.join(save_base_path, f"{repo.account.id}__{repo.name}")

    def get_repo_commits(self, repo: Repo) -> list[Commit]:
        response = requests.get(
            f"https://api.github.com/repos/{repo.owner}/{repo.name}/commits",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

        self.check_response(response)

        return sorted(
            [
                Commit(
                    ref=item["sha"],
                    committed_datetime=dateutil.parser.isoparse(
                        item["commit"]["committer"]["date"]
                    ),
                    message=item["commit"]["message"],
                    repo_id=repo.id,
                )
                for item in response.json()
            ],
            key=lambda x: x.committed_datetime,
        )

    def download_and_unzip_commit(self, commit: Commit) -> str:
        repo = commit.repo
        response = requests.get(
            f"https://api.github.com/repos/{repo.owner}/{repo.name}/zipball/{commit.ref}",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            allow_redirects=True,
        )

        self.check_response(response)

        logging.debug(f"got zip from github, headers: {response.headers}")

        repo_path = self.construct_repo_path(commit.repo)
        os.makedirs(repo_path, exist_ok=True)

        commit_dir_path = os.path.join(repo_path, commit.ref)
        try:
            os.makedirs(commit_dir_path, exist_ok=False)
        except FileExistsError:
            logging.warning(
                f"strangely dir for commit {commit.ref} already exists at {commit_dir_path}, will remove it"
            )
            shutil.rmtree(commit_dir_path)
            os.makedirs(commit_dir_path, exist_ok=False)

        commit_zip_path = f"{commit_dir_path}.zip"
        with open(commit_zip_path, "wb") as f:
            f.write(response.content)

        with zipfile.ZipFile(commit_zip_path, "r") as zip_ref:
            zip_ref.extractall(commit_dir_path)

        os.unlink(commit_zip_path)

        return commit_dir_path
