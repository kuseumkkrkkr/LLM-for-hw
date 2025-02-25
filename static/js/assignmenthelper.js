document.addEventListener('DOMContentLoaded', () => {
    // 탭 전환 기능
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            document.getElementById(tab.dataset.tab).classList.add('active');
        });
    });

    // 단어 수 및 글자 수 카운트 기능
    const textarea = document.getElementById('inputText');
    const wordCountSpan = document.getElementById('wordCount');
    const charCountSpan = document.getElementById('charCount'); //글자수 보는건데 굳이 필요업음

    textarea.addEventListener('input', () => {
        const text = textarea.value;
        const words = text.trim().split(/\s+/);
        const wordCount = words[0] === '' ? 0 : words.length;
        const charCount = text.length;

        wordCountSpan.textContent = wordCount;
        charCountSpan.textContent = charCount;
    });

    // 분석 시작 버튼 이벤트 ===============================================
    document.getElementById('analyzeBtn').addEventListener('click', () => {
        const text = document.getElementById('inputText').value;
        const style = document.getElementById('styleSelect').value;
        
        // 체크박스를 통해 선택된 톤 값 가져오기 ===============================================
        const selectedTones = [];
        document.querySelectorAll('input[type="checkbox"]:checked').forEach(checkbox => {
            selectedTones.push(checkbox.value);
        }); // 아니 어떤 또라이가 그걸 줄줄이 해놓노.... 

        // 텍스트 0개 경고 ===============================================
        if (!text) {
            alert('텍스트를 입력해주세요.');
            return;
        }

        // 텍스트 분석 함수 호출
        analyzeText(text, style, selectedTones);// 텍스트, 스타일, 체크박스
        checkGrammar(text); // 문법함수 
    });

    // 텍스트 분석 함수 ===============================================
    function analyzeText(text, style, tones) {
        // tones 배열을 콤마로 구분된 문자열로 변환하여 전달

        console.log('전송 전 데이터:', {
            text: text,
            style: style,
            tones: tones
        });

        const tonesParam = encodeURIComponent(tones.join(','));
        fetch(`/getchat?question=${encodeURIComponent(text)}&selected_tones=${tonesParam}&style=${encodeURIComponent(style)}`)
            .then(response => response.json())
            .then(data => {
                // 텍스트 요약 (style 값은 여기 영향줌)
                document.getElementById('summary').textContent = data.summary.text;
                // 수정 제안 (Tones 값은 여기 영향줌)
                document.getElementById('suggestions').textContent = data.improvement_suggestions.suggestions.join('\n');
                // 문장 구조 분석
                document.getElementById('structure').textContent = data.structure_analysis.description;
            })
            .catch(error => {
                console.error('Error:', error);
            });
        }
    })
