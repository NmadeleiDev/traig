import json
import logging
import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from ipaddress import IPv4Network

import sqlalchemy.exc
import sqlmodel
from db import local_session
from db.create_view import create_metrics_view
from exception import ClientFailure, ServerFailure
from github import GithubClient
from model import Account, Commit, MetricTypeEnum, MetricUpdate, Repo, RunConfig
from tasks.celery import app

docker_network_name = os.getenv("DOCKER_NETWORK_NAME", "traig_traignetwork")


def get_traig_docker_network_subnet() -> tuple[str, list[str]]:
    result = subprocess.run(
        f"docker network inspect {docker_network_name}",
        shell=True,
        check=True,
        capture_output=True,
    )
    network_info = [
        x for x in json.loads(result.stdout) if x["Name"] == docker_network_name
    ][0]
    network_subnet = network_info["IPAM"]["Config"][0]["Subnet"]
    reserved_ips = [
        x["IPv4Address"].split("/")[0] for x in network_info["Containers"].values()
    ]
    return network_subnet, reserved_ips


def run_docker_cmd(commit_dir_path: str, container_ip: str, repo: Repo):
    if not os.path.isfile(
        os.path.join(commit_dir_path, repo.traig_compose_file_path_from_repo_root)
    ):
        raise ClientFailure(
            f"unable to find docker compose for traig: "
            f"file {repo.traig_compose_file_path_from_repo_root} not found is {commit_dir_path}"
        )

    commit_ref = os.path.basename(commit_dir_path).lower()
    image_name = commit_ref + "-traigsession"
    container_name = f"{image_name}-1"
    subprocess.run(
        f"docker compose -f {repo.traig_compose_file_path_from_repo_root} build",
        shell=True,
        cwd=commit_dir_path,
        check=True,
    )
    subprocess.run(
        f"docker rm -f {container_name}", shell=True, check=False, cwd=commit_dir_path
    )

    stdout = tempfile.TemporaryFile()
    stderr = tempfile.TemporaryFile()
    exc_str = None
    is_interrupted = False

    try:
        subprocess.run(
            [
                "docker run "
                f"--network={docker_network_name} "
                f"--ip={container_ip} "
                f"--name {container_name} "
                "--rm " + image_name,
            ],
            shell=True,
            cwd=commit_dir_path,
            check=True,
            stdout=stdout,
            stderr=stderr,
            timeout=60 * 10,  # TODO продумать
        )
    except subprocess.TimeoutExpired:
        is_interrupted = True
    except Exception as e:
        exc_str = str(e)

    stdout.seek(0)
    stderr.seek(0)

    stdout_str = stdout.read()  # TODO: поставить ограничение на размер лога
    stderr_str = stderr.read()

    stdout.close()
    stderr.close()

    return stdout_str.decode("utf-8"), stderr_str.decode("utf-8"), exc_str, is_interrupted


@app.task
def download_commit(account_id: int, commit_id: int):
    with local_session() as session:
        account = session.get(Account, account_id)
        if not account:
            raise ServerFailure(f"account not found for id: {account_id}")

        commit = session.get(Commit, commit_id)
        if not commit:
            raise ServerFailure(f"commit not found for id: {commit_id}")

        repo = commit.repo

        github = GithubClient(account.github_personal_api_token)
        commit_dir_path = github.download_and_unzip_commit(commit)

    return os.path.join(commit_dir_path, f"{repo.owner}-{repo.name}-{commit.ref}")


def mode(vals: list):
    counts = {}

    for val in vals:
        if val not in counts:
            counts[val] = 1
        else:
            counts[val] += 1

    max_count = max(counts.values())

    result = [k for k, v in counts.items() if v == max_count]

    return result[0] if len(result) == 1 else result


