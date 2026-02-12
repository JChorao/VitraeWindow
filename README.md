# VitraeWindow
O VitraeWindow, faz parte do projeto VitraeView, é um dashboard interativo desenvolvido em Python utilizando a biblioteca tkinter. O projeto foi concebido para funcionar como uma central de informações visual, ideal para ecrãs fixos ou dispositivos como o Raspberry Pi.

🚀 Funcionalidades Atuais
O dashboard organiza-se numa grelha 3x3 com os seguintes widgets:

Relógio Digital: Exibe a hora atual sincronizada com a API WorldTimeAPI (fuso horário Europe/Lisbon), atualizando-se a cada segundo.

Meteorologia: Apresenta a temperatura atual para a região de Castelo Branco (coordenadas 39.82, -7.49) através da API Open-Meteo.

Spotify Integration: Widget com autenticação via QR Code que exibe a música e o artista em reprodução no momento.

Google Calendar: Placeholder preparado para integração futura de eventos do calendário.

Botão de Emergência: Um botão de alerta visual ("ALERTA GÁS") para situações críticas.

🛠️ Tecnologias Utilizadas
Linguagem: Python 3.13

Interface Gráfica: tkinter

Servidor Web: Flask (utilizado para o fluxo de autenticação OAuth2 do Spotify).

Segurança: pyOpenSSL para geração de certificados SSL autoassinados necessários para a comunicação HTTPS.

Bibliotecas Principais:

spotipy: Para integração com a API do Spotify.

Pillow & qrcode: Para geração e visualização do QR Code de login.

requests: Para consumo de APIs externas.

⚙️ Configuração e Instalação
1. Requisitos Prévios
Certifique-se de que tem o Python instalado e as dependências necessárias:

Bash
pip install -r requirements.txt
As dependências incluem: flask, flask-cors, pyOpenSSL, spotipy, Pillow e qrcode.

2. Configuração do Spotify
Para que o widget do Spotify funcione, é necessário:

Criar uma aplicação no Spotify Developer Dashboard.

Configurar as credenciais (CLIENT_ID e CLIENT_SECRET) no ficheiro widgets/spotify.py.

Adicionar a Redirect URI no painel do Spotify seguindo o formato: https://<O_TEU_IP_LOCAL>:8888/callback.

🖥️ Como Executar
Execute o ficheiro principal para iniciar o dashboard:

Bash
python Main.py
O sistema detetará automaticamente o seu IP local para configurar o servidor de autenticação.

Nota sobre o Spotify: Ao iniciar pela primeira vez, será exibido um QR Code. Digitalize-o com o telemóvel, aceite o certificado de segurança (devido ao HTTPS autoassinado) e autorize a aplicação para que as informações de reprodução comecem a aparecer.

🧹 Manutenção
O projeto inclui uma função de limpeza automática (cleanup_app_data) que remove ficheiros de cache e certificados temporários ao fechar a aplicação, garantindo que os dados de sessão não ficam corrompidos.