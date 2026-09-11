# app/color_detector.py - 1-BOSQICH TEZLASHTIRILGAN
from PIL import Image
from io import BytesIO
from collections import Counter
from app.utils import logger

class SimpleColorDetector:
    @staticmethod
    async def get_dominant_color(photo_file):
        """Rasmning MARKAZIDAN asosiy rangni aniqlash (tezlashtirilgan)"""
        try:
            # ✅ YANGI: To'g'ridan-to'g'ri byte sifatida yuklaymiz (HTTP yo'q)
            file = await photo_file.get_file()
            image_data = await file.download_as_bytearray()
            
            img = Image.open(BytesIO(image_data))
            img = img.convert('RGB')
            
            # Markaziy 40% ni kesib olamiz
            width, height = img.size
            left = int(width * 0.3)
            top = int(height * 0.3)
            right = int(width * 0.7)
            bottom = int(height * 0.7)
            
            center_crop = img.crop((left, top, right, bottom))
            center_crop = center_crop.resize((50, 50), Image.Resampling.LANCZOS)
            pixels = list(center_crop.getdata())
            
            # Fon ranglarni filtrlash
            filtered_pixels = []
            for r, g, b in pixels:
                is_gray = abs(r - g) < 25 and abs(g - b) < 25 and abs(r - b) < 25
                is_white = r > 210 and g > 210 and b > 210
                is_black = r < 25 and g < 25 and b < 25
                
                if not (is_gray or is_white or is_black):
                    filtered_pixels.append((r, g, b))
            
            if filtered_pixels:
                color_counts = Counter(filtered_pixels)
            else:
                color_counts = Counter(pixels)
            
            dominant_rgb = color_counts.most_common(1)[0][0]
            hex_color = '#{:02X}{:02X}{:02X}'.format(*dominant_rgb)
            
            return hex_color
            
        except Exception as e:
            logger.error(f"Rang aniqlash xatosi: {e}")
            return None

    @staticmethod
    async def get_top_colors(photo_file, count=5):
        """Eng ko'p uchraydigan ranglarni olish"""
        try:
            file = await photo_file.get_file()
            image_data = await file.download_as_bytearray()
            
            img = Image.open(BytesIO(image_data))
            img = img.convert('RGB')
            
            width, height = img.size
            left = int(width * 0.3)
            top = int(height * 0.3)
            right = int(width * 0.7)
            bottom = int(height * 0.7)
            
            center_crop = img.crop((left, top, right, bottom))
            center_crop = center_crop.resize((80, 80), Image.Resampling.LANCZOS)
            pixels = list(center_crop.getdata())
            
            filtered_pixels = []
            for r, g, b in pixels:
                is_gray = abs(r - g) < 25 and abs(g - b) < 25 and abs(r - b) < 25
                is_white = r > 210 and g > 210 and b > 210
                is_black = r < 25 and g < 25 and b < 25
                
                if not (is_gray or is_white or is_black):
                    filtered_pixels.append((r, g, b))
            
            source = filtered_pixels if filtered_pixels else pixels
            color_counts = Counter(source)
            top_colors = color_counts.most_common(count)
            
            result = []
            total = len(source)
            for rgb, freq in top_colors:
                hex_color = '#{:02X}{:02X}{:02X}'.format(*rgb)
                percentage = (freq / total) * 100 if total > 0 else 0
                result.append({
                    'hex': hex_color,
                    'rgb': rgb,
                    'percentage': round(percentage, 1)
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Ranglar olishda xato: {e}")
            return []