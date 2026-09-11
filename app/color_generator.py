# app/color_generator.py - TO'LIQ YANGI FAYL
from PIL import Image
import io

class ColorSquareGenerator:
    @staticmethod
    def create_color_square(hex_color, size=200):
        """HEX kod uchun rang kvadrati yaratish"""
        try:
            # HEX kodni RGB ga o'tkazish
            hex_color = hex_color.lstrip('#')
            rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            
            # Yangi rasm yaratish
            image = Image.new('RGB', (size, size), rgb)
            
            # Rasmni saqlash uchun buffer
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            return img_buffer
        except Exception as e:
            print(f"Rang kvadrati yaratishda xatolik: {e}")
            return None
