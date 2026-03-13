import os
import asyncio
import shlex
from typing import Tuple

os.environ['GIT_PYTHON_REFRESH'] = 'quiet'
from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

import config

from ..logging import LOGGER


def install_req(cmd: str) -> Tuple[str, str, int, int]:
    async def install_requirements():
        args = shlex.split(cmd)
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return (
            stdout.decode("utf-8", "replace").strip(),
            stderr.decode("utf-8", "replace").strip(),
            process.returncode,
            process.pid,
        )

    return asyncio.get_event_loop().run_until_complete(install_requirements())


def git():
    REPO_LINK = config.UPSTREAM_REPO
    if config.GIT_TOKEN:
        GIT_USERNAME = REPO_LINK.split("com/")[1].split("/")[0]
        TEMP_REPO = REPO_LINK.split("https://")[1]
        UPSTREAM_REPO = f"https://{GIT_USERNAME}:{config.GIT_TOKEN}@{TEMP_REPO}"
    else:
        UPSTREAM_REPO = config.UPSTREAM_REPO

    try:
        repo = Repo()
        LOGGER(__name__).info(f"Git Client Found [VPS DEPLOYER]")
    except (GitCommandError, InvalidGitRepositoryError):
        try:
            repo = Repo.init()
            LOGGER(__name__).info(f"Initialized new Git repository.")
        except Exception as e:
            LOGGER(__name__).error(f"Failed to initialize Git: {e}")
            return

    try:
        # Force update the origin URL to the one we want to use (with token if provided)
        if "origin" in repo.remotes:
            origin = repo.remote("origin")
            origin.set_url(UPSTREAM_REPO)
        else:
            origin = repo.create_remote("origin", UPSTREAM_REPO)

        # Set git config to be strictly non-interactive
        with repo.config_writer() as cw:
            cw.set_value("core", "askpass", "true")
            cw.set_value("credential", "helper", "")
        
        os.environ['GIT_TERMINAL_PROMPT'] = '0'

        try:
            LOGGER(__name__).info(f"Fetching updates from {REPO_LINK}...")
            origin.fetch(config.UPSTREAM_BRANCH)
        except Exception as e:
            LOGGER(__name__).warning(f"Git Fetch Failed (skipping update): {e}")
            return

        # Ensure the head is correct
        try:
            if config.UPSTREAM_BRANCH not in repo.heads:
                repo.create_head(
                    config.UPSTREAM_BRANCH,
                    origin.refs[config.UPSTREAM_BRANCH],
                )
            
            head = repo.heads[config.UPSTREAM_BRANCH]
            head.set_tracking_branch(origin.refs[config.UPSTREAM_BRANCH])
            head.checkout(True)
            
            # Pull updates
            origin.pull(config.UPSTREAM_BRANCH)
        except GitCommandError:
            repo.git.reset("--hard", "FETCH_HEAD")
        except Exception as e:
            LOGGER(__name__).warning(f"Git Pull Failed (skipping update): {e}")
            return

        install_req("pip3 install --no-cache-dir -r requirements.txt")
        LOGGER(__name__).info(f"Successfully updated from upstream repository.")
    except Exception as e:
        LOGGER(__name__).error(f"Unexpected Git Error: {e}")
