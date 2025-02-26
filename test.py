import os
import uuid
import base64
import logging
from flask import Flask, request, render_template_string
import fitz  # PyMuPDF
from google import genai
from google.genai import types

# 디버그 로깅 설정 (DEBUG 레벨)
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Flask 애플리케이션 설정
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
# 100MB 이상 업로드 불가
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Gemini API 설정 (자신의 API 키로 교체)
client = genai.Client(api_key="AIzaSyD_9V2Yk8nflCNbIi7UIaFaulDv3OO14_s")

# 업로드 페이지 템플릿 (진행률 게이지 및 예상 소요시간 포함)
upload_template = """
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <title>PDF 업로드 및 분석</title>
  <style>
    body {
      font-family: 'Segoe UI', sans-serif;
      background-color: #f4f4f4;
      margin: 0;
      padding: 20px;
    }
    .container {
      background: white;
      padding: 25px;
      border-radius: 8px;
      box-shadow: 0px 0px 10px rgba(0,0,0,0.1);
      max-width: 1000px;
      margin: auto;
    }
    .left-panel, .right-panel {
      display: inline-block;
      vertical-align: top;
    }
    .left-panel {
      width: 60%;
    }
    .right-panel {
      width: 40%;
      border-left: 1px solid #ddd;
      padding-left: 25px;
    }
    .input-section {
      margin-top: 20px;
    }
    .input-section input[type="file"] {
      width: 100%;
      padding: 10px;
      border: 1px solid #ddd;
      border-radius: 5px;
      margin-bottom: 15px;
      box-sizing: border-box;
    }
    .controls {
      display: flex;
      flex-direction: column;
      gap: 15px;
      margin-bottom: 20px;
    }
    select,
    button {
      width: 100%;
      padding: 10px;
      border-radius: 5px;
      border: 1px solid #ddd;
      font-size: 14px;
    }
    button {
      background-color: #007bff;
      color: white;
      border: none;
      cursor: pointer;
      transition: background-color 0.3s;
      font-weight: bold;
    }
    button:hover {
      background-color: #0056b3;
    }
    .features {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 15px;
    }
    .feature-card {
      padding: 15px;
      border: 1px solid #ddd;
      border-radius: 5px;
      background-color: white;
    }
    .feature-card h3 {
      margin: 0 0 10px 0;
      font-size: 14px;
      color: #333;
    }
    .feature-card p {
      margin: 0;
      font-size: 13px;
      color: #666;
    }
    h1, h2, h3 {
      margin: 0 0 15px 0;
      color: #333;
    }
    /* 진행률 게이지 스타일 */
    #progress-bar {
      width: 100%;
      background-color: #ddd;
      border-radius: 5px;
      overflow: hidden;
      margin: 20px auto;
      height: 20px;
      max-width: 500px;
    }
    #progress-fill {
      width: 0%;
      height: 100%;
      background-color: #007bff;
      transition: width 0.3s;
    }
    @media (max-width: 768px) {
      .container {
        width: 95%;
        padding: 15px;
      }
      .left-panel, .right-panel {
        width: 100%;
        display: block;
        padding: 0;
        border: none;
      }
      .right-panel {
        border-top: 1px solid #ddd;
        padding-top: 20px;
        margin-top: 20px;
      }
    }
  </style>
  <script>
    // 파일 선택 시 예상 소요시간 계산 (1MB 당 약 2초 산정)
    function updateEstimatedTime() {
      const fileInput = document.querySelector('input[type="file"]');
      const estimatedElem = document.getElementById('estimated-time');
      if(fileInput.files.length > 0) {
        const fileSize = fileInput.files[0].size; // bytes
        const sizeMB = fileSize / (1024 * 1024);
        const estimatedSec = Math.round(sizeMB * 2);
        estimatedElem.textContent = "예상 소요 시간: 약 " + estimatedSec + "초";
      } else {
        estimatedElem.textContent = "";
      }
    }
    // 폼 제출 시 진행률 게이지 표시
    function showProgress(e) {
      e.preventDefault();
      const fileInput = document.querySelector('input[type="file"]');
      if(fileInput.files.length === 0) return;
      const fileSize = fileInput.files[0].size;
      if(fileSize > 100 * 1024 * 1024) {
        alert("파일 크기는 최대 100MB까지 업로드 가능합니다.");
        return;
      }
      document.getElementById('upload-form').style.display = "none";
      document.getElementById('progress-container').style.display = "block";
      let progressFill = document.getElementById('progress-fill');
      let progress = 0;
      const interval = setInterval(function() {
        if(progress < 80) {
          progress += 1;
          progressFill.style.width = progress + "%";
        } else {
          clearInterval(interval);
        }
      }, 60);
      // 실제 폼 제출
      e.target.submit();
    }
  </script>
</head>
<body>
  <div class="container">
    <div id="upload-form">
      <!-- 왼쪽 패널: 업로드 폼 -->
      <div class="left-panel">
        <h1>PDF 업로드 및 분석</h1>
        <form method="post" enctype="multipart/form-data" class="input-section" onsubmit="showProgress(event)">
          <input type="file" name="pdf" accept="application/pdf" onchange="updateEstimatedTime()" required>
          <input type="hidden" name="analysis_type" id="analysis_type">
          <div class="controls">
            <button type="submit" onclick="document.getElementById('analysis_type').value='smart'">스마트 분석</button>
            <button type="submit" onclick="document.getElementById('analysis_type').value='speed'">스피드 분석</button>
          </div>
          <p id="estimated-time" style="font-size: 14px; color: #666;"></p>
        </form>
      </div>
      <!-- 오른쪽 패널: 분석 가이드 -->
      <div class="right-panel">
        <h2>분석 가이드</h2>
        <p>PDF 파일을 업로드한 후, 원하는 분석 유형을 선택하세요.</p>
        <ul>
          <li><strong>스마트 분석:</strong> 상세 분석 및 고급 기능 제공</li>
          <li><strong>스피드 분석:</strong> 빠른 결과 제공</li>
        </ul>
        <h3>주요 기능</h3>
        <div class="features">
          <div class="feature-card">
            <h3>내용 요약</h3>
            <p>문서의 핵심 내용을 자동으로 추출합니다.</p>
          </div>
          <div class="feature-card">
            <h3>텍스트 추출</h3>
            <p>PDF 내 텍스트를 쉽게 편집할 수 있도록 제공합니다.</p>
          </div>
          <div class="feature-card">
            <h3>통계 분석</h3>
            <p>문서 내 단어 빈도 및 통계 정보를 확인하세요.</p>
          </div>
        </div>
      </div>
    </div>
    <!-- 진행률 게이지 영역 (폼 제출 후 표시) -->
    <div id="progress-container" style="display:none; text-align:center;">
      <p>파일 업로드 및 분석 중입니다. 잠시만 기다려주세요.</p>
      <div id="progress-bar">
        <div id="progress-fill"></div>
      </div>
    </div>
  </div>
</body>
</html>
"""

# 분석 결과 페이지 템플릿
result_template = """
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <title>분석 결과</title>
  <style>
    body {
      font-family: 'Segoe UI', sans-serif;
      background-color: #f4f4f4;
      margin: 0;
      padding: 20px;
    }
    .container {
      background: white;
      padding: 25px;
      border-radius: 8px;
      box-shadow: 0px 0px 10px rgba(0,0,0,0.1);
      max-width: 1000px;
      margin: auto;
    }
    .result {
      margin-bottom: 20px;
      border: 1px solid #ccc;
      padding: 15px;
      border-radius: 5px;
      background-color: #fafafa;
    }
    .result h3 {
      margin: 0 0 10px 0;
      color: #333;
    }
    .result img {
      max-width: 300px;
      display: block;
      margin-bottom: 10px;
      border-radius: 5px;
    }
    .result p {
      font-size: 14px;
      color: #666;
      margin: 0;
      line-height: 1.5;
    }
    a {
      display: inline-block;
      margin-top: 20px;
      text-decoration: none;
      color: #007bff;
      font-weight: bold;
      transition: color 0.3s;
    }
    a:hover {
      color: #0056b3;
    }
    @media (max-width: 768px) {
      .container {
        width: 95%;
        padding: 15px;
      }
      .result img {
        max-width: 100%;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>분석 결과</h1>
    {% for page in results %}
      <div class="result">
        <h3>페이지 {{ page.page }}</h3>
        {% if page.image_data %}
          <img src="{{ page.image_data }}" alt="페이지 이미지">
        {% endif %}
        <p>{{ page.summary }}</p>
      </div>
    {% endfor %}
    <a href="/">다시 업로드</a>
  </div>
</body>
</html>
"""


def analyze_smart(pdf_path):
    logging.debug("스마트 분석 시작: %s", pdf_path)
    results = []
    try:
        doc = fitz.open(pdf_path)  # PDF 파일 열기
        logging.debug("PDF 페이지 수: %d", doc.page_count) 
        for i in range(doc.page_count):
            page = doc.load_page(i)  # 페이지 로드
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # dpi 업스케일링 적용
            image_bytes = pix.tobytes("jpeg")  # 이미지 바이트 변환
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")  # base64 인코딩

            # Gemini API 호출: types.Part를 사용해 이미지 데이터를 전달함
            logging.debug("페이지 %d: Gemini API 호출 시작", i+1)
            try:
                image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
                response = client.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents=["이 이미지의 내용을 요약해줘.", image_part]
                )

                summary = response.text if response else "요약 실패"
                logging.debug("페이지 %d: 요약 완료", i+1)
            except Exception as e:
                logging.error("Gemini API 호출 오류: %s", str(e))
                summary = f"요약 실패: {str(e)}"

            results.append({
                'page': i+1,
                'summary': summary,
                'image_data': f"data:image/jpeg;base64,{image_base64}"
            })
    except Exception as e:
        logging.error("PDF 처리 오류: %s", str(e))
        return {"error": str(e)}
    finally:
        if 'doc' in locals():
            doc.close()
    return results



def analyze_speed(pdf_path):
    logging.debug("스피드 분석 시작: %s", pdf_path)
    results = []
    try:
        doc = fitz.open(pdf_path)
        logging.debug("PDF 페이지 수: %d", doc.page_count)
        for i in range(doc.page_count):
            page = doc.load_page(i)
            text = page.get_text("text")
            logging.debug("페이지 %d: 추출 텍스트 (최대 100자): %s", i+1, text[:100])
            
            response = client.models.generate_content(
              model="gemini-2.0-flash", 
              contents=  "다음 텍스트를 요약해줘:\n" + text)
            summary = response.text if response else "요약 실패"
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            image_bytes = pix.tobytes("jpeg")
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            results.append({
                "page": i+1,
                "summary": summary,
                "image_data": f"data:image/jpeg;base64,{image_base64}"
            })
            logging.debug("페이지 %d: 스피드 분석 완료", i+1)
    except Exception as e:
        logging.exception("스피드 분석 오류:")
    finally:
        if 'doc' in locals():
            doc.close()
    return results

@app.errorhandler(413)
def too_large(e):
    return "파일 크기는 최대 100MB까지 업로드 가능합니다.", 413

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        logging.debug("POST 요청 수신됨")
        if "pdf" not in request.files:
            logging.error("파일 업로드 없음")
            return "PDF 파일이 업로드되지 않았습니다.", 400
        pdf_file = request.files["pdf"]
        if pdf_file.filename == "":
            logging.error("파일 미선택")
            return "파일을 선택해 주세요.", 400
        analysis_type = request.form.get("analysis_type")
        if analysis_type not in ["smart", "speed"]:
            logging.error("잘못된 분석 유형: %s", analysis_type)
            return "유효하지 않은 분석 유형입니다.", 400
        
        pdf_filename = str(uuid.uuid4()) + ".pdf"
        pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], pdf_filename)
        pdf_file.save(pdf_path)
        logging.debug("PDF 저장됨: %s", pdf_path)
        
        if analysis_type == "smart":
            results = analyze_smart(pdf_path)
        else:
            results = analyze_speed(pdf_path)
        
        # 분석 완료 후 즉시 파일 삭제
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
            logging.debug("PDF 삭제됨: %s", pdf_path)
        
        return render_template_string(result_template, results=results)
    return render_template_string(upload_template)

if __name__ == "__main__":
    logging.debug("서버 시작")
    app.run(debug=True)
