FROM python:3.9.13

# 환경 변수 설정
ENV PYTHONUNBUFFERED 1

# 작업 디렉토리 설정
WORKDIR /app/

# 의존성 파일 복사 및 설치
COPY requirements.txt /app/
RUN grep -vE 'pywin32|pypiwin32|coverage|pipdeptree|twisted-iocpsupport|Flask|Werkzeug' requirements.txt > requirements_docker.txt
RUN pip install --no-cache-dir -r requirements_docker.txt

# 나머지 프로젝트 파일 복사
COPY . /app/

# 8000번 포트 사용
EXPOSE 8000

# Django 애플리케이션 실행
CMD ["gunicorn", "manda_project.wsgi:application", "--bind", "0.0.0.0:8000"]