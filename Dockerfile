# 1-qadam: Python-ning engil versiyasini tanlaymiz
FROM python:3.11-slim

# 2-qadam: Ishchi katalogni belgilaymiz
WORKDIR /app

# 3-qadam: Tizim kutubxonalarini yangilaymiz (agar cryptography uchun kerak bo'lsa)
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 4-qadam: Avval requirements faylini nusxalash (keshlashni yaxshilash uchun)
COPY requirements.txt .

# 5-qadam: Kutubxonalarni o'rnatish
RUN pip install --no-cache-dir -r requirements.txt

# 6-qadam: Loyiha kodlarini nusxalash
COPY . .

# 7-qadam: SQLite bazasi va sessiyalar uchun papka yaratish
RUN mkdir -p data

# 8-qadam: Botni ishga tushirish (asl faylingiz nomi bot.py deb hisoblandi)
CMD ["python", "bot.py"]