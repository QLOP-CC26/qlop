import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from services.pdf_extractor import process_pdf_cv
import fitz

cv_text = '''Mandailing Natal, Sumatera Utara
Sixth- semester Computer Science student at IPB University with strong academic performance and frequent
competition experience. Skilled in problem-solving, teamwork, and communication, with broad interests spanning
full-stack development, machine learning, data science, robotics, and competitive programming.
Education Level
Institut Pertanian Bogor - Bogor, Jawa Barat
Jul 2023 - May 2027 (Expected)
Computer Science Student, 3.86/4.00
3rd Place in the Competitive Programming category, Multimedia and Game Event (MAGE) X ITS
Work Experiences
Career Development and Assessment IPB University - Bogor, Indonesia
Feb 2026 - Present
Junior Programmer Intern
Independently implemented extensive new features and system enhancements across 3 full- stack web applications, improving
functionality and user experience.
Proton Catalyst - Bogor, Indonesia
Oct 2023 - Mar 2024
Tutor
'''

doc = fitz.open()
page = doc.new_page()
page.insert_text((72,72), cv_text)
pdf_bytes = doc.tobytes()
doc.close()

response = process_pdf_cv(pdf_bytes, 'CV_Husni Abdillah_April 26.pdf')
print(response.model_dump_json(indent=2))
