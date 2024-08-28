from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from modules.GDB import GDB, GDBStatus, GDBManager

app = Flask(__name__)
app.secret_key = "supersecretkey"

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        gdb_command = request.form.get("gdb_command")

        if gdb_command == "gdb":
            file = request.files["file"]
            if file:
                # Criar uma nova sessão GDB para o arquivo enviado
                instance_id = GDBManager.create_session()
                gdb_instance = GDBManager.get_session(instance_id)
                # Aqui você deve adicionar a lógica para carregar o arquivo no GDB
                # Exemplo:
                # result = gdb_instance.load_file(file_path)
                flash("Arquivo carregado com sucesso.", "success")
                return redirect(url_for('analysis', instance_id=instance_id, section_name="cpu"))
            else:
                flash("Nenhum arquivo foi enviado.", "error")

        elif gdb_command == "gdbserver":
            ip = request.form.get("ip")
            port = request.form.get("port")
            if ip and port:
                # Criar uma nova sessão GDB Server
                instance_id = GDBManager.create_session()
                session_data = GDBManager.get_session(instance_id)
                gdb_instance = session_data["gdb_instance"]
                connection_status, resp_data = gdb_instance.send_command(f"target remote {ip}:{port}")
                if connection_status == GDBStatus.SUCCESS:
                    flash("Conexão concluída com sucesso.", "success")
                    return redirect(url_for('analysis', instance_id=instance_id, section_name="cpu"))
                else:
                    GDBManager.terminate_section(instance_id)
                    flash(f"Erro ao conectar a {ip}:{port}", "error")
            else:
                flash("IP e Porta são obrigatórios para GDB Server.", "error")

    # Carrega todas as sessões existentes
    sessions = GDBManager.load_all_sessions()
    
    return render_template("index.html", sessions=sessions)

@app.route("/analysis/<string:instance_id>")
def analysis(instance_id):
    session = GDBManager.get_session(instance_id)
    if not session:
        flash("Sessão não encontrada. Por favor, inicie uma nova sessão.", "error")
        return redirect(url_for('index'))
    return render_template("analysis.html", instance_id=instance_id)

@app.route("/terminate/<session_id>", methods=["POST"])
def terminate_session(session_id):
    if GDBManager.terminate_section(session_id):
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Sessão não encontrada."})

@app.route("/section/<string:section_name>/<string:instance_id>")
def load_section(section_name, instance_id):
    session = GDBManager.get_session(instance_id)
    if not session:
        return jsonify({"error": "Sessão não encontrada."}), 404

    gdb_instance = session["gdb_instance"]

    if section_name == "cpu":
        resp_status, disassembly = gdb_instance.send_command("disassemble")
        resp_status, registers = gdb_instance.send_command("info registers")
        resp_status, memory = gdb_instance.send_command("info proc mappings")
        resp_status, stack = gdb_instance.send_command("info frame")
        
        return render_template(
            "sections/cpu.html", 
            cpu_data={
                "disassembly": GDB.parse_disassembly(disassembly),
                "registers": GDB.parse_registers(registers),
                "memory": GDB.parse_memory(memory),
                "stack": GDB.parse_stack(stack)
            }
        )
    elif section_name == "breakpoints":
        return render_template("sections/breakpoints.html")
    elif section_name == "callstack":
        return render_template("sections/callstack.html")
    else:
        return jsonify({"error": "Seção não encontrada."}), 404


@app.route("/section/cpu/<string:instance_id>/<subsection>")
def load_cpu_subsection(instance_id, subsection):
    session = GDBManager.get_session(instance_id)
    if not session:
        return jsonify({"error": "Sessão não encontrada."}), 404

    gdb_instance = session["gdb_instance"]

    if subsection == "disassembly":
        breakpoints = GDBManager.list_breakpoints(instance_id)
        resp_status, disassembly = gdb_instance.send_command("disassemble")
        return jsonify(GDB.parse_disassembly(disassembly, breakpoints))
    elif subsection == "registers":
        resp_status, registers = gdb_instance.send_command("info registers")
        return jsonify(GDB.parse_registers(registers))
    elif subsection == "memory":
        resp_status, memory = gdb_instance.send_command("info proc mappings")
        return jsonify(GDB.parse_memory(memory))
    elif subsection == "stack":
        resp_status, stack = gdb_instance.send_command("info frame")
        return jsonify(GDB.parse_stack(stack))
    else:
        return jsonify([])


@app.route("/recive_command/<string:instance_id>/", methods=["POST"])
def recive_commands(instance_id):
    session = GDBManager.get_session(instance_id)
    if not session:
        return jsonify({"error": "Sessão não encontrada."}), 404
    
    command = request.form.get("command")
    
    if not command:
        return jsonify({"error": "Nenhum comando fornecido."}), 400
    
    gdb_instance = session["gdb_instance"]
    resp_status, output = gdb_instance.send_command(command)
    
    if resp_status == GDBStatus.SUCCESS:
        return jsonify({"status": "success", "output": output})
    elif resp_status == GDBStatus.ERROR:
        return jsonify({"status": "error", "output": output})
    elif resp_status == GDBStatus.RUNNING:
        return jsonify({"status": "running", "output": output})
    elif resp_status == GDBStatus.FINALIZED:
        # Finalizar e remover a sessão se o processo GDB foi encerrado
        GDBManager.terminate_section(instance_id)
        return jsonify({"status": "finalized", "output": output})
    else:
        return jsonify({"status": "undefined", "output": output})

@app.route("/breakpoints/<string:instance_id>", methods=["GET", "POST", "DELETE"])
def manage_breakpoints(instance_id):
    if request.method == "GET":
        # Listar todos os breakpoints
        session_data = GDBManager.get_session(instance_id)
        if session_data is None:
            return jsonify({"error": "Sessão não encontrada."}), 404
        
        breakpoints = GDBManager.list_breakpoints(instance_id)
        return jsonify({"breakpoints": breakpoints})
    
    elif request.method == "POST":
        # Adicionar um novo breakpoint
        data = request.json
        breakpoint = data.get("breakpoint")
        if not breakpoint:
            return jsonify({"error": "Nenhum breakpoint fornecido."}), 400

        session_data = GDBManager.add_breakpoint(instance_id, breakpoint)
        if session_data is None:
            return jsonify({"error": "Sessão não encontrada."}), 404

        # Enviar comando para o GDB
        gdb_instance = session_data["gdb_instance"]
        resp_status, output = gdb_instance.send_command(f"break *{breakpoint}")
        
        if resp_status == GDBStatus.SUCCESS:
            return jsonify({"status": "success", "breakpoints": session_data["data"]["breakpoints"], "output": output})
        else:
            return jsonify({"status": "error", "output": output})
    
    elif request.method == "DELETE":
        # Remover um breakpoint
        data = request.json
        breakpoint = data.get("breakpoint")
        if not breakpoint:
            return jsonify({"error": "Nenhum breakpoint fornecido."}), 400

        session_data = GDBManager.remove_breakpoint(instance_id, breakpoint)
        if session_data is None:
            return jsonify({"error": "Sessão não encontrada."}), 404

        # Enviar comando para o GDB
        gdb_instance = session_data["gdb_instance"]
        resp_status, output = gdb_instance.send_command(f"clear *{breakpoint}")
        
        if resp_status == GDBStatus.SUCCESS:
            return jsonify({"status": "success", "breakpoints": session_data["data"]["breakpoints"], "output": output})
        else:
            return jsonify({"status": "error", "output": output})  
if __name__ == "__main__":
    app.run(debug=True)
