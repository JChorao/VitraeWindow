"""Templates HTML para as páginas do servidor"""

SUCCESS_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Spotify Conectado</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #1DB954 0%, #191414 100%);
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            color: white;
        }
        .container {
            text-align: center;
            padding: 40px;
            background: rgba(255,255,255,0.1);
            border-radius: 20px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }
        h1 { 
            font-size: 2.5em; 
            margin: 0 0 20px 0;
            font-weight: 700;
        }
        p { 
            font-size: 1.2em; 
            opacity: 0.9;
            line-height: 1.6;
        }
        .checkmark {
            font-size: 5em;
            animation: bounce 0.6s ease;
            display: inline-block;
        }
        @keyframes bounce {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.3); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="checkmark">✓</div>
        <h1>Conectado!</h1>
        <p>O teu Spotify está agora ligado ao Dashboard</p>
        <p style="font-size: 0.9em; margin-top: 30px; opacity: 0.7;">
            Podes fechar esta janela
        </p>
    </div>
</body>
</html>
"""

ERROR_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Erro</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #E53935 0%, #B71C1C 100%);
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            color: white;
        }
        .container {
            text-align: center;
            padding: 40px;
            background: rgba(255,255,255,0.1);
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }
        h1 { 
            font-size: 2.5em; 
            margin: 0 0 20px 0;
        }
        p { 
            font-size: 1.2em; 
            opacity: 0.9;
        }
        .error-icon {
            font-size: 5em;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="error-icon">⚠️</div>
        <h1>Erro na Autenticação</h1>
        <p>Tenta scanear o QR code novamente</p>
    </div>
</body>
</html>
"""