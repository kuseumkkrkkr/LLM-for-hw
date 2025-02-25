from google import genai
import os
import uuid
import io
import base64
import logging
from flask import Flask, request, render_template_string
import fitz  # PyMuPDF
from PIL import Image

# 로깅 설정 (DEBUG 레벨)
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Flask 애플리케이션 설정
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["IMAGE_FOLDER"] = "static/images"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["IMAGE_FOLDER"], exist_ok=True)

# Google Generative AI (Gemini API) 설정 변경
import google.generativeai as genai
genai.configure(api_key="AIzaSyD_9V2Yk8nflCNbIi7UIaFaulDv3OO14_s")

# HTML 템플릿 (업로드 페이지)
upload_template = """
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <title>PDF 업로드 및 분석</title>
</head>
<body>
  <h1>PDF 업로드 및 분석</h1>
  <form method="post" enctype="multipart/form-data">
    <input type="file" name="pdf" accept="application/pdf" required>
    <input type="hidden" name="analysis_type" id="analysis_type">
    <br><br>
    <button type="submit" onclick="document.getElementById('analysis_type').value='smart'">스마트 분석</button>
    <button type="submit" onclick="document.getElementById('analysis_type').value='speed'">스피드 분석</button>
  </form>
</body>
</html>
"""

# HTML 템플릿 (분석 결과 페이지)
result_template = """
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <title>분석 결과</title>
</head>
<body>
  <h1>분석 결과</h1>
  {% for page in results %}
    <div style="margin-bottom:20px; border:1px solid #ccc; padding:10px;">
      <h3>페이지 {{ page.page }}</h3>
      {% if page.image_data %}
        <img src="{{ page.image_data }}" style="max-width:300px;"><br>
      {% endif %}
      <p>{{ page.summary }}</p>
    </div>
  {% endfor %}
  <a href="/">다시 업로드</a>
</body>
</html>
"""

def analyze_smart(pdf_path):
    """
    [스마트 분석]
    - PyMuPDF를 사용해 PDF의 각 페이지를 이미지로 변환
    - 각 페이지 이미지를 Gemini API("gemini-image")에 전달하여 요약 결과를 수신
    - 이미지 데이터는 base64로 인코딩되어 웹 미리보기로 사용됨
    """
    results = []
    try:
        doc = fitz.open(pdf_path)
        logging.debug("PDF에서 %d 페이지를 로드함", doc.page_count)
        for i in range(doc.page_count):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 해상도 조절(2배)
            
            # JPEG 바이트로 변환
            image_bytes = pix.tobytes("jpeg")
            
            # base64로 인코딩 (웹 미리보기용)
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            logging.debug("페이지 %d: Gemini API (이미지) 호출 시작", i+1)
            
            try:
                # Gemini API에 전달할 이미지 준비
                image_parts = [
                    {
                        "mime_type": "image/jpeg",
                        "data": image_bytes
                    }
                ]
                
                # Gemini 모델 설정 및 호출
                model = genai.GenerativeModel('gemini-2.0-flash')
                response = model.generate_content(
                    contents=[
                        "이 이미지의 내용을 요약해줘.",
                        image_parts[0]
                    ]
                )
                response.resolve()  # 응답 완료 대기
                
                summary = response.text if response else "요약 실패"
                logging.debug("페이지 %d: 요약 완료 - %s", i+1, summary[:100])
                
            except Exception as e:
                logging.error("Gemini API 호출 중 오류 발생: %s", str(e))
                summary = f"요약 실패: {str(e)}"
            
            results.append({
                'page': i + 1,
                'summary': summary,
                'image': f"data:image/jpeg;base64,{image_base64}"
            })
            
    except Exception as e:
        logging.error("PDF 처리 중 오류 발생: %s", str(e))
        return {'error': str(e)}
    
    finally:
        if 'doc' in locals():
            doc.close()
    
    return results

def analyze_speed(pdf_path):
    """
    [스피드 분석]
    - PyMuPDF를 사용하여 PDF 각 페이지에서 텍스트를 추출
    - 추출한 텍스트를 Gemini API("gemini-text")에 전달하여 요약 결과를 수신
    - 페이지 미리보기 이미지는 PyMuPDF를 사용해 생성하여 포함
    """
    results = []
    try:
        doc = fitz.open(pdf_path)
        logging.debug("PDF에서 %d 페이지를 로드함", doc.page_count)
        for i in range(doc.page_count):
            page = doc.load_page(i)
            text = page.get_text("text")
            logging.debug("페이지 %d: 추출 텍스트 (최대 100자): %s", i+1, text[:100])
            logging.debug("페이지 %d: Gemini API (텍스트) 호출 시작", i+1)
            
            # Gemini API 호출 부분 수정
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content("다음 텍스트를 요약해줘:\n" + text)
            
            summary = response.text if response else "요약 실패"
            # 미리보기용 이미지 생성
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            image_bytes = pix.tobytes("jpeg")
            img_b64 = base64.b64encode(image_bytes).decode("utf-8")
            img_data = f"data:image/jpeg;base64,{img_b64}"
            results.append({
                "page": i+1,
                "summary": summary,
                "image_data": img_data
            })
            logging.debug("페이지 %d 스피드 분석 완료", i+1)
    except Exception as e:
        logging.exception("스피드 분석 중 오류 발생:")
    return results

@app.route("/", methods=["GET", "POST"])
def upload_file():
    """
    PDF 업로드 및 분석 처리:
      - 업로드된 PDF를 서버에 저장한 후, 선택된 분석 방식에 따라 스마트 또는 스피드 분석을 실행
      - 결과는 각 페이지별 요약과 미리보기 이미지로 구성됨
    """
    if request.method == "POST":
        if "pdf" not in request.files:
            return "PDF 파일이 업로드되지 않았습니다.", 400
        pdf_file = request.files["pdf"]
        if pdf_file.filename == "":
            return "파일을 선택해 주세요.", 400
        analysis_type = request.form.get("analysis_type")
        if analysis_type not in ["smart", "speed"]:
            return "유효하지 않은 분석 유형입니다.", 400

        # PDF 파일 저장
        pdf_filename = str(uuid.uuid4()) + ".pdf"
        pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], pdf_filename)
        pdf_file.save(pdf_path)
        logging.debug("업로드된 PDF 저장됨: %s", pdf_path)
        
        # 선택된 분석 방식에 따라 처리
        if analysis_type == "smart":
            results = analyze_smart(pdf_path)
        else:
            results = analyze_speed(pdf_path)
        
        os.remove(pdf_path)  # 사용 후 PDF 파일 삭제
        return render_template_string(result_template, results=results)
    return render_template_string(upload_template)

if __name__ == "__main__":
    logging.debug("서버 시작")
    app.run(debug=True)
