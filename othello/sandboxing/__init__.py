import json
import logging
import subprocess
import traceback

from django.conf import settings

logger = logging.getLogger("othello")


def import_strategy_sandboxed(path):
    cmd_args = ["python3", "-u", settings.IMPORT_DRIVER, path]
    if not settings.DEBUG:
        cmd_args = get_sandbox_args(cmd_args)

    p = subprocess.Popen(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = p.communicate()
    if p.returncode == 0:
        return 0
    else:
        try:
            return json.loads(error.decode("latin-1"))
        except:
            logger.error(f"Failed to import/load strategy file {traceback.format_exc()}")
            return {"message": error.decode()}


def get_sandbox_args(cmd_args, *, whitelist=None, readonly=None, extra_args=None):
    firejail_args = [
        "firejail",
        "--quiet",
        "--net=none",
        f"--profile={settings.FIREJAIL_PROFILE}",
        f"--whitelist={settings.JAILEDRUNNER_DRIVER}",
        f"--read-only={settings.JAILEDRUNNER_DRIVER}",
        f"--whitelist={settings.MODERATOR_ROOT}",
        f"--read-only={settings.MODERATOR_ROOT}",
        f"--whitelist={settings.IMPORT_DRIVER}",
        f"--read-only={settings.IMPORT_DRIVER}",
    ]

    if whitelist:
        for path in whitelist:
            firejail_args.append(f"--whitelist={path}")

    if readonly:
        for path in readonly:
            firejail_args.append(f"--read-only={path}")

    if extra_args:
        firejail_args.extend(extra_args)

    return [*firejail_args, *cmd_args]
