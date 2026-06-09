from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    # 핑키 카메라 서버(5000)와 안 겹치게 8080 사용
    app.run(host='0.0.0.0', port=8080, debug=True, use_reloader=False)