.\Scripts\Active.ps1    

alembic revision --autogenerate -m "update role enum in user table"
alembic upgrade head

fastapi dev app/main.py

không commit tk mk db lên

model -> schemas -> /endpoint -> api.py