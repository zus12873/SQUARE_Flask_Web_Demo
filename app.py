import os,platform
from flask import Flask, Response, request, jsonify, render_template, redirect, url_for, flash
import subprocess
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_for_testing')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db = SQLAlchemy(app)

# 初始化登录管理器
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# 用户模型
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 创建所有数据库表
with app.app_context():
    db.create_all()

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('登录失败，请检查用户名和密码')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # 检查用户名是否已存在
        user = User.query.filter_by(username=username).first()
        if user:
            flash('用户名已存在')
            return render_template('register.html')
        
        # 检查密码是否匹配
        if password != confirm_password:
            flash('两次输入的密码不匹配')
            return render_template('register.html')
        
        # 创建新用户
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('注册成功，请登录')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/run_java_algorithm_stream', methods=['GET', 'POST'])
@login_required
def run_java_algorithm_stream():
    # 获取前端传入的参数（POST 的 JSON数据；GET时使用默认值）
    if request.method == 'POST' and request.is_json:
        data = request.get_json()
    else:
        data = {}
    # 获取参数
    estimation = data.get('estimation', 'supervised')
    dataset = data.get('dataset', 'HCB')
    nfold = data.get('nfold', 10)
    method=data.get('method', 'All') #Majority,Raykar,Bayes,Zen

    # 根据监督方式构造配置文件及保存目录
    if estimation == "supervised":
        if nfold > 0:
            supervision_percentage = 100 / nfold
        else:
            supervision_percentage = 100 - (100 / abs(nfold))
        folder_name = "nFoldSet_" + str(supervision_percentage)
        saveDir = f"./nFoldSets/{dataset}/{method}/{estimation}/{folder_name}/"
        text_content = (
            f"--responses ./data/{dataset}/responses.txt "
            f"--category ./data/{dataset}/categories.txt "
            f"--groundTruth ./data/{dataset}/groundTruth.txt "
            f"--method {method} --nfold -{nfold} "
            f"--estimation {estimation} --saveDir {saveDir}"
        )
        text_file_name = f"genNFold{nfold}_{dataset}_{estimation}_CLA.txt"
    else:
        saveDir = f"./nFoldSets/{dataset}/{method}/{estimation}/"
        text_content = (
            f"--responses ./data/{dataset}/responses.txt "
            f"--category ./data/{dataset}/categories.txt "
            f"--groundTruth ./data/{dataset}/groundTruth.txt "
            f"--method {method} --estimation {estimation} --saveDir {saveDir}"
            
        )
        text_file_name = f"gen_{dataset}_{estimation}_CLA.txt"

    # 将配置内容写入文件
    with open(text_file_name, "w", encoding="utf-8") as file:
        file.write(text_content)
    print(f"内容已写入 {text_file_name}")

    # # 构造 Java 命令，注意根据你的 jar 路径调整
    # cmd = [
    #     'java',
    #     '-Xmx2048m',
    #     '-ea',
    #     '-cp',
    #     './algorithm/jblas-1.2.4.jar:./algorithm/log4j-core-2.4.jar:./algorithm/log4j-api-2.4.jar:./algorithm/qa-2.0.jar',
    #     'org.square.qa.analysis.Main',
    #     '--file',
    #     text_file_name
    # ]
    sep = ';' if platform.system() == 'Windows' else ':'

    classpath = sep.join([
        'algorithm/jblas-1.2.4.jar',
        'algorithm/log4j-core-2.4.jar',
        'algorithm/log4j-api-2.4.jar',
        'algorithm/qa-2.0.jar'
    ])

    cmd = [
        'java',
        '-Xmx2048m',
        '-ea',
        '-cp',
        classpath,
        'org.square.qa.analysis.Main',
        '--file',
        text_file_name
    ]
    
    def generate():
        # 启动 Java 进程，并实时输出日志
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in iter(process.stdout.readline, ''):
            yield f"data: {line}\n\n"
        process.stdout.close()
        return_code = process.wait()
        yield f"data: Process finished with return code {return_code}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')


@app.route('/get_evaluation_results', methods=['POST'])
@login_required
def get_evaluation_results():
    """
    该接口根据前端传入的参数读取结果文件夹下所有 .txt 文件，
    提取文件名中的评分方法，并解析文件内容，将数据打包成 JSON 返回给前端。
    """
    data = request.get_json() or {}
    estimation = data.get('estimation', 'supervised')
    dataset = data.get('dataset', 'HCB')
    nfold = data.get('nfold', 10)
    method = data.get('method', 'All')
    print(f"estimation: {estimation}, dataset: {dataset}, nfold: {nfold}, method: {method}")
    # 构造结果文件夹路径
    if estimation == "supervised":
        if nfold > 0:
            supervision_percentage = 100 / nfold
        else:
            supervision_percentage = 100 - (100 / abs(nfold))
        results_folder = f"./nFoldSets/{dataset}/{method}/{estimation}/nFoldSet_{supervision_percentage}/results/nFold"
        print(f"results_folder: {results_folder}")
    else:
        results_folder = f"./nFoldSets/{dataset}/{method}/{estimation}/results/nFold"
        print(f"results_folder: {results_folder}")
    
    results = []
    if os.path.exists(results_folder):
        for filename in os.listdir(results_folder):
            if filename.endswith('.txt'):
                # 提取文件名中评分方法部分（例如 "Majority_unsupervised_results.txt" 提取 "Majority"）
                method = filename.split('_')[0]
                file_path = os.path.join(results_folder, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = [line.strip() for line in f if line.strip()]
                        # 分别获取以 "%" 开头的 header 行和其它数据行
                        headers = [line for line in lines if line.startswith('%')]
                        data_lines = [line for line in lines if not line.startswith('%')]
                    results.append({
                        "method": method,
                        "filename": filename,
                        "headers": headers,
                        "data": data_lines
                    })
                except Exception as e:
                    results.append({
                        "method": method,
                        "filename": filename,
                        "error": str(e)
                    })
        return jsonify({"results": results})
    else:
        return jsonify({"error": f"Results folder {results_folder} does not exist"}), 404

if __name__ == '__main__':
    app.run(debug=True)