def save_run_result_and_delete_updates(
    run_config: RunConfig,
    run_ok: bool,
    err_str: str | None,
    stdout: str | None,
    stderr: str | None,
    is_interrupted: bool
):
    with local_session() as session:
        session_updates = session.exec(
            sqlmodel.select(MetricUpdate)
            .where(MetricUpdate.commit_id == run_config.commit_id)
            .order_by(MetricUpdate.created_at)
        ).all()

        result = None
        if run_config.metrics_config is not None:
            all_metric_vals = {k: [] for k in run_config.metrics_config.keys()}

            for update in session_updates:
                for k, v in update.data.items():
                    all_metric_vals[k].append(v)

            result = dict()

            for metric_name, metric_vals in all_metric_vals.items():
                if len(metric_vals) == 0:
                    result[metric_name] = None
                elif run_config.metrics_config[metric_name] == MetricTypeEnum.value:
                    result[metric_name] = metric_vals[-1]
                elif run_config.metrics_config[metric_name] == MetricTypeEnum.max:
                    result[metric_name] = max(metric_vals)
                elif run_config.metrics_config[metric_name] == MetricTypeEnum.min:
                    result[metric_name] = min(metric_vals)
                elif run_config.metrics_config[metric_name] == MetricTypeEnum.sum:
                    result[metric_name] = sum(metric_vals)
                elif run_config.metrics_config[metric_name] == MetricTypeEnum.mean:
                    result[metric_name] = sum(metric_vals) / len(metric_vals)
                elif run_config.metrics_config[metric_name] == MetricTypeEnum.median:
                    sorted_vals = sorted(metric_vals)
                    if len(sorted_vals) % 2:
                        result[metric_name] = sorted_vals[len(sorted_vals) // 2]
                    else:
                        result[metric_name] = (
                            sorted_vals[len(sorted_vals) // 2]
                            + sorted_vals[len(sorted_vals) // 2 + 1]
                        ) / 2
                elif run_config.metrics_config[metric_name] == MetricTypeEnum.count:
                    result[metric_name] = len(metric_vals)
                elif run_config.metrics_config[metric_name] == MetricTypeEnum.mode:
                    result[metric_name] = mode(metric_vals)
                else:
                    raise ServerFailure(
                        f'metric type "{run_config.metrics_config[metric_name]}" is not known'
                    )
        else:
            logging.debug(
                f"seems like metrics were not initialized for commit_id={run_config.commit_id}, "
                f"run_config_id={run_config.id}"
            )
            run_ok = False

        commit = session.get(Commit, run_config.commit_id)

        commit.json_run_result = result
        commit.run_ok = run_ok
        commit.processed = True
        commit.run_error = err_str
        commit.container_stdout = stdout
        commit.container_stderr = stderr
        commit.run_finished_at = datetime.now()
        commit.is_interrupted = is_interrupted

        session.add(commit)
        for session_update in session_updates:
            session.delete(session_update)
        session.commit()


def register_run_config_with_available_ip_address_for_commit(
    commit_id: int,
) -> RunConfig:
    subnet_str, reserved_ips = get_traig_docker_network_subnet()
    network = IPv4Network(subnet_str)

    run_config = None
    with local_session() as session:
        current_runs = session.exec(sqlmodel.select(RunConfig)).all()
        reserved_ips.extend([x.client_ip for x in current_runs])

        hosts = network.hosts()
        next(hosts)  # пропускаем gateway
        for host in hosts:
            if str(host) in reserved_ips:
                continue

            run_config = RunConfig(commit_id=commit_id, client_ip=str(host))
            session.add(run_config)
            try:
                session.commit()
                session.refresh(run_config)
            except (
                sqlalchemy.exc.IntegrityError
            ):  # если этот адрес стал занят, берем следующий
                logging.debug(
                    f"seems like ip {str(host)} is already reserved for some session, wil try other one"
                )
                session.rollback()
                run_config = None
                continue

            break

    if run_config is None:
        raise ServerFailure("unable to find available ip, will retry later")

    return run_config


@app.task
def execute_compose_in_commit_repo(commit_dir_path: str, commit_id: int):
    logging.debug(
        f"starting run for commit_id={commit_id}, commit_dir_path={commit_dir_path}"
    )

    with local_session() as session:
        commit = session.get(Commit, commit_id)
        repo = commit.repo

    run_config = register_run_config_with_available_ip_address_for_commit(commit_id)

    run_err, stdout, stderr, is_interrupted = None, None, None, False
    try:
        stdout, stderr, run_err, is_interrupted = run_docker_cmd(
            commit_dir_path, run_config.client_ip, repo
        )
    except Exception as e:
        logging.error(f"failed to run container for commit: {e}")
        run_err = str(e)
        run_ok = False
    else:
        run_ok = True
    logging.debug(f"finished container execution for commit_id={commit_id}")

    with local_session() as session:
        run_config = session.get(RunConfig, run_config.id)

        save_run_result_and_delete_updates(run_config, run_ok, run_err, stdout, stderr, is_interrupted)

        session.delete(run_config)
        session.commit()

    shutil.rmtree(commit_dir_path)


@app.task
def create_result_metrics_view(group_result, repo_id: int):
    with local_session() as session:
        create_metrics_view(session.get(Repo, repo_id), session)
