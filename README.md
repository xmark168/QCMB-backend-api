.\.venv\Scripts\Activate.ps1

alembic revision --autogenerate -m "update role enum in user table"
alembic upgrade head


fastapi dev app/main.py

không commit tk mk db lên

model -> schemas -> /endpoint -> api.py


FE
apiService -> model -> request -> response


#91C8E4 -> xanh nhạt
#749BC2 -> xanh trung bình
#4682A9 -> xanh đậm