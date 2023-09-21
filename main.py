from threading import Thread
from application_web import http_server, socket_server
import logging
import time
import signal
import sys


def boot_socket_server(name):
    th_socket_server = Thread(name=name, target=socket_server.run)
    th_socket_server.start()
    return th_socket_server


def boot_http_server(name):
    th_http_server = Thread(name=name, target=http_server.run)
    th_http_server.start()
    return th_http_server


def run_threads():
    logger.info("run_threads")

    servers_boot = {
        "HTTP_SERVER": boot_http_server,
        "SOCKET_SERVER": boot_socket_server
    }

    threads = {}

    for name, boot_server in servers_boot.items():
        th = boot_server(name)
        threads[th.name] = th

    logger.info("run WATHCDOG timer for servers in threads")
    while True:
        for name, th in threads.items():
            if not th.is_alive():
                logger.error(f"thread crashed, restart - {th.name}")
                th = servers_boot[name](name)
                threads[name] = th
        time.sleep(2)


def signal_handler(sig, frame):
    logger.info("Received SIGINT, shutting down...")
    sys.exit(0)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG, format="%(asctime)s [ %(threadName)s ] < %(filename)s:%(lineno)d > %(message)s"
    )
    logger = logging.getLogger(__name__)

    signal.signal(signal.SIGINT, signal_handler)

    run_threads()