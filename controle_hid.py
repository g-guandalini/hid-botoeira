import time
import json
from pynput.keyboard import Controller, Key
import pywinusb.hid as hid
import traceback

# --- CONFIGURAÇÕES ---
CONFIG_FILE_PATH = 'config.json'
keyboard_controller = Controller()

# Global variable to store the very first report, assumed to be the idle state
initial_report_bytes = None

# --- Carrega a configuração do arquivo JSON ---
def load_config(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
        for mapping in config_data['MAPPINGS']:
            # Garante que 'idle_value', 'press_value', 'deactivation_threshold' são inteiros se existirem
            if 'idle_value' in mapping:
                mapping['idle_value'] = int(mapping['idle_value'])
            if 'press_value' in mapping:
                mapping['press_value'] = int(mapping['press_value'])
            if 'deactivation_threshold' in mapping:
                mapping['deactivation_threshold'] = int(mapping['deactivation_threshold'])
            
            # --- Tenta converter a string da chave para um objeto pynput.keyboard.Key ---
            key_str = mapping['key']
            # Verifica se a string é um nome de tecla especial reconhecido pelo pynput (ex: 'f5', 'space', 'enter')
            if isinstance(key_str, str) and len(key_str) > 1 and hasattr(Key, key_str): 
                mapping['key'] = getattr(Key, key_str)
            # Caso contrário, mantém como string (pynput Controller.press() aceita 'a', '1', etc.)
        return config_data

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
except ValueError as ve:
    print(f"Erro de validação no config.json: {ve}")
    input("Pressione Enter para fechar a janela...")
    exit(1)
except Exception as e:
    print(f"Erro ao carregar o arquivo de configuração: {e}")
    input("Pressione Enter para fechar a janela...")
    exit(1)

TARGET_VENDOR_ID = int(app_config['TARGET_VENDOR_ID'], 16)
TARGET_PRODUCT_ID = int(app_config['TARGET_PRODUCT_ID'], 16)
MAPPINGS = app_config['MAPPINGS']

# --- Encontra o Dispositivo HID ---
device = None
devices = hid.find_all_hid_devices()

for d in devices:
    try:
        if d.vendor_id == TARGET_VENDOR_ID and d.product_id == TARGET_PRODUCT_ID:
            device = d
            break
    except hid.HIDError:
        continue
    except Exception:
        pass # Ignora erros em dispositivos que podem não ser relevantes ou estar mal-formados

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
# Dicionário para manter o estado das teclas virtuais pressionadas
pressed_virtual_keys = {}

# --- Handler de Dados HID ---
def hid_handler(data):
    global last_report, pressed_virtual_keys, initial_report_bytes

    current_report = tuple(data)

    if last_report is None:
        last_report = current_report
        initial_report_bytes = current_report # Armazena o primeiro report como o estado inicial/ocioso
        print(f"[{time.strftime('%H:%M:%S')}] Primeiro report inicializado.")
        return

    # Dicionário para rastrear bytes que mudaram e se foram 'tratados' por um mapeamento
    byte_changes_info = {}
    if last_report is not None:
        max_len = max(len(current_report), len(last_report))
        for i in range(max_len):
            current_val = current_report[i] if i < len(current_report) else -1 
            last_val = last_report[i] if i < len(last_report) else -1
            if current_val != last_val:
                byte_changes_info[i] = {'last_val': last_val, 'current_val': current_val, 'handled': False}
    
    # Processa os mapeamentos configurados
    for mapping in MAPPINGS:
        key_to_emulate = mapping['key']
        map_type = mapping.get('type', 'digital') # Default é 'digital'

        was_previously_pressed = key_to_emulate in pressed_virtual_keys
        
        # Determine current state based on mapping type
        is_currently_active = False

        if map_type == 'compound_digital':
            is_currently_active_check = True
            for condition in mapping['conditions_to_be_active']:
                idx = condition['byte_index']
                expected_value = condition['value_is']
                if idx >= len(current_report) or current_report[idx] != expected_value:
                    is_currently_active_check = False
                    break
            is_currently_active = is_currently_active_check

            # Se ativado ou desativado, marca os bytes relevantes como tratados
            if is_currently_active != was_previously_pressed: # Apenas se o estado mudou
                for condition in mapping['conditions_to_be_active']:
                    idx = condition['byte_index']
                    if idx in byte_changes_info:
                        byte_changes_info[idx]['handled'] = True

        elif map_type == 'analog':
            idx = mapping['byte_index']
            idle_value = mapping['idle_value']
            activation_threshold = mapping['press_value']
            
            if idx >= len(current_report): continue
            cur_byte_val = current_report[idx]

            activates_on_increase = idle_value < activation_threshold
            if activates_on_increase: 
                is_currently_active = cur_byte_val > activation_threshold
            else: 
                is_currently_active = cur_byte_val < activation_threshold

            if is_currently_active != was_previously_pressed: # Apenas se o estado mudou
                if idx in byte_changes_info:
                    byte_changes_info[idx]['handled'] = True

        else: # map_type == 'digital'
            idx = mapping['byte_index']
            # idle_value = mapping['idle_value'] # Não é diretamente usado aqui para 'is_currently_active'
            activation_value = mapping['press_value']

            if idx >= len(current_report): continue
            cur_byte_val = current_report[idx]

            # Simplified active check for digital
            is_currently_active = (cur_byte_val == activation_value)
            
            if is_currently_active != was_previously_pressed: # Apenas se o estado mudou
                if idx in byte_changes_info:
                    byte_changes_info[idx]['handled'] = True

        # --- Lógica de Pressionamento/Soltura de Teclas ---
        if is_currently_active and not was_previously_pressed:
            try:
                keyboard_controller.press(key_to_emulate)
                pressed_virtual_keys[key_to_emulate] = True
                print(f"Apertou {mapping['name']} e o resultado é: {key_to_emulate}")
            except ValueError:
                print(f"AVISO: Tecla '{key_to_emulate}' para '{mapping['name']}' não reconhecida pela pynput.")
        
        elif not is_currently_active and was_previously_pressed:
            try:
                keyboard_controller.release(key_to_emulate)
                del pressed_virtual_keys[key_to_emulate]
                # print(f"Liberou {mapping['name']} (tecla {key_to_emulate})") # Não imprimir release por padrão
            except ValueError:
                print(f"AVISO: Tecla '{key_to_emulate}' para '{mapping['name']}' não reconhecida pela pynput.")

    # --- Relatar bytes não mapeados que mudaram ---
    for idx, info in byte_changes_info.items():
        if not info['handled']:
            # Loga APENAS se o byte mudou DO seu estado inicial/ocioso PARA um estado diferente.
            # Isso filtra as "solturas" (voltar para o estado inicial) e outras mudanças não-ociosas.
            if initial_report_bytes is not None and \
               idx < len(initial_report_bytes) and \
               info['last_val'] == initial_report_bytes[idx] and \
               info['current_val'] != initial_report_bytes[idx]:
                print(f"Botão não mapeado: byte_index: {idx}, idle_value: {info['last_val']}, press_value: {info['current_val']}")

    last_report = current_report

device.set_raw_data_handler(hid_handler)

print("\n--- Controlador HID Iniciado ---")
print("O controle agora está ativo e emulará as teclas configuradas.")
print("Verifique o arquivo 'config.json' para seus mapeamentos.")
print("Para encerrar o programa, pressione Ctrl+C no console.")
print("-" * 50)


try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nEncerrando por interrupção do teclado (Ctrl+C)...")
except Exception as e:
    print(f"\n--- ERRO CRÍTICO INESPERADO ---")
    print(f"Ocorreu um erro: {e}")
    traceback.print_exc()
finally:
    print("Fechando o dispositivo...")
    if device:
        device.close()
    # Garante que todas as teclas virtualmente pressionadas sejam liberadas ao sair
    for key in pressed_virtual_keys:
        try:
            keyboard_controller.release(key)
        except ValueError:
            pass # Ignora se a tecla já não for reconhecida
    print("Recursos liberados.")
    input("Pressione Enter para fechar a janela...")