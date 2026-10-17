"""
gerar.py - Versão 1
Cria um vídeo vertical (1080x1920) no estilo meme para Reels/Shorts/TikTok:
fundo preto, título no topo, vídeo no meio e legendas automáticas embaixo.

Uso:
    python gerar.py video.mp4 "Você encontrou a página que fala tudo sobre GTA 6"
    python gerar.py https://link-do-video "Meu título"
"""
import re
import shutil
import subprocess
import sys
import textwrap
import unicodedata
from datetime import datetime
from pathlib import Path

# =====================================================================
# CONFIGURAÇÕES - altere aqui à vontade
# =====================================================================
LARGURA = 1080                 # largura do vídeo final (pixels)
ALTURA = 1920                  # altura do vídeo final (pixels)
COR_FUNDO = "black"            # cor do fundo

FONTE = "C:/Windows/Fonts/arialbd.ttf"   # fonte do título (Arial Negrito)
TITULO_COR = "white"
TITULO_TAMANHO = 72            # tamanho da letra do título
TITULO_CARACTERES_POR_LINHA = 22   # quebra de linha automática
TITULO_TOPO = 200              # distância do título até o topo (pixels)
TITULO_ESPACO_ENTRE_LINHAS = 20

VIDEO_ALTURA_MAXIMA = 1100     # altura máxima do vídeo original no meio

LEGENDA_FONTE = "Arial"
LEGENDA_TAMANHO = 13           # escala do libass (13 ≈ 85px na tela)
LEGENDA_MARGEM_BAIXO = 40      # distância da legenda até a borda de baixo

WHISPER_MODELO = "small"       # tiny, base, small, medium, large-v3
WHISPER_IDIOMA = "pt"

PASTA_PRONTOS = Path("prontos")      # onde os vídeos finais são salvos
PASTA_TRABALHO = Path("trabalho")    # arquivos temporários
# =====================================================================


def erro(mensagem):
    """Mostra uma mensagem de erro clara e encerra o programa."""
    print(f"\n[ERRO] {mensagem}\n")
    sys.exit(1)


def verificar_ffmpeg():
    """Confere se o ffmpeg está instalado."""
    if not shutil.which("ffmpeg"):
        erro("O ffmpeg não foi encontrado.\n"
             "Instale com:  winget install Gyan.FFmpeg\n"
             "Depois feche e abra o terminal de novo.")


def baixar_video(url, pasta):
    """Baixa o vídeo de um link usando o yt-dlp e devolve o caminho do arquivo."""
    try:
        import yt_dlp
    except ImportError:
        erro("O yt-dlp não está instalado. Rode:  pip install yt-dlp")

    print("Baixando o vídeo...")
    opcoes = {
        "outtmpl": str(pasta / "download.%(ext)s"),
        "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b",
        "merge_output_format": "mp4",
        "quiet": True,
    }
    try:
        with yt_dlp.YoutubeDL(opcoes) as ydl:
            info = ydl.extract_info(url, download=True)
            return Path(ydl.prepare_filename(info)).with_suffix(".mp4")
    except Exception as e:
        erro(f"Não consegui baixar o vídeo: {e}")


