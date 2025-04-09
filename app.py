from flask import Flask, render_template, Response, request, jsonify, render_template_string
from google import genai #AI 호출
from pydantic import BaseModel #baseline 모델 활용(최적화화)
from typing import List
import json 
#여기까지 텍스트 분석용 라이브러리리 (저기 위에 render_template_string 라이브러리 제외외)

#여기는 pdf 분석용 라이브러리리
import os
import uuid #고유 식별자 없으면 인터넷 느린 그 순간 남의 파일 분석당함
#다만 주의를 좀 해줘야 하는 부분이 지금 상태로는 최대 10개 소켓만 있는상태임
#2025-02-26 10:15:29,696 - INFO - AFC is enabled with max remote calls: 10 <-실행하면 이렇게 뜰거임

from google.genai import types
import base64
import logging #디버그 코드 (나중에 빼고 난 다음 다른것도 없애애)
import fitz #pdf 파일 분석용
#=================================================
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
#just for debug 나중에 제거거

#=================================================
#API 키 유출하면 죽는다
client = genai.Client(api_key="APIKEY")
#=================================================
#API키 env 파일로 관리해야하는데 quick build 라서 잠시놔둠



#지정함수 패키지 (pdf분석용)========================
#스마트 분석 : pdf OCR 을 gemini api가 하는 부분으로 입출력에 상당한 시간이 소모됨
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

                    #================================================= 프롬포트 작성
                    contents=["이 이미지의 내용을 반드시 한글로 요약해줘.", image_part]
                    #================================================= 
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
#=================================================
#스피드 분석 : 이미지를 미리 파이썬이 OCR을 하고 텍스트 입출력으로만 하는 방식으로 종전보다 속도가 빠름
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
            #여기까지 텍스트 추출
            
            response = client.models.generate_content(
              model="gemini-2.0-flash", #여기서는 텍스트만 결국 들어가서 2.0모델이 더 좋음음
              
              #================================================= 프롬포트 작성
              contents=  "다음 텍스트를 요약해줘:\n" + text) 
              #================================================= 
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
#================================================= 
#여기까지 분석함수 박스인데 제발 부탁하는게 소켓이 최대 10개까지만 들어가져
#나중에 호출 제한횟수를 풀어야 분석이 가능할것같고, 10개 초과 시 분석 실패로 넘어가는게 아니라
#바로 404가 나버리니까 그건 차후에 구현할 일일

#이거 제발 없애지마================================
app = Flask(__name__)
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/assignmenthelper')
def assignmenthelper():
    return render_template('assignmenthelper.html')

@app.route('/ppt')
def ppt():
    return render_template('ppt.html')

#왜 pptresult는 안하냐 하는데 그거 라우팅 연속 두번하면 메모리 튕김
#=================================================
@app.errorhandler(413)
def too_large(e):
    return "파일 크기는 최대 100MB까지 업로드 가능합니다.", 413 #오류표출용용
#=================================================
#업로드할 파일을 보는 부분임 로직 달라지면 안먹히니까 함부로 수정하지마
app.config["UPLOAD_FOLDER"] = "uploads"
# 100MB 이상 업로드 불가능한 코드 100 × 1024 × 1024 = 104,857,600 Bytes
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
#=================================================


#================================================= 프롬포트를 구성하는 클래스
#이 부분을 확장하여 다른 응답도 받아볼 수 있음
#이상한거 쳐넣지마 제발
#=================================================
class Summary(BaseModel):
    text: str #요약

class ImprovementSuggestions(BaseModel):
    suggestions: List[str] #개선요청사항

class StructureAnalysis(BaseModel):
    description: str  # 문장 구조 분석을 자연어 문장으로 제공

class TextAnalysis(BaseModel): #없어지면 안되는 코드 이거 죽이면 안됨
    summary: Summary
    improvement_suggestions: ImprovementSuggestions
    structure_analysis: StructureAnalysis
#=================================================


#=================================================
# 수정가능한 또다른 부분, 아래쪽애 프롬포트 구성만 바꾸셈
# 다른 코드 건드리면 작동안함
#=================================================
#Gemini API 호출&질의응답 처리구간
@app.route('/getchat')
def getchat():
    print("api 에 접근함")
    question = request.args.get('question', '').strip()
    style = request.args.get('style', '').strip()
    if not question:
        return jsonify({"error": "No text provided"}), 400
#================================================= Get 요청
#================================================= 체크박스에서 프롬포트를 불러와 로딩하는 과정

    selected_tones_str = request.args.get('selected_tones', '').strip()
    print(f"Received selected_tones: {selected_tones_str}")
    selected_tones = list(set(selected_tones_str.split(','))) if selected_tones_str else []
    print(f"Selected tones: {selected_tones}")

