from flask import Blueprint, request, session, jsonify, flash, send_from_directory
import json
import os
import time
from datetime import datetime, timedelta

atestados_bp = Blueprint("atestados", __name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

atestados_FILE_PATH = os.path.join(BASE_DIR+"\\JSON\\", 'atestados.json')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
JSON_FILE = os.path.join(BASE_DIR+"\\JSON\\", 'uploads.json')
USERS_FILE = os.path.join(BASE_DIR+"\\JSON\\", 'users.json')

if not os.path.exists(BASE_DIR+"/JSON/"):
    os.makedirs(BASE_DIR+"/JSON/")  # Cria a pasta se ela não existir
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)  # Cria a pasta se ela não existir
if not os.path.exists(JSON_FILE):
    with open(JSON_FILE, 'w') as f:
        json.dump([], f)  # Cria uma lista vazia no JSON


ALLOWED_EXTENSIONS = {'pdf'}  # Definição das extensões permitidas

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_to_json(filename, file_path, ra, duration, filetype):
    if os.path.exists(JSON_FILE) and os.path.getsize(JSON_FILE) > 0:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)  # Carrega os dados existentes
    else:
        data = []
        with open(JSON_FILE, 'w') as f:
            json.dump([], f)  # Cria uma lista vazia no JSON

    # Adiciona um novo registro com informações do usuário
    data.append({
        "filename": filename,
        "uploaded_by": ra,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "duration": int(duration),
        "status": 'undefined',
        "filetype": filetype
    })
    data.extend
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)  # Salva os dados atualizados

def is_duplicate(filename, user):
    if os.path.exists(JSON_FILE) and os.path.getsize(JSON_FILE) > 0:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return any(entry['filename'] == filename and entry['uploaded_by'] == user for entry in data)
    else:
        with open(JSON_FILE, 'w') as f:
            json.dump([], f)  # Cria uma lista vazia no JSON

def checkValidate(validation, filename):
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

        entry_updated = False
        for entry in data:
            if entry['filename'] == filename:
                if validation == 'accept':
                    entry['status'] = 'accepted'
                elif validation == 'deny':
                    entry['status'] = 'denied'
                entry_updated = True
                break
    
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        if entry_updated:
            json.dump(data, f)
            return f"Entry {filename} updated successfuly!", 201
        else:
            return f"Entry {filename} not updated", 400
def get_user_dict():
    if os.path.exists(USERS_FILE) and os.path.getsize(USERS_FILE) > 0:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            users = json.load(f)
        # Cria um dicionário {ra: nome}
        return {str(user['ra']): user['nome'] for user in users}
    return {}


@atestados_bp.route('/validate/', methods=['POST'])
def validate_atestado():
    data = request.get_json()
    filename = data.get("filename")
    validation = data.get("validation")  # 'accept' ou 'deny'

    if not filename or validation not in ['accept', 'deny']:
        return jsonify({"message": "Parâmetros inválidos"}), 400

    msg, status = checkValidate(validation, filename)
    flash(f"Atestado {'aprovado' if validation == 'accept' else 'reprovado'} com sucesso!", "success") if status == 201 else flash(f"Erro ao realizar ação: {msg}", "danger")
    return jsonify({"message": msg}), status

@atestados_bp.route('/upload/', methods=['POST'])
def upload_file():
    if 'file' not in request.files:  # Verifica se o arquivo foi recebido
        return "Nenhum arquivo enviado!", 400

    file = request.files['file']  # Obtém o arquivo do formulário
    if file.filename == '':  # Verifica se o usuário selecionou um arquivo
        return "Nenhum arquivo selecionado!", 400
    
    if not allowed_file(file.filename):  # Verifica a extensão
        return "Apenas arquivos PDF são permitidos!", 400
    
    if  not request.values.get('duration'): # verifica se a duração foi recebida
        return "duração não recebida", 400
    
    if not request.values.get('filetype') or request.values.get('filetype') == 'undefined':
        return "Tipo não especificado!", 400
    
    filetype = request.values.get('filetype')
    duration = request.values.get('duration') # Salva a duração
    
    if duration == 0: # Verifica se a duração é igual a zero
        return "A duração não pode ser zero", 400
    
    # Obtém o usuário logado
    user = session.get("RA")
    if not user:
        return "Usuário não autenticado!", 403
    
    # Evitar sobrescrever e gerar nome único
    timestamped_filename = f"{int(time.time())}_{file.filename}"
    file_path = os.path.join(UPLOAD_FOLDER, timestamped_filename)
    

    # if is_duplicate(file.filename, user):
    #     return "Você já enviou esse arquivo anteriormente!", 400

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)  
    file.save(file_path)  # Salva o arquivo na pasta

    # Salva os detalhes do arquivo no JSON, incluindo o usuário logado
    save_to_json(file.filename, file_path, user, duration, filetype)
    flash(f"Documento {file.filename} enviado com sucesso!", "success")
    return jsonify({"message": f"Documento {file.filename} enviado com sucesso!"}), 201


@atestados_bp.route('/lista/', methods=['GET'])
def recuperar_atestados():
    # Carrega os dados
    if not os.path.exists(JSON_FILE):
        return jsonify([]), 200
    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            atestados = json.load(f)

        user_dict = get_user_dict()

        # Adiciona campos necessários para o frontend
        for atestado in atestados:
            atestado['name'] = atestado['filename']
            atestado['date'] = atestado['timestamp']
            atestado['file_url'] = f"/atestado/uploads/{atestado['filename']}"
            atestado['username'] = user_dict.get(str(atestado.get('uploaded_by')), atestado.get('uploaded_by'))

        return jsonify(atestados), 200

    except json.JSONDecodeError:
        return jsonify([]), 500
    except Exception as e:
        return jsonify({"erro": f"Erro interno do servidor: {str(e)}"}), 500
    
@atestados_bp.route('/lista_aluno/<ra>', methods=['GET'])
def recuperar_atestados_aluno(ra):
    # Carrega os dados
    if not os.path.exists(JSON_FILE):
        return jsonify([]), 200
    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            atestados = json.load(f)

        user_dict = get_user_dict()

        atestados_aluno = [a for a in atestados if str(a.get("uploaded_by")) == str(ra)]
        # Adiciona campos necessários para o frontend
        for atestado in atestados_aluno:
            atestado['name'] = atestado['filename']
            atestado['date'] = atestado['timestamp']
            atestado['file_url'] = f"/atestado/uploads/{atestado['filename']}"
            atestado['username'] = user_dict.get(str(ra), ra)

        return jsonify(atestados_aluno), 200

    except json.JSONDecodeError:
        return jsonify([]), 500
    except Exception as e:
        return jsonify({"erro": f"Erro interno do servidor: {str(e)}"}), 500
    
    
# Rota para servir arquivos da pasta uploads
@atestados_bp.route('/uploads/<filename>', methods=['GET'])
def serve_uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)