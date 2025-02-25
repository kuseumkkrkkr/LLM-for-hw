from flask import Flask, render_template, Response, request, jsonify
from google import genai #AI 호출
from pydantic import BaseModel #baseline 모델 활용(최적화화)
from typing import List
import json

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
#API 키 유출하면 죽는다
client = genai.Client(api_key="AIzaSyD_9V2Yk8nflCNbIi7UIaFaulDv3OO14_s")
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


#문법 검사 함수=================================================


# 밑에 이부분 없애면 아예 Run 실행이 안됨됨
if __name__ == '__main__':
    app.run(debug=True)


#https://cw202080.pythonanywhere.com/
#웹 배포중