def formatar_tempo(segundos):
    """Converte segundos (ex.: 3.5) para o formato do .srt (00:00:03,500)."""
    ms = int(round(segundos * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def gerar_legendas(video, arquivo_srt):
    """Transcreve o áudio com o faster-whisper e salva um arquivo .srt."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        erro("O faster-whisper não está instalado. Rode:  pip install faster-whisper")

    print(f"Transcrevendo o áudio (modelo '{WHISPER_MODELO}', pode demorar na 1ª vez)...")
    # Extraímos o áudio com o ffmpeg (16 kHz, mono), que é o formato que o Whisper usa.
    # Fazemos isso nós mesmos para não depender do leitor de áudio interno dele.
    import numpy as np
    resultado = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", str(video),
         "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
        capture_output=True,
    )
    if resultado.returncode != 0 or not resultado.stdout:
        print("  Aviso: o vídeo não tem áudio, então ficará sem legenda.")
        return False
    audio = np.frombuffer(resultado.stdout, dtype=np.float32)

    modelo = WhisperModel(WHISPER_MODELO, device="cpu", compute_type="int8")
    segmentos, _ = modelo.transcribe(audio, language=WHISPER_IDIOMA, vad_filter=True)

    numero = 0
    with open(arquivo_srt, "w", encoding="utf-8") as f:
        for seg in segmentos:
            texto = seg.text.strip()
            if texto:
                numero += 1
                f.write(f"{numero}\n")
                f.write(f"{formatar_tempo(seg.start)} --> {formatar_tempo(seg.end)}\n")
                f.write(f"{texto}\n\n")
    print(f"  {numero} trechos de legenda gerados.")
    return numero > 0


def nome_unico(titulo):
    """Cria um nome de arquivo único: data-hora + parte do título."""
    # Tira os acentos (ê -> e, á -> a) e troca o resto por "-"
    sem_acento = unicodedata.normalize("NFKD", titulo).encode("ascii", "ignore").decode()
    trecho = re.sub(r"[^a-zA-Z0-9]+", "-", sem_acento.lower()).strip("-")[:40]
    agora = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{agora}-{trecho or 'video'}.mp4"


def montar_video(video, titulo, tem_legenda, saida, pasta):
    """Usa o ffmpeg para montar o vídeo final no estilo meme."""
    # Copiamos a fonte para a pasta de trabalho para evitar problemas com
    # o "C:" do Windows dentro dos filtros do ffmpeg.
    if not Path(FONTE).exists():
        erro(f"Fonte não encontrada: {FONTE}\nAltere a configuração FONTE no topo do arquivo.")
    shutil.copy(FONTE, pasta / "fonte.ttf")

    # 1) Vídeo original: reduz para caber no meio, sem distorcer,
    #    e coloca sobre um fundo preto de 1080x1920.
    filtros = (
        f"[0:v]scale={LARGURA}:{VIDEO_ALTURA_MAXIMA}:force_original_aspect_ratio=decrease,"
        f"pad={LARGURA}:{ALTURA}:(ow-iw)/2:(oh-ih)/2:color={COR_FUNDO},setsar=1"
    )

    # 2) Título: cada linha é desenhada separada para ficar centralizada.
    #    O texto vai em arquivos .txt para não precisar escapar acentos e símbolos.
    linhas = textwrap.wrap(titulo, TITULO_CARACTERES_POR_LINHA)
    for i, linha in enumerate(linhas):
        (pasta / f"titulo{i}.txt").write_text(linha, encoding="utf-8")
        y = TITULO_TOPO + i * (TITULO_TAMANHO + TITULO_ESPACO_ENTRE_LINHAS)
        filtros += (
            f",drawtext=fontfile=fonte.ttf:textfile=titulo{i}.txt:"
            f"fontsize={TITULO_TAMANHO}:fontcolor={TITULO_COR}:x=(w-text_w)/2:y={y}"
        )

    # 3) Legendas queimadas na parte de baixo, com contorno preto.
    if tem_legenda:
        estilo = (f"FontName={LEGENDA_FONTE},FontSize={LEGENDA_TAMANHO},Bold=1,"
                  "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
                  f"BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV={LEGENDA_MARGEM_BAIXO}")
        filtros += f",subtitles=legendas.srt:force_style='{estilo}'"

    comando = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(video.resolve()),
        "-vf", filtros,
        "-map", "0:v:0", "-map", "0:a?",          # "?" = áudio é opcional
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart",
        str(saida.resolve()),
    ]
    print("Montando o vídeo final com o ffmpeg...")
    # cwd=pasta: o ffmpeg roda dentro da pasta de trabalho, assim
    # "fonte.ttf", "titulo0.txt" e "legendas.srt" são encontrados direto.
    resultado = subprocess.run(comando, cwd=pasta, capture_output=True, text=True)
    if resultado.returncode != 0:
        erro(f"O ffmpeg falhou:\n{resultado.stderr}")


def processar_video(entrada, titulo):
    """Faz todo o processo para UM vídeo e devolve o caminho do resultado.
    Fica separado do main() para que o futuro modo lote possa chamá-lo várias vezes."""
    PASTA_TRABALHO.mkdir(exist_ok=True)
    PASTA_PRONTOS.mkdir(exist_ok=True)

    # Link ou arquivo local?
    if entrada.startswith(("http://", "https://")):
        video = baixar_video(entrada, PASTA_TRABALHO)
    else:
        video = Path(entrada)
        if not video.exists():
            erro(f"Arquivo não encontrado: {video}")

    tem_legenda = gerar_legendas(video, PASTA_TRABALHO / "legendas.srt")

    saida = PASTA_PRONTOS / nome_unico(titulo)
    montar_video(video, titulo, tem_legenda, saida, PASTA_TRABALHO)
    if tem_legenda:
        shutil.copy(PASTA_TRABALHO / "legendas.srt", saida.with_suffix(".srt"))
    return saida

    # ---------------------------------------------------------------
    # PRÓXIMAS FASES (ainda não implementadas). Ideias de onde encaixar:
    # - Modo lote: um laço que chama processar_video() para cada arquivo de uma pasta.
    # - Variações (zoom, corte, música): acrescentar filtros em montar_video().
    # - Título/descrição com a API do Claude: nova função gerar_textos(legendas).
    # - Agendar posts (Instagram Graph API / YouTube Data API): novo arquivo postar.py.
    # ---------------------------------------------------------------


def main():
    if len(sys.argv) != 3:
        print('Uso: python gerar.py <video.mp4 ou link> "Título do vídeo"')
        sys.exit(1)

    verificar_ffmpeg()
    saida = processar_video(sys.argv[1], sys.argv[2])
    print(f"\nPronto! Vídeo salvo em: {saida}")


if __name__ == "__main__":
    main()
