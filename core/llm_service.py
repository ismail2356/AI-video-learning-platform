import google.generativeai as genai
import os
from django.conf import settings
import time
from functools import wraps
import logging
import random

logger = logging.getLogger(__name__)

# Rate limiting için değişkenler
RATE_LIMIT_PER_MINUTE = 10  # Dakikada maksimum istek sayısı (daha düşük değer)
RATE_LIMIT_PER_DAY = 500   # Günde maksimum istek sayısı (daha düşük değer)
RETRY_MAX_ATTEMPTS = 2     # Maksimum yeniden deneme sayısı
RETRY_BASE_DELAY = 50      # Temel bekleme süresi (saniye)

# Gemini API key
API_KEY = settings.GEMINI_API_KEY

# Rate limiting için dekoratör
def rate_limit(func):
    last_request_time = 0
    request_count = 0
    day_start = time.time()
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal last_request_time, request_count, day_start
        
        current_time = time.time()
        
        # Günlük limit kontrolü
        if current_time - day_start >= 86400:  # 24 saat
            request_count = 0
            day_start = current_time
            
        if request_count >= RATE_LIMIT_PER_DAY:
            wait_time = 86400 - (current_time - day_start)
            logger.warning(f"Günlük limit aşıldı. {wait_time:.2f} saniye bekleniyor.")
            time.sleep(wait_time)
            request_count = 0
            day_start = time.time()
        
        # Dakikalık limit kontrolü - bir sonraki isteğe kadar beklenmesi gereken minimum süre
        min_interval = 60 / RATE_LIMIT_PER_MINUTE  # Dakikada istek başına saniye
        time_since_last = current_time - last_request_time
        
        if time_since_last < min_interval:
            wait_time = min_interval - time_since_last
            logger.warning(f"Dakikalık limit kontrolü. {wait_time:.2f} saniye bekleniyor.")
            time.sleep(wait_time)
        
        # API isteği gönderme ve yeniden deneme mantığı
        attempt = 0
        while attempt < RETRY_MAX_ATTEMPTS:
            try:
                last_request_time = time.time()  # İstek yapılmadan önce zamanı güncelle
                result = func(*args, **kwargs)
                request_count += 1
                return result
            except Exception as e:
                error_msg = str(e)
                attempt += 1
                
                if "429" in error_msg and attempt < RETRY_MAX_ATTEMPTS:
                    # Exponential backoff ile retry
                    jitter = random.uniform(0.5, 1.5)  # %50 yukarı veya aşağı rastgele değişim
                    delay = RETRY_BASE_DELAY * (2 ** (attempt - 1)) * jitter
                    logger.warning(f"Rate limit hatası. Deneme {attempt}/{RETRY_MAX_ATTEMPTS}. {delay:.2f} saniye bekleniyor.")
                    time.sleep(delay)
                elif attempt == RETRY_MAX_ATTEMPTS:
                    logger.error(f"Maksimum deneme sayısına ulaşıldı: {error_msg}")
                    return f"Üzgünüm, şu anda API servisine erişimde sorun yaşıyorum. Lütfen daha sonra tekrar deneyin."
                else:
                    logger.error(f"API hatası: {error_msg}")
                    raise e
            
    return wrapper

# Mevcut Gemini modelleri:
# 1. gemini-2.0-flash - Çok amaçlı ve hızlı model
# 2. gemini-2.0-flash-lite - Maliyet açısından verimli model
# 3. gemini-1.5-flash - Daha düşük kapasiteli ama hızlı model
# 4. gemini-1.5-pro - Daha karmaşık görevler için uygun
# 5. models/gemini-1.5-flash-latest - En son Flash modeli
# 6. gemini-1.0-pro - Eski model, daha basit görevler için

# Her istek için API anahtarını yeniden yapılandır
@rate_limit
def gemini_generate(prompt, model_name="models/gemini-2.0-flash-lite", max_tokens=1024):
    """
    Gemini API kullanarak içerik oluşturur.
    
    Args:
        prompt (str): İstek metni
        model_name (str): Kullanılacak Gemini modeli. Video analizi ve soru-cevap için önerilen: 
                         "models/gemini-2.0-flash-lite" veya "models/gemini-1.5-flash" 
        max_tokens (int): Maksimum çıktı token sayısı
        
    Returns:
        str: Gemini'den alınan yanıt metni
    """
    # Her istekte API anahtarını yeniden yapılandır
    genai.configure(api_key=API_KEY)
    
    try:
        model = genai.GenerativeModel(model_name)
        
        # Soru-cevap amacıyla yapılandırılmış generation_config
        generation_config = {
            "max_output_tokens": max_tokens,
            "temperature": 0.2,         # Daha düşük değer, daha determistik yanıtlar
            "top_p": 0.95,              # Yüksek kaliteli yanıtlar için 
            "top_k": 40                 # Makul değer
        }
        
        response = model.generate_content(
            prompt, 
            generation_config=generation_config
        )
        
        return response.text if hasattr(response, 'text') else str(response)
    except Exception as e:
        logger.error(f"Gemini API hatası: {str(e)}")
        raise e 