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
