# Vitrae Window 🪟

Projeto focado na interface e comunicação de hardware para gestão de janelas e leitura de sensores de presença/radar.

## 🧠 Arquitetura e Funcionalidades Implementadas

### 1. Sistema Principal (Core)
O script central responsável pela coordenação e execução do sistema, processando dados e integrando as lógicas de leitura.
*Ficheiro:* `Main.py`

### 2. Interface Gráfica (GUI) do Radar
Uma interface desenvolvida para visualizar de forma clara e em tempo real a atividade e os dados captados pelos sensores/radares associados à janela.
*Ficheiro:* `radar_gui.py`

### 3. Integração e Teste de Hardware
Scripts dedicados para simular, testar e validar o correto funcionamento da comunicação com o radar de presença ou outros sensores envolvidos.
*Ficheiro:* `teste_radar.py`

### 4. Configuração e Identificação
Gestão de dependências necessárias à execução e identificação única da instância ou dispositivo Vitrae.
*Ficheiros:* `requirements.txt` (dependências), `vitrae_id.txt` (identificador único, ex: VITRAE-01006).

## 🛠️ Tecnologias e Ferramentas
* **Linguagem principal:** Python
* **Hardware/Sensores:** Integração com dispositivos de radar para deteção/movimento.
* **Dependências Mapeadas:** Configuradas através do `requirements.txt`.# VitraeWindow
