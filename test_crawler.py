import asyncio
from crawler import crawl_and_record

async def test_otp():
    async def mock_otp():
        print("MOCK OTP TRIGGERED!")
        return "123456"
        
    await crawl_and_record("https://www.indoplay.io", duration=30, task_id=999, otp_callback=mock_otp)

asyncio.run(test_otp())
