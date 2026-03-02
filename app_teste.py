from flask import Flask

# Cria o aplicativo web
app = Flask(__name__)

# Cria a página principal (a "raiz" do site)
@app.route("/")
def pagina_inicial():
    return "<h1>Bem-vinda ao sistema da Sabor do Amor Churvete! 🍦</h1>"

# Roda o servidor web
if __name__ == "__main__":
    app.run(debug=True)