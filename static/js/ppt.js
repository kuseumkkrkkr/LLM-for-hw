// 파일 선택 버튼 클릭 시 숨겨진 파일 입력을 실행
document.getElementById('fileSelectBtn').addEventListener('click', function() {
    document.getElementById('fileInput').click();
  });
  
  document.getElementById('fileInput').addEventListener('change', function (event) {
    const file = event.target.files[0];
    if (file) {
      const allowedExtensions = ['pdf', 'jpg', 'jpeg', 'png'];
      const fileName = file.name.toLowerCase();
      const fileExtension = fileName.split('.').pop();
      if (!allowedExtensions.includes(fileExtension)) {
        alert("허용되지 않는 파일 형식입니다. pdf, jpg, jpeg, png 만 허용됩니다.");
        return;
      }
      previewFile(file);
    }
  });
  
  function previewFile(file) {
    const viewer = document.getElementById('viewer');
    viewer.innerHTML = ""; // 기존 내용 삭제
    const fileExtension = file.name.toLowerCase().split('.').pop();
    if (fileExtension === 'pdf') {
      const embed = document.createElement('embed');
      embed.src = URL.createObjectURL(file);
      embed.type = 'application/pdf';
      embed.width = '100%';
      embed.height = '500px';
      viewer.appendChild(embed);
    } else {
      const img = document.createElement('img');
      img.src = URL.createObjectURL(file);
      img.style.maxWidth = '100%';
      img.style.maxHeight = '500px';
      viewer.appendChild(img);
    }
  }
  
  document.getElementById('uploadBtn').addEventListener('click', function() {
    alert("업로드 버튼 클릭됨");
  });
  
  document.getElementById('analyzeBtn').addEventListener('click', function() {
    alert("분석 버튼 클릭됨");
  });
  
  // 파일 삭제 버튼 클릭 시 파일 미리보기 초기화 및 파일 입력 값 리셋
  document.getElementById('fileDeleteBtn').addEventListener('click', function() {
    document.getElementById('viewer').innerHTML = "파일 미리보기가 여기에 표시됩니다.";
    document.getElementById('fileInput').value = "";
  });