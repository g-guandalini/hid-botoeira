import time
import json
import threading
from pynput.keyboard import Controller, Key, Listener
import pywinusb.hid as hid
import traceback # Importar para imprimir a pilha de erros

# --- CONFIG ---
CONFIG_FILE_PATH = 'config.json'

keyboard_controller = Controller()

# --- Load config ---
def load_config(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Carrega a configuração do aplicativo
try:
    app_config = load_config(CONFIG_FILE_PATH)
except FileNotFoundError:
    print(f"Erro: O arquivo de configuração '{CONFIG_FILE_PATH}' não foi encontrado.")
    input("Pressione Enter para fechar a janela...")
    exit(1)
except json.JSONDecodeError:
    print(f"Erro: O arquivo '{CONFIG_FILE_PATH}' contém JSON inválido. Verifique a sintaxe.")
    input("Pressione Enter para fechar a janela...")
    exit(1)
except Exception as e:
    print(f"Erro ao carregar o arquivo de configuração: {e}")
    input("Pressione Enter para fechar a janela...")
    exit(1)


TARGET_VENDOR_ID = int(app_config['TARGET_VENDOR_ID'], 16)
TARGET_PRODUCT_ID = int(app_config['TARGET_PRODUCT_ID'], 16)

BUTTON_CONFIGS = []
for byte_config in app_config['BUTTON_CONFIGS']:
    BUTTON_CONFIGS.append({
        "byte_index": byte_config['byte_index'],
        "idle_value": byte_config['idle_value'],
        "actions": {int(k): v for k, v in byte_config['actions'].items()}
    })

# Garante que as chaves de desbloqueio sejam carregadas corretamente
UNLOCK_KEYS = set()
for k_name in app_config['UNLOCK_KEY_NAMES']:
    try:
        UNLOCK_KEYS.add(getattr(Key, k_name))
    except AttributeError:
        print(f"Aviso: Tecla de desbloquequeio '{k_name}' não reconhecida pela pynput. Verifique o 'UNLOCK_KEY_NAMES' no config.json.")

if not UNLOCK_KEYS:
    print("Aviso: Nenhuma tecla de desbloqueio válida configurada. O desbloqueio manual não funcionará.")


# --- Lock logic ---
buttons_locked = False
current_pressed_keys = set()

def on_key_press(key):
    global buttons_locked
    current_pressed_keys.add(key)
    if all(k in current_pressed_keys for k in UNLOCK_KEYS) and UNLOCK_KEYS:
        if buttons_locked:
            buttons_locked = False
            print(f"[{time.strftime('%H:%M:%S')}] Botões HID DESBLOQUEADOS")

def on_key_release(key):
    if key in current_pressed_keys:
        current_pressed_keys.remove(key)

keyboard_listener = Listener(on_press=on_key_press, on_release=on_key_release)
keyboard_listener.start()

# --- Find HID Device ---
devices = hid.find_all_hid_devices()
device = None

for d in devices:
    try: # Adiciona try-except para lidar com dispositivos que podem não ter vendor_id/product_id
        if d.vendor_id == TARGET_VENDOR_ID and d.product_id == TARGET_PRODUCT_ID:
            device = d
            break
    except hid.HIDError: # Pode ocorrer se o dispositivo não estiver pronto ou não tiver os IDs
        continue

if not device:
    print(f"Controle HID não encontrado com VENDOR_ID={app_config['TARGET_VENDOR_ID']} e PRODUCT_ID={app_config['TARGET_PRODUCT_ID']}.")
    print("Verifique se o controle está conectado e se os IDs no config.json estão corretos.")
    input("Pressione Enter para fechar a janela...")
    exit(1)

print(f"Dispositivo aberto: {device.product_name} (Vendor ID: {hex(device.vendor_id)}, Product ID: {hex(device.product_id)})")
try:
    device.open()
except Exception as e:
    print(f"Erro ao abrir o dispositivo HID: {e}")
    print("Verifique se o dispositivo não está sendo usado por outro programa ou se as permissões estão corretas.")
    input("Pressione Enter para fechar a janela...")
    exit(1)


last_report = None

# --- HID handler ---
def hid_handler(data):
    global last_report, buttons_locked

    current_report = tuple(data)

    if last_report is None:
        last_report = current_report
        print(f"[{time.strftime('%H:%M:%S')}] Primeiro report inicializado")
        # ADIÇÃO PARA DEBUG: Imprime o report inicial para referência
        print(f"  DEBUG: Report inicial (tupla): {current_report}")
        return

    if current_report == last_report:
        return

    # ADIÇÃO PARA DEBUG: Imprime o report sempre que houver uma mudança
    print(f"\n--- [{time.strftime('%H:%M:%S')}] MUDANÇA NO REPORT ---")
    print(f"  DEBUG: Report ANTERIOR (tupla): {last_report}")
    print(f"  DEBUG: Report ATUAL (tupla): {current_report}")

    # ADIÇÃO PARA DEBUG: Destaca as mudanças byte a byte para facilitar a visualização
    # Garante que não tente acessar índices fora do range
    max_len = max(len(current_report), len(last_report))
    for i in range(max_len):
        current_val = current_report[i] if i < len(current_report) else "N/A"
        last_val = last_report[i] if i < len(last_report) else "N/A"

        if current_val != last_val:
            print(f"  DEBUG: Byte {i}: ANTERIOR={last_val}, ATUAL={current_val}")


    button_state_changed = False

    for config in BUTTON_CONFIGS:
        idx = config['byte_index']
        idle = config['idle_value']
        actions = config['actions']

        # Verifica se o byte_index está dentro do report atual
        if idx >= len(current_report) or idx >= len(last_report):
            # print(f"Aviso: byte_index {idx} fora do alcance do report para esta configuração.")
            continue

        cur = current_report[idx]
        prev = last_report[idx]

        # Verifica o pressionamento do botão
        if prev == idle and str(cur) in actions: # Convertemos cur para string para match com chaves do JSON
            button_state_changed = True
            action = actions[str(cur)] # Usamos str(cur) aqui também

            if not buttons_locked:
                print(f"[{time.strftime('%H:%M:%S')}] {action['name']} PRESSIONADO")
                keyboard_controller.press(action['key'])
                buttons_locked = True
                print("Botões HID BLOQUEADOS")
            else:
                print(f"[{action['name']}] IGNORADO (bloqueado)")

        # Verifica o soltar do botão
        elif cur == idle and str(prev) in actions: # Convertemos prev para string para match com chaves do JSON
            button_state_changed = True
            action = actions[str(prev)] # Usamos str(prev) aqui também
            print(f"[{time.strftime('%H:%M:%S')}] {action['name']} SOLTO")
            keyboard_controller.release(action['key'])

    last_report = current_report

device.set_raw_data_handler(hid_handler)

print("\nControlador HID iniciado.")
print(f"Pressione {list(str(k) for k in UNLOCK_KEYS)} para desbloquear a emulação do controle.")
print("Para encerrar o programa, pressione Ctrl+C no console.")
print("-" * 50)


try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nEncerrando por interrupção do teclado (Ctrl+C)...")
except Exception as e: # Captura qualquer outra exceção não tratada
    print(f"\n--- ERRO CRÍTICO INESPERADO ---")
    print(f"Ocorreu um erro: {e}")
    traceback.print_exc() # Imprime a pilha de erros completa
finally:
    print("Fechando o dispositivo e parando o listener de teclado...")
    if device:
        device.close()
    if keyboard_listener.is_alive(): # Verifica se o thread do listener ainda está ativo
        keyboard_listener.stop()
        keyboard_listener.join() # Aguarda o thread terminar
    print("Recursos liberados.")
    # Adiciona input para manter a janela aberta no Windows/executáveis
    input("Pressione Enter para fechar a janela...")
