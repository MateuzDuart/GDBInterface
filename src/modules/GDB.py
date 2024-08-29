import subprocess, re, uuid, threading, queue, json, os
from enum import Enum
from filelock import FileLock
from erros.gdbErrors import Closed_pipe


class GDBStatus(Enum):
    SUCCESS = "^done"
    ERROR = "^error"
    RUNNING = "^running"
    FINALIZED = "finalized"
    UNDEFINED = "undefined"


class GDBManager:
    base_path = "sections"
    instances = {}  # Dicionário para manter as instâncias do GDB em memória
    cache = {}  # Dicionário para armazenar o cache na memória

    @staticmethod
    def is_cache_available(cache_key):
        """
        Verifica se o cache está disponível para a chave fornecida.
        """
        return cache_key in GDBManager.cache

    @staticmethod
    def get_cache(cache_key):
        """
        Retorna o valor armazenado no cache para a chave fornecida.
        """
        return GDBManager.cache.get(cache_key)

    @staticmethod
    def set_cache(cache_key, data):
        """
        Define o valor no cache para a chave fornecida.
        """
        GDBManager.cache[cache_key] = data

    @staticmethod
    def clear_cache(cache_key=None):
        """
        Limpa o cache. Se uma chave for fornecida, limpa apenas essa chave.
        Caso contrário, limpa todo o cache.
        """
        if cache_key:
            if cache_key in GDBManager.cache:
                del GDBManager.cache[cache_key]
        else:
            GDBManager.cache.clear()

    @staticmethod
    def create_session(
        gdb_path="D:\\android-NDK\\prebuilt\\windows-x86_64\\bin\\gdb.exe",
    ):
        session_id = str(uuid.uuid4())
        session_dir = os.path.join(GDBManager.base_path, session_id)
        os.makedirs(session_dir, exist_ok=True)

        gdb_instance = GDB(gdb_path)
        gdb_instance.start()

        session_data = {
            "id": session_id,
            "breakpoints": [],
            "commands": [],
            "status": "created",
        }

        # Salva a sessão e armazena a instância do GDB na memória
        GDBManager.save_session(session_id, session_data)
        GDBManager.instances[session_id] = gdb_instance

        return session_id

    @staticmethod
    def get_session(session_id):
        # Checa se já existe uma instância do GDB para essa sessão na memória
        if session_id in GDBManager.instances:
            gdb_instance = GDBManager.instances[session_id]
            if not gdb_instance:
                raise Closed_pipe("A sessão finalizou, reinicialize.")

            session_file = os.path.join(
                GDBManager.base_path, session_id, "session.json"
            )
            with open(session_file, "r") as file:
                session_data = json.load(file)
            return {"data": session_data, "gdb_instance": gdb_instance}
        else:
            session_data = GDBManager.init_section(session_id)

            if not session_data:
                return None

            return session_data

    @staticmethod
    def save_session(session_id, data):
        session_file = os.path.join(GDBManager.base_path, session_id, "session.json")
        lock = FileLock(f"{session_file}.lock")

        with lock:
            with open(session_file, "w") as file:
                json.dump(data, file, indent=4)

    @staticmethod
    def load_session(session_id):
        session_file = os.path.join(GDBManager.base_path, session_id, "session.json")
        if os.path.exists(session_file):
            with open(session_file, "r") as file:
                return json.load(file)
        return None

    @staticmethod
    def load_all_sessions():
        sessions = []
        if os.path.exists(GDBManager.base_path):
            for session_id in os.listdir(GDBManager.base_path):
                session_path = os.path.join(GDBManager.base_path, session_id)
                if os.path.isdir(session_path):
                    session_data = GDBManager.load_session(session_id)
                    if session_data:
                        sessions.append(session_data)
        return sessions

    @staticmethod
    def init_section(session_id):
        session_file = os.path.join(GDBManager.base_path, session_id, "session.json")
        if not os.path.exists(session_file):
            return None

        with open(session_file, "r") as file:
            session_data = json.load(file)

        gdb_instance = GDBManager.init_pipe(
            session_id, session_data["commands"], session_data["breakpoints"]
        )

        return {"data": session_data, "gdb_instance": gdb_instance}

    @staticmethod
    def terminate_section(session_id):
        # Termina a sessão GDB e remove a instância da memória
        if session_id in GDBManager.instances:
            GDBManager.instances[session_id].terminate()
            del GDBManager.instances[session_id]

        session_dir = os.path.join(GDBManager.base_path, session_id)
        if os.path.exists(session_dir):
            import shutil

            shutil.rmtree(session_dir)
            return True
        return False

    @staticmethod
    def add_commands(session_id, command):
        session_data = GDBManager.load_session(session_id)
        session_data["commands"].append(command)

        GDBManager.save_session(session_id, session_data)

    @staticmethod
    def add_breakpoint(session_id, breakpoint):
        session_data = GDBManager.get_session(session_id)
        if not session_data:
            return None

        session_data["data"]["breakpoints"].append(breakpoint)
        GDBManager.save_session(session_id, session_data["data"])
        return session_data

    @staticmethod
    def list_breakpoints(session_id):
        session_data = GDBManager.get_session(session_id)
        if not session_data:
            return None

        return session_data["data"].get("breakpoints", [])

    @staticmethod
    def remove_breakpoint(session_id, breakpoint):
        session_data = GDBManager.get_session(session_id)
        if not session_data:
            return None

        if breakpoint in session_data["data"]["breakpoints"]:
            session_data["data"]["breakpoints"].remove(breakpoint)
        else:
            print(f"Breakpoint {breakpoint} não encontrado na sessão {session_id}")

        GDBManager.save_session(session_id, session_data["data"])
        return session_data

    @staticmethod
    def init_pipe(session_id, commands=[], breakpoints=[]):
        if session_id in GDBManager.instances:
            gdb_instance = GDBManager.instances[session_id]
            if gdb_instance:
                return gdb_instance

        gdb_instance = GDB("D:\\android-NDK\\prebuilt\\windows-x86_64\\bin\\gdb.exe")
        gdb_instance.start()
        GDBManager.instances[session_id] = gdb_instance  # Armazena a instância

        for command in commands:
            gdb_instance.send_command(command)
        for breakpoint in breakpoints:
            gdb_instance.send_command(f"break *{breakpoint}")

        return gdb_instance

    @staticmethod
    def restart_pipe(session_id):
        if session_id in GDBManager.instances:
            gdb_instance = GDBManager.instances[session_id]
            if gdb_instance:
                GDBManager.close_gdb_pipe(session_id)

            session_file = os.path.join(
                GDBManager.base_path, session_id, "session.json"
            )
            if not os.path.exists(session_file):
                return None

            with open(session_file, "r") as file:
                session_data = json.load(file)

            gdb_instance = GDBManager.init_pipe(
                session_id, session_data["commands"], session_data["breakpoints"]
            )

            return True
        return False

    @staticmethod
    def close_gdb_pipe(session_id):
        gdb_instance = GDBManager.instances[session_id]
        if gdb_instance:
            gdb_instance.terminate()
            GDBManager.instances[session_id] = None


