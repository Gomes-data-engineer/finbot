import os
import sys
import logging
from dotenv import load_dotenv

# Configura o Logger para o projeto
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("FinBotConfig")

# Carrega o arquivo .env se ele existir na pasta raiz do projeto
load_dotenv()

# Variáveis exigidas
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def validate_config():
    """Valida se todas as variáveis de ambiente necessárias estão presentes."""
    missing = []
    if not TELEGRAM_TOKEN:
        missing.append("TELEGRAM_TOKEN")
    if not SUPABASE_URL:
        missing.append("SUPABASE_URL")
    if not SUPABASE_KEY:
        missing.append("SUPABASE_KEY")
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
        
    if missing:
        logger.error(f"Erro: As seguintes variáveis de ambiente estão faltando no .env: {', '.join(missing)}")
        logger.error("Por favor, crie um arquivo .env na raiz do projeto com estas chaves.")
        return False
    
    logger.info("Todas as variáveis de ambiente foram carregadas com sucesso.")
    return True

# Se importado em qualquer lugar do projeto, opcionalmente avisa se falta algo
# mas não mata o script imediatamente caso seja usado pelo dashboard Streamlit ou outro
if not TELEGRAM_TOKEN or not SUPABASE_URL or not SUPABASE_KEY or not GEMINI_API_KEY:
    logger.warning("Alerta: Algumas variáveis de ambiente não foram encontradas no .env!")
