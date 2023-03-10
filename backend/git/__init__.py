from abc import ABC

from model import Commit, Repo, Branch


class _BaseGitClient(ABC):
    def get_repo_branches(self, repo: Repo) -> list[Branch]:
        pass

    def get_branch_commits(self, branch: Branch) -> list[Commit]:
        pass

    def download_and_unzip_commit(self, commit: Commit) -> str:
        pass
