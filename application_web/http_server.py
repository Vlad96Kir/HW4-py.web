from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import urllib.parse
import mimetypes
import json
import logging
from datetime import datetime
import socket


class SocketClient():
    def __init__(self, ip='127.0.0.1', port=5000) -> None:
        self.UDP_IP = ip
        self.UDP_PORT = port

    def run_socket_client(self, message: str) -> bool:
        result = False
        try:
            sock: socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            server = (self.UDP_IP, self.UDP_PORT)
            if message:
                data = message.encode()
                sock.sendto(data, server)
                response = sock.recvfrom(1024)
                status = json.loads(response[0])
                if status.get("STATUS") == "OK":
                    logger.info('SAVED OK')
                    result = True
                else:
                    logger.error('ERROR ON SAVING')
        except Exception as e:
            logger.error(f'Error in run_socket_client: {e}')
        finally:
            sock.close()
        return result


class WWWHandler(BaseHTTPRequestHandler):
    BASE_ROOT_DIR = Path()
    BASE_STORAGE_DIR = Path()
    socket_client = None

    @staticmethod
    def set_root(path: Path, storage_path: Path = None, socket_client: SocketClient = None):
        WWWHandler.BASE_ROOT_DIR = path
        if storage_path:
            WWWHandler.BASE_STORAGE_DIR = storage_path
        if socket_client:
            WWWHandler.socket_client = socket_client

    def save_data(self, data: dict) -> bool:
        json_data = json.dumps(data, ensure_ascii=False)
        result = self.socket_client.run_socket_client(json_data)
        return result

    def get_file(self, filename, state=200):
        self.send_response(state)
        mmtype, _ = mimetypes.guess_type(filename)
        if mmtype:
            self.send_header("Content-Type", mmtype)
        else:
            self.send_header("Content-Type", "plain/text")
        self.end_headers()
        try:
            with open(filename, "rb") as fp:
                self.wfile.write(fp.read())
        except Exception as e:
            logger.error(e)

    def do_POST(self):
        route_path = urllib.parse.urlparse(self.path)
        if route_path.path == "/message":
            cont_len = int(self.headers["Content-Length"])
            data = self.rfile.read(cont_len).decode()
            data_parse = {
                key: urllib.parse.unquote_plus(val) for key, val in [el.split("=") for el in data.split("&")]
            }
            if not data_parse or all(val == '' for val in data_parse.values()):
                self.send_response(301)
                self.send_header("Location", "/empty_message.html")
                self.end_headers()
                return
            # if not data_parse:
            #     self.send_response(301)
            #     self.send_header("Location", "/empty_message.html")
            #     self.end_headers()
            #     return

            timestamp = str(datetime.now())
            data_record = {
                timestamp: data_parse
            }

            try:
                json_data = json.dumps(data_record, ensure_ascii=False)
                result = self.save_data(data_record)
                location = "/message_done.html" if result else "/error.html"
                self.send_response(301)
                self.send_header("Location", location)
                self.end_headers()

            except Exception as e:
                logger.error(e)
        else:
            self.send_response(301)
            self.send_header("Location", "/error.html")
            self.end_headers()

    def do_GET(self):
        route_path = urllib.parse.urlparse(self.path)
        match route_path.path:
            case "/":
                filename = self.BASE_ROOT_DIR / "index.html"
                self.get_file(filename)
            case _:
                filename = self.BASE_ROOT_DIR / route_path.path[1:]
                if filename.exists():
                    self.get_file(filename)
                else:
                    filename = self.BASE_ROOT_DIR / "error.html"
                    self.get_file(filename, 404)


def init_storage(storage: Path):
    if not storage.is_dir():
        logger.debug(f"init_storage : creating need folder: {storage}")
        try:
            storage.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f'Error in init_storage: {e}')
    data_file = storage / "data.json"
    if not data_file.is_file():
        with open(data_file, "w", encoding="utf-8") as fp:
            try:
                json.dump({}, fp)
            except Exception as e:
                logger.error(f'Error in init_storage: {e}')


def run(server=HTTPServer, handler=WWWHandler):
    global logger
    logger = logging.getLogger(__name__)
    address = ("", 3000)
    www_root = Path("www-data/")
    storage = Path("storage/")
    socket_client = SocketClient()
    handler.set_root(www_root, storage, socket_client)
    http_server = server(address, handler)
    logger.info(f"Start HTTP server at port: {address[1]}")
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()
    except Exception as e:
        logger.error(e)
        http_server.server_close()


logger: logging

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG, format="%(asctime)s [ %(threadName)s ] %(message)s"
    )
    run()