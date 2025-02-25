// 사이드바 토글 함수
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    sidebar.classList.toggle('hidden');
    mainContent.classList.toggle('full');
  }
  
  // 프로젝트 전환 함수
  function showProject(projectId, event) {
    // 모든 프로젝트 항목에서 active 클래스 제거
    document.querySelectorAll('.project-item').forEach(item => {
      item.classList.remove('active');
    });
  
    // 클릭된 항목에 active 클래스 추가
    event.target.classList.add('active');
  
    // iframe 소스 업데이트
    const projectFrame = document.getElementById('projectFrame');
  
    switch (projectId) {
      case 'assignmenthelper':
        projectFrame.src = 'assignmenthelper.html';
        break;
      case 'ppt':
        projectFrame.src = 'ppt.html';
        break;
      case 'project3':
        projectFrame.src = 'project3.html';
        break;
      case 'project4':
        projectFrame.src = 'project4.html';
        break;
    }
  }
  