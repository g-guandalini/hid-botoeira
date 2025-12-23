# Projeto: Mapeador de Controle HID para Teclado

Este projeto consiste em um script Python que permite mapear botões de um controle Human Interface Device (HID), como um controle de Xbox, para teclas do teclado. O script `controle.py` opera em segundo plano, monitorando as entradas do controle e simulando os pressionamentos de tecla correspondentes.

Para um controle preciso da emulação, o sistema inclui um mecanismo de bloqueio/desbloqueio que pode ser acionado por uma combinação específica de teclas do teclado.

## Arquivos do Projeto

*   `controle.py`: O script principal em Python. Ele interage com o dispositivo HID, processa os inputs e simula as teclas do teclado. **Esta versão do `controle.py` já contém funcionalidades de depuração para ajudar a identificar os bytes dos botões e um tratamento de erros aprimorado para manter a janela do console aberta em caso de falha.**
*   `config.json`: O arquivo de configuração onde você define qual controle HID será monitorado, como seus botões são mapeados para as teclas do teclado e quais teclas do teclado controlam o bloqueio/desbloqueio da emulação.

---

## Utilização do Projeto

Esta seção detalha como configurar o mapeamento dos botões do seu controle e como descobrir os valores necessários para essa configuração.

### 1. Configuração do `config.json`

O arquivo `config.json` é a base da personalização do seu mapeador. Ele especifica o dispositivo e o mapeamento desejado.

```json
{
    "TARGET_VENDOR_ID": "0x0079",
    "TARGET_PRODUCT_ID": "0x0006",
    "BUTTON_CONFIGS": [
      {
        "byte_index": 5,
        "idle_value": 15,
        "actions": {
          "31": {"name": "Botão A (Byte 5)", "key": "1"},
          "47": {"name": "Botão B (Byte 5)", "key": "2"},
          "79": {"name": "Botão C (Byte 5)", "key": "3"},
          "143": {"name": "Botão D (Byte 5)", "key": "4"},
          "4": {"name": "Botão Seta Baixo (Byte 5)", "key": "5"}
        }
      },
      {
        "byte_index": 0,
        "idle_value": 127,
        "actions": {
          "0": {"name": "Botão Esquerdo (Byte 0)", "key": "esquerda"},
          "255": {"name": "Botão Direito (Byte 0)", "key": "direita"}
        }
      },
      {
        "byte_index": 1,
        "idle_value": 127,
        "actions": {
          "0": {"name": "Botão Cima (Byte 1)", "key": "cima"},
          "255": {"name": "Botão Baixo (Byte 1)", "key": "baixo"}
        }
      }
    ],
    "UNLOCK_KEY_NAMES": [
      "ctrl_l",
      "shift_l",
      "delete"
    ]
}
```

## Detalhamento das Seções do `config.json`:

### `TARGET_VENDOR_ID` e `TARGET_PRODUCT_ID`:

*   **Função**: São os identificadores únicos (Vendor ID e Product ID) do seu dispositivo HID. O script utiliza esses valores para localizar e estabelecer uma conexão com o controle correto.
*   **Formato**: Devem ser fornecidos como strings hexadecimais (por exemplo, `"0x0079"`).
*   **Como Encontrar (no Windows)**:
    1.  Abra o "Gerenciador de Dispositivos" (pesquise no menu Iniciar).
    2.  Localize seu controle (geralmente sob "Dispositivos de Interface Humana" ou "Controladores de som, vídeo e jogo").
    3.  Clique com o botão direito no dispositivo desejado, selecione "Propriedades" e, em seguida, a aba "Detalhes".
    4.  No menu suspenso "Propriedade", selecione "IDs de Hardware".
    5.  Você verá uma ou mais strings similares a `HID\VID_045E&PID_028E&MI_03&COL01`. O valor após `VID_` é o **Vendor ID**, e o valor após `PID_` é o **Product ID**.

### `BUTTON_CONFIGS`:

