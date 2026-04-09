"""
Skill: Leitura de Arquivos
===========================
Acesso a documentos reais do projeto Rhode Jeans — estratégia, brandbook, etc.
O agente usa isso para basear respostas em documentos atualizados.
"""
from pathlib import Path
from anthropic import beta_tool


# Diretório raiz do projeto Rhode Jeans
PROJETO_DIR = Path("/Users/user/Documents/Teste VS Code + Claude Code ")


def _ler_arquivo(caminho: Path, limite_chars: int = 4000) -> str:
    """Lê um arquivo com tratamento de erro e limite de tamanho."""
    try:
        conteudo = caminho.read_text(encoding="utf-8")
        if len(conteudo) > limite_chars:
            return conteudo[:limite_chars] + f"\n\n[... truncado — {len(conteudo)} chars no total]"
        return conteudo
    except FileNotFoundError:
        return f"Arquivo não encontrado: {caminho}"
    except Exception as e:
        return f"Erro ao ler '{caminho.name}': {e}"


@beta_tool
def ler_estrategia() -> str:
    """Lê o documento de estratégia atual da Rhode Jeans (ESTRATEGIA_RHODE_JEANS.md).
    Use esta ferramenta para basear recomendações nos objetivos reais do negócio.
    """
    return _ler_arquivo(PROJETO_DIR / "ESTRATEGIA_RHODE_JEANS.md")


@beta_tool
def listar_arquivos_projeto() -> str:
    """Lista todos os arquivos disponíveis no projeto Rhode Jeans."""
    try:
        arquivos = [
            {"nome": f.name, "tipo": f.suffix, "tamanho_kb": round(f.stat().st_size / 1024, 1)}
            for f in PROJETO_DIR.iterdir()
            if f.is_file()
        ]
        return str(arquivos)
    except Exception as e:
        return f"Erro ao listar arquivos: {e}"


@beta_tool
def ler_arquivo_por_nome(nome_arquivo: str) -> str:
    """Lê qualquer arquivo do projeto Rhode Jeans pelo nome.

    Args:
        nome_arquivo: Nome do arquivo com extensão — ex: "ESTRATEGIA_RHODE_JEANS.md"
    """
    return _ler_arquivo(PROJETO_DIR / nome_arquivo)
