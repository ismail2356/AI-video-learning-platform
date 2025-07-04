#!/usr/bin/env python
"""
Bu script, bilgi kartlarındaki HTML etiketlerini ve gereksiz karakterleri temizler.
"""

import os
import re
import django
import logging
import traceback

# Logging yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("flashcard_cleaner.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("flashcard_cleaner")

# Django ortamını ayarla
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'video_learning_platform.settings')
django.setup()

from flashcards.models import Flashcard

def clean_text(text):
    """
    Metindeki HTML etiketlerini ve gereksiz karakterleri temizler
    """
    if not text:
        return ""
    
    try:
        # HTML etiketlerini temizle (daha kapsamlı regex)
        text = re.sub(r'<[^>]*>', '', text)
        
        # <br /> ve benzeri etiketleri boşlukla değiştir
        text = text.replace('<br />', ' ')
        text = text.replace('<br/>', ' ')
        text = text.replace('<br>', ' ')
        text = text.replace('&nbsp;', ' ')  # HTML boşluk karakteri
        text = text.replace('&lt;', '<')    # HTML < karakteri
        text = text.replace('&gt;', '>')    # HTML > karakteri
        text = text.replace('&amp;', '&')   # HTML & karakteri
        text = text.replace('&quot;', '"')  # HTML " karakteri
        
        # Yıldız işaretlerini temizle (daha kapsamlı regex)
        text = re.sub(r'\*+', '', text)  # Birden fazla yıldızı temizle
        text = re.sub(r'\*\s*\*', '', text)  # Arada boşluk olan yıldızları temizle
        text = re.sub(r'\s*\*\s*', ' ', text)  # Boşluk-yıldız-boşluk kombinasyonlarını düzelt
        
        # Markdown biçimlendirmesini temizle
        text = re.sub(r'#{1,6}\s+', '', text)  # Başlıkları temizle
        text = re.sub(r'`{1,3}', '', text)     # Kod bloklarını temizle
        text = re.sub(r'>{1,}', '', text)      # Alıntıları temizle
        
        # "Bilgi Kartı X" ifadelerini temizle
        text = re.sub(r'Bilgi Kartı\s*\d*\s*', '', text)
        text = re.sub(r'Kart\s*\d+\s*[:]*', '', text)
        
        # Fazla boşlukları temizle
        text = re.sub(r'\s+', ' ', text)
        
        # Başlangıç ve sondaki boşlukları temizle
        text = text.strip()
        
        return text
    except Exception as e:
        logger.error(f"Metin temizleme sırasında hata: {str(e)}")
        logger.error(traceback.format_exc())
        return text  # Hata durumunda orijinal metni döndür

def main():
    """
    Tüm bilgi kartlarını temizler
    """
    try:
        flashcards = Flashcard.objects.all()
        total_count = len(flashcards)
        
        logger.info(f"Toplam {total_count} bilgi kartı bulundu.")
        
        cleaned_count = 0
        error_count = 0
        
        for card in flashcards:
            try:
                # Kart ID'sini logla
                logger.info(f"Kart ID: {card.id} işleniyor...")
                
                # Orijinal metinleri kaydet
                original_question = card.question_text
                original_answer = card.answer_text
                
                # HTML etiketlerini ve gereksiz karakterleri temizle
                clean_question = clean_text(original_question)
                clean_answer = clean_text(original_answer)
                
                # Değişiklik varsa kaydet
                if clean_question != original_question or clean_answer != original_answer:
                    logger.info(f"Kart ID: {card.id} - Değişiklik tespit edildi")
                    logger.debug(f"Eski Soru: {original_question}")
                    logger.debug(f"Yeni Soru: {clean_question}")
                    logger.debug(f"Eski Cevap: {original_answer}")
                    logger.debug(f"Yeni Cevap: {clean_answer}")
                    
                    card.question_text = clean_question
                    card.answer_text = clean_answer
                    card.save()
                    cleaned_count += 1
                else:
                    logger.info(f"Kart ID: {card.id} - Değişiklik yok")
            except Exception as e:
                logger.error(f"Kart ID: {card.id} için hata: {str(e)}")
                logger.error(traceback.format_exc())
                error_count += 1
        
        logger.info(f"İşlem tamamlandı.")
        logger.info(f"Toplam kart sayısı: {total_count}")
        logger.info(f"Temizlenen kart sayısı: {cleaned_count}")
        logger.info(f"Hata oluşan kart sayısı: {error_count}")
        
        print(f"\nToplam {cleaned_count} bilgi kartı temizlendi.")
        if error_count > 0:
            print(f"{error_count} kart işlenirken hata oluştu. Detaylar için log dosyasını kontrol edin.")
        
    except Exception as e:
        logger.critical(f"Ana işlem sırasında kritik hata: {str(e)}")
        logger.critical(traceback.format_exc())
        print(f"Kritik hata oluştu: {str(e)}")

if __name__ == "__main__":
    main()