*   **Função**: Uma lista de objetos, onde cada objeto define como um byte específico do pacote de dados (o "report HID") enviado pelo controle deve ser interpretado.
*   **Componentes de Cada Objeto**:
    *   **`byte_index`**: O índice (posição) do byte dentro da tupla de dados que o controle envia. O índice começa do 0.
    *   **`idle_value`**: O valor que o byte no `byte_index` especificado assume quando **nenhum** dos botões associados a ele está sendo pressionado (ou seja, o estado de repouso).
    *   **`actions`**: Um dicionário que mapeia os valores que o `byte_index` pode assumir para ações específicas do teclado.
        *   **Chave (ex: `"31"`)**: O valor **decimal** que o byte terá quando um botão específico for pressionado. **É crucial que as chaves do dicionário `actions` no `config.json` sejam strings que representam os valores decimais dos bytes (ex: `"31"` em vez de `31`). O script internamente converterá para inteiro para comparação.**
        *   **Valor (objeto `{"name": "...", "key": "..."}`)**:
            *   `"name"`: Um nome descritivo para o botão (ex: `"Botão A (Byte 5)"`). Este nome é usado nas mensagens de log no console.
            *   `"key"`: A tecla que será simulada no teclado (ex: `"1"`, `"esquerda"`, `"enter"`). Para teclas especiais (como Ctrl, Shift, Alt, setas, etc.), utilize os nomes dos atributos da classe `pynput.keyboard.Key` (ex: `"ctrl_l"` para Control Esquerdo, `"space"` para barra de espaço, `"up"` para seta para cima).

### `UNLOCK_KEY_NAMES`:

*   **Função**: Define uma combinação de teclas do teclado que, quando pressionadas simultaneamente, "desbloqueiam" a emulação de botões do controle. Isso é útil para evitar interferências no uso normal do computador quando você não está utilizando o controle para o propósito mapeado.
*   **Formato**: Uma lista de strings, onde cada string representa o nome de uma tecla do teclado.
*   **Nomes Válidos**: Devem corresponder aos nomes de atributos da classe `pynput.keyboard.Key` (ex: `"ctrl_l"` para Control Esquerdo, `"shift_l"` para Shift Esquerdo, `"delete"` para a tecla Delete).

---

## 2. Como Descobrir `byte_index`, `idle_value` e Valores de Ação (Mapeamento de Botões)

A versão atual do `controle.py` inclui saídas de depuração essenciais para este processo de descoberta dos bytes do seu controle.

1.  **Execute o `controle.py` com Python** (veja a seção "Execução do Script" abaixo).
2.  **Observe o "Report inicial"**: O script imprimirá uma tupla de bytes no console, representando o estado de repouso do controle. Exemplo: `DEBUG: Report inicial (tupla): (0, 0, 0, 0, 0, 15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)`. Anote-o como referência.
3.  **Pressione um botão não mapeado**: Pressione **apenas um** botão no seu controle que você deseja mapear. Mantenha-o pressionado por um breve momento e, em seguida, solte-o.
4.  **Analise a saída de depuração no console**: O console exibirá as mudanças byte a byte de forma clara:
    ```
    --- [HH:MM:SS] MUDANÇA NO REPORT ---
      DEBUG: Report ANTERIOR (tupla): (...)
      DEBUG: Report ATUAL (tupla):   (...)
      DEBUG: Byte X: ANTERIOR=Y, ATUAL=Z
    ```
    *   **`X`**: Será o `byte_index` do botão que você pressionou (a posição do byte que mudou).
    *   **`Y`**: O valor `ANTERIOR` (quando o botão estava solto) será o `idle_value` para esse `byte_index`.
    *   **`Z`**: O valor `ATUAL` (quando o botão foi pressionado) será a chave a ser adicionada ao dicionário `actions` para esse `byte_index`. **Lembre-se de converter `Z` para string ao adicioná-lo como chave no `config.json` (ex: `"31"`).**
5.  **Atualize o `config.json`**: Com base nos valores `X`, `Y` e `Z` que você identificou, adicione uma nova entrada (ou ajuste uma existente) dentro da lista `"BUTTON_CONFIGS"` no seu `config.json`.
6.  **Remova as linhas de depuração (Opcional)**: Após mapear todos os botões desejados, você pode remover as linhas de `print(f" DEBUG: ...")` e os blocos `print(f"\n--- [...]")` e `for i in range(...)` da função `hid_handler` no `controle.py` para um console mais limpo, ou mantê-las se for útil para futuras depurações.

---

## Execução do Script

Esta seção descreve como executar o `controle.py` em seu ambiente.

### Pré-requisitos:

