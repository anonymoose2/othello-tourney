import os
import select
import signal
import subprocess
import time

import psutil

from django.conf import settings

from ..sandboxing import get_sandbox_args
from .utils import ServerError, UserError, capture_generator_value


class PlayerRunner:
    def __init__(self, path, driver):
        if not os.path.isfile(path):
            raise OSError("file not found")
        self.path = path
        self.process = None
        self.driver = driver

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def start(self):
        cmd_args = ["python3", "-u", self.driver, self.path]
        if settings.DEBUG:
            cmd_args = get_sandbox_args(
                cmd_args, whitelist=[os.path.dirname(self.path)], readonly=[self.path]
            )

        self.process = subprocess.Popen(
            cmd_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
            cwd=os.path.dirname(self.path),
            preexec_fn=os.setpgrp,
        )

    def stop(self):
        if self.process is not None:
            children = psutil.Process(self.process.pid).children(recursive=True)
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                self.process.kill()
            for child in children:
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            self.process = None

    @capture_generator_value
    def get_move(self, board, player, time_limit, last_move):
        if self.process.poll():
            print(self.process.communicate())
            return -1, ServerError.PROCESS_EXITED
        self.process.stdin.write(
            f"{str(time_limit)}\n{player}\n{''.join(board)}\n".encode("latin-1")
        )
        self.process.stdin.flush()
        move = -1

        start, total_timeout = time.time(), time_limit + 10
        while move == -1:
            if self.process.poll():
                print(self.process.communicate())
                return -1, ServerError.PROCESS_EXITED
            if (timeout := total_timeout - (time.time() - start)) <= 0:
                return -1, ServerError.TIMEOUT

            files_ready = select.select(
                [self.process.stdout, self.process.stderr], [], [], timeout
            )[0]
            if self.process.stderr in files_ready:
                yield self.process.stderr.read(8192).decode("latin-1")
            if self.process.stdout in files_ready:
                try:
                    move = int(self.process.stdout.readline())
                    print(f"GOT MOVE {move}")
                    if move < 0 or move >= 64:
                        return -1, UserError.READ_INVALID
                except ValueError:
                    return -1, UserError.READ_INVALID
        return move, 0


class YourselfRunner:
    def __init__(self, game, timeout):
        self.timeout = timeout
        self.game = game

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def stop(self):
        pass

    @capture_generator_value
    def get_move(self, board, player, time_limit, last_move):
        yield "Choose your move!"
        start = time.time()
        while True:
            self.game.refresh_from_db()
            if not self.game.playing:
                return -1, ServerError.DISCONNECT
            if (time.time() - start) > self.timeout:
                return -1, UserError.NO_MOVE_ERROR
            if (m := self.game.moves.latest()) != last_move:
                if m is not None:
                    m.delete()
                    return m.move, 0
                else:
                    return -1, ServerError.DISCONNECT