#메인 프롬포트 라인 ================================
#프롬포트가 추가되는 과정 : 체크박스가 2개 체크되어있다 그러면 ,상징 및 비유 사용을 고려해야 합니다 + 문법 점검이 필요합니다 이렇게 추가됨
#프롬포트를 수정해서 강화할 수 있음
#================================================= 이건 톤 프롬포트
    tone_prompts = {
        'formal': ' - 주제 명료화가 필요합니다.',
        'semiformal': ' - 목적 정의가 부족합니다.',
        'depth': ' - 정보의 깊이가 부족합니다.',
        'flow': ' - 구성 및 흐름이 자연스럽지 않습니다.',
        'tone': ' - 문체 및 어조를 개선해야 합니다.',
        'symbolism': ' - 상징 및 비유 사용을 고려해야 합니다.',
        'argument': ' - 주장 및 근거를 강화해야 합니다.',
        'grammar': ' - 문법 점검이 필요합니다.',
        'conclusion': ' - 결론을 강하게 만들어야 합니다.'
    } #아니 html에 있는 파라미터는 하나도 안바꿔놔서 키워드가 안먹힘.. 해결완료 제로해진다?
    #value 값 조심부탁
#================================================= 이건 요약부 프롬포트

    summary_prompts = {
        'academic': ' - 요약에서 핵심적인 이론과 데이터를 명확하게 제시하세요.',
        'logical': ' - 요약에서 주장을 논리적으로 연결하고 근거를 제시하세요.',
        'casual': ' - 요약에서 간결하고 쉽게 이해할 수 있는 언어를 사용하세요.',
        'professional': ' - 요약에서 전문적인 용어를 사용하고 정확성을 유지하세요.',
        'creative': ' - 요약에서 창의적인 관점을 강조하고 색다른 접근을 보여주세요.'
    }

    summary_prompts = summary_prompts.get(style, ' - 기본적인 요약을 제공하세요.') #style 변수 없애면 아무것도 안들어와짐

#=================================================



#프롬포트 파싱 라인 ================================
    additional_suggestions = [] #이 배열 안으로 프롬포트가 합쳐져서 들어가고 있음
    for tone in selected_tones:
        if tone in tone_prompts:
            additional_suggestions.append(tone_prompts[tone]) #배열 append 함수
    additional_prompt = "\n추가 개선사항:\n" + "\n".join(additional_suggestions) if additional_suggestions else ""
    print(additional_prompt)
#이 바로 위에가 프롬포트 덧셈하는 과정이긴함
#=================================================


#================================================= 프롬포트 구성 (대화형 프롬포트 이 부분 수정)
    prompt = f"""
    Analyze the following text and provide the summary, improvement suggestions, and structure analysis in JSON format.
    The structure analysis should be in natural language, describing paragraph count, sentence count, and types of sentences in a concise way:
    Use Korean language:
    "{question}"
    {additional_prompt}
    {summary_prompts}
    """

    print(f"Generated prompt: {summary_prompts}{additional_prompt}")    #디버그 코드
#=================================================
# 여기 이 프롬포트가 지금 모델에 들어가는 프롬포트임
# 저거 보면 JSON 포맷으로 제공하라 되어있는데 저 포맷으로 안나오게 되면 클래스 안에 다른게 들어가게되고 그때부터 꼬임
# 두번째 문장이 이제 문단 분석이라고 보면 됨
# 수정요령 : 클래스 + JSON 포맷으로 시키기, 아랫문장에 클래스의 상세 기능동작을 묘사한다 생각하면 편함
# Question 이거 뽑아버리면 지시가 안들어간다는 이야기임 뽑으면 안됨됨
#================================================= 모델 호출
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash", #모델명
            contents=prompt, #프롬포트
            config={
                "response_mime_type": "application/json", #응답형식(현재는json)
                "response_schema": TextAnalysis, #클래스명명
            },
        )
# 모델 핵심 파라미터=================================
# 모델 종류 수정가능
# 그 밑에꺼가 프롬포트 구성을 보내는부분임, 수정금지지
#================================================================================
# 응답에서 parsed 속성으로 결과 추출 및 디코딩 처리 (이거 죽이면 우리 한글이 아니라 바이트코드로 나와 ㅅㅂ)
        if isinstance(response.parsed, bytes):
            decoded_response = response.parsed.decode('utf-8')
            analysis_result = json.loads(decoded_response) #UTF-8 인코딩, 바이트코드로 처리중임 까보면면
        else:
            analysis_result = response.parsed.dict()

        json_str = json.dumps(analysis_result, ensure_ascii=False)
        return Response(json_str, mimetype='application/json')

    except Exception as e:
        print(f"Error occurred: {e}")
        error_json = json.dumps({"error": "Failed to get a valid response from the API"}, ensure_ascii=False)
        return Response(error_json, status=500, mimetype='application/json')
#================================================= 코드끝


#================================================= 프리젠테이션 프로세스 처리 
#여긴 디버그 코드가 많아서 굳이 주석처리 안함함
@app.route("/pptresult", methods=["GET", "POST"])
def pptresult():
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
            logging.debug("PDF 삭제됨: %s", pdf_path) #없애지마라
        
        return render_template('pptresult.html', results=results)
    return render_template('ppt.html')
#=================================================

#문법 검사 함수=================================================
#호출 안할듯듯

# 밑에 이부분 없애면 아예 Run 실행이 안됨됨
if __name__ == '__main__':
    logging.debug("서버 실행 시작")
    app.run(debug=True)


#https://cw202080.pythonanywhere.com/
#웹 배포중