*   **Python 3**: Certifique-se de ter o Python 3 instalado (versão 3.6 ou superior é recomendada). Você pode baixá-lo em {https://www.python.org/downloads/}.
*   **pip**: O gerenciador de pacotes do Python (geralmente já vem com a instalação do Python).
*   **Bibliotecas Python**: Instale as bibliotecas necessárias usando o `pip` no seu terminal:
    ```bash
    pip install pynput pywinusb
    ```
    *   **Atenção**: A biblioteca `pywinusb` é **exclusivamente para Windows**. Consequentemente, o `controle.py` em sua forma atual só funcionará em sistemas operacionais Windows. Para Linux ou macOS, a parte do código que interage com o HID (`pywinusb.hid`) precisaria ser reescrita utilizando uma biblioteca compatível com essas plataformas (ex: `hidapi` - via `pip install pyhidapi`, ou `pyusb`).

### Executando com Python no Windows:

1.  Salve os arquivos `controle.py` e `config.json` na mesma pasta.
2.  Abra o **Prompt de Comando** ou **PowerShell**. **É crucial executar o script a partir de um terminal persistente; não clique duas vezes no arquivo `.py`**, pois a janela do console fechará automaticamente se ocorrer um erro, impedindo a visualização da mensagem.
3.  Navegue até a pasta onde você salvou os arquivos. Por exemplo, se seus arquivos estão em `C:\Projetos\MapeadorControle`:
    ```bash
    cd C:\Projetos\MapeadorControle
    ```
4.  Execute o script Python:
    ```bash
    python controle.py
    ```
    *   **Tratamento de Erros e Depuração**: O script foi modificado para incluir um tratamento de erros robusto que mantém a janela do console aberta em caso de falha, permitindo que você leia a mensagem de erro e a pilha de chamadas (`traceback`). Além disso, as mensagens de `DEBUG` serão impressas para auxiliar no mapeamento de novos botões. Após a exibição de um erro ou após o encerramento normal do script, ele pedirá que você "Pressione Enter para fechar a janela...", dando tempo para análise.
    *   **Para encerrar o script manualmente**: Pressione `Ctrl+C` no console.

### Executando com Python no Linux/macOS:

*   Conforme mencionado nos pré-requisitos, o script `controle.py` *requer modificações significativas* na sua seção de interação com dispositivos HID (`pywinusb.hid`) para ser funcional em sistemas operacionais que não sejam Windows. O código fornecido atualmente **não é compatível** com Linux/macOS sem essas alterações.

---

## Compilação do Script

Esta seção explica como converter o script Python em um executável autônomo, permitindo que ele seja executado em máquinas que não possuem uma instalação Python completa. A ferramenta recomendada para isso é o `PyInstaller`.

### Pré-requisitos para Compilação:

*   Python 3 e pip (já instalados conforme os pré-requisitos de execução).
*   **PyInstaller**: Instale-o via pip:
    ```bash
    pip install pyinstaller
    ```

### Compilando para Windows:

1.  Certifique-se de que `controle.py` e `config.json` estão localizados na mesma pasta.
2.  Abra o **Prompt de Comando** ou **PowerShell** na pasta do seu projeto.
3.  Execute o PyInstaller com os seguintes parâmetros:
    ```bash
    pyinstaller --onefile --add-data "config.json;." controle.py
    ```
    *   `--onefile`: Gera um único arquivo executável (mais conveniente do que uma pasta com múltiplos arquivos).
    *   `--add-data "config.json;."`: Inclui o arquivo `config.json` junto ao executável. O `;` é o separador para Windows, e `.` indica que o arquivo deve ser colocado no diretório raiz do executável.
    *   `controle.py`: Especifica o script Python principal a ser compilado.
    *   **Para ocultar a janela do console (após a fase de depuração)**: Se você não deseja que uma janela de console preta apareça ao iniciar o executável, adicione a flag `--noconsole` (ou `--windowed`). Isso é recomendado para a versão final do seu aplicativo, mas **NÃO** durante a fase de depuração, pois você precisará ver as mensagens de log:
        ```bash
        pyinstaller --onefile --noconsole --add-data "config.json;." controle.py
        ```

4.  Após a compilação, o executável (por exemplo, `controle.exe`) será gerado e localizado dentro da pasta `dist/` que será criada no seu diretório de projeto.

### Compilando para Linux:

*   **Aviso**: Da mesma forma que na execução direta, para compilar para Linux, você *precisaria primeiro modificar o `controle.py`* para ser compatível com Linux (substituindo a parte do `pywinusb` por uma alternativa cross-platform como `pyhidapi`). O executável gerado pelo PyInstaller é específico para o sistema operacional onde a compilação foi realizada.

*   **Se o `controle.py` *tivesse* sido modificado para Linux/macOS e você estivesse compilando em um ambiente Linux**:
    1.  Abra o **Terminal** na pasta do projeto.
    2.  Execute o PyInstaller. Note que o separador para `--add-data` em sistemas baseados em Unix é diferente (`:`):
        ```bash
        pyinstaller --onefile --add-data "config.json:." controle.py
        ```
    3.  O executável resultante será encontrado na pasta `dist/`.