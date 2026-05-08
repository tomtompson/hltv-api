import base64
token_real = "1418970711"
token_ofuscado = base64.b64encode(token_real.encode()).decode()
print(token_ofuscado)
# Saída: NzE1MDU5MTU4MDpBQUhrZmdoSktMbU5PUFFSc3RVVldYeXoxMjM0NTY3ODkw