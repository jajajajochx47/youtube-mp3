# Local YouTube MP3 Downloader

เว็บ local สำหรับใช้เองในเครื่อง วางลิงก์หลายบรรทัดแล้วโหลดเป็น MP3 ตามคิว

> ใช้กับวิดีโอหรือเสียงที่คุณเป็นเจ้าของ หรือมีสิทธิ์ดาวน์โหลดเท่านั้น

## ติดตั้ง

ดับเบิลคลิกไฟล์ `install-python-deps.bat` เพื่อสร้าง environment Python ในโฟลเดอร์โปรเจกต์และติดตั้ง package ที่จำเป็นให้เอง

ถ้าอยากติดตั้งด้วยมือ:

```cmd
python -m pip install -r requirements.txt
```

ติดตั้ง ffmpeg 
```text
winget install ffmpeg
```

ต้องมี `ffmpeg` ด้วย ถ้าใช้ Windows แนะนำแตกไฟล์ไว้ที่:

```text
C:\ffmpeg\bin\ffmpeg.exe
```

## รันเว็บ

ดับเบิลคลิก `run.bat` เพื่อเริ่มเว็บโดยอัตโนมัติ

หรือรันด้วยมือ:

```cmd
python app.py
```

จากนั้นเปิด:

```text
http://127.0.0.1:3000
```
