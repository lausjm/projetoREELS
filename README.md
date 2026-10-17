# Gerador de vídeos curtos (GTA 6)

Cria vídeos verticais (1080x1920) no estilo meme: fundo preto, título no topo, vídeo no meio e legendas automáticas embaixo.

## Instalação (uma vez só)

1. Python 3.10 ou mais novo: https://www.python.org
2. ffmpeg:
   ```
   winget install Gyan.FFmpeg
   ```
   Depois **feche e abra o terminal** de novo.
3. Bibliotecas Python:
   ```
   pip install -r requirements.txt
   ```

## Como usar

```
python gerar.py video.mp4 "Você encontrou a página que fala tudo sobre GTA 6"
```

Também funciona com um link no lugar do arquivo. Use apenas vídeos que são seus ou que você tem permissão para usar.

O vídeo final vai para a pasta `prontos/`, junto com a legenda em `.srt`.
Na primeira execução, o modelo do Whisper é baixado (cerca de 500 MB para o `small`).

## Personalizar

Abra o `gerar.py` e altere o bloco **CONFIGURAÇÕES** no topo: fonte, cores, tamanhos e modelo do Whisper (`tiny` é mais rápido, `medium` é mais preciso).