class GDB:
    def __init__(self, gdb_path, mi_version="mi2"):
        self.gdb_command = [gdb_path, "-q", f"--interpreter={mi_version}"]
        self.gdb_process = None
        self.command_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.lock = threading.Lock()

    def start(self):
        try:
            self.gdb_process = subprocess.Popen(
                self.gdb_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            threading.Thread(target=self.process_commands, daemon=True).start()
            return self.read_gdb_output()
        except Exception as e:
            print(f"Erro ao iniciar o GDB: {e}")
            return GDBStatus.ERROR, []

    def send_command(self, command):
        if not self.gdb_process or self.gdb_process.stdin is None:
            raise Exception(
                "GDB process is not running or has been terminated. Please start the process first."
            )
        self.command_queue.put(command)
        return self.result_queue.get()

    def process_commands(self):
        while True:
            command = self.command_queue.get()
            if command is None:
                break
            if self.gdb_process and self.gdb_process.stdin:
                with self.lock:
                    self.gdb_process.stdin.write(command + "\n")
                    self.gdb_process.stdin.flush()
                result = self.read_gdb_output()
                self.result_queue.put(result)
            else:
                self.result_queue.put((GDBStatus.ERROR, []))

    def read_gdb_output(self):
        output = []
        while True:
            with self.lock:
                if not self.gdb_process or not self.gdb_process.stdout:
                    return GDBStatus.ERROR, []

                line = self.gdb_process.stdout.readline().strip()

            if line:
                output.append(line)

            if "exited with code" in line:
                return GDBStatus.FINALIZED, output
            elif "(gdb)" in line:
                break

        status = self.get_command_status(output)
        if status == GDBStatus.RUNNING:
            return self.read_gdb_output()

        return status, output

    def get_command_status(self, output):
        if len(output) < 2:
            return GDBStatus.UNDEFINED

        if output[-2].startswith(GDBStatus.SUCCESS.value):
            return GDBStatus.SUCCESS
        elif output[-2].startswith(GDBStatus.ERROR.value):
            return GDBStatus.ERROR
        elif len(output) >= 3 and output[-3].startswith(GDBStatus.RUNNING.value):
            return GDBStatus.RUNNING

        return GDBStatus.UNDEFINED

    def terminate(self):
        with self.lock:
            if self.gdb_process:
                self.command_queue.put(None)  # Signal to end the process_commands loop
                self.gdb_process.terminate()
                self.gdb_process = None

    @staticmethod
    def parse_disassembly(output, breakpoints=None):
        if breakpoints is None:
            breakpoints = []

        disassembly = []
        parsed_output = []
        capture = False

        for line in output:
            if not capture and "Dump of assembler code" in line:
                capture = True
                continue
            if "End of assembler dump" in line:
                break
            if capture:
                clean_line = line.strip('~"').strip()
                disassembly.append(clean_line)

        if not disassembly:
            return []

        pattern = re.compile(r"^(=> )?(0x[0-9a-f]+) <(\+\d+)>:\s*(.*)$")
        for line in disassembly:
            match = pattern.match(line)
            if match:
                indicator = match.group(1) or ""
                address = match.group(2)
                offset = match.group(3)
                instruction_line = (
                    match.group(4).replace("\\t", " ").replace("\\n", "").strip()
                )
                parts = instruction_line.split(" ", 1)
                instruction = parts[0]
                arguments = parts[1] if len(parts) > 1 else ""

                # Verifica se o endereço atual é um breakpoint
                is_breakpoint = address in breakpoints

                # Verifica se é a linha atual
                is_current_line = bool(indicator)

                parsed_output.append(
                    [
                        is_current_line,
                        is_breakpoint,
                        address,
                        offset,
                        instruction,
                        arguments,
                    ]
                )
        return parsed_output

    @staticmethod
    def parse_registers(output):
        registers = []
        register_pattern = re.compile(r'^~"(\w+)\s+0x([0-9a-f]+)')
        for line in output:
            match = register_pattern.match(line)
            if match:
                register_name = match.group(1)
                register_value = match.group(2)
                registers.append((register_name, register_value))
        return registers

    @staticmethod
    def parse_memory(output):
        memory_mappings = []
        memory_pattern = re.compile(
            r'~"\\t(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(.*)\\n"'
        )
        for line in output:
            match = memory_pattern.match(line)
            if match:
                start_addr = match.group(1)
                end_addr = match.group(2)
                size = match.group(3)
                offset = match.group(4)
                objfile = match.group(5)
                hex_data = " ".join(f"{ord(c):02x}" for c in objfile)
                ascii_data = "".join(c if 32 <= ord(c) <= 126 else "." for c in objfile)
                memory_mappings.append((start_addr, hex_data, ascii_data))
        return memory_mappings

    @staticmethod
    def parse_stack(output):
        stack_info = []
        stack_pattern = re.compile(r'~"(.+)"')
        for line in output:
            match = stack_pattern.match(line)
            if match:
                clean_line = line.strip('~"').replace("\\n", "").strip()
                if clean_line:
                    stack_info.append(clean_line)
        return stack_info

    @staticmethod
    def parse_functions(output):
        """
        Parse the output of the 'info functions' command.

        Args:
            output (list): The list of lines from the GDB output.

        Returns:
            list: A list of dictionaries with function address and name.
        """
        functions = []
        function_pattern = re.compile(r"^0x([0-9a-f]+)\s+(.+)$")

        for line in output:
            match = function_pattern.match(line.strip('~"'))
            if match:
                functions.append(
                    {"address": match.group(1), "name": match.group(2)[:-2]}
                )

        return functions

    @staticmethod
    def parse_backtrace(output):
        """
        Parse the output of the 'bt' (backtrace) command.

        Args:
            output (list): The list of lines from the GDB output.

        Returns:
            list: A list of dictionaries with frame number, function name, and address.
        """
        backtrace = []
        backtrace_pattern = re.compile(r"#(\d+)\s+0x([0-9a-f]+) in (.+) \((.*)\)")

        for line in output:
            match = backtrace_pattern.match(line.strip('~"'))
            if match:
                backtrace.append(
                    {
                        "framePosition": match.group(1),
                        "address": match.group(2),
                        "function": match.group(3),
                        "args": match.group(4),
                    }
                )

        return backtrace
