# launcher.py
import time
import sys
import os
import requests
import subprocess
import re

# --- Configuração do Lançador ---
# ATENÇÃO: Substitua 'localhost' pelo IP do Servidor Principal
SERVER_IP = "147.185.221.22"
SERVER_URL = f"http://{SERVER_IP}:40943"
WORKER_FILENAME = "worker.py"
EXIT_CODE_UPDATE_REQUIRED = 10
# -----------------------------

def get_server_config():
    """Busca a configuração do servidor."""
    try:
        response = requests.get(f"{SERVER_URL}/config", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"[Launcher] ERRO: Não foi possível obter configuração do servidor. Tentando novamente em 30s. Erro: {e}")
        return None

def get_local_worker_version():
    """Lê a versão diretamente do arquivo worker.py sem importá-lo."""
    if not os.path.exists(WORKER_FILENAME):
        return 0 # Se não existe, a versão é 0 para forçar o download inicial.
    
    try:
        with open(WORKER_FILENAME, 'r', encoding='utf-8') as f:
            content = f.read()
            # Usa expressão regular para encontrar a linha da versão
            match = re.search(r"^CURRENT_WORKER_VERSION\s*=\s*(\d+)", content, re.MULTILINE)
            if match:
                return int(match.group(1))
            return 0 # Se não encontrar a linha, força o download.
    except Exception as e:
        print(f"[Launcher] ERRO: Não foi possível ler a versão do {WORKER_FILENAME}. Erro: {e}")
        return 0

def download_new_worker(current_version, required_version):
    """Baixa o novo script do worker do servidor."""
    print(f"[Launcher] Atualização necessária. Versão local: {current_version}, Versão do servidor: {required_version}")
    print(f"[Launcher] Baixando a nova versão de {WORKER_FILENAME}...")
    try:
        response = requests.get(f"{SERVER_URL}/get_worker_script", timeout=60)
        response.raise_for_status()
        
        with open(WORKER_FILENAME, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        print("[Launcher] Download concluído com sucesso.")
        return True
    except requests.RequestException as e:
        print(f"[Launcher] ERRO: Falha ao baixar o novo worker. Tentando novamente em 30s. Erro: {e}")
        return False


def run_worker():
    """Inicia e monitora o processo do worker."""
    process = None
    try:
        print(f"[Launcher] Iniciando o processo {WORKER_FILENAME}...")
        # Usamos sys.executable para garantir que estamos usando o mesmo interpretador python
        process = subprocess.Popen([sys.executable, WORKER_FILENAME])
        return_code = process.wait() # Espera o processo do worker terminar
        print(f"[Launcher] Processo worker finalizado com código de saída: {return_code}")
        return return_code
    except KeyboardInterrupt:
        print("[Launcher] Interrupção de teclado recebida. Encerrando o worker...")
        if process:
            process.terminate()
        raise # Re-levanta a exceção para encerrar o lançador
    except Exception as e:
        print(f"[Launcher] ERRO ao executar o worker: {e}")
        return 1 # Código de erro genérico

def main():
    """Loop principal que gerencia a versão e a execução do worker."""
    while True:
        print("\n" + "="*50)
        print(f"[Launcher] {time.strftime('%d/%m/%Y %H:%M:%S')} - Iniciando ciclo de verificação...")
        
        config = get_server_config()
        if not config:
            time.sleep(30)
            continue
            
        required_version = config.get("MINIMUM_WORKER_VERSION", 1)
        local_version = get_local_worker_version()
        
        if local_version < required_version:
            if not download_new_worker(local_version, required_version):
                time.sleep(30)
                continue
        else:
            print(f"[Launcher] Worker local (v{local_version}) está atualizado.")

        # Inicia o worker e espera ele terminar
        exit_code = run_worker()
        
        # Se o worker pediu uma atualização, o loop recomeça imediatamente.
        # Senão, espera um pouco para evitar loops de crash muito rápidos.
        if exit_code != EXIT_CODE_UPDATE_REQUIRED:
            print("[Launcher] O worker parou por uma razão inesperada. Reiniciando em 15 segundos...")
            time.sleep(15)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[Launcher] Lançador encerrado pelo usuário